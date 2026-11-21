"""Pytest test configuration and fixtures for Milestone 2."""

import sys
from pathlib import Path
from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

# Ensure backend directory is in sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.database.redis import redis_client
from app.database.session import AsyncSessionLocal
from app.main import app


@pytest.fixture(autouse=True)
async def clean_storage_state():
    """Clean Redis keys and PostgreSQL tables before each test execution."""
    try:
        await redis_client.flushdb()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE simulation_workers, simulation_metrics, event_summaries, simulation_runs CASCADE;"
                )
            )
            await session.commit()
    except Exception:
        pass
    yield


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client fixture."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
