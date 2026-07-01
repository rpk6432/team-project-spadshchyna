from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

# Regions


class RegionResponse(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"id": 1, "name": "Khmelnytskyi Region", "slug": "khmelnytskyi"}
            ]
        }
    }


# Nested schemas for detail


class HostResponse(BaseModel):
    id: int
    name: str
    photo_url: str | None
    languages: list[str]


class PhotoResponse(BaseModel):
    id: int
    url: str
    is_main: bool
    sort_order: int


class AmenityResponse(BaseModel):
    id: int
    name: str


class ReviewResponse(BaseModel):
    id: int
    category: str
    text: str
    author_name: str
    country: str
    rating: float
    created_at: datetime


class PricingResponse(BaseModel):
    price_per_night: int
    base_guests: int
    extra_guest_fee: int
    max_guests: int
    cleaning_fee: int
    service_fee_pct: int


# Catalog card


class HomesteadCard(BaseModel):
    id: int
    name: str
    location: str
    description: str
    short_description: str
    region: str
    price_per_night: int
    rating: float
    review_count: int
    main_photo: str | None
    amenities: list[str]
    is_favourited: bool | None = Field(
        None, description="true/false if authenticated, null if not"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "Stara Khata",
                    "location": "Kamianets-Podilskyi city",
                    "description": (
                        "A cozy village house in the heart of Podillia."
                        " Learn the art of traditional pottery,"
                        " taste home-cooked meals,"
                        " and explore sunflower fields."
                    ),
                    "short_description": (
                        "A cozy village house in the heart of Podillia."
                    ),
                    "region": "Khmelnytskyi Region",
                    "price_per_night": 1200,
                    "rating": 4.8,
                    "review_count": 12,
                    "main_photo": "https://s3.example.com/homesteads/1/main.jpg",
                    "amenities": [
                        "Traditional stove",
                        "Heritage tours",
                        "Historic vibe",
                    ],
                    "is_favourited": None,
                }
            ]
        }
    }


# Detail


class HomesteadDetail(BaseModel):
    id: int
    name: str
    location: str
    description: str
    short_description: str
    bedrooms: int
    beds: int
    bathrooms: int
    rating: float
    review_count: int
    region: str
    host: HostResponse
    photos: list[PhotoResponse]
    amenities: list[AmenityResponse]
    featured_amenities: list[AmenityResponse]
    reviews: list[ReviewResponse]
    pricing: PricingResponse
    is_favourited: bool | None = Field(
        description="true/false if user is authenticated, null if not"
    )


# Availability


class AvailabilityRequest(BaseModel):
    check_in: date
    check_out: date
    guests: int = Field(ge=1)

    @model_validator(mode="after")
    def check_dates(self) -> AvailabilityRequest:
        if self.check_out <= self.check_in:
            msg = "check_out must be after check_in"
            raise ValueError(msg)
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"check_in": "2026-08-01", "check_out": "2026-08-05", "guests": 2}
            ]
        }
    }


class AvailabilityResponse(BaseModel):
    available: bool
    nights: int
    accommodation_total: int
    cleaning_fee: int
    service_fee: int
    total: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "available": True,
                    "nights": 4,
                    "accommodation_total": 4800,
                    "cleaning_fee": 500,
                    "service_fee": 144,
                    "total": 5444,
                }
            ]
        }
    }
