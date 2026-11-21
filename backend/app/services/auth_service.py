"""Authentication and Operator RBAC Service."""

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

    async def bootstrap_admin(self, db: AsyncSession) -> None:
        """Ensure initial administrative account exists on system startup."""
        count = await user_repository.count_users(db)
        if count == 0:
            admin_user = User(
                username=settings.admin_username,
                email=settings.admin_email,
                hashed_password=get_password_hash(settings.admin_password),
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            await user_repository.create_user(db, admin_user)
            logger.info(
                "Initial admin user '%s' bootstrapped successfully.",
                settings.admin_username,
            )


auth_service = AuthService()
