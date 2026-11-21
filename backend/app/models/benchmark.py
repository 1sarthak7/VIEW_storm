"""Benchmark Execution Database Model with Extended Reproducibility Metadata."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class BenchmarkResult(Base):
    """Persistent record of a controlled performance benchmark experiment."""

    __tablename__ = "benchmark_results"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"bmk_{uuid.uuid4().hex[:16]}",
    )
    profile_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    test_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="locust_local",
    )
    run_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    target_environment: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="local",
    )
    virtual_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    actual_active_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    spawn_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    total_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    accepted_events: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    requests_per_second: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    avg_latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    p50_latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    p95_latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    p99_latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    max_latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    error_rate_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    passed_thresholds: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    preflight_passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    approval_operator: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    abort_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Detailed reproducibility & environment metadata
    software_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(String, "sqlite"),
        nullable=True,
    )
    infrastructure_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(String, "sqlite"),
        nullable=True,
    )
    workload_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(String, "sqlite"),
        nullable=True,
    )
    resource_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(String, "sqlite"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
