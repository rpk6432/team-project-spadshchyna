from typing import Any

from sqladmin import ModelView
from sqlalchemy import func, select
from starlette.requests import Request
from wtforms import SelectField
from wtforms.validators import Email

from database import async_session
from models.amenity import Amenity
from models.booking import Booking
from models.homestead import Homestead
from models.region import Region
from models.user import User


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    column_list = [User.id, User.email, User.first_name, User.last_name, User.is_admin]
    column_details_exclude_list = [User.password_hash]
    form_excluded_columns = [
        User.password_hash,
        User.bookings,
        User.favourites,
        User.created_at,
    ]
    form_args = {"email": {"validators": [Email()]}}
    can_create = False
    can_delete = False

    async def on_model_change(
        self, data: dict[str, Any], model: User, is_created: bool, request: Request
    ) -> None:
        current_user_id = request.session.get("user_id")
        if model.id == current_user_id and not data.get("is_admin", True):
            raise ValueError("You cannot remove admin rights from yourself.")


class RegionAdmin(ModelView, model=Region):
    name = "Region"
    name_plural = "Regions"
    icon = "fa-solid fa-map"
    column_list = [Region.id, Region.name, Region.slug]
    form_excluded_columns = [Region.homesteads]

    async def on_model_delete(self, model: Region, request: Request) -> None:
        async with async_session() as session:
            result = await session.execute(
                select(func.count()).where(Homestead.region_id == model.id)
            )
            if result.scalar_one():
                raise ValueError(
                    f"Cannot delete region '{model.name}': "
                    "it still has homesteads assigned."
                )


class AmenityAdmin(ModelView, model=Amenity):
    name = "Amenity"
    name_plural = "Amenities"
    icon = "fa-solid fa-wifi"
    column_list = [Amenity.id, Amenity.name]


class BookingAdmin(ModelView, model=Booking):
    name = "Booking"
    name_plural = "Bookings"
    icon = "fa-solid fa-calendar-check"
    column_list = [
        Booking.id,
        Booking.user,
        Booking.homestead,
        Booking.check_in,
        Booking.status,
    ]
    column_details_exclude_list = [
        Booking.user_id,
        Booking.homestead_id,
        Booking.stripe_session_id,
    ]
    form_columns = [Booking.status]
    form_overrides = {"status": SelectField}
    form_args = {
        "status": {
            "choices": [
                ("pending", "pending"),
                ("confirmed", "confirmed"),
                ("canceled", "canceled"),
                ("completed", "completed"),
            ],
        },
    }
    can_create = False
    can_delete = False
