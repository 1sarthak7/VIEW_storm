"""Startup Lifecycle Reconciliation Service.

Detects and recovers orphan / interrupted simulation states caused by unexpected server termination.
"""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.models.simulation import SimulationRun
from app.schemas.run import SimulationStatus


class LifecycleReconciliationService:
    """Reconciles persistent simulation states on backend boot."""

    async def reconcile_interrupted_runs(self, db: AsyncSession) -> int:
        """Scan PostgreSQL for zombie runs and mark them as interrupted."""
        zombie_statuses = [
            SimulationStatus.RUNNING.value,
            SimulationStatus.STARTING.value,
            "waiting_for_workers",
        ]
        stmt = select(SimulationRun).where(SimulationRun.status.in_(zombie_statuses))
        result = await db.execute(stmt)
        orphan_runs = result.scalars().all()

        if not orphan_runs:
            logger.info("Startup lifecycle check: No interrupted runs detected.")
            return 0

        now = datetime.now(timezone.utc)
        reconciled_count = 0

        for run in orphan_runs:
            logger.warning(
                "Lifecycle reconciliation: Found ungracefully terminated run '%s' (status: %s). Marking INTERRUPTED.",
                run.id,
                run.status,
            )
            run.status = SimulationStatus.INTERRUPTED.value
            run.finished_at = now
            run.error_message = (
                "Simulation interrupted due to backend restart or ungraceful process termination."
            )
            reconciled_count += 1

        await db.commit()
        logger.info(
            "Startup lifecycle reconciliation completed. %d interrupted run(s) cleaned up.",
            reconciled_count,
        )
        return reconciled_count


lifecycle_reconciliation_service = LifecycleReconciliationService()
