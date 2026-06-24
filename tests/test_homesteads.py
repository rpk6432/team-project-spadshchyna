from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.amenity import Amenity, homestead_amenity
from models.booking import Booking
from models.homestead import Homestead, HomesteadPhoto
from models.host import Host
from models.region import Region
from models.review import Review
from models.user import User

API = "/api/v1"


async def _seed(db: AsyncSession) -> tuple[Homestead, User]:
    """Insert minimal seed data and return the homestead and user."""
    region = Region(name="Khmelnytskyi Region", slug="khmelnytskyi")
    host = Host(name="Olha", email="olha@example.com", languages=["Ukrainian"])
    user = User(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password_hash="hashed",
    )
    db.add_all([region, host, user])
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
    amenity = Amenity(name="Traditional stove")
    db.add_all([photo, amenity])
    await db.flush()

    await db.execute(
        homestead_amenity.insert().values(
            homestead_id=homestead.id, amenity_id=amenity.id
        )
    )

    review = Review(
        homestead_id=homestead.id,
        category="atmosphere",
        text="Wonderful stay!",
        author_name="John Doe",
        country="Ukraine",
        rating=4.8,
    )
    db.add(review)
    await db.commit()
    return homestead, user


# Catalog


async def test_catalog_empty(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/homesteads")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_catalog_with_data(client: AsyncClient, db: AsyncSession) -> None:
    await _seed(db)
    resp = await client.get(f"{API}/homesteads")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    card = data["items"][0]
    assert card["name"] == "Stara Khata"
    assert card["region"] == "Khmelnytskyi Region"
    assert card["main_photo"] is not None


async def test_catalog_filter_region(client: AsyncClient, db: AsyncSession) -> None:
    await _seed(db)
    resp = await client.get(f"{API}/homesteads", params={"region_id": 999})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_catalog_filter_price(client: AsyncClient, db: AsyncSession) -> None:
    await _seed(db)
    resp = await client.get(f"{API}/homesteads", params={"price_min": 2000})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    resp = await client.get(f"{API}/homesteads", params={"price_max": 2000})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_catalog_filter_guests(client: AsyncClient, db: AsyncSession) -> None:
    await _seed(db)
    resp = await client.get(f"{API}/homesteads", params={"guests": 10})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    resp = await client.get(f"{API}/homesteads", params={"guests": 3})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_catalog_pagination(client: AsyncClient, db: AsyncSession) -> None:
    await _seed(db)
    resp = await client.get(f"{API}/homesteads", params={"limit": 1, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["limit"] == 1
    assert data["offset"] == 0

    resp = await client.get(f"{API}/homesteads", params={"limit": 1, "offset": 1})
    assert resp.json()["items"] == []


# Detail


async def test_detail_success(client: AsyncClient, db: AsyncSession) -> None:
    hs, _ = await _seed(db)
    resp = await client.get(f"{API}/homesteads/{hs.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Stara Khata"
    assert data["host"]["name"] == "Olha"
    assert len(data["photos"]) == 1
    assert len(data["amenities"]) == 1
    assert len(data["reviews"]) == 1
    assert data["pricing"]["service_fee_pct"] == 3
    assert data["is_favourited"] is None


async def test_detail_not_found(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/homesteads/99999")
    assert resp.status_code == 404


async def test_detail_inactive(client: AsyncClient, db: AsyncSession) -> None:
    hs, _ = await _seed(db)
    hs.is_active = False
    db.add(hs)
    await db.commit()

    resp = await client.get(f"{API}/homesteads/{hs.id}")
    assert resp.status_code == 404


# Availability


async def test_availability_available(client: AsyncClient, db: AsyncSession) -> None:
    hs, _ = await _seed(db)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=3)
    resp = await client.post(
        f"{API}/homesteads/{hs.id}/check-availability",
        json={
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert data["nights"] == 3
    assert data["accommodation_total"] == 3600
    assert data["cleaning_fee"] == 500
    assert data["service_fee"] == 108
    assert data["total"] == 4208


async def test_availability_conflict(client: AsyncClient, db: AsyncSession) -> None:
    hs, user = await _seed(db)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=3)

    booking = Booking(
        user_id=user.id,
        homestead_id=hs.id,
        check_in=check_in,
        check_out=check_out,
        guests=2,
        status="confirmed",
        accommodation_total=3600,
        cleaning_fee=500,
        service_fee=108,
        donation_pct=0,
        donation_amount=0,
        total=4208,
        stripe_session_id="cs_test_123",
    )
    db.add(booking)
    await db.commit()

    resp = await client.post(
        f"{API}/homesteads/{hs.id}/check-availability",
        json={
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 2,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["available"] is False


async def test_availability_past_date(client: AsyncClient, db: AsyncSession) -> None:
    hs, _ = await _seed(db)
    resp = await client.post(
        f"{API}/homesteads/{hs.id}/check-availability",
        json={"check_in": "2020-01-01", "check_out": "2020-01-05", "guests": 2},
    )
    assert resp.status_code == 400


async def test_availability_too_many_guests(
    client: AsyncClient, db: AsyncSession
) -> None:
    hs, _ = await _seed(db)
    check_in = date.today() + timedelta(days=10)
    check_out = check_in + timedelta(days=2)
    resp = await client.post(
        f"{API}/homesteads/{hs.id}/check-availability",
        json={
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 99,
        },
    )
    assert resp.status_code == 400


async def test_availability_invalid_dates(
    client: AsyncClient, db: AsyncSession
) -> None:
    hs, _ = await _seed(db)
    check_in = date.today() + timedelta(days=10)
    resp = await client.post(
        f"{API}/homesteads/{hs.id}/check-availability",
        json={
            "check_in": check_in.isoformat(),
            "check_out": check_in.isoformat(),
            "guests": 2,
        },
    )
    assert resp.status_code == 422


# Recommendations


async def test_recommendations(client: AsyncClient, db: AsyncSession) -> None:
    hs, _ = await _seed(db)
    resp = await client.get(f"{API}/homesteads/{hs.id}/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    for card in data:
        assert card["id"] != hs.id


async def test_recommendations_not_found(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/homesteads/99999/recommendations")
    assert resp.status_code == 404


# Regions


async def test_regions(client: AsyncClient, db: AsyncSession) -> None:
    await _seed(db)
    resp = await client.get(f"{API}/regions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Khmelnytskyi Region"
    assert data[0]["slug"] == "khmelnytskyi"


async def test_regions_empty(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/regions")
    assert resp.status_code == 200
    assert resp.json() == []
