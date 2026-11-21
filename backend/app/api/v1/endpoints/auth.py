"""Authentication and User Management Endpoints."""

from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_admin, require_viewer
from app.core.errors import UserNotFoundError
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.auth import (
    BootstrapAdminRequest,
    BootstrapStatusResponse,
    TokenResponse,
    UserCreateRequest,
    UserLoginRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.get("/bootstrap/status", response_model=BootstrapStatusResponse)
async def get_bootstrap_status(
    db: AsyncSession = Depends(get_db),
) -> BootstrapStatusResponse:
    """Check whether the system requires initial administrator bootstrapping."""
    return await auth_service.check_bootstrap_status(db=db)


@router.post("/bootstrap", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def execute_bootstrap(
    payload: BootstrapAdminRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Consume one-time bootstrap token to initialize root system administrator."""
    return await auth_service.execute_bootstrap(payload, db=db)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with username and password to obtain a JWT Bearer token."""
    client_ip = request.client.host if request.client else "unknown"
    return await auth_service.authenticate(payload, db=db, client_ip=client_ip)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(require_viewer),
) -> UserResponse:
    """Retrieve profile and role information for currently authenticated operator."""
    return UserResponse.model_validate(current_user)


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> List[UserResponse]:
    """List all registered system operators (Admin only)."""
    users = await user_repository.list_users(db, limit=limit, offset=offset)
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserResponse:
    """Register a new operator or viewer account (Admin only)."""
    return await auth_service.create_user(payload, db=db)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserResponse:
    """Update role or active status for a user (Admin only)."""
    user = await user_repository.get_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(user_id)

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    updated = await user_repository.update_user(db, user)
    return UserResponse.model_validate(updated)
