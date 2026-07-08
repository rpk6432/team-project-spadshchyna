from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dashboard.schemas import (
    DashboardResponse,
    DashboardStats,
    FavouriteItem,
    PastJourney,
    UpcomingStay,
)
from homesteads.service import main_photo
from models.booking import Booking
from models.favourite import Favourite
from models.homestead import Homestead
from models.region import Region

_ACTIVE_STATUSES = ["confirmed", "completed"]


async def get_dashboard(db: AsyncSession, user_id: int) -> DashboardResponse:
    today = datetime.now(UTC).date()
    stats = await _get_stats(db, user_id)
    upcoming = await _get_upcoming(db, user_id, today)
    past = await _get_past_journeys(db, user_id, today)
    favourites = await _get_favourites(db, user_id)
    return DashboardResponse(
        stats=stats,
        upcoming_stay=upcoming,
        past_journeys=past,
        favourite_homesteads=favourites,
    )


async def _get_stats(db: AsyncSession, user_id: int) -> DashboardStats:
    result = await db.execute(
        select(
            func.coalesce(func.sum(Booking.check_out - Booking.check_in), 0),
            func.coalesce(func.sum(Booking.donation_amount), 0),
        )
        .join(Homestead, Booking.homestead_id == Homestead.id)
        .where(Booking.user_id == user_id, Booking.status.in_(_ACTIVE_STATUSES))
    )
    nights, donated = result.one()
    return DashboardStats(
        total_nights=int(nights),
        total_donated=int(donated),
    )


async def _get_upcoming(
    db: AsyncSession, user_id: int, today: date
) -> UpcomingStay | None:
    result = await db.execute(
        select(Booking)
        .join(Homestead, Booking.homestead_id == Homestead.id)
        .options(
            selectinload(Booking.homestead)
            .load_only(Homestead.name, Homestead.region_id)
            .selectinload(Homestead.region)
            .load_only(Region.name),
            selectinload(Booking.homestead).selectinload(Homestead.photos),
        )
        .where(
            Booking.user_id == user_id,
            Booking.status.in_(_ACTIVE_STATUSES),
            Booking.check_out > today,
        )
        .order_by(Booking.check_in)
        .limit(1)
    )
    booking = result.scalar_one_or_none()
    if booking is None:
        return None
    return UpcomingStay(
        booking_id=booking.id,
        homestead_name=booking.homestead.name,
        region=booking.homestead.region.name,
        main_photo=main_photo(booking.homestead),
        check_in=booking.check_in,
        check_out=booking.check_out,
        guests=booking.guests,
    )


async def _get_past_journeys(
    db: AsyncSession, user_id: int, today: date
) -> list[PastJourney]:
    result = await db.execute(
        select(Booking)
        .join(Homestead, Booking.homestead_id == Homestead.id)
        .options(
            selectinload(Booking.homestead)
            .load_only(Homestead.name, Homestead.region_id, Homestead.rating)
            .selectinload(Homestead.region)
            .load_only(Region.name),
            selectinload(Booking.homestead).selectinload(Homestead.photos),
        )
        .where(
            Booking.user_id == user_id,
            Booking.status.in_(_ACTIVE_STATUSES),
            Booking.check_out <= today,
        )
        .order_by(Booking.check_out.desc())
        .limit(3)
    )
    return [
        PastJourney(
            booking_id=b.id,
            homestead_name=b.homestead.name,
            region=b.homestead.region.name,
            main_photo=main_photo(b.homestead),
            rating=b.homestead.rating,
            check_in=b.check_in,
            check_out=b.check_out,
        )
        for b in result.scalars().all()
    ]


async def _get_favourites(db: AsyncSession, user_id: int) -> list[FavouriteItem]:
    result = await db.execute(
        select(Homestead)
        .join(Favourite, Favourite.homestead_id == Homestead.id)
        .where(Favourite.user_id == user_id, Homestead.is_active.is_(True))
        .options(selectinload(Homestead.photos))
        .order_by(Favourite.created_at.desc())
        .limit(5)
    )
    return [
        FavouriteItem(
            id=h.id,
            name=h.name,
            main_photo=main_photo(h),
        )
        for h in result.scalars().all()
    ]
