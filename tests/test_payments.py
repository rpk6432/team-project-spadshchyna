from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.booking import Booking
from models.homestead import Homestead, HomesteadPhoto
from models.host import Host
from models.region import Region

API = "/api/v1"
AUTH = "/api/v1/auth"

REGISTER_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "password": "securepass123",
}


async def _seed(db: AsyncSession) -> Homestead:
    """Insert minimal data and return a homestead."""
    region = Region(name="Carpathians", slug="carpathians")
    host = Host(name="Olha", email="olha@example.com", languages=["Ukrainian"])
    db.add_all([region, host])
    await db.flush()

    homestead = Homestead(
        host_id=host.id,
        region_id=region.id,
        name="Stara Khata",
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


async def _auth_header(client: AsyncClient) -> dict[str, str]:
    """Register a user and return Authorization header."""
    resp = await client.post(f"{AUTH}/register", json=REGISTER_DATA)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _mock_stripe_session() -> MagicMock:
    """Return a mock Stripe Checkout Session."""
    session = MagicMock()
    session.id = "cs_test_123"
    session.url = "https://checkout.stripe.com/test"
    return session


def _booking_body(homestead_id: int) -> dict:
    """Return a valid booking request body."""
    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=3)
    return {
        "homestead_id": homestead_id,
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "guests": 2,
        "donation_pct": 5,
    }


# Create booking


@patch("payments.service.stripe.checkout.Session.create")
async def test_create_booking(
    mock_create: MagicMock, client: AsyncClient, db: AsyncSession
) -> None:
    mock_create.return_value = _mock_stripe_session()
    homestead = await _seed(db)
    headers = await _auth_header(client)

    resp = await client.post(
        f"{API}/bookings", json=_booking_body(homestead.id), headers=headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["checkout_url"] == "https://checkout.stripe.com/test"
    assert data["homestead_id"] == homestead.id
    assert data["nights"] == 3
    assert data["donation_amount"] > 0


@patch("payments.service.stripe.checkout.Session.create")
async def test_create_booking_dates_conflict(
    mock_create: MagicMock, client: AsyncClient, db: AsyncSession
) -> None:
    mock_create.return_value = _mock_stripe_session()
    homestead = await _seed(db)
    headers = await _auth_header(client)
    body = _booking_body(homestead.id)

    await client.post(f"{API}/bookings", json=body, headers=headers)
    resp = await client.post(f"{API}/bookings", json=body, headers=headers)
    assert resp.status_code == 409


@patch("payments.service.stripe.checkout.Session.create")
async def test_create_booking_past_date(
    mock_create: MagicMock, client: AsyncClient, db: AsyncSession
) -> None:
    homestead = await _seed(db)
    headers = await _auth_header(client)
    body = _booking_body(homestead.id)
    body["check_in"] = "2020-01-01"
    body["check_out"] = "2020-01-05"

    resp = await client.post(f"{API}/bookings", json=body, headers=headers)
    assert resp.status_code == 400


@patch("payments.service.stripe.checkout.Session.create")
async def test_create_booking_too_many_guests(
    mock_create: MagicMock, client: AsyncClient, db: AsyncSession
) -> None:
    homestead = await _seed(db)
    headers = await _auth_header(client)
    body = _booking_body(homestead.id)
    body["guests"] = 99

    resp = await client.post(f"{API}/bookings", json=body, headers=headers)
    assert resp.status_code == 400


async def test_create_booking_not_found(client: AsyncClient) -> None:
    headers = await _auth_header(client)
    resp = await client.post(
        f"{API}/bookings", json=_booking_body(99999), headers=headers
    )
    assert resp.status_code == 404


async def test_create_booking_unauthenticated(
    client: AsyncClient, db: AsyncSession
) -> None:
    homestead = await _seed(db)
    resp = await client.post(f"{API}/bookings", json=_booking_body(homestead.id))
    assert resp.status_code == 401


# List bookings


async def test_list_bookings_empty(client: AsyncClient) -> None:
    headers = await _auth_header(client)
    resp = await client.get(f"{API}/bookings", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


@patch("payments.service.stripe.checkout.Session.create")
async def test_list_bookings_with_data(
    mock_create: MagicMock, client: AsyncClient, db: AsyncSession
) -> None:
    mock_create.return_value = _mock_stripe_session()
    homestead = await _seed(db)
    headers = await _auth_header(client)
    await client.post(
        f"{API}/bookings", json=_booking_body(homestead.id), headers=headers
    )

    resp = await client.get(f"{API}/bookings", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["homestead_name"] == "Stara Khata"
    assert items[0]["status"] == "pending"


async def test_list_bookings_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/bookings")
    assert resp.status_code == 401


# Webhook


@patch("payments.service.stripe.checkout.Session.create")
async def test_webhook_confirms_booking(
    mock_create: MagicMock, client: AsyncClient, db: AsyncSession
) -> None:
    mock_create.return_value = _mock_stripe_session()
    homestead = await _seed(db)
    headers = await _auth_header(client)
    await client.post(
        f"{API}/bookings", json=_booking_body(homestead.id), headers=headers
    )

    mock_event = MagicMock()
    mock_event.type = "checkout.session.completed"
    mock_event.data.object.id = "cs_test_123"

    with patch(
        "payments.service.stripe.Webhook.construct_event",
        return_value=mock_event,
    ):
        resp = await client.post(
            f"{API}/bookings/webhook",
            content=b"raw_payload",
            headers={"stripe-signature": "sig_test"},
        )
    assert resp.status_code == 200

    result = await db.execute(
        Booking.__table__.select().where(Booking.stripe_session_id == "cs_test_123")
    )
    booking = result.first()
    assert booking is not None
    assert booking.status == "confirmed"


async def test_webhook_ignores_other_events(client: AsyncClient) -> None:
    mock_event = MagicMock()
    mock_event.type = "payment_intent.created"

    with patch(
        "payments.service.stripe.Webhook.construct_event",
        return_value=mock_event,
    ):
        resp = await client.post(
            f"{API}/bookings/webhook",
            content=b"raw_payload",
            headers={"stripe-signature": "sig_test"},
        )
    assert resp.status_code == 200


async def test_create_booking_invalid_dates(
    client: AsyncClient, db: AsyncSession
) -> None:
    homestead = await _seed(db)
    headers = await _auth_header(client)
    body = _booking_body(homestead.id)
    body["check_out"] = body["check_in"]

    resp = await client.post(f"{API}/bookings", json=body, headers=headers)
    assert resp.status_code == 422
