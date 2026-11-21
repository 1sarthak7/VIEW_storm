"""Authentication and Operator RBAC Service."""

import os
import secrets
from pathlib import Path
from typing import Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import (
    AuthenticationError,
    AuthenticationRateLimitError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.database.redis import redis_client
from app.models.user import User, UserRole
from app.repositories.user_repository import user_repository
from app.schemas.auth import (
    BootstrapAdminRequest,
    BootstrapStatusResponse,
    TokenResponse,
    UserCreateRequest,
    UserLoginRequest,
    UserResponse,
)


class AuthService:
    """Handles operator authentication, JWT issuance, rate limiting, and administration."""

    def __init__(self, redis: Optional[Redis] = None) -> None:
        self._redis = redis or redis_client

    async def authenticate(
        self,
        credentials: UserLoginRequest,
        db: AsyncSession,
        client_ip: Optional[str] = None,
    ) -> TokenResponse:
        """Authenticate user credentials with brute-force rate-limiting."""
        rate_key = f"viewstorm:auth:rate_limit:{credentials.username.strip().lower()}"

        # Check rate-limit counter in Redis
        try:
            attempts_raw = await self._redis.get(rate_key)
            if attempts_raw and int(attempts_raw) >= settings.login_rate_limit_max_attempts:
                logger.warning(
                    "Login rate-limit exceeded for user '%s' from IP '%s'",
                    credentials.username,
                    client_ip,
                )
                raise AuthenticationRateLimitError(
                    f"Too many failed login attempts. Account temporarily locked for {settings.login_rate_limit_window_seconds // 60} minutes."
                )
        except AuthenticationRateLimitError:
            raise
        except Exception as e:
            logger.debug("Redis rate-limit check skipped: %s", e)

        # Lookup user
        user = await user_repository.get_by_username(db, credentials.username.strip())
        if not user or not user.is_active:
            await self._record_failed_attempt(rate_key)
            logger.warning("Authentication failed: user '%s' not found or inactive", credentials.username)
            raise AuthenticationError("Invalid username or password.")

        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            await self._record_failed_attempt(rate_key)
            logger.warning("Authentication failed: invalid password for user '%s'", credentials.username)
            raise AuthenticationError("Invalid username or password.")

        # Successful login: clear rate limit counter
        try:
            await self._redis.delete(rate_key)
        except Exception:
            pass

        token_data = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
        }
        token = create_access_token(token_data)
        expires_in = settings.access_token_expire_minutes * 60

        logger.info("Operator '%s' (role: %s) authenticated successfully", user.username, user.role)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserResponse.model_validate(user),
        )

    async def _record_failed_attempt(self, key: str) -> None:
        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, settings.login_rate_limit_window_seconds)
        except Exception as e:
            logger.debug("Could not record failed attempt in Redis: %s", e)

    async def create_user(
        self,
        payload: UserCreateRequest,
        db: AsyncSession,
    ) -> UserResponse:
        """Create a new operator account (Admin only)."""
        existing_user = await user_repository.get_by_username(db, payload.username)
        if existing_user:
            raise UserAlreadyExistsError("username", payload.username)

        existing_email = await user_repository.get_by_email(db, payload.email)
        if existing_email:
            raise UserAlreadyExistsError("email", payload.email)

        new_user = User(
            username=payload.username.strip(),
            email=payload.email.strip().lower(),
            hashed_password=get_password_hash(payload.password),
            role=payload.role,
            is_active=True,
        )
        saved = await user_repository.create_user(db, new_user)
        logger.info("Created new user '%s' with role '%s'", saved.username, saved.role)
        return UserResponse.model_validate(saved)

    async def check_bootstrap_status(self, db: AsyncSession) -> BootstrapStatusResponse:
        """Query whether initial system administrator bootstrap is pending."""
        count = await user_repository.count_users(db)
        if count == 0:
            return BootstrapStatusResponse(
                bootstrap_required=True,
                message="No operators detected. Initial administrative bootstrap required.",
            )
        return BootstrapStatusResponse(
            bootstrap_required=False,
            message="System is already provisioned with administrative operator.",
        )

    async def execute_bootstrap(
        self,
        payload: BootstrapAdminRequest,
        db: AsyncSession,
    ) -> UserResponse:
        """Execute one-time administrative bootstrap with verified single-use token."""
        count = await user_repository.count_users(db)
        if count > 0:
            raise AuthenticationError(
                "System has already been provisioned. One-time bootstrap is permanently disabled."
            )

        # Retrieve valid bootstrap token
        expected_token = settings.bootstrap_token
        redis_key = "viewstorm:auth:bootstrap_token"
        if not expected_token:
            raw = await self._redis.get(redis_key)
            if raw:
                expected_token = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)

        if not expected_token:
            token_file = Path(settings.bootstrap_token_file)
            if token_file.exists():
                try:
                    expected_token = token_file.read_text().strip()
                except Exception:
                    pass

        if not expected_token or not secrets.compare_digest(payload.bootstrap_token.strip(), expected_token.strip()):
            logger.warning("Failed administrative bootstrap attempt: invalid or mismatched token.")
            raise AuthenticationError("Invalid or expired bootstrap token.")

        # Provision new root administrator
        admin_user = User(
            username=payload.username.strip(),
            email=payload.email.strip().lower(),
            hashed_password=get_password_hash(payload.password),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        saved = await user_repository.create_user(db, admin_user)
        logger.info("Root administrator '%s' successfully bootstrapped.", saved.username)

        # Invalidate and purge the bootstrap token permanently
        try:
            await self._redis.delete(redis_key)
            token_file = Path(settings.bootstrap_token_file)
            if token_file.exists():
                token_file.unlink()
            logger.info("One-time bootstrap secret successfully destroyed.")
        except Exception as e:
            logger.warning("Error cleaning up bootstrap token file: %s", e)

        return UserResponse.model_validate(saved)

    async def bootstrap_admin(self, db: AsyncSession) -> None:
        """Securely initialize bootstrap token or configure admin from explicit env vars."""
        count = await user_repository.count_users(db)
        if count == 0:
            if settings.admin_password:
                # Explicit password supplied via environment (e.g. secure CI/CD)
                admin_user = User(
                    username=settings.admin_username,
                    email=settings.admin_email,
                    hashed_password=get_password_hash(settings.admin_password),
                    role=UserRole.ADMIN.value,
                    is_active=True,
                )
                await user_repository.create_user(db, admin_user)
                logger.info(
                    "Admin user '%s' initialized via explicit environment variable.",
                    settings.admin_username,
                )
            else:
                # Generate unique, high-entropy one-time bootstrap secret
                token = settings.bootstrap_token or secrets.token_urlsafe(32)
                redis_key = "viewstorm:auth:bootstrap_token"
                await self._redis.set(redis_key, token, ex=86400)

                # Persist to local restricted file
                try:
                    token_file = Path(settings.bootstrap_token_file)
                    token_file.write_text(token)
                    os.chmod(settings.bootstrap_token_file, 0o600)
                    logger.warning(
                        "SECURITY PRECONDITION: No administrator exists. "
                        "One-time bootstrap token generated and written to '%s'. "
                        "Complete bootstrap via POST /api/v1/auth/bootstrap.",
                        settings.bootstrap_token_file,
                    )
                except Exception as e:
                    logger.warning("Could not write bootstrap token file: %s", e)


auth_service = AuthService()
