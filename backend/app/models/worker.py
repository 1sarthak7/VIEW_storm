"""Distributed Simulation Worker Entity."""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SimulationWorker(Base):
    """Tracks registered distributed load generator workers and heartbeats."""

    __tablename__ = "simulation_workers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_identifier: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="idle")
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource_information: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    run: Mapped["SimulationRun"] = relationship("SimulationRun", back_populates="workers")
