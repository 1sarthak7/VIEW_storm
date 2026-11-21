"""V1 API Router Assembly."""

from fastapi import APIRouter
from app.api.v1.endpoints import events, health, runs, stats

api_v1_router = APIRouter()

api_v1_router.include_router(health.router)
api_v1_router.include_router(runs.router)
api_v1_router.include_router(events.router)
api_v1_router.include_router(stats.router)
