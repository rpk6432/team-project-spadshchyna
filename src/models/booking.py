from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.homestead import Homestead
    from models.user import User


class Booking(Base):
    __tablename__ = "bookings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    homestead_id: Mapped[int] = mapped_column(ForeignKey("homesteads.id"), index=True)
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    guests: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    accommodation_total: Mapped[int]
    cleaning_fee: Mapped[int]
    service_fee: Mapped[int]
    donation_pct: Mapped[float]
    donation_amount: Mapped[int]
    total: Mapped[int]
    stripe_session_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped[User] = relationship(back_populates="bookings")
    homestead: Mapped[Homestead] = relationship(back_populates="bookings")

    def __str__(self) -> str:
        return f"Booking #{self.id}"
