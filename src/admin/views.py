import io
import uuid
from typing import Any

from PIL import Image
from sqladmin import ModelView
from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import FileField as WTFileField
from wtforms import MultipleFileField as WTMultipleFileField
from wtforms import SelectField, SelectMultipleField
from wtforms.validators import Email, NumberRange

from admin.hooks import recalc_homestead_rating
from admin.utils import (
    HOST_AVATAR_SIZE,
    format_s3_thumbnail,
    guess_content_type,
    resize_image,
)
from admin.widgets import DualListboxWidget, ImageUploadWidget, MultiImageUploadWidget
from database import async_session
from models.amenity import Amenity, homestead_amenity
from models.booking import Booking
from models.homestead import Homestead, HomesteadPhoto
from models.host import Host
from models.region import Region
from models.review import Review
from models.user import User
from s3.client import delete_file, upload_file


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


class HostAdmin(ModelView, model=Host):
    name = "Host"
    name_plural = "Hosts"
    icon = "fa-solid fa-house-user"
    column_list = [Host.id, Host.name, Host.email]
    form_excluded_columns = [Host.homesteads, Host.photo_url]
    form_args = {"email": {"validators": [Email()]}}
    column_labels = {"photo_url": "Photo"}
    column_formatters_detail = {
        "photo_url": lambda m, _: format_s3_thumbnail(getattr(m, "photo_url", None)),
    }

    async def scaffold_form(self, form_rules: list[str] | None = None) -> type:
        form = await super().scaffold_form(form_rules)
        form.photo_file = WTFileField("Photo", widget=ImageUploadWidget())
        if not hasattr(Host, "photo_file"):
            Host.photo_file = None
        return form

    async def on_model_change(
        self, data: dict[str, Any], model: Host, is_created: bool, request: Request
    ) -> None:
        self._pending_photo: dict[str, Any] | None = None
        upload = data.get("photo_file")
        if upload and hasattr(upload, "read"):
            content = await upload.read()
            if content:
                try:
                    content = resize_image(content, *HOST_AVATAR_SIZE)
                except Exception as exc:
                    raise ValueError("Uploaded file is not a valid image.") from exc
                self._pending_photo = {
                    "content": content,
                    "filename": upload.filename or "photo.jpg",
                    "content_type": guess_content_type(upload.filename),
                    "old_key": model.photo_url,
                }

    async def after_model_change(
        self, data: dict[str, Any], model: Host, is_created: bool, request: Request
    ) -> None:
        pending = getattr(self, "_pending_photo", None)
        if not pending:
            return
        if pending["old_key"]:
            await delete_file(pending["old_key"])
        uid = uuid.uuid4().hex[:8]
        key = f"hosts/{model.id}/{uid}_{pending['filename']}"
        await upload_file(key, pending["content"], pending["content_type"])
        async with async_session() as session:
            await session.execute(
                update(Host).where(Host.id == model.id).values(photo_url=key)
            )
            await session.commit()

    async def on_model_delete(self, model: Host, request: Request) -> None:
        async with async_session() as session:
            result = await session.execute(
                select(func.count()).where(Homestead.host_id == model.id)
            )
            if result.scalar_one():
                raise ValueError(
                    f"Cannot delete host '{model.name}': "
                    "host still has homesteads assigned."
                )
        self._deleted_photo_key = model.photo_url

    async def after_model_delete(self, model: Host, request: Request) -> None:
        key = getattr(self, "_deleted_photo_key", None)
        if key:
            await delete_file(key)


class HomesteadAdmin(ModelView, model=Homestead):
    name = "Homestead"
    name_plural = "Homesteads"
    icon = "fa-solid fa-house"
    column_list = [
        Homestead.id,
        Homestead.name,
        Homestead.region,
        Homestead.price_per_night,
        Homestead.is_active,
    ]
    form_excluded_columns = [
        Homestead.bookings,
        Homestead.photos,
        Homestead.reviews,
        Homestead.rating,
        Homestead.review_count,
        Homestead.amenities,
        Homestead.created_at,
    ]
    column_details_exclude_list = [Homestead.host_id, Homestead.region_id]
    details_template = "homestead_detail.html"
    form_ajax_refs = {
        "host": {"fields": ["name"], "order_by": "name"},
        "region": {"fields": ["name"], "order_by": "name"},
    }

    async def on_model_delete(self, model: Homestead, request: Request) -> None:
        async with async_session() as session:
            result = await session.execute(
                select(func.count()).where(Booking.homestead_id == model.id)
            )
            if result.scalar_one():
                raise ValueError(
                    f"Cannot delete homestead '{model.name}': it still has bookings."
                )
            rows = await session.execute(
                select(HomesteadPhoto.url).where(
                    HomesteadPhoto.homestead_id == model.id
                )
            )
            self._deleted_photo_keys = [r for r in rows.scalars().all() if r]

    async def after_model_delete(self, model: Homestead, request: Request) -> None:
        for key in getattr(self, "_deleted_photo_keys", []):
            await delete_file(key)

    _positive = {"validators": [NumberRange(min=0)]}
    form_args = {
        "price_per_night": _positive,
        "base_guests": _positive,
        "extra_guest_fee": _positive,
        "max_guests": _positive,
        "cleaning_fee": _positive,
        "bedrooms": _positive,
        "beds": _positive,
        "bathrooms": _positive,
    }

    def form_edit_query(self, request: Request) -> Select[Any]:
        return (
            super().form_edit_query(request).options(selectinload(Homestead.amenities))
        )

    async def scaffold_form(self, form_rules: list[str] | None = None) -> type:
        form = await super().scaffold_form(form_rules)

        amenity_field = SelectMultipleField(
            "Amenities", coerce=int, widget=DualListboxWidget()
        )
        async with async_session() as session:
            result = await session.execute(select(Amenity).order_by(Amenity.name))
            amenity_field.kwargs["choices"] = [
                (a.id, a.name) for a in result.scalars().all()
            ]
        form.amenity_ids = amenity_field

        form.upload_photos = WTMultipleFileField(
            "Upload Photos", widget=MultiImageUploadWidget()
        )
        if not hasattr(Homestead, "amenity_ids"):
            Homestead.amenity_ids = property(
                lambda self: [a.id for a in self.amenities]
            )
        if not hasattr(Homestead, "upload_photos"):
            Homestead.upload_photos = None

        return form

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: Homestead,
        is_created: bool,
        request: Request,
    ) -> None:
        self._pending_amenity_ids: list[int] = data.pop("amenity_ids", []) or []
        self._pending_photos: list[dict[str, Any]] = []

        uploads = data.pop("upload_photos", []) or []
        for upload in uploads:
            if not hasattr(upload, "read"):
                continue
            content = await upload.read()
            if not content:
                continue
            try:
                Image.open(io.BytesIO(content)).verify()
            except Exception as exc:
                raise ValueError(f"'{upload.filename}' is not a valid image.") from exc
            self._pending_photos.append(
                {
                    "content": content,
                    "filename": upload.filename or "photo.jpg",
                    "content_type": guess_content_type(upload.filename),
                }
            )

    async def after_model_change(
        self,
        data: dict[str, Any],
        model: Homestead,
        is_created: bool,
        request: Request,
    ) -> None:
        amenity_ids = getattr(self, "_pending_amenity_ids", [])
        pending_photos = getattr(self, "_pending_photos", [])
        if not amenity_ids and not pending_photos and not is_created:
            return

        async with async_session() as session:
            await session.execute(
                homestead_amenity.delete().where(
                    homestead_amenity.c.homestead_id == model.id
                )
            )
            if amenity_ids:
                await session.execute(
                    homestead_amenity.insert(),
                    [
                        {"homestead_id": model.id, "amenity_id": aid}
                        for aid in amenity_ids
                    ],
                )

            if pending_photos:
                result = await session.execute(
                    select(
                        func.coalesce(func.max(HomesteadPhoto.sort_order), -1)
                    ).where(HomesteadPhoto.homestead_id == model.id)
                )
                max_order: int = result.scalar_one()

                has_main = await session.execute(
                    select(HomesteadPhoto.id)
                    .where(
                        HomesteadPhoto.homestead_id == model.id,
                        HomesteadPhoto.is_main.is_(True),
                    )
                    .limit(1)
                )
                need_main = has_main.scalar_one_or_none() is None

                for i, photo in enumerate(pending_photos):
                    uid = uuid.uuid4().hex[:8]
                    key = f"homesteads/{model.id}/{uid}_{photo['filename']}"
                    await upload_file(key, photo["content"], photo["content_type"])
                    session.add(
                        HomesteadPhoto(
                            homestead_id=model.id,
                            url=key,
                            is_main=need_main and i == 0,
                            sort_order=max_order + 1 + i,
                        )
                    )

            await session.commit()


class HomesteadPhotoAdmin(ModelView, model=HomesteadPhoto):
    name = "Photo"
    name_plural = "Photos"
    icon = "fa-solid fa-image"
    column_list = [
        HomesteadPhoto.id,
        HomesteadPhoto.homestead,
        HomesteadPhoto.url,
        HomesteadPhoto.is_main,
    ]
    column_details_exclude_list = [
        HomesteadPhoto.homestead_id,
        HomesteadPhoto.sort_order,
    ]
    form_excluded_columns = [HomesteadPhoto.url]
    form_ajax_refs = {"homestead": {"fields": ["name"], "order_by": "name"}}
    column_labels = {"url": "Photo"}
    column_formatters = {
        "url": lambda m, _: format_s3_thumbnail(getattr(m, "url", None)),
    }
    column_formatters_detail = {
        "url": lambda m, _: format_s3_thumbnail(getattr(m, "url", None)),
    }

    async def scaffold_form(self, form_rules: list[str] | None = None) -> type:
        form = await super().scaffold_form(form_rules)
        form.photo_file = WTFileField("Upload Photo", widget=ImageUploadWidget())
        if not hasattr(HomesteadPhoto, "photo_file"):
            HomesteadPhoto.photo_file = None
        return form

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: HomesteadPhoto,
        is_created: bool,
        request: Request,
    ) -> None:
        self._pending_photo: dict[str, Any] | None = None
        upload = data.get("photo_file")
        if upload and hasattr(upload, "read"):
            content = await upload.read()
            if content:
                try:
                    Image.open(io.BytesIO(content)).verify()
                except Exception as exc:
                    raise ValueError("Uploaded file is not a valid image.") from exc
                self._pending_photo = {
                    "content": content,
                    "filename": upload.filename or "photo.jpg",
                    "content_type": guess_content_type(upload.filename),
                    "old_key": model.url if not is_created else None,
                }

    async def after_model_change(
        self,
        data: dict[str, Any],
        model: HomesteadPhoto,
        is_created: bool,
        request: Request,
    ) -> None:
        pending = getattr(self, "_pending_photo", None)
        if not pending and not model.is_main:
            return

        async with async_session() as session:
            if pending:
                if pending["old_key"]:
                    await delete_file(pending["old_key"])
                uid = uuid.uuid4().hex[:8]
                key = f"homesteads/{model.homestead_id}/{uid}_{pending['filename']}"
                await upload_file(key, pending["content"], pending["content_type"])
                await session.execute(
                    update(HomesteadPhoto)
                    .where(HomesteadPhoto.id == model.id)
                    .values(url=key)
                )

            if model.is_main:
                await session.execute(
                    update(HomesteadPhoto)
                    .where(
                        HomesteadPhoto.homestead_id == model.homestead_id,
                        HomesteadPhoto.id != model.id,
                        HomesteadPhoto.is_main.is_(True),
                    )
                    .values(is_main=False)
                )

            await session.commit()


class ReviewAdmin(ModelView, model=Review):
    name = "Review"
    name_plural = "Reviews"
    icon = "fa-solid fa-star"
    column_list = [
        Review.id,
        Review.homestead,
        Review.author_name,
        Review.rating,
    ]
    column_details_exclude_list = [Review.homestead_id]
    form_excluded_columns = [Review.created_at]
    form_ajax_refs = {"homestead": {"fields": ["name"], "order_by": "name"}}
    form_args = {"rating": {"validators": [NumberRange(min=1, max=5)]}}

    async def after_model_change(
        self, data: dict[str, Any], model: Review, is_created: bool, request: Request
    ) -> None:
        await recalc_homestead_rating(model.homestead_id)

    async def on_model_delete(self, model: Review, request: Request) -> None:
        self._deleted_homestead_id = model.homestead_id

    async def after_model_delete(self, model: Review, request: Request) -> None:
        homestead_id: int | None = getattr(self, "_deleted_homestead_id", None)
        if homestead_id:
            await recalc_homestead_rating(homestead_id)
