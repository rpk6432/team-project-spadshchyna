import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from auth.utils import create_access_token, hash_password, verify_password
from config import settings
from core.exceptions import AlreadyExistsError, UnauthorizedError
from core.redis import get_redis
from models.user import User
from tasks.email import send_welcome_email

REFRESH_PREFIX = "refresh:"
REFRESH_TTL = settings.jwt_refresh_ttl_days * 86400


async def _generate_tokens(user_id: int) -> tuple[str, str]:
    access_token = create_access_token(user_id)
    refresh_token = str(uuid.uuid4())
    await get_redis().setex(
        f"{REFRESH_PREFIX}{refresh_token}", REFRESH_TTL, str(user_id)
    )
    return access_token, refresh_token


async def register(db: AsyncSession, body: RegisterRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise AlreadyExistsError("Email already registered")

    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()

    send_welcome_email.delay(user.email, body.first_name)

    access_token, refresh_token = await _generate_tokens(user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def login(db: AsyncSession, body: LoginRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    access_token, refresh_token = await _generate_tokens(user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh(body: RefreshRequest) -> AccessTokenResponse:
    key = f"{REFRESH_PREFIX}{body.refresh_token}"
    user_id = await get_redis().get(key)
    if user_id is None:
        raise UnauthorizedError("Invalid refresh token")

    access_token = create_access_token(int(user_id))
    return AccessTokenResponse(access_token=access_token)


async def logout(refresh_token: str) -> None:
    key = f"{REFRESH_PREFIX}{refresh_token}"
    deleted = await get_redis().delete(key)
    if not deleted:
        raise UnauthorizedError("Invalid refresh token")
