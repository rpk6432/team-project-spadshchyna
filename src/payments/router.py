from fastapi import APIRouter, Request, status

from auth.dependencies import CurrentUser, DBSession
from payments import service
from payments.schemas import BookingListItem, BookingRequest, BookingResponse
from schemas.docs import ERROR_400, ERROR_401, ERROR_404, ERROR_409

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create booking",
    response_model=BookingResponse,
    responses={
        400: ERROR_400,
        401: ERROR_401,
        404: ERROR_404,
        409: ERROR_409,
    },
)
async def create_booking(
    body: BookingRequest, user: CurrentUser, db: DBSession
) -> BookingResponse:
    """
    Create a pending booking and generate a Stripe Checkout session.
    Returns the URL where the user should complete payment.
    """
    return await service.create_booking(db, user.id, body)


@router.post(
    "/webhook",
    summary="Stripe webhook",
    include_in_schema=False,
)
async def stripe_webhook(request: Request, db: DBSession) -> dict[str, str]:
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    await service.handle_webhook(db, payload, sig)
    return {"status": "ok"}


@router.get(
    "",
    summary="List bookings",
    response_model=list[BookingListItem],
    responses={401: ERROR_401},
)
async def list_bookings(user: CurrentUser, db: DBSession) -> list[BookingListItem]:
    """Return all bookings for the current user."""
    return await service.get_bookings(db, user.id)
