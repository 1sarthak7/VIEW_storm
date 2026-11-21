"""V1 API Router Assembly."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    admin,
    auth,
    benchmarks,
    events,
    health,
    runs,
    stats,
    worker_nodes,
)

api_v1_router = APIRouter()

api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(benchmarks.router)
api_v1_router.include_router(runs.router)
api_v1_router.include_router(events.router)
api_v1_router.include_router(stats.router)
api_v1_router.include_router(worker_nodes.router)
