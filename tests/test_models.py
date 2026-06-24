from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Amenity,
    Booking,
    Favourite,
    Homestead,
    HomesteadPhoto,
    Host,
    Region,
    Review,
    User,
)


async def _create_user(db: AsyncSession) -> User:
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password_hash="fakehash",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_region(db: AsyncSession) -> Region:
    region = Region(name="Carpathians", slug="carpathians")
    db.add(region)
    await db.commit()
    await db.refresh(region)
    return region


async def _create_host(db: AsyncSession) -> Host:
    host = Host(
        name="Ivan Petrenko",
        languages=["uk", "en"],
        email="host@example.com",
    )
    db.add(host)
    await db.commit()
    await db.refresh(host)
    return host


async def _create_homestead(db: AsyncSession, host: Host, region: Region) -> Homestead:
    homestead = Homestead(
        host_id=host.id,
        region_id=region.id,
        name="Test Homestead",
        location="Yaremche village",
        description="A lovely place to stay",
        price_per_night=1000,
        base_guests=2,
        extra_guest_fee=200,
        max_guests=6,
        cleaning_fee=300,
        bedrooms=2,
        beds=3,
        bathrooms=1,
    )
    db.add(homestead)
    await db.commit()
    await db.refresh(homestead)
    return homestead


async def test_create_user(db: AsyncSession) -> None:
    user = await _create_user(db)
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.is_admin is False


async def test_create_region(db: AsyncSession) -> None:
    region = await _create_region(db)
    assert region.id is not None
    assert region.slug == "carpathians"


async def test_create_host(db: AsyncSession) -> None:
    host = await _create_host(db)
    assert host.id is not None
    assert host.languages == ["uk", "en"]
    assert host.photo_url is None


async def test_create_homestead_with_photo(db: AsyncSession) -> None:
    host = await _create_host(db)
    region = await _create_region(db)
    homestead = await _create_homestead(db, host, region)

    photo = HomesteadPhoto(
        homestead_id=homestead.id, url="http://example.com/photo.jpg", is_main=True
    )
    db.add(photo)
    await db.commit()

    await db.refresh(homestead, ["photos"])
    assert len(homestead.photos) == 1
    assert homestead.photos[0].is_main is True


async def test_homestead_amenity_m2m(db: AsyncSession) -> None:
    host = await _create_host(db)
    region = await _create_region(db)
    homestead = await _create_homestead(db, host, region)

    amenity = Amenity(name="Wi-Fi")
    db.add(amenity)
    await db.commit()

    await db.refresh(homestead, ["amenities"])
    homestead.amenities.append(amenity)
    await db.commit()

    await db.refresh(homestead, ["amenities"])
    assert len(homestead.amenities) == 1
    assert homestead.amenities[0].name == "Wi-Fi"


async def test_create_review(db: AsyncSession) -> None:
    host = await _create_host(db)
    region = await _create_region(db)
    homestead = await _create_homestead(db, host, region)

    review = Review(
        homestead_id=homestead.id,
        category="location",
        text="Wonderful place!",
        author_name="Maria",
        country="Ukraine",
        rating=4.5,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    assert review.id is not None
    assert review.rating == 4.5


async def test_create_booking(db: AsyncSession) -> None:
    user = await _create_user(db)
    host = await _create_host(db)
    region = await _create_region(db)
    homestead = await _create_homestead(db, host, region)

    booking = Booking(
        user_id=user.id,
        homestead_id=homestead.id,
        check_in=date(2025, 7, 1),
        check_out=date(2025, 7, 5),
        guests=2,
        status="pending",
        accommodation_total=4000,
        cleaning_fee=300,
        service_fee=120,
        donation_pct=0.0,
        donation_amount=0,
        total=4420,
        stripe_session_id="cs_test_123",
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    assert booking.id is not None
    assert booking.total == 4420


async def test_create_favourite(db: AsyncSession) -> None:
    user = await _create_user(db)
    host = await _create_host(db)
    region = await _create_region(db)
    homestead = await _create_homestead(db, host, region)

    fav = Favourite(user_id=user.id, homestead_id=homestead.id)
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    assert fav.id is not None


async def test_cascade_delete_homestead_photos(db: AsyncSession) -> None:
    host = await _create_host(db)
    region = await _create_region(db)
    homestead = await _create_homestead(db, host, region)

    photo = HomesteadPhoto(homestead_id=homestead.id, url="http://example.com/1.jpg")
    db.add(photo)
    await db.commit()

    await db.delete(homestead)
    await db.commit()

    result = await db.execute(select(HomesteadPhoto))
    assert result.scalars().all() == []
