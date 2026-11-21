"""Worker Calibration Database Model."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class WorkerCalibration(Base):
    """Persistent calibration measurements for load generator worker capacity."""

    __tablename__ = "worker_calibrations"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"cal_{uuid.uuid4().hex[:16]}",
    )
    worker_node_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    worker_identifier: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    cpu_cores: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    total_memory_mb: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    steps_tested: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB().with_variant(String, "sqlite"),
        nullable=True,
    )
    max_stable_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    max_stable_rps: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    saturation_bottleneck: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    recommended_capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
