"""Schemas for Worker Registration, Authentication, Heartbeats, and Assignments."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WorkerNodeStatus(str, Enum):
    """Lifecycle status of a load generator node."""
    ONLINE = "online"
    BUSY = "busy"
    STALE = "stale"
    OFFLINE = "offline"
    INCOMPATIBLE = "incompatible"


class WorkerRegisterRequest(BaseModel):
    """Payload submitted by a WorkerAgent upon initial registration."""
    worker_identifier: str = Field(..., description="Unique hardware or UUID identity")
    worker_name: str = Field(..., description="Human-friendly node label")
    hostname: str = Field(..., description="Machine network hostname")
    platform: str = Field(..., description="OS platform (e.g. Darwin, Linux)")
    cpu_cores: int = Field(default=1, ge=1)
    total_memory_bytes: int = Field(default=0, ge=0)
    available_memory_bytes: int = Field(default=0, ge=0)
    locust_version: str = Field(..., description="Pinned Locust version string")
    software_version: str = Field(default="1.0.0")
    build_identifier: str = Field(default="release")
    capacity: int = Field(default=100, ge=1, description="Max virtual users this node can handle")
    auth_token: str = Field(..., min_length=8, description="Pre-shared or agent authentication token")


class WorkerRegisterResponse(BaseModel):
    """Response returned upon successful worker registration."""
    worker_id: str
    worker_identifier: str
    status: WorkerNodeStatus
    registered_at: datetime
    message: str = "Worker registered successfully"


class WorkerHeartbeatRequest(BaseModel):
    """Periodic heartbeat payload sent by WorkerAgent."""
    worker_id: str
    hostname: str
    status: WorkerNodeStatus = WorkerNodeStatus.ONLINE
    active_run_id: Optional[str] = None
    active_worker_processes: int = 0
    cpu_utilization: float = 0.0
    ram_utilization: float = 0.0
    available_memory_bytes: int = 0
    software_version: str = "1.0.0"
    timestamp: datetime


class WorkerHeartbeatResponse(BaseModel):
    """Response acknowledging heartbeat with active state instruction."""
    acknowledged: bool = True
    status: WorkerNodeStatus
    active_run_id: Optional[str] = None
    should_stop_run: bool = False


class WorkerAssignment(BaseModel):
    """Simulation run assignment details dispatched to a worker."""
    run_id: str
    master_host: str
    master_port: int = 5557
    assigned_users: int
    spawn_rate: float
    duration_seconds: int
    target_host: str
    event_type: str = "playback_start"
    watch_duration_min: int = 5
    watch_duration_max: int = 60


class WorkerAssignmentResponse(BaseModel):
    """Response returned when a WorkerAgent polls for work."""
    has_assignment: bool
    assignment: Optional[WorkerAssignment] = None


class WorkerAssignmentAcknowledgeRequest(BaseModel):
    """WorkerAgent confirmation that it received assignment and launched workers."""
    run_id: str
    worker_id: str
    accepted: bool
    worker_process_count: int = 1
    error_message: Optional[str] = None


class WorkerNodeResponse(BaseModel):
    """Information about a registered load generator node."""
    id: str
    worker_identifier: str
    worker_name: str
    hostname: str
    platform: str
    cpu_cores: int
    total_memory_bytes: int
    available_memory_bytes: int
    locust_version: str
    software_version: str
    status: WorkerNodeStatus
    capacity: int
    last_heartbeat: datetime
    registered_at: datetime
