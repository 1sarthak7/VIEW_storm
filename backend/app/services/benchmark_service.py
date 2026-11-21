"""Controlled Benchmarking Framework Service with SLA Thresholds and Automated Guardrails."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import (
    BenchmarkProfileNotFoundError,
    EmergencyStopActiveError,
    SimulationNotFoundError,
)
from app.core.logging import logger
from app.database.session import AsyncSessionLocal
from app.models.benchmark import BenchmarkResult
from app.models.simulation import SimulationRun
from app.schemas.benchmark import (
    BenchmarkComparisonResponse,
    BenchmarkProfile,
    BenchmarkResultResponse,
    BenchmarkRunRequest,
    ThresholdEvaluation,
)
from app.schemas.run import SimulationRunCreate
from app.services.distributed_runner_service import distributed_runner_service
from app.services.emergency_service import emergency_service
from app.services.locust_runner_service import locust_runner_service
from app.services.simulation_service import simulation_service
from app.services.stats_service import stats_service

PREDEFINED_PROFILES: Dict[str, BenchmarkProfile] = {
    "smoke": BenchmarkProfile(
        name="smoke",
        description="Lightweight sanity check to verify API responsiveness and end-to-end ingestion pipeline.",
        virtual_users=10,
        spawn_rate=2.0,
        duration_seconds=30,
        recommended_mode="local",
        max_error_rate_pct=1.0,
        max_p95_latency_ms=500.0,
    ),
    "baseline": BenchmarkProfile(
        name="baseline",
        description="Standard single-node baseline verification under typical operational load.",
        virtual_users=50,
        spawn_rate=5.0,
        duration_seconds=60,
        recommended_mode="local",
        max_error_rate_pct=2.0,
        max_p95_latency_ms=1000.0,
    ),
    "medium": BenchmarkProfile(
        name="medium",
        description="Stress simulation assessing local concurrency limits and Redis counter throughput.",
        virtual_users=200,
        spawn_rate=20.0,
        duration_seconds=120,
        recommended_mode="local",
        max_error_rate_pct=5.0,
        max_p95_latency_ms=2000.0,
    ),
    "high": BenchmarkProfile(
        name="high",
        description="High-concurrency stress test testing saturation boundaries.",
        virtual_users=500,
        spawn_rate=50.0,
        duration_seconds=180,
        recommended_mode="local",
        max_error_rate_pct=5.0,
        max_p95_latency_ms=3000.0,
    ),
    "distributed": BenchmarkProfile(
        name="distributed",
        description="Distributed cluster benchmark orchestrating multiple worker nodes via ZeroMQ.",
        virtual_users=1000,
        spawn_rate=100.0,
        duration_seconds=300,
        recommended_mode="distributed",
        max_error_rate_pct=5.0,
        max_p95_latency_ms=5000.0,
    ),
}


class BenchmarkService:
    """Orchestrates controlled performance benchmarks with automatic SLA threshold guards."""

    def get_profiles(self) -> List[BenchmarkProfile]:
        return list(PREDEFINED_PROFILES.values())

    def get_profile(self, name: str) -> Optional[BenchmarkProfile]:
        return PREDEFINED_PROFILES.get(name.lower())

    async def run_benchmark(
        self,
        request: BenchmarkRunRequest,
        db: AsyncSession,
        operator: str = "operator",
    ) -> BenchmarkResultResponse:
        """Initialize, launch, and monitor a standardized benchmark run."""
        profile = self.get_profile(request.profile_name)
        if not profile:
            raise BenchmarkProfileNotFoundError(request.profile_name)

        # Enforce emergency stop
        active_stop, stop_meta = await emergency_service.is_active()
        if active_stop:
            reason = stop_meta.get("reason", "Locked") if stop_meta else "Emergency Stop active"
            raise EmergencyStopActiveError(reason)

        exec_mode = request.execution_mode or profile.recommended_mode

        # 1. Create Simulation Run
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

        # 2. Create initial BenchmarkResult record
        benchmark = BenchmarkResult(
            profile_name=profile.name,
            test_type=f"locust_{exec_mode}",
            run_id=sim_run.id,
            target_environment=request.target_environment,
            virtual_users=profile.virtual_users,
            spawn_rate=profile.spawn_rate,
            duration_seconds=profile.duration_seconds,
            passed_thresholds=True,
            notes=request.notes,
        )
        db.add(benchmark)
        await db.commit()
        await db.refresh(benchmark)

        # 3. Launch execution engine
        if exec_mode == "distributed":
            await distributed_runner_service.start_master(sim_run.id, db=db)
        else:
            await locust_runner_service.start_runner(sim_run.id, db=db)

        # 4. Spawn background guardrail monitor
        asyncio.create_task(
            self._monitor_benchmark_guardrails(
                benchmark_id=benchmark.id,
                run_id=sim_run.id,
                profile=profile,
                execution_mode=exec_mode,
            )
        )

        return self._to_response(benchmark, profile)

    async def _monitor_benchmark_guardrails(
        self,
        benchmark_id: str,
        run_id: str,
        profile: BenchmarkProfile,
        execution_mode: str,
    ) -> None:
        """Monitor running benchmark for SLA breach and automatically abort if safety limits exceeded."""
        logger.info("Guardrail monitor started for benchmark %s (run %s)", benchmark_id, run_id)
        # Safety breach multipliers (abort if error rate > 3x limit or latency > 4x limit)
        abort_error_threshold = max(profile.max_error_rate_pct * 3.0, 15.0)
        abort_latency_threshold = profile.max_p95_latency_ms * 4.0

        for _ in range(profile.duration_seconds + 30):
            await asyncio.sleep(2.0)

            # Check if runner is still running
            is_active = (
                distributed_runner_service.is_master_active(run_id)
                if execution_mode == "distributed"
                else locust_runner_service.is_runner_active(run_id)
            )

            if not is_active:
                break

            # Check live metrics
            try:
                stats = await stats_service.get_current_stats(run_id)
                if stats.total_events > 50:
                    current_error_rate = (
                        (stats.rejected_events / stats.total_events) * 100.0
                        if stats.total_events > 0
                        else 0.0
                    )

                    # Check for runaway error rate
                    if current_error_rate > abort_error_threshold:
                        logger.error(
                            "AUTOMATIC BENCHMARK ABORT: Run %s error rate (%.2f%%) exceeded safety threshold (%.2f%%)",
                            run_id,
                            current_error_rate,
                            abort_error_threshold,
                        )
                        abort_reason = (
                            f"Safety guardrail triggered: error rate reached {current_error_rate:.2f}% "
                            f"(limit: {profile.max_error_rate_pct}%)"
                        )
                        if execution_mode == "distributed":
                            await distributed_runner_service.stop_master(run_id)
                        else:
                            await locust_runner_service.stop_runner(run_id)

                        await self._finalize_benchmark(benchmark_id, run_id, profile, abort_reason=abort_reason)
                        return
            except Exception as e:
                logger.debug("Guardrail check error: %s", e)

        # Benchmark finished normally: collect report
        await self._finalize_benchmark(benchmark_id, run_id, profile)

    async def _finalize_benchmark(
        self,
        benchmark_id: str,
        run_id: str,
        profile: BenchmarkProfile,
        abort_reason: Optional[str] = None,
    ) -> None:
        """Persist final report metrics into the BenchmarkResult entity."""
        await asyncio.sleep(3.0)  # Allow final flush to disk and DB
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

                benchmark.total_requests = report.total_http_requests or report.total_submissions
                benchmark.requests_per_second = report.requests_per_second or report.average_throughput_eps
                benchmark.avg_latency_ms = report.avg_latency_ms
                benchmark.p50_latency_ms = report.p50_latency_ms
                benchmark.p95_latency_ms = p95
                benchmark.p99_latency_ms = report.p99_latency_ms
                benchmark.error_rate_pct = round(error_rate, 2)
                benchmark.passed_thresholds = passed
                benchmark.abort_reason = abort_reason

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
        return [
            self._to_response(b, self.get_profile(b.profile_name))
            for b in results
        ]

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

        # Compute percentage deltas
        def calc_delta(b_val: float, c_val: float) -> float:
            if b_val == 0.0:
                return 0.0
            return round(((c_val - b_val) / b_val) * 100.0, 2)

        rps_delta = calc_delta(b_res.requests_per_second, c_res.requests_per_second)
        p95_delta = calc_delta(b_res.p95_latency_ms, c_res.p95_latency_ms)
        avg_delta = calc_delta(b_res.avg_latency_ms, c_res.avg_latency_ms)
        err_delta = round(c_res.error_rate_pct - b_res.error_rate_pct, 2)

        # Verdict
        if p95_delta > 15.0 or err_delta > 2.0 or rps_delta < -15.0:
            verdict = "REGRESSION"
        elif rps_delta > 10.0 and p95_delta <= 5.0 and err_delta <= 0.5:
            verdict = "IMPROVEMENT"
        else:
            verdict = "STABLE"

        return BenchmarkComparisonResponse(
            baseline=b_res,
            candidate=c_res,
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
