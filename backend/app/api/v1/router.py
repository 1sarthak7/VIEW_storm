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

# Unified Router (all endpoints)
api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(benchmarks.router)
api_v1_router.include_router(runs.router)
api_v1_router.include_router(events.router)
api_v1_router.include_router(stats.router)
api_v1_router.include_router(worker_nodes.router)

# Control Plane Router (Orchestration, Auth, Benchmarks, Runs, Worker Nodes)
control_plane_router = APIRouter()
control_plane_router.include_router(health.router)
control_plane_router.include_router(auth.router)
control_plane_router.include_router(admin.router)
control_plane_router.include_router(benchmarks.router)
control_plane_router.include_router(runs.router)
control_plane_router.include_router(stats.router)
control_plane_router.include_router(worker_nodes.router)

# Data Plane Router (High-Throughput Playback Event Ingestion & Event Statistics)
data_plane_router = APIRouter()
data_plane_router.include_router(health.router)
data_plane_router.include_router(events.router)
data_plane_router.include_router(stats.router)
