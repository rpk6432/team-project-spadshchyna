from typing import TYPE_CHECKING

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.homestead import Homestead


class Host(Base):
    __tablename__ = "hosts"

    name: Mapped[str] = mapped_column(String(100))
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    email: Mapped[str] = mapped_column(String(255))

    homesteads: Mapped[list[Homestead]] = relationship(back_populates="host")

    def __str__(self) -> str:
        return self.name
