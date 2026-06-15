from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.homestead import Homestead
    from models.user import User


class Favourite(Base):
    __tablename__ = "favourites"
    __table_args__ = (UniqueConstraint("user_id", "homestead_id"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    homestead_id: Mapped[int] = mapped_column(ForeignKey("homesteads.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped[User] = relationship(back_populates="favourites")
    homestead: Mapped[Homestead] = relationship()

    def __str__(self) -> str:
        return f"Favourite #{self.id}"
