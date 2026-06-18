from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class BookingRequest(BaseModel):
    homestead_id: int
    check_in: date
    check_out: date
    guests: int = Field(ge=1)
    donation_pct: int = Field(0, ge=0, le=100)

    @model_validator(mode="after")
    def check_dates(self) -> BookingRequest:
        if self.check_out <= self.check_in:
            msg = "check_out must be after check_in"
            raise ValueError(msg)
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "homestead_id": 1,
                    "check_in": "2026-08-01",
                    "check_out": "2026-08-05",
                    "guests": 2,
                    "donation_pct": 5,
                }
            ]
        }
    }


class BookingResponse(BaseModel):
    id: int
    homestead_id: int
    status: str
    checkout_url: str
    nights: int
    accommodation_total: int
    cleaning_fee: int
    service_fee: int
    donation_amount: int
    total: int


class BookingListItem(BaseModel):
    id: int
    homestead_id: int
    homestead_name: str
    check_in: date
    check_out: date
    guests: int
    status: str
    total: int
    created_at: datetime
