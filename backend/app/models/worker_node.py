"""Load Generator Node Database Entity for Distributed Worker Registry."""

from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class LoadGeneratorNode(Base):
    """Persistent registry of authenticated distributed load generator machines."""

    __tablename__ = "load_generator_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    worker_identifier: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    worker_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_memory_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    available_memory_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    locust_version: Mapped[str] = mapped_column(String(32), nullable=False)
    software_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    build_identifier: Mapped[str] = mapped_column(String(64), nullable=False, default="release")
    auth_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="online", index=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
