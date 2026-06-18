from math import floor

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from core.exceptions import AlreadyExistsError
from homesteads.service import compute_price, get_validated_homestead
from models.booking import Booking
from models.homestead import Homestead
from payments.schemas import BookingListItem, BookingRequest, BookingResponse


async def create_booking(
    db: AsyncSession, user_id: int, body: BookingRequest
) -> BookingResponse:
    homestead = await get_validated_homestead(
        db, body.homestead_id, body.check_in, body.guests
    )

    # Check overlap with pending + confirmed bookings
    overlap_q = select(Booking.id).where(
        Booking.homestead_id == body.homestead_id,
        Booking.status.in_(["pending", "confirmed"]),
        Booking.check_in < body.check_out,
        Booking.check_out > body.check_in,
    )
    conflict = (await db.execute(overlap_q)).scalar_one_or_none()
    if conflict is not None:
        raise AlreadyExistsError("Dates are not available")

    price = compute_price(homestead, body.check_in, body.check_out, body.guests)
    donation = floor(price.accommodation * body.donation_pct / 100)
    total = price.total + donation

    booking = Booking(
        user_id=user_id,
        homestead_id=body.homestead_id,
        check_in=body.check_in,
        check_out=body.check_out,
        guests=body.guests,
        status="pending",
        accommodation_total=price.accommodation,
        cleaning_fee=price.cleaning,
        service_fee=price.service_fee,
        donation_pct=body.donation_pct,
        donation_amount=donation,
        total=total,
        stripe_session_id="",
    )
    db.add(booking)
    await db.flush()

    try:
        stripe.api_key = settings.stripe_secret_key
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "uah",
                        "unit_amount": total * 100,
                        "product_data": {
                            "name": (
                                f"Booking at {homestead.name}, "
                                f"{body.check_in} — {body.check_out}"
                            ),
                        },
                    },
                    "quantity": 1,
                },
            ],
            success_url=(
                f"{settings.frontend_url}/booking/success"
                f"?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{settings.frontend_url}/booking/cancel",
            metadata={"booking_id": str(booking.id)},
        )
    except Exception:
        await db.rollback()
        raise

    booking.stripe_session_id = session.id
    assert session.url is not None
    await db.commit()

    return BookingResponse(
        id=booking.id,
        homestead_id=booking.homestead_id,
        status=booking.status,
        checkout_url=session.url,
        nights=price.nights,
        accommodation_total=price.accommodation,
        cleaning_fee=price.cleaning,
        service_fee=price.service_fee,
        donation_amount=donation,
        total=total,
    )


async def handle_webhook(db: AsyncSession, payload: bytes, sig: str) -> None:
    """Verify Stripe signature and confirm booking on successful payment."""
    event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
        payload, sig, settings.stripe_webhook_secret
    )

    if event.type != "checkout.session.completed":
        return

    session_id = event.data.object.id
    result = await db.execute(
        select(Booking).where(Booking.stripe_session_id == session_id)
    )
    booking = result.scalar_one_or_none()
    if booking is None:
        return

    booking.status = "confirmed"
    await db.commit()


async def get_bookings(db: AsyncSession, user_id: int) -> list[BookingListItem]:
    """Return all bookings for a user, newest first."""
    result = await db.execute(
        select(Booking)
        .where(Booking.user_id == user_id)
        .options(selectinload(Booking.homestead).load_only(Homestead.name))
        .order_by(Booking.created_at.desc())
    )
    bookings = result.scalars().all()
    return [
        BookingListItem(
            id=b.id,
            homestead_id=b.homestead_id,
            homestead_name=b.homestead.name,
            check_in=b.check_in,
            check_out=b.check_out,
            guests=b.guests,
            status=b.status,
            total=b.total,
            created_at=b.created_at,
        )
        for b in bookings
    ]
