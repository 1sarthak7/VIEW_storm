"""Simulation Metric Time-Series Entity."""

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SimulationMetric(Base):
    """Snapshot time-series performance data for a simulation run."""

    __tablename__ = "simulation_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    active_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests_per_second: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    successful_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_latency: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p95_latency: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p99_latency: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationship back to parent run
    run: Mapped["SimulationRun"] = relationship("SimulationRun", back_populates="metrics")
