"""FastAPI Request Dependencies for Security, RBAC, and Storage."""

from typing import Callable, List, Optional
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import AuthenticationError, InsufficientPermissionsError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import user_repository

# Optional bearer token extraction scheme (doesn't automatically 403 on missing)
bearer_scheme = HTTPBearer(auto_error=False)

# Synthetic administrator user for development / test bypass
SYSTEM_DEV_USER = User(
    id="usr_system_dev_admin",
    username="dev_admin",
    email="dev@viewstorm.local",
    role=UserRole.ADMIN.value,
    is_active=True,
)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT Bearer token, retrieving the authenticated operator."""
    if not credentials or not credentials.credentials:
        # Check if auth is disabled in configuration
        if not settings.auth_enabled:
            return SYSTEM_DEV_USER
        raise AuthenticationError("Authorization Bearer token required.")

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise AuthenticationError("Invalid or expired authentication token.")

    user_id = payload.get("sub")
    user = await user_repository.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise AuthenticationError("User account inactive or not found.")

    return user


def require_role(allowed_roles: List[str]) -> Callable:
    """Dependency factory enforcing specific RBAC roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise InsufficientPermissionsError(allowed_roles, current_user.role)
        return current_user

    return role_checker


# Role dependencies
require_admin = require_role([UserRole.ADMIN.value])
require_operator = require_role([UserRole.ADMIN.value, UserRole.OPERATOR.value])
require_viewer = require_role([
    UserRole.ADMIN.value,
    UserRole.OPERATOR.value,
    UserRole.VIEWER.value,
])
