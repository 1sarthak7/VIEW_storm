"""Controlled Large-Scale Benchmarking Service with SLA Guardrails and Reproducibility Metadata."""

import asyncio
import hashlib
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psutil
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import (
    BenchmarkProfileNotFoundError,
    EmergencyStopActiveError,
    SimulationNotFoundError,
    ViewStormException,
)
from app.core.logging import logger
from app.database.redis import redis_client
from app.database.session import AsyncSessionLocal
from app.models.benchmark import BenchmarkResult
from app.models.simulation import SimulationRun
from app.schemas.benchmark import (
    BenchmarkComparisonResponse,
    BenchmarkProfile,
    BenchmarkResultResponse,
    BenchmarkRunRequest,
    BenchmarkStage,
    PreflightCheckResponse,
    ThresholdEvaluation,
)
from app.schemas.run import SimulationRunCreate
from app.services.distributed_runner_service import distributed_runner_service
from app.services.emergency_service import emergency_service
from app.services.locust_runner_service import locust_runner_service
from app.services.simulation_service import simulation_service
from app.services.stats_service import stats_service
from app.services.worker_registry_service import worker_registry_service

# The 9 Standardized Milestone 7 Benchmark Profiles
PREDEFINED_PROFILES: Dict[str, BenchmarkProfile] = {
    "smoke": BenchmarkProfile(
        name="smoke",
        description="Profile 1 — Sanity check to verify all pipeline components and baseline connectivity.",
        virtual_users=10,
        spawn_rate=2.0,
        duration_seconds=30,
        recommended_mode="local",
        max_error_rate_pct=1.0,
        max_p95_latency_ms=500.0,
        requires_explicit_approval=False,
        min_worker_nodes=1,
        stages=[
            BenchmarkStage(stage_number=1, name="Warmup", target_users=5, duration_seconds=10, is_stabilization=False),
            BenchmarkStage(stage_number=2, name="Full Load", target_users=10, duration_seconds=20, is_stabilization=True),
        ],
    ),
    "baseline": BenchmarkProfile(
        name="baseline",
        description="Profile 2 — Standard baseline verification under typical operational single-node load.",
        virtual_users=100,
        spawn_rate=10.0,
        duration_seconds=60,
        recommended_mode="local",
        max_error_rate_pct=2.0,
        max_p95_latency_ms=1000.0,
        requires_explicit_approval=False,
        min_worker_nodes=1,
        stages=[
            BenchmarkStage(stage_number=1, name="Warmup", target_users=25, duration_seconds=15, is_stabilization=False),
            BenchmarkStage(stage_number=2, name="Full Load", target_users=100, duration_seconds=45, is_stabilization=True),
        ],
    ),
    "small": BenchmarkProfile(
        name="small",
        description="Profile 3 — 1,000 virtual users monitoring worker and backend health.",
        virtual_users=1000,
        spawn_rate=50.0,
        duration_seconds=120,
        recommended_mode="local",
        max_error_rate_pct=3.0,
        max_p95_latency_ms=1500.0,
        requires_explicit_approval=False,
        min_worker_nodes=1,
        stages=[
            BenchmarkStage(stage_number=1, name="Ramp-1", target_users=250, duration_seconds=20, is_stabilization=False),
            BenchmarkStage(stage_number=2, name="Ramp-2", target_users=500, duration_seconds=30, is_stabilization=False),
            BenchmarkStage(stage_number=3, name="Measurement", target_users=1000, duration_seconds=70, is_stabilization=True),
        ],
    ),
    "medium": BenchmarkProfile(
        name="medium",
        description="Profile 4 — 5,000 virtual users across multiple workers with controlled ramp-up.",
        virtual_users=5000,
        spawn_rate=100.0,
        duration_seconds=180,
        recommended_mode="distributed",
        max_error_rate_pct=5.0,
        max_p95_latency_ms=2000.0,
        requires_explicit_approval=False,
        min_worker_nodes=2,
    ),
    "large": BenchmarkProfile(
        name="large",
        description="Profile 5 — 10,000 virtual users measuring master and backend capacity boundaries.",
        virtual_users=10000,
        spawn_rate=250.0,
        duration_seconds=300,
        recommended_mode="distributed",
        max_error_rate_pct=5.0,
        max_p95_latency_ms=2500.0,
        requires_explicit_approval=False,
        min_worker_nodes=4,
    ),
    "extended": BenchmarkProfile(
        name="extended",
        description="Profile 6 — 25,000 virtual users on dedicated worker infrastructure.",
        virtual_users=25000,
        spawn_rate=500.0,
        duration_seconds=600,
        recommended_mode="distributed",
        max_error_rate_pct=5.0,
        max_p95_latency_ms=3000.0,
        requires_explicit_approval=True,
        min_worker_nodes=8,
    ),
    "high_capacity": BenchmarkProfile(
        name="high_capacity",
        description="Profile 7 — 50,000 virtual users requiring explicit infrastructure authorization.",
        virtual_users=50000,
        spawn_rate=1000.0,
        duration_seconds=900,
        recommended_mode="distributed",
        max_error_rate_pct=5.0,
        max_p95_latency_ms=4000.0,
        requires_explicit_approval=True,
        min_worker_nodes=16,
    ),
    "extreme": BenchmarkProfile(
        name="extreme",
        description="Profile 8 — 100,000 virtual users on dedicated, capacity-verified infrastructure.",
        virtual_users=100000,
        spawn_rate=2000.0,
        duration_seconds=1200,
        recommended_mode="distributed",
        max_error_rate_pct=5.0,
        max_p95_latency_ms=5000.0,
        requires_explicit_approval=True,
        min_worker_nodes=32,
    ),
    "target": BenchmarkProfile(
        name="target",
        description="Profile 9 — Target 200,000 concurrent synthetic virtual users with strict preflight verification.",
        virtual_users=200000,
        spawn_rate=5000.0,
        duration_seconds=1800,
        recommended_mode="distributed",
        max_error_rate_pct=5.0,
        max_p95_latency_ms=6000.0,
        requires_explicit_approval=True,
        min_worker_nodes=64,
    ),
}


class BenchmarkService:
    """Orchestrates controlled large-scale benchmarks with safety guardrails and reproducibility tracking."""

    def get_profiles(self) -> List[BenchmarkProfile]:
        return list(PREDEFINED_PROFILES.values())

    def get_profile(self, name: str) -> Optional[BenchmarkProfile]:
        return PREDEFINED_PROFILES.get(name.lower())

    async def preflight_check(
        self,
        profile_name: str,
        execution_mode: Optional[str],
        db: AsyncSession,
    ) -> PreflightCheckResponse:
        """Evaluate cluster readiness, registered worker capacity, and storage connectivity."""
        profile = self.get_profile(profile_name)
        if not profile:
            raise BenchmarkProfileNotFoundError(profile_name)

        mode = execution_mode or profile.recommended_mode
        messages: List[str] = []
        ready = True

        # 1. Check Emergency Stop
        active_stop, stop_meta = await emergency_service.is_active()
        if active_stop:
            ready = False
            reason = stop_meta.get("reason", "Lock engaged") if stop_meta else "Emergency Stop active"
            messages.append(f"Blocked: Emergency Stop is currently engaged ({reason}).")

        # 2. Check Redis
        redis_ok = False
        try:
            pong = await redis_client.ping()
            redis_ok = bool(pong)
        except Exception as e:
            ready = False
            messages.append(f"Redis connectivity failed: {e}")

        # 3. Check DB
        db_ok = True
        try:
            await db.execute(select(1))
        except Exception as e:
            ready = False
            db_ok = False
            messages.append(f"PostgreSQL database check failed: {e}")

        # 4. Check Available Host Memory
        avail_mem_mb = psutil.virtual_memory().available / (1024 * 1024)
        memory_ok = avail_mem_mb > 500.0
        if not memory_ok:
            ready = False
            messages.append(f"Low system memory: {avail_mem_mb:.1f} MB available (min 500 MB required).")

        # 5. Check Distributed Workers if in distributed mode
        online_nodes = await worker_registry_service.list_active_nodes(status="online", db=db)
        total_worker_capacity = sum(n.capacity for n in online_nodes)
        online_count = len(online_nodes)

        if mode == "distributed":
            if online_count < profile.min_worker_nodes:
                ready = False
                messages.append(
                    f"Insufficient worker nodes online: {online_count} found vs {profile.min_worker_nodes} required for {profile.name}."
                )

            if total_worker_capacity < profile.virtual_users:
                ready = False
                messages.append(
                    f"Insufficient verified worker capacity: {total_worker_capacity} users available vs {profile.virtual_users} required."
                )

        if profile.requires_explicit_approval:
            messages.append("Explicit operator authorization required before executing this profile.")

        if ready:
            messages.append("Cluster preflight verification passed. Ready for execution.")

        return PreflightCheckResponse(
            ready=ready,
            profile_name=profile.name,
            required_users=profile.virtual_users,
            available_worker_nodes=online_count,
            total_worker_capacity=total_worker_capacity,
            redis_ok=redis_ok,
            db_ok=db_ok,
            memory_ok=memory_ok,
            requires_explicit_approval=profile.requires_explicit_approval,
            messages=messages,
        )

    async def run_benchmark(
        self,
        request: BenchmarkRunRequest,
        db: AsyncSession,
        operator: str = "operator",
    ) -> BenchmarkResultResponse:
        """Launch a controlled benchmark experiment with automated SLA guardrails."""
        profile = self.get_profile(request.profile_name)
        if not profile:
            raise BenchmarkProfileNotFoundError(request.profile_name)

        exec_mode = request.execution_mode or profile.recommended_mode

        # Run preflight check
        preflight = await self.preflight_check(profile.name, execution_mode=exec_mode, db=db)
        if not preflight.ready:
            raise ViewStormException(
                message=f"Preflight check failed for benchmark profile '{profile.name}': {'; '.join(preflight.messages)}",
                status_code=412,
            )

        if profile.requires_explicit_approval and not request.approval_confirmed:
            raise ViewStormException(
                message=f"Benchmark profile '{profile.name}' ({profile.virtual_users:,} users) requires explicit operator authorization flag 'approval_confirmed=True'.",
                status_code=403,
            )

        # 1. Capture Environment & Software Metadata
        software_meta = self._capture_software_metadata()
        infra_meta = await self._capture_infrastructure_metadata(db=db)
        workload_meta = {
            "profile_name": profile.name,
            "virtual_users": profile.virtual_users,
            "spawn_rate": profile.spawn_rate,
            "duration_seconds": profile.duration_seconds,
            "execution_mode": exec_mode,
            "target_environment": request.target_environment,
            "stages": [s.model_dump() for s in profile.stages] if profile.stages else None,
        }

        # 2. Create Simulation Run
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        run_payload = SimulationRunCreate(
            name=f"Benchmark [{profile.name.upper()}] {now_str}",
            target_environment=request.target_environment,
            execution_mode=exec_mode,
            virtual_users=profile.virtual_users,
            spawn_rate=profile.spawn_rate,
            duration_seconds=profile.duration_seconds,
            event_type="playback_start",
            watch_duration_min=5,
            watch_duration_max=60,
        )
        sim_run = await simulation_service.create_run(run_payload, db=db)

        # 3. Create Persistent BenchmarkResult
        benchmark = BenchmarkResult(
            profile_name=profile.name,
            test_type=f"locust_{exec_mode}",
            run_id=sim_run.id,
            target_environment=request.target_environment,
            virtual_users=profile.virtual_users,
            actual_active_users=0,
            spawn_rate=profile.spawn_rate,
            duration_seconds=profile.duration_seconds,
            passed_thresholds=True,
            preflight_passed=True,
            approval_operator=operator if profile.requires_explicit_approval else None,
            notes=request.notes,
            software_metadata=software_meta,
            infrastructure_metadata=infra_meta,
            workload_metadata=workload_meta,
        )
        db.add(benchmark)
        await db.commit()
        await db.refresh(benchmark)

        # 4. Launch execution engine
        if exec_mode == "distributed":
            await distributed_runner_service.start_master(sim_run.id, db=db)
        else:
            await locust_runner_service.start_runner(sim_run.id, db=db)

        # 5. Spawn background safety guardrail monitor
        asyncio.create_task(
            self._monitor_benchmark_guardrails(
                benchmark_id=benchmark.id,
                run_id=sim_run.id,
                profile=profile,
                execution_mode=exec_mode,
            )
        )

        return self._to_response(benchmark, profile)

    def _capture_software_metadata(self) -> Dict[str, Any]:
        """Collect current git commit, python version, locust version, and config hash."""
        git_commit = "unknown"
        git_branch = "unknown"
        try:
            git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            git_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        except Exception:
            pass

        import locust
        config_str = f"{settings.project_name}-{settings.version}-{settings.environment}"
        checksum = hashlib.sha256(config_str.encode()).hexdigest()[:16]

        return {
            "git_commit": git_commit,
            "git_branch": git_branch,
            "viewstorm_version": settings.version,
            "locust_version": locust.__version__,
            "python_version": sys.version.split()[0],
            "config_checksum": checksum,
        }

    async def _capture_infrastructure_metadata(self, db: AsyncSession) -> Dict[str, Any]:
        """Collect host system specs and active worker node configurations."""
        mem = psutil.virtual_memory()
        online_nodes = await worker_registry_service.list_active_nodes(status="online", db=db)

        return {
            "master_os": platform.system(),
            "master_os_release": platform.release(),
            "master_arch": platform.machine(),
            "master_cpu_cores": psutil.cpu_count(logical=True) or 1,
            "master_total_ram_gb": round(mem.total / (1024**3), 2),
            "master_available_ram_gb": round(mem.available / (1024**3), 2),
            "worker_node_count": len(online_nodes),
            "worker_node_identifiers": [n.worker_identifier for n in online_nodes],
            "total_worker_capacity": sum(n.capacity for n in online_nodes),
        }

    async def _monitor_benchmark_guardrails(
        self,
        benchmark_id: str,
        run_id: str,
        profile: BenchmarkProfile,
        execution_mode: str,
    ) -> None:
        """Continuously monitor running benchmark for SLA breaches or resource exhaustion."""
        logger.info("Guardrail monitor started for benchmark %s (run %s)", benchmark_id, run_id)
        abort_error_threshold = max(profile.max_error_rate_pct * 2.5, 12.0)
        abort_latency_threshold = profile.max_p95_latency_ms * 3.0

        for _ in range(profile.duration_seconds + 30):
            await asyncio.sleep(2.0)

            is_active = (
                distributed_runner_service.is_master_active(run_id)
                if execution_mode == "distributed"
                else locust_runner_service.is_runner_active(run_id)
            )

            if not is_active:
                break

            # 1. System Memory Safeguard
            avail_mb = psutil.virtual_memory().available / (1024 * 1024)
            if avail_mb < 300.0:
                abort_reason = f"Safety abort: Available host memory critical ({avail_mb:.1f} MB < 300 MB limit)."
                await self._trigger_abort(run_id, execution_mode)
                await self._finalize_benchmark(benchmark_id, run_id, profile, abort_reason=abort_reason)
                return

            # 2. SLA Metric Safeguards
            try:
                stats = await stats_service.get_current_stats(run_id)
                if stats.total_events > 50:
                    current_error_rate = (
                        (stats.rejected_events / stats.total_events) * 100.0
                        if stats.total_events > 0
                        else 0.0
                    )

                    if current_error_rate > abort_error_threshold:
                        abort_reason = (
                            f"Safety abort: Error rate ({current_error_rate:.2f}%) exceeded threshold ({abort_error_threshold:.1f}%)"
                        )
                        await self._trigger_abort(run_id, execution_mode)
                        await self._finalize_benchmark(benchmark_id, run_id, profile, abort_reason=abort_reason)
                        return
            except Exception as e:
                logger.debug("Guardrail poll error: %s", e)

        await self._finalize_benchmark(benchmark_id, run_id, profile)

    async def _trigger_abort(self, run_id: str, execution_mode: str) -> None:
        """Halt active runner process."""
        try:
            if execution_mode == "distributed":
                await distributed_runner_service.stop_master(run_id)
            else:
                await locust_runner_service.stop_runner(run_id)
        except Exception as e:
            logger.error("Error halting runner %s: %s", run_id, e)

    async def _finalize_benchmark(
        self,
        benchmark_id: str,
        run_id: str,
        profile: BenchmarkProfile,
        abort_reason: Optional[str] = None,
    ) -> None:
        """Persist final report metrics and telemetry into the BenchmarkResult entity."""
        await asyncio.sleep(2.5)
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(BenchmarkResult).where(BenchmarkResult.id == benchmark_id)
                res = await session.execute(stmt)
                benchmark = res.scalars().first()
                if not benchmark:
                    return

                report = await stats_service.generate_report(run_id, db=session)

                error_rate = 0.0
                if report.total_http_requests > 0:
                    error_rate = (report.failed_http_requests / report.total_http_requests) * 100.0
                elif report.total_submissions > 0:
                    error_rate = (report.rejected_events / report.total_submissions) * 100.0

                p95 = report.p95_latency_ms or 0.0
                passed = (error_rate <= profile.max_error_rate_pct) and (p95 <= profile.max_p95_latency_ms)
                if abort_reason:
                    passed = False

                benchmark.actual_active_users = report.configured_users
                benchmark.total_requests = report.total_http_requests or report.total_submissions
                benchmark.accepted_events = report.accepted_events
                benchmark.requests_per_second = report.requests_per_second or report.average_throughput_eps
                benchmark.avg_latency_ms = report.avg_latency_ms
                benchmark.p50_latency_ms = report.p50_latency_ms
                benchmark.p95_latency_ms = p95
                benchmark.p99_latency_ms = report.p99_latency_ms
                benchmark.max_latency_ms = report.max_latency_ms or 0.0
                benchmark.error_rate_pct = round(error_rate, 2)
                benchmark.passed_thresholds = passed
                benchmark.abort_reason = abort_reason
                benchmark.resource_metrics = report.resource_observations

                await session.commit()
                logger.info(
                    "Benchmark %s finalized. Passed: %s, RPS: %.1f, p95: %.1fms, Errors: %.2f%%",
                    benchmark_id,
                    passed,
                    benchmark.requests_per_second,
                    benchmark.p95_latency_ms,
                    benchmark.error_rate_pct,
                )
        except Exception as e:
            logger.error("Failed to finalize benchmark %s: %s", benchmark_id, e)

    async def list_results(
        self,
        db: AsyncSession,
        profile_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BenchmarkResultResponse]:
        """List historical benchmark runs with SLA evaluation."""
        stmt = select(BenchmarkResult).order_by(desc(BenchmarkResult.created_at)).offset(offset).limit(limit)
        if profile_name:
            stmt = stmt.where(BenchmarkResult.profile_name == profile_name.lower())
        res = await db.execute(stmt)
        results = res.scalars().all()
        return [self._to_response(b, self.get_profile(b.profile_name)) for b in results]

    async def get_result(
        self,
        db: AsyncSession,
        benchmark_id: str,
    ) -> Optional[BenchmarkResultResponse]:
        """Retrieve single benchmark record."""
        stmt = select(BenchmarkResult).where(BenchmarkResult.id == benchmark_id)
        res = await db.execute(stmt)
        result = res.scalars().first()
        if not result:
            return None
        return self._to_response(result, self.get_profile(result.profile_name))

    async def compare_results(
        self,
        db: AsyncSession,
        baseline_id: str,
        candidate_id: str,
    ) -> BenchmarkComparisonResponse:
        """Compute performance delta between baseline and candidate benchmark executions."""
        b_res = await self.get_result(db, baseline_id)
        c_res = await self.get_result(db, candidate_id)

        if not b_res or not c_res:
            raise SimulationNotFoundError(f"One or both benchmark IDs ({baseline_id}, {candidate_id}) not found")

        # Compatibility check: if profiles or test types are radically different, flag INCOMPARABLE
        if b_res.profile_name != c_res.profile_name and (
            abs(b_res.virtual_users - c_res.virtual_users) > b_res.virtual_users * 0.5
        ):
            return BenchmarkComparisonResponse(
                baseline=b_res,
                candidate=c_res,
                is_comparable=False,
                incomparable_reason=(
                    f"Workload scale mismatch: baseline '{b_res.profile_name}' ({b_res.virtual_users:,} users) "
                    f"vs candidate '{c_res.profile_name}' ({c_res.virtual_users:,} users)."
                ),
                rps_delta_pct=0.0,
                p95_latency_delta_pct=0.0,
                avg_latency_delta_pct=0.0,
                error_rate_delta_pct=0.0,
                performance_verdict="INCOMPARABLE",
            )

        def calc_delta(b_val: float, c_val: float) -> float:
            if b_val == 0.0:
                return 0.0
            return round(((c_val - b_val) / b_val) * 100.0, 2)

        rps_delta = calc_delta(b_res.requests_per_second, c_res.requests_per_second)
        p95_delta = calc_delta(b_res.p95_latency_ms, c_res.p95_latency_ms)
        avg_delta = calc_delta(b_res.avg_latency_ms, c_res.avg_latency_ms)
        err_delta = round(c_res.error_rate_pct - b_res.error_rate_pct, 2)

        if p95_delta > 15.0 or err_delta > 2.0 or rps_delta < -15.0:
            verdict = "REGRESSION"
        elif rps_delta > 10.0 and p95_delta <= 5.0 and err_delta <= 0.5:
            verdict = "IMPROVEMENT"
        else:
            verdict = "STABLE"

        return BenchmarkComparisonResponse(
            baseline=b_res,
            candidate=c_res,
            is_comparable=True,
            incomparable_reason=None,
            rps_delta_pct=rps_delta,
            p95_latency_delta_pct=p95_delta,
            avg_latency_delta_pct=avg_delta,
            error_rate_delta_pct=err_delta,
            performance_verdict=verdict,
        )

    def _to_response(
        self,
        b: BenchmarkResult,
        profile: Optional[BenchmarkProfile],
    ) -> BenchmarkResultResponse:
        eval_sla = None
        if profile:
            eval_sla = ThresholdEvaluation(
                passed=b.passed_thresholds,
                max_error_rate_pct=profile.max_error_rate_pct,
                actual_error_rate_pct=b.error_rate_pct,
                error_rate_passed=b.error_rate_pct <= profile.max_error_rate_pct,
                max_p95_latency_ms=profile.max_p95_latency_ms,
                actual_p95_latency_ms=b.p95_latency_ms,
                p95_latency_passed=b.p95_latency_ms <= profile.max_p95_latency_ms,
            )

        resp = BenchmarkResultResponse.model_validate(b)
        resp.threshold_evaluation = eval_sla
        return resp


benchmark_service = BenchmarkService()
