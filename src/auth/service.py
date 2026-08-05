import secrets

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
from core.exceptions import AlreadyExistsError, BadRequestError, UnauthorizedError
from core.redis import get_redis
from models.user import User
from tasks.email import send_reset_code_email, send_welcome_email

REFRESH_PREFIX = "refresh:"
REFRESH_TTL = settings.jwt_refresh_ttl_days * 86400

RESET_PREFIX = "reset:"
RESET_COOLDOWN_PREFIX = "reset_cooldown:"
RESET_ATTEMPTS_PREFIX = "reset_attempts:"
RESET_TTL = 600
COOLDOWN_TTL = 15
MAX_RESET_ATTEMPTS = 5


async def _generate_tokens(user_id: int) -> tuple[str, str]:
    access_token = create_access_token(user_id)
    refresh_token = secrets.token_urlsafe(32)
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


async def forgot_password(db: AsyncSession, email: str) -> None:
    redis = get_redis()

    cooldown_key = f"{RESET_COOLDOWN_PREFIX}{email}"
    if await redis.exists(cooldown_key):
        return

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        return

    code = secrets.randbelow(900000) + 100000

    await redis.setex(f"{RESET_PREFIX}{email}", RESET_TTL, f"{code}:{user.id}")
    await redis.setex(cooldown_key, COOLDOWN_TTL, "1")
    await redis.delete(f"{RESET_ATTEMPTS_PREFIX}{email}")

    send_reset_code_email.delay(email, user.first_name, str(code))


async def reset_password(
    db: AsyncSession, email: str, code: str, new_password: str
) -> None:
    redis = get_redis()

    reset_key = f"{RESET_PREFIX}{email}"
    stored = await redis.get(reset_key)
    if stored is None:
        raise BadRequestError("Invalid or expired code")

    attempts_key = f"{RESET_ATTEMPTS_PREFIX}{email}"
    attempts = await redis.incr(attempts_key)
    if attempts == 1:
        await redis.expire(attempts_key, RESET_TTL)
    if attempts > MAX_RESET_ATTEMPTS:
        await redis.delete(reset_key)
        await redis.delete(attempts_key)
        raise BadRequestError("Too many attempts, request a new code")

    stored_code, user_id = stored.split(":", 1)
    if code != stored_code:
        raise BadRequestError("Invalid or expired code")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise BadRequestError("Invalid or expired code")

    user.password_hash = hash_password(new_password)
    await db.flush()

    await redis.delete(reset_key)
    await redis.delete(attempts_key)

    cursor: int = 0
    while True:
        cursor, keys = await redis.scan(cursor, match=f"{REFRESH_PREFIX}*", count=100)
        for k in keys:
            if await redis.get(k) == user_id:
                await redis.delete(k)
        if cursor == 0:
            break
