"""Admin Control Plane and Emergency Stop API Endpoints."""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_admin, require_viewer
from app.database.session import get_db
from app.models.user import User
from app.services.emergency_service import emergency_service

router = APIRouter(prefix="/admin", tags=["Admin & System Control"])


class EmergencyStopRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=256, description="Justification for emergency halt")


@router.post("/emergency-stop")
async def trigger_emergency_stop(
    payload: EmergencyStopRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger system-wide emergency stop, terminating all active runners and locking simulation commands."""
    return await emergency_service.trigger_emergency_stop(
        reason=payload.reason,
        operator=current_user.username,
        db=db,
    )


@router.post("/emergency-stop/clear")
async def clear_emergency_stop(
    current_user: User = Depends(require_admin),
) -> Dict[str, Any]:
    """Clear emergency stop lock and restore normal simulation operations."""
    return await emergency_service.clear_emergency_stop(operator=current_user.username)


@router.get("/emergency-stop/status")
async def get_emergency_stop_status(
    _: User = Depends(require_viewer),
) -> Dict[str, Any]:
    """Query current status of emergency stop subsystem."""
    return await emergency_service.get_status()
