from datetime import date, timedelta

from conftest import API, auth_header, get_user_id, seed_homestead
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.booking import Booking
from models.favourite import Favourite

# Empty dashboard


async def test_dashboard_empty(client: AsyncClient) -> None:
    headers = await auth_header(client)
    resp = await client.get(f"{API}/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["total_nights"] == 0

    assert data["stats"]["total_donated"] == 0
    assert data["upcoming_stay"] is None
    assert data["past_journeys"] == []
    assert data["favourite_homesteads"] == []


# Dashboard with data


async def test_dashboard_with_bookings(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await seed_homestead(db)
    headers = await auth_header(client)
    user_id = await get_user_id(client, headers)

    today = date.today()

    # Past booking (3 nights, confirmed)
    past = Booking(
        user_id=user_id,
        homestead_id=homestead.id,
        check_in=today - timedelta(days=10),
        check_out=today - timedelta(days=7),
        guests=2,
        status="confirmed",
        accommodation_total=3600,
        cleaning_fee=500,
        service_fee=108,
        donation_pct=5,
        donation_amount=180,
        total=4388,
        stripe_session_id="cs_past_1",
    )

    # Upcoming booking (2 nights, confirmed)
    future = Booking(
        user_id=user_id,
        homestead_id=homestead.id,
        check_in=today + timedelta(days=5),
        check_out=today + timedelta(days=7),
        guests=3,
        status="confirmed",
        accommodation_total=2400,
        cleaning_fee=500,
        service_fee=72,
        donation_pct=0,
        donation_amount=0,
        total=2972,
        stripe_session_id="cs_future_1",
    )

    db.add_all([past, future])
    await db.commit()

    resp = await client.get(f"{API}/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Stats: past (3 nights, 180 donated) + future (2 nights, 0 donated)
    assert data["stats"]["total_nights"] == 5

    assert data["stats"]["total_donated"] == 180

    # Upcoming stay
    assert data["upcoming_stay"] is not None
    assert data["upcoming_stay"]["guests"] == 3
    assert data["upcoming_stay"]["region"] == "Carpathians"
    assert data["upcoming_stay"]["main_photo"] is not None

    # Past journeys
    assert len(data["past_journeys"]) == 1
    assert data["past_journeys"][0]["homestead_name"] == "Stara Khata"
    assert data["past_journeys"][0]["region"] == "Carpathians"
    assert data["past_journeys"][0]["main_photo"] is not None
    assert data["past_journeys"][0]["rating"] >= 0


async def test_dashboard_with_favourites(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await seed_homestead(db)
    headers = await auth_header(client)
    user_id = await get_user_id(client, headers)

    db.add(Favourite(user_id=user_id, homestead_id=homestead.id))
    await db.commit()

    resp = await client.get(f"{API}/dashboard", headers=headers)
    assert resp.status_code == 200
    favs = resp.json()["favourite_homesteads"]
    assert len(favs) == 1
    assert favs[0]["name"] == "Stara Khata"
    assert favs[0]["main_photo"] is not None


# Unauthenticated


async def test_dashboard_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/dashboard")
    assert resp.status_code == 401
