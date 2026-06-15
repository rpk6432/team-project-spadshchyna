from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.homestead import Homestead


class Region(Base):
    __tablename__ = "regions"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)

    homesteads: Mapped[list[Homestead]] = relationship(back_populates="region")

    def __str__(self) -> str:
        return self.name
