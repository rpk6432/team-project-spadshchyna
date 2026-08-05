from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.amenity import homestead_amenity
from models.base import Base

if TYPE_CHECKING:
    from models.amenity import Amenity
    from models.booking import Booking
    from models.host import Host
    from models.region import Region
    from models.review import Review


class Homestead(Base):
    __tablename__ = "homesteads"

    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id", ondelete="RESTRICT"))
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    short_description: Mapped[str] = mapped_column(String(200))
    price_per_night: Mapped[int]
    base_guests: Mapped[int]
    extra_guest_fee: Mapped[int]
    max_guests: Mapped[int]
    cleaning_fee: Mapped[int]
    bedrooms: Mapped[int]
    beds: Mapped[int]
    bathrooms: Mapped[int]
    rating: Mapped[float] = mapped_column(default=0.0)
    review_count: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    host: Mapped[Host] = relationship(back_populates="homesteads")
    region: Mapped[Region] = relationship(back_populates="homesteads")
    photos: Mapped[list[HomesteadPhoto]] = relationship(
        back_populates="homestead",
        order_by="HomesteadPhoto.sort_order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    amenities: Mapped[list[Amenity]] = relationship(secondary=homestead_amenity)
    reviews: Mapped[list[Review]] = relationship(
        back_populates="homestead", passive_deletes=True
    )
    bookings: Mapped[list[Booking]] = relationship(
        back_populates="homestead", passive_deletes=True
    )

    def __str__(self) -> str:
        return self.name


class HomesteadPhoto(Base):
    __tablename__ = "homestead_photos"

    homestead_id: Mapped[int] = mapped_column(
        ForeignKey("homesteads.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(String(500), default="")
    is_main: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    homestead: Mapped[Homestead] = relationship(back_populates="photos")

    def __str__(self) -> str:
        return f"Photo #{self.sort_order}"
