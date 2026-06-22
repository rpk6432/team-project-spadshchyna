from fastapi import FastAPI
from sqladmin import Admin

from admin.auth import AdminAuth
from admin.views import AmenityAdmin, BookingAdmin, RegionAdmin, UserAdmin
from config import settings
from database import engine


def setup_admin(app: FastAPI) -> None:
    authentication_backend = AdminAuth(secret_key=settings.jwt_secret)
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
    )
    admin.add_view(UserAdmin)
    admin.add_view(RegionAdmin)
    admin.add_view(AmenityAdmin)
    admin.add_view(BookingAdmin)
