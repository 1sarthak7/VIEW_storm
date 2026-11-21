"""Simulation Run Database Entity with Execution Mode."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SimulationRun(Base):
    """Persistent record of a simulation run configuration and lifecycle state."""

    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_environment: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    virtual_users: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    spawn_rate: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, default="playback_start")
    watch_duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    watch_duration_max: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    metrics: Mapped[List["SimulationMetric"]] = relationship(
        "SimulationMetric",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="SimulationMetric.timestamp",
    )
    workers: Mapped[List["SimulationWorker"]] = relationship(
        "SimulationWorker",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    event_summaries: Mapped[List["EventSummary"]] = relationship(
        "EventSummary",
        back_populates="run",
        cascade="all, delete-orphan",
    )
