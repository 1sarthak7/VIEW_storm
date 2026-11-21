"""Global Emergency Stop Subsystem.

Provides an immediate, distributed kill-switch mechanism across all running simulations.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import EMERGENCY_STOP_GAUGE
from app.database.redis import redis_client
from app.models.simulation import SimulationRun
from app.schemas.run import SimulationStatus
from app.services.distributed_runner_service import distributed_runner_service
from app.services.locust_runner_service import locust_runner_service


class EmergencyService:
    """Manages system-wide emergency halt state and execution termination."""

    def __init__(self, redis: Optional[Redis] = None) -> None:
        self._redis = redis or redis_client

    async def is_active(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if the emergency stop lock is active."""
        try:
            val = await self._redis.get(settings.emergency_stop_key)
            if val and val.decode("utf-8") if isinstance(val, bytes) else str(val) == "1":
                raw_meta = await self._redis.get(settings.emergency_stop_meta_key)
                meta = {}
                if raw_meta:
                    if isinstance(raw_meta, bytes):
                        raw_meta = raw_meta.decode("utf-8")
                    try:
                        meta = json.loads(raw_meta)
                    except Exception:
                        pass
                return True, meta
        except Exception as e:
            logger.error("Failed to query emergency stop status in Redis: %s", e)
        return False, None

    async def trigger_emergency_stop(
        self,
        reason: str,
        operator: str,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Immediately engage emergency stop, abort all runners and active simulations."""
        now = datetime.now(timezone.utc)
        meta = {
            "active": True,
            "reason": reason,
            "operator": operator,
            "triggered_at": now.isoformat(),
        }

        # 1. Engage Redis emergency keys
        await self._redis.set(settings.emergency_stop_key, "1")
        await self._redis.set(settings.emergency_stop_reason_key, reason)
        await self._redis.set(settings.emergency_stop_meta_key, json.dumps(meta))

        # 2. Update Prometheus metric
        EMERGENCY_STOP_GAUGE.set(1)

        # 3. Kill local Locust runner subprocesses
        local_aborted = []
        for run_id in list(locust_runner_service._active_runners.keys()):
            try:
                await locust_runner_service.stop_runner(run_id)
                local_aborted.append(run_id)
            except Exception as e:
                logger.error("Error stopping local runner %s during emergency stop: %s", run_id, e)

        # 4. Kill distributed Locust master subprocesses
        dist_aborted = []
        for run_id in list(distributed_runner_service._active_masters.keys()):
            try:
                await distributed_runner_service.stop_master(run_id)
                dist_aborted.append(run_id)
            except Exception as e:
                logger.error("Error stopping distributed master %s during emergency stop: %s", run_id, e)

        # 5. Transition all active DB simulation records to INTERRUPTED
        db_aborted = 0
        if db is not None:
            active_statuses = [
                SimulationStatus.RUNNING.value,
                SimulationStatus.STARTING.value,
                "waiting_for_workers",
            ]
            stmt = select(SimulationRun).where(SimulationRun.status.in_(active_statuses))
            result = await db.execute(stmt)
            active_runs = result.scalars().all()
            for r in active_runs:
                r.status = SimulationStatus.INTERRUPTED.value
                r.finished_at = now
                r.error_message = f"Aborted by Emergency Stop: {reason} (operator: {operator})"
                db_aborted += 1
            await db.commit()

        logger.critical(
            "EMERGENCY STOP ENGAGED by '%s'. Reason: '%s'. Aborted: local=%s, dist=%s, db_records=%s",
            operator,
            reason,
            local_aborted,
            dist_aborted,
            db_aborted,
        )

        return {
            "status": "engaged",
            "reason": reason,
            "operator": operator,
            "triggered_at": now.isoformat(),
            "local_runners_aborted": local_aborted,
            "distributed_masters_aborted": dist_aborted,
            "simulations_interrupted": db_aborted,
        }

    async def clear_emergency_stop(self, operator: str) -> Dict[str, Any]:
        """Disengage emergency stop lock to resume standard operations."""
        await self._redis.delete(settings.emergency_stop_key)
        await self._redis.delete(settings.emergency_stop_reason_key)
        await self._redis.delete(settings.emergency_stop_meta_key)
        EMERGENCY_STOP_GAUGE.set(0)

        logger.info("Emergency stop cleared by operator '%s'. Normal operations resumed.", operator)
        return {
            "status": "cleared",
            "operator": operator,
            "cleared_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_status(self) -> Dict[str, Any]:
        """Return human-readable emergency status."""
        active, meta = await self.is_active()
        if active:
            return meta or {"active": True, "reason": "Emergency stop active"}
        return {"active": False}


emergency_service = EmergencyService()
