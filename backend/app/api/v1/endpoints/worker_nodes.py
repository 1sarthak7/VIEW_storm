"""Worker Node Management and Assignment Polling API Endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_operator, require_viewer
from app.database.redis import get_redis
from app.database.session import get_db
from app.models.user import User
from app.schemas.worker import (
    WorkerAssignmentAcknowledgeRequest,
    WorkerAssignmentResponse,
    WorkerHeartbeatRequest,
    WorkerHeartbeatResponse,
    WorkerNodeResponse,
    WorkerRegisterRequest,
    WorkerRegisterResponse,
)
from app.schemas.worker_calibration import (
    WorkerCalibrationRequest,
    WorkerCalibrationResponse,
)
from app.services.worker_assignment_service import worker_assignment_service
from app.services.worker_calibration_service import worker_calibration_service
from app.services.worker_registry_service import worker_registry_service

router = APIRouter(prefix="/worker-nodes", tags=["Worker Nodes"])


@router.post(
    "/register",
    response_model=WorkerRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_worker_node(
    payload: WorkerRegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> WorkerRegisterResponse:
    """Register a new or returning distributed worker node."""
    return await worker_registry_service.register_node(payload, db=db, redis=redis)


@router.post(
    "/heartbeat",
    response_model=WorkerHeartbeatResponse,
)
async def record_worker_heartbeat(
    payload: WorkerHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> WorkerHeartbeatResponse:
    """Record periodic heartbeat from a worker agent."""
    return await worker_registry_service.record_heartbeat(payload, db=db, redis=redis)


@router.get(
    "",
    response_model=List[WorkerNodeResponse],
)
async def list_worker_nodes(
    status: Optional[str] = Query(None, description="Filter by status (e.g. online, busy, stale)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_viewer),
) -> List[WorkerNodeResponse]:
    """List registered load generator nodes."""
    return await worker_registry_service.list_active_nodes(status=status, db=db)


@router.get(
    "/calibrations",
    response_model=List[WorkerCalibrationResponse],
)
async def list_worker_calibrations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_viewer),
) -> List[WorkerCalibrationResponse]:
    """List historical capacity calibration experiments."""
    return await worker_calibration_service.list_calibrations(db=db, limit=limit, offset=offset)


@router.post(
    "/calibrate-local",
    response_model=WorkerCalibrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def calibrate_local_node(
    payload: WorkerCalibrationRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_operator),
) -> WorkerCalibrationResponse:
    """Calibrate local host machine load generation capacity."""
    return await worker_calibration_service.calibrate_worker(
        worker_node_id=None,
        request=payload,
        db=db,
    )


@router.get(
    "/{worker_id}/assignments",
    response_model=WorkerAssignmentResponse,
)
async def get_worker_assignment(
    worker_id: str,
    redis: Redis = Depends(get_redis),
) -> WorkerAssignmentResponse:
    """Poll for a pending simulation assignment assigned to this worker node."""
    return await worker_assignment_service.get_worker_assignment(worker_id, redis=redis)


@router.get(
    "/{worker_id}",
    response_model=WorkerNodeResponse,
)
async def get_worker_node(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_viewer),
) -> WorkerNodeResponse:
    """Retrieve details for a specific registered worker node."""
    from fastapi import HTTPException
    node = await worker_registry_service.get_node(worker_id, db=db)
    if not node:
        raise HTTPException(status_code=404, detail=f"Worker node '{worker_id}' not found")
    return node


@router.get(
    "/{worker_id}/calibration",
    response_model=Optional[WorkerCalibrationResponse],
)
async def get_latest_worker_calibration(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_viewer),
) -> Optional[WorkerCalibrationResponse]:
    """Retrieve most recent capacity calibration for a worker node."""
    return await worker_calibration_service.get_latest_calibration(worker_node_id=worker_id, db=db)


@router.post(
    "/{worker_id}/assignments/{run_id}/acknowledge",
    status_code=status.HTTP_200_OK,
)
async def acknowledge_worker_assignment(
    worker_id: str,
    run_id: str,
    payload: WorkerAssignmentAcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Acknowledge worker subprocess launch for an assignment."""
    payload.worker_id = worker_id
    payload.run_id = run_id
    success = await worker_assignment_service.acknowledge_assignment(payload, db=db)
    return {"acknowledged": success}


@router.post(
    "/{worker_id}/calibrate",
    response_model=WorkerCalibrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def calibrate_worker_node(
    worker_id: str,
    payload: WorkerCalibrationRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_operator),
) -> WorkerCalibrationResponse:
    """Execute stepped load calibration for a registered worker node to determine saturation limits."""
    return await worker_calibration_service.calibrate_worker(
        worker_node_id=worker_id,
        request=payload,
        db=db,
    )
