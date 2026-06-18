from dataclasses import dataclass

from sqlalchemy import Select

from core.exceptions import BadRequestError
from models.homestead import Homestead


@dataclass
class HomesteadFilters:
    region_id: int | None = None
    price_min: int | None = None
    price_max: int | None = None
    rating_min: float | None = None
    guests: int | None = None
    limit: int = 12
    offset: int = 0

    def __post_init__(self) -> None:
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise BadRequestError("price_min must be less than or equal to price_max")

    def apply(self, query: Select[tuple[Homestead]]) -> Select[tuple[Homestead]]:
        query = query.where(Homestead.is_active.is_(True))

        if self.region_id is not None:
            query = query.where(Homestead.region_id == self.region_id)
        if self.price_min is not None:
            query = query.where(Homestead.price_per_night >= self.price_min)
        if self.price_max is not None:
            query = query.where(Homestead.price_per_night <= self.price_max)
        if self.rating_min is not None:
            query = query.where(Homestead.rating >= self.rating_min)
        if self.guests is not None:
            query = query.where(Homestead.max_guests >= self.guests)

        return query
