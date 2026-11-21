"""Worker Capacity Calibration Service.

Executes stepped load generation to measure CPU, RAM, throughput, latency percentiles,
detect saturation thresholds, and determine verified sustainable operating capacity.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psutil
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ViewStormException
from app.core.logging import logger
from app.models.worker_calibration import WorkerCalibration
from app.models.worker_node import LoadGeneratorNode
from app.schemas.run import SimulationRunCreate
from app.schemas.worker_calibration import (
    CalibrationStepResult,
    WorkerCalibrationRequest,
    WorkerCalibrationResponse,
)
from app.services.locust_runner_service import locust_runner_service
from app.services.simulation_service import simulation_service
from app.services.stats_service import stats_service


class WorkerCalibrationService:
    """Orchestrates stepped capacity calibration for load generator workers."""

    async def calibrate_worker(
        self,
        worker_node_id: Optional[str],
        request: WorkerCalibrationRequest,
        db: AsyncSession,
    ) -> WorkerCalibrationResponse:
        """Run progressive calibration steps to measure worker limits."""
        node: Optional[LoadGeneratorNode] = None
        worker_identifier = "local_node"
        cpu_cores = psutil.cpu_count(logical=True) or 1
        total_mem_mb = round(psutil.virtual_memory().total / (1024 * 1024), 2)

        if worker_node_id:
            stmt = select(LoadGeneratorNode).where(LoadGeneratorNode.id == worker_node_id)
            res = await db.execute(stmt)
            node = res.scalars().first()
            if node:
                worker_identifier = node.worker_identifier
                cpu_cores = node.cpu_cores
                total_mem_mb = round(node.total_memory_bytes / (1024 * 1024), 2)

        logger.info(
            "Starting capacity calibration for worker '%s' (cores=%d, mem=%.1fMB) over steps: %s",
            worker_identifier,
            cpu_cores,
            total_mem_mb,
            request.steps,
        )

        steps_tested: List[Dict[str, Any]] = []
        max_stable_users = 0
        max_stable_rps = 0.0
        saturation_bottleneck: Optional[str] = None

        for step_users in sorted(request.steps):
            logger.info("Executing calibration step: %d virtual users...", step_users)
            step_result = await self._execute_step(
                users=step_users,
                duration=request.step_duration_seconds,
                target_env=request.target_environment,
                db=db,
            )

            # Evaluate saturation thresholds
            is_saturated = False
            reasons = []

            if step_result.worker_cpu_pct >= request.max_cpu_pct_threshold:
                is_saturated = True
                reasons.append(f"CPU utilization ({step_result.worker_cpu_pct:.1f}%) exceeded {request.max_cpu_pct_threshold:.1f}%")

            if step_result.error_rate_pct >= request.max_error_rate_threshold:
                is_saturated = True
                reasons.append(f"Error rate ({step_result.error_rate_pct:.2f}%) exceeded {request.max_error_rate_threshold:.1f}%")

            if step_result.p95_latency_ms >= request.max_p95_latency_threshold_ms:
                is_saturated = True
                reasons.append(f"P95 latency ({step_result.p95_latency_ms:.1f}ms) exceeded {request.max_p95_latency_threshold_ms:.1f}ms")

            if is_saturated:
                step_result.is_saturated = True
                step_result.saturation_reason = "; ".join(reasons)
                saturation_bottleneck = step_result.saturation_reason
                steps_tested.append(step_result.model_dump())
                logger.warning(
                    "Worker saturation detected at %d users: %s. Halting higher calibration steps.",
                    step_users,
                    step_result.saturation_reason,
                )
                break
            else:
                max_stable_users = step_users
                max_stable_rps = step_result.requests_per_second
                steps_tested.append(step_result.model_dump())

        # Sustainable operating capacity: 75% of max verified stable users (minimum 10)
        recommended = max(10, int(max_stable_users * 0.75)) if max_stable_users > 0 else 10

        # Update worker node capacity if node exists
        if node:
            node.capacity = recommended
            await db.commit()
            logger.info("Updated worker node '%s' capacity to %d", node.worker_name, recommended)

        # Persist calibration record
        calibration = WorkerCalibration(
            worker_node_id=node.id if node else None,
            worker_identifier=worker_identifier,
            cpu_cores=cpu_cores,
            total_memory_mb=total_mem_mb,
            steps_tested=steps_tested,
            max_stable_users=max_stable_users,
            max_stable_rps=max_stable_rps,
            saturation_bottleneck=saturation_bottleneck,
            recommended_capacity=recommended,
            notes=request.notes,
        )
        db.add(calibration)
        await db.commit()
        await db.refresh(calibration)

        logger.info(
            "Capacity calibration completed for '%s'. Max stable: %d users (%.1f RPS). Recommended: %d users.",
            worker_identifier,
            max_stable_users,
            max_stable_rps,
            recommended,
        )
        return WorkerCalibrationResponse.model_validate(calibration)

    async def _execute_step(
        self,
        users: int,
        duration: int,
        target_env: str,
        db: AsyncSession,
    ) -> CalibrationStepResult:
        """Run a single calibration step simulation and sample telemetry."""
        now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
        spawn_rate = max(1.0, float(users / 5.0))

        run_payload = SimulationRunCreate(
            name=f"Calibration-Step-{users}u-{now_str}",
            target_environment=target_env,
            execution_mode="local",
            virtual_users=users,
            spawn_rate=spawn_rate,
            duration_seconds=duration,
        )
        run = await simulation_service.create_run(run_payload, db=db)
        await locust_runner_service.start_runner(run, db=db)

        # Sample system metrics during execution
        cpu_samples: List[float] = []
        ram_samples: List[float] = []

        for _ in range(duration):
            await asyncio.sleep(1.0)
            cpu_samples.append(psutil.cpu_percent(interval=None))
            ram_samples.append(psutil.virtual_memory().percent)
            if not locust_runner_service.is_runner_active(run.id):
                break

        # Stop runner gracefully if still active
        if locust_runner_service.is_runner_active(run.id):
            await locust_runner_service.stop_runner(run.id)

        # Collect report
        await asyncio.sleep(1.5)
        report = await stats_service.generate_report(run.id, db=db)

        total_reqs = report.total_http_requests or report.total_submissions
        failed_reqs = report.failed_http_requests or report.rejected_events
        error_rate = (failed_reqs / total_reqs * 100.0) if total_reqs > 0 else 0.0
        rps = report.requests_per_second or report.average_throughput_eps

        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else psutil.cpu_percent()
        avg_ram_pct = sum(ram_samples) / len(ram_samples) if ram_samples else psutil.virtual_memory().percent
        ram_mb = round((psutil.virtual_memory().total - psutil.virtual_memory().available) / (1024 * 1024), 2)

        return CalibrationStepResult(
            users=users,
            duration_seconds=duration,
            requests_per_second=round(rps, 2),
            total_requests=total_reqs,
            accepted_events=report.accepted_events,
            error_rate_pct=round(error_rate, 2),
            avg_latency_ms=round(report.avg_latency_ms, 2),
            p50_latency_ms=round(report.p50_latency_ms, 2),
            p95_latency_ms=round(report.p95_latency_ms, 2),
            p99_latency_ms=round(report.p99_latency_ms, 2),
            worker_cpu_pct=round(avg_cpu, 2),
            worker_ram_mb=ram_mb,
            worker_ram_pct=round(avg_ram_pct, 2),
            is_saturated=False,
            saturation_reason=None,
        )

    async def list_calibrations(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkerCalibrationResponse]:
        """List historical worker calibration experiments."""
        stmt = select(WorkerCalibration).order_by(desc(WorkerCalibration.created_at)).offset(offset).limit(limit)
        res = await db.execute(stmt)
        return [WorkerCalibrationResponse.model_validate(c) for c in res.scalars().all()]

    async def get_latest_calibration(
        self,
        worker_node_id: str,
        db: AsyncSession,
    ) -> Optional[WorkerCalibrationResponse]:
        """Retrieve most recent calibration outcome for a worker node."""
        stmt = (
            select(WorkerCalibration)
            .where(WorkerCalibration.worker_node_id == worker_node_id)
            .order_by(desc(WorkerCalibration.created_at))
            .limit(1)
        )
        res = await db.execute(stmt)
        cal = res.scalars().first()
        return WorkerCalibrationResponse.model_validate(cal) if cal else None


worker_calibration_service = WorkerCalibrationService()
