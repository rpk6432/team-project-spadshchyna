from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.homestead import Homestead


class Review(Base):
    __tablename__ = "reviews"

    homestead_id: Mapped[int] = mapped_column(
        ForeignKey("homesteads.id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100))
    rating: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    homestead: Mapped[Homestead] = relationship(back_populates="reviews")

    def __str__(self) -> str:
        return f"Review by {self.author_name}"
