from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

homestead_amenity = Table(
    "homestead_amenity",
    Base.metadata,
    Column(
        "homestead_id",
        Integer,
        ForeignKey("homesteads.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "amenity_id",
        Integer,
        ForeignKey("amenities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Amenity(Base):
    __tablename__ = "amenities"

    name: Mapped[str] = mapped_column(String(100), unique=True)

    def __str__(self) -> str:
        return self.name
