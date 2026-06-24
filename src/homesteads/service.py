import random
from datetime import UTC, date, datetime
from math import floor
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from core.exceptions import BadRequestError, NotFoundError
from homesteads.filters import HomesteadFilters
from homesteads.schemas import (
    AmenityResponse,
    AvailabilityRequest,
    AvailabilityResponse,
    HomesteadCard,
    HomesteadDetail,
    HostResponse,
    PhotoResponse,
    PricingResponse,
    RegionResponse,
    ReviewResponse,
)
from models.booking import Booking
from models.favourite import Favourite
from models.homestead import Homestead
from models.region import Region
from s3.client import get_public_url


def _photo_url(url: str | None) -> str | None:
    return get_public_url(url) if url else None


def main_photo(homestead: Homestead) -> str | None:
    for photo in homestead.photos:
        if photo.is_main:
            return _photo_url(photo.url)
    if homestead.photos:
        return _photo_url(homestead.photos[0].url)
    return None


async def _favourited_ids(
    db: AsyncSession, user_id: int | None, homestead_ids: list[int]
) -> dict[int, bool | None]:
    """Return {homestead_id: True/False} for authenticated, {id: None} for anonymous."""
    if user_id is None:
        return {hid: None for hid in homestead_ids}
    if not homestead_ids:
        return {}
    result = await db.execute(
        select(Favourite.homestead_id).where(
            Favourite.user_id == user_id,
            Favourite.homestead_id.in_(homestead_ids),
        )
    )
    fav_set = set(result.scalars().all())
    return {hid: hid in fav_set for hid in homestead_ids}


class PriceBreakdown(NamedTuple):
    nights: int
    accommodation: int
    cleaning: int
    service_fee: int
    total: int


def compute_price(
    homestead: Homestead, check_in: date, check_out: date, guests: int
) -> PriceBreakdown:
    """Compute price breakdown for a homestead booking."""
    nights = (check_out - check_in).days
    extra_guests = max(0, guests - homestead.base_guests)
    accommodation = (
        homestead.price_per_night + homestead.extra_guest_fee * extra_guests
    ) * nights
    cleaning = homestead.cleaning_fee
    service_fee = floor(accommodation * settings.service_fee_pct / 100)
    total = accommodation + cleaning + service_fee
    return PriceBreakdown(nights, accommodation, cleaning, service_fee, total)


async def get_validated_homestead(
    db: AsyncSession, homestead_id: int, check_in: date, guests: int
) -> Homestead:
    """Fetch active homestead and validate booking params."""
    result = await db.execute(
        select(Homestead).where(
            Homestead.id == homestead_id, Homestead.is_active.is_(True)
        )
    )
    homestead = result.scalar_one_or_none()
    if homestead is None:
        raise NotFoundError("Homestead not found")

    today = datetime.now(UTC).date()
    if check_in < today:
        raise BadRequestError("check_in must be today or later")
    if guests > homestead.max_guests:
        raise BadRequestError(f"Maximum {homestead.max_guests} guests allowed")

    return homestead


def to_card(homestead: Homestead, is_favourited: bool | None = None) -> HomesteadCard:
    return HomesteadCard(
        id=homestead.id,
        name=homestead.name,
        location=homestead.location,
        region=homestead.region.name,
        price_per_night=homestead.price_per_night,
        rating=homestead.rating,
        review_count=homestead.review_count,
        main_photo=main_photo(homestead),
        is_favourited=is_favourited,
    )


async def get_catalog(
    db: AsyncSession, filters: HomesteadFilters, user_id: int | None = None
) -> tuple[list[HomesteadCard], int]:
    base = select(Homestead)
    base = filters.apply(base)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    items_q = (
        base.options(
            selectinload(Homestead.region),
            selectinload(Homestead.photos),
        )
        .order_by(Homestead.id.asc())
        .limit(filters.limit)
        .offset(filters.offset)
    )
    result = await db.execute(items_q)
    homesteads = list(result.scalars().all())

    fav_ids = await _favourited_ids(db, user_id, [h.id for h in homesteads])
    return [to_card(h, fav_ids.get(h.id)) for h in homesteads], total


async def get_detail(
    db: AsyncSession, homestead_id: int, user_id: int | None
) -> HomesteadDetail:
    query = (
        select(Homestead)
        .where(Homestead.id == homestead_id, Homestead.is_active.is_(True))
        .options(
            selectinload(Homestead.region),
            selectinload(Homestead.host),
            selectinload(Homestead.photos),
            selectinload(Homestead.amenities),
            selectinload(Homestead.reviews),
        )
    )
    result = await db.execute(query)
    homestead = result.scalar_one_or_none()
    if homestead is None:
        raise NotFoundError("Homestead not found")

    is_favourited: bool | None = None
    if user_id is not None:
        fav_q = select(Favourite.id).where(
            Favourite.user_id == user_id,
            Favourite.homestead_id == homestead_id,
        )
        is_favourited = (await db.execute(fav_q)).scalar_one_or_none() is not None

    all_amenities = [AmenityResponse(id=a.id, name=a.name) for a in homestead.amenities]
    sample_size = min(3, len(all_amenities))
    featured = random.sample(all_amenities, sample_size)

    return HomesteadDetail(
        id=homestead.id,
        name=homestead.name,
        location=homestead.location,
        description=homestead.description,
        bedrooms=homestead.bedrooms,
        beds=homestead.beds,
        bathrooms=homestead.bathrooms,
        rating=homestead.rating,
        review_count=homestead.review_count,
        region=homestead.region.name,
        host=HostResponse(
            id=homestead.host.id,
            name=homestead.host.name,
            photo_url=_photo_url(homestead.host.photo_url),
            languages=homestead.host.languages,
        ),
        photos=[
            PhotoResponse(
                id=p.id,
                url=get_public_url(p.url),
                is_main=p.is_main,
                sort_order=p.sort_order,
            )
            for p in homestead.photos
        ],
        amenities=all_amenities,
        featured_amenities=featured,
        reviews=[
            ReviewResponse(
                id=r.id,
                category=r.category,
                text=r.text,
                author_name=r.author_name,
                country=r.country,
                rating=r.rating,
                created_at=r.created_at,
            )
            for r in homestead.reviews
        ],
        pricing=PricingResponse(
            price_per_night=homestead.price_per_night,
            base_guests=homestead.base_guests,
            extra_guest_fee=homestead.extra_guest_fee,
            max_guests=homestead.max_guests,
            cleaning_fee=homestead.cleaning_fee,
            service_fee_pct=settings.service_fee_pct,
        ),
        is_favourited=is_favourited,
    )


async def check_availability(
    db: AsyncSession, homestead_id: int, body: AvailabilityRequest
) -> AvailabilityResponse:
    homestead = await get_validated_homestead(
        db, homestead_id, body.check_in, body.guests
    )

    price = compute_price(homestead, body.check_in, body.check_out, body.guests)

    overlap_q = select(Booking.id).where(
        Booking.homestead_id == homestead_id,
        Booking.status == "confirmed",
        Booking.check_in < body.check_out,
        Booking.check_out > body.check_in,
    )
    conflict = (await db.execute(overlap_q)).scalar_one_or_none()
    available = conflict is None

    return AvailabilityResponse(
        available=available,
        nights=price.nights,
        accommodation_total=price.accommodation,
        cleaning_fee=price.cleaning,
        service_fee=price.service_fee,
        total=price.total,
    )


async def get_recommendations(
    db: AsyncSession, homestead_id: int, user_id: int | None = None
) -> list[HomesteadCard]:
    exists = await db.execute(
        select(Homestead.id).where(
            Homestead.id == homestead_id, Homestead.is_active.is_(True)
        )
    )
    if exists.scalar_one_or_none() is None:
        raise NotFoundError("Homestead not found")

    query = (
        select(Homestead)
        .where(Homestead.is_active.is_(True), Homestead.id != homestead_id)
        .options(
            selectinload(Homestead.region),
            selectinload(Homestead.photos),
        )
        .order_by(func.random())
        .limit(4)
    )
    result = await db.execute(query)
    homesteads = list(result.scalars().all())

    fav_ids = await _favourited_ids(db, user_id, [h.id for h in homesteads])
    return [to_card(h, fav_ids.get(h.id)) for h in homesteads]


async def get_regions(db: AsyncSession) -> list[RegionResponse]:
    result = await db.execute(select(Region).order_by(Region.name))
    return [
        RegionResponse(id=r.id, name=r.name, slug=r.slug)
        for r in result.scalars().all()
    ]
