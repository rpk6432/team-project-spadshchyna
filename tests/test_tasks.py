from datetime import datetime, timedelta

import pytest
from conftest import seed_homestead
from sqlalchemy.ext.asyncio import AsyncSession

from models.booking import Booking
from tasks.bookings import PENDING_TTL_MINUTES, expire_pending_bookings


async def _create_booking(
    db: AsyncSession, homestead_id: int, user_id: int, *, minutes_ago: int
) -> Booking:
    booking = Booking(
        user_id=user_id,
        homestead_id=homestead_id,
        check_in=datetime.utcnow().date(),
        check_out=datetime.utcnow().date(),
        guests=1,
        status="pending",
        accommodation_total=1000,
        cleaning_fee=0,
        service_fee=0,
        donation_pct=0,
        donation_amount=0,
        total=1000,
        stripe_session_id=f"cs_test_{minutes_ago}",
        created_at=datetime.utcnow() - timedelta(minutes=minutes_ago),
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


@pytest.fixture
async def setup_data(db: AsyncSession) -> tuple[int, int]:
    """Seed homestead and user, return (homestead_id, user_id)."""
    from auth.utils import hash_password
    from models.user import User

    homestead = await seed_homestead(db)
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password_hash=hash_password("test1234"),
    )
    db.add(user)
    await db.flush()
    return homestead.id, user.id


@pytest.fixture(autouse=True)
def _patch_sync_session(db: AsyncSession) -> None:
    """Patch sync_session in tasks.bookings to reuse the test DB."""
    import database
    from config import Settings

    test_settings = Settings(_env_file=".env.test")
    sync_url = test_settings.database_url.replace("+asyncpg", "+psycopg")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    test_sync_engine = create_engine(sync_url, poolclass=NullPool)
    test_sync_session = sessionmaker(test_sync_engine, expire_on_commit=False)
    database.sync_session = test_sync_session


async def test_expire_old_pending_booking(
    db: AsyncSession, setup_data: tuple[int, int]
) -> None:
    homestead_id, user_id = setup_data
    booking = await _create_booking(
        db, homestead_id, user_id, minutes_ago=PENDING_TTL_MINUTES + 5
    )

    expire_pending_bookings()

    await db.refresh(booking)
    assert booking.status == "canceled"


async def test_fresh_pending_not_expired(
    db: AsyncSession, setup_data: tuple[int, int]
) -> None:
    homestead_id, user_id = setup_data
    booking = await _create_booking(db, homestead_id, user_id, minutes_ago=5)

    expire_pending_bookings()

    await db.refresh(booking)
    assert booking.status == "pending"


async def test_confirmed_booking_not_expired(
    db: AsyncSession, setup_data: tuple[int, int]
) -> None:
    homestead_id, user_id = setup_data
    booking = await _create_booking(
        db, homestead_id, user_id, minutes_ago=PENDING_TTL_MINUTES + 5
    )
    booking.status = "confirmed"
    await db.commit()

    expire_pending_bookings()

    await db.refresh(booking)
    assert booking.status == "confirmed"
