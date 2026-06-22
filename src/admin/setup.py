from pathlib import Path

from fastapi import FastAPI
from sqladmin import Admin

from admin.auth import AdminAuth
from admin.views import (
    AmenityAdmin,
    BookingAdmin,
    HomesteadAdmin,
    HomesteadPhotoAdmin,
    HostAdmin,
    RegionAdmin,
    ReviewAdmin,
    UserAdmin,
)
from config import settings
from database import engine
from s3.client import get_public_url

_TEMPLATES_DIR = str(Path(__file__).parent / "templates")


def setup_admin(app: FastAPI) -> None:
    authentication_backend = AdminAuth(secret_key=settings.jwt_secret)
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        templates_dir=_TEMPLATES_DIR,
    )
    admin.add_view(UserAdmin)
    admin.add_view(RegionAdmin)
    admin.add_view(AmenityAdmin)
    admin.add_view(BookingAdmin)
    admin.add_view(HostAdmin)
    admin.add_view(HomesteadAdmin)
    admin.add_view(HomesteadPhotoAdmin)
    admin.add_view(ReviewAdmin)

    admin.templates.env.filters["s3_url"] = get_public_url
