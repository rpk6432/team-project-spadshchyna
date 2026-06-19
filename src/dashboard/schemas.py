from datetime import date

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_nights: int
    total_donated: int


class UpcomingStay(BaseModel):
    booking_id: int
    homestead_name: str
    check_in: date
    check_out: date
    guests: int


class PastJourney(BaseModel):
    booking_id: int
    homestead_name: str
    region: str
    check_in: date
    check_out: date


class FavouriteItem(BaseModel):
    id: int
    name: str
    main_photo: str | None


class DashboardResponse(BaseModel):
    stats: DashboardStats
    upcoming_stay: UpcomingStay | None
    past_journeys: list[PastJourney]
    favourite_homesteads: list[FavouriteItem]
