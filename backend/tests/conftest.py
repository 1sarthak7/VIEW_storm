"""Pytest test configuration and fixtures."""

import sys
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.main import app
from app.services.event_service import event_service
from app.services.simulation_service import simulation_service


@pytest.fixture(autouse=True)
def clean_services_state():
    """Reset in-memory state before each test execution."""
    with simulation_service._lock:
        simulation_service._runs.clear()
    with event_service._global_lock:
        event_service._aggregators.clear()
    yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Test client fixture for synchronous HTTP request tests."""
    with TestClient(app) as test_client:
        yield test_client
