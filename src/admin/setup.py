from fastapi import FastAPI
from sqladmin import Admin

from admin.auth import AdminAuth
from config import settings
from database import engine


def setup_admin(app: FastAPI) -> None:
    authentication_backend = AdminAuth(secret_key=settings.jwt_secret)
    Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
    )
