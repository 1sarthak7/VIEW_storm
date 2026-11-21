"""Unit Tests for Authentication, Password Hashing, JWTs, and Operator RBAC."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.database.session import AsyncSessionLocal
from app.main import app
from app.models.user import User, UserRole
from app.repositories.user_repository import user_repository
from app.services.auth_service import auth_service


@pytest.mark.asyncio
async def test_argon2id_password_hashing():
    """Verify Argon2id hashes passwords securely and detects mismatches."""
    password = "StrongPassword2026!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert "$argon2" in hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.asyncio
async def test_jwt_token_creation_and_decoding():
    """Verify JWT token encoding and signature validation."""
    data = {"sub": "usr_test123", "username": "operator1", "role": "operator"}
    token = create_access_token(data)

    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "usr_test123"
    assert decoded["username"] == "operator1"
    assert decoded["role"] == "operator"

    # Tampered token
    tampered = token[:-4] + "abcd"
    assert decode_access_token(tampered) is None


@pytest.mark.asyncio
async def test_auth_login_success(client: AsyncClient):
    """Verify successful authentication returns JWT and user profile."""
    # Temporarily remove dependency override so auth runs against real DB
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncSessionLocal() as session:
        user = User(
            username="test_admin_user",
            email="test_admin@viewstorm.local",
            hashed_password=get_password_hash("SecretPassword123!"),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        await user_repository.create_user(session, user)

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "test_admin_user", "password": "SecretPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "test_admin_user"
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_auth_login_invalid_password(client: AsyncClient):
    """Verify login failure with incorrect credentials returns 401."""
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncSessionLocal() as session:
        user = User(
            username="test_operator",
            email="test_operator@viewstorm.local",
            hashed_password=get_password_hash("SecretPassword123!"),
            role=UserRole.OPERATOR.value,
            is_active=True,
        )
        await user_repository.create_user(session, user)

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "test_operator", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_login_brute_force_rate_limiting(client: AsyncClient):
    """Verify login rate limit triggers after consecutive failed attempts."""
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncSessionLocal() as session:
        user = User(
            username="target_user",
            email="target@viewstorm.local",
            hashed_password=get_password_hash("CorrectPassword123!"),
            role=UserRole.OPERATOR.value,
            is_active=True,
        )
        await user_repository.create_user(session, user)

    # 5 failed attempts
    for _ in range(settings.login_rate_limit_max_attempts):
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "target_user", "password": "BadPassword"},
        )
        assert res.status_code == 401

    # 6th attempt should be blocked by rate limit (HTTP 429)
    res_blocked = await client.post(
        "/api/v1/auth/login",
        json={"username": "target_user", "password": "BadPassword"},
    )
    assert res_blocked.status_code == 429
    assert "Too many failed login attempts" in res_blocked.json()["error"]["message"]


@pytest.mark.asyncio
async def test_rbac_insufficient_permissions(client: AsyncClient):
    """Verify viewer role cannot trigger operator or admin operations."""
    app.dependency_overrides.pop(get_current_user, None)

    async with AsyncSessionLocal() as session:
        viewer = User(
            id="usr_viewer_test",
            username="readonly_viewer",
            email="viewer@viewstorm.local",
            hashed_password=get_password_hash("ViewerPass123!"),
            role=UserRole.VIEWER.value,
            is_active=True,
        )
        await user_repository.create_user(session, viewer)

    token = create_access_token({"sub": viewer.id, "username": viewer.username, "role": viewer.role})
    headers = {"Authorization": f"Bearer {token}"}

    # Viewer attempting to create simulation run should get 403 Forbidden
    response = await client.post(
        "/api/v1/runs",
        headers=headers,
        json={
            "name": "Viewer Forbidden Run",
            "target_environment": "local",
            "virtual_users": 10,
            "spawn_rate": 2.0,
            "duration_seconds": 30,
        },
    )
    assert response.status_code == 403
    assert "Access denied" in response.json()["error"]["message"]
