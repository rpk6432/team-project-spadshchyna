from datetime import UTC, datetime, timedelta

from sqlalchemy import update

import database
from models.booking import Booking
from tasks import app

PENDING_TTL_MINUTES = 30


@app.task
def expire_pending_bookings() -> None:
    """Cancel pending bookings older than PENDING_TTL_MINUTES."""
    cutoff = datetime.now(UTC) - timedelta(minutes=PENDING_TTL_MINUTES)
    with database.sync_session() as session:
        session.execute(
            update(Booking)
            .where(Booking.status == "pending", Booking.created_at < cutoff)
            .values(status="canceled")
        )
        session.commit()
