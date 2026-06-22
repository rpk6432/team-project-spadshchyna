from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from auth.utils import verify_password
from database import async_session
from models.user import User


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username", "")
        password = form.get("password", "")

        async with async_session() as session:
            result = await session.execute(select(User).where(User.email == str(email)))
            user = result.scalar_one_or_none()

        if user is None or not verify_password(str(password), user.password_hash):
            return False
        if not user.is_admin:
            return False

        request.session.update({"user_id": user.id})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return "user_id" in request.session
