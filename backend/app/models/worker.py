"""Distributed Simulation Worker Assignment Entity."""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SimulationWorker(Base):
    """Tracks a worker node's assigned workload for a specific simulation run."""

    __tablename__ = "simulation_workers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_node_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("load_generator_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    worker_identifier: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="assigned", index=True)
    assigned_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_process_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource_information: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    run: Mapped["SimulationRun"] = relationship("SimulationRun", back_populates="workers")
