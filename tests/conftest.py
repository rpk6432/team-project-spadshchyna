from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import Settings
from database import get_db_session
from main import app
from models import Base
from models.homestead import Homestead, HomesteadPhoto
from models.host import Host
from models.region import Region

test_settings = Settings(_env_file=".env.test")
test_engine = create_async_engine(test_settings.database_url)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def _override_get_db_session() -> AsyncIterator[AsyncSession]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
async def setup_tables() -> AsyncIterator[None]:
    async with test_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    async with test_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
async def reset_redis() -> AsyncIterator[None]:
    import core.redis as redis_module

    redis_module._client = Redis.from_url(
        test_settings.redis_url, decode_responses=True
    )
    await redis_module._client.flushdb()
    yield
    await redis_module._client.flushdb()
    await redis_module._client.aclose()


@pytest.fixture(autouse=True)
def _mock_email_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent email tasks from hitting the Celery broker during tests."""
    import tasks.email as email_module

    monkeypatch.setattr(email_module.send_welcome_email, "delay", lambda *a, **kw: None)
    monkeypatch.setattr(
        email_module.send_booking_confirmed, "delay", lambda *a, **kw: None
    )


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    import admin.auth as admin_auth_module
    import database

    app.dependency_overrides[get_db_session] = _override_get_db_session
    original_session = database.async_session
    database.async_session = test_session_factory
    admin_auth_module.async_session = test_session_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    database.async_session = original_session
    admin_auth_module.async_session = original_session
    app.dependency_overrides.clear()


# Shared test helpers

API = "/api/v1"
AUTH = "/api/v1/auth"

REGISTER_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "password": "securepass123",
}


async def seed_homestead(db: AsyncSession) -> Homestead:
    """Insert minimal data and return a homestead."""

    region = Region(name="Carpathians", slug="carpathians")
    host = Host(name="Olha", email="olha@example.com", languages=["Ukrainian"])
    db.add_all([region, host])
    await db.flush()

    homestead = Homestead(
        host_id=host.id,
        region_id=region.id,
        name="Stara Khata",
        location="Yaremche village",
        description="A cozy village house.",
        price_per_night=1200,
        base_guests=2,
        extra_guest_fee=300,
        max_guests=5,
        cleaning_fee=500,
        bedrooms=2,
        beds=3,
        bathrooms=1,
        rating=4.8,
        review_count=1,
    )
    db.add(homestead)
    await db.flush()

    photo = HomesteadPhoto(
        homestead_id=homestead.id, url="homesteads/1/main.jpg", is_main=True
    )
    db.add(photo)
    await db.commit()
    return homestead


async def auth_header(client: AsyncClient) -> dict[str, str]:
    """Register a user and return Authorization header."""
    resp = await client.post(f"{AUTH}/register", json=REGISTER_DATA)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def get_user_id(client: AsyncClient, headers: dict[str, str]) -> int:
    """Return the user ID from /auth/me."""
    resp = await client.get(f"{AUTH}/me", headers=headers)
    return resp.json()["id"]
