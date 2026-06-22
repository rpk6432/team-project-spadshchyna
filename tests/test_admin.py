from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.utils import hash_password
from models.user import User


async def _create_admin(db: AsyncSession) -> User:
    user = User(
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        password_hash=hash_password("adminpass123"),
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    return user


async def _create_regular_user(db: AsyncSession) -> User:
    user = User(
        first_name="Regular",
        last_name="User",
        email="regular@example.com",
        password_hash=hash_password("userpass123"),
        is_admin=False,
    )
    db.add(user)
    await db.commit()
    return user


# Admin login


async def test_admin_login_success(client: AsyncClient, db: AsyncSession) -> None:
    await _create_admin(db)
    resp = await client.post(
        "/admin/login",
        data={"username": "admin@example.com", "password": "adminpass123"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    assert "session" in resp.cookies or resp.headers.get("location") == "/admin/"


async def test_admin_login_non_admin(client: AsyncClient, db: AsyncSession) -> None:
    await _create_regular_user(db)
    resp = await client.post(
        "/admin/login",
        data={"username": "regular@example.com", "password": "userpass123"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


async def test_admin_login_wrong_password(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _create_admin(db)
    resp = await client.post(
        "/admin/login",
        data={"username": "admin@example.com", "password": "wrongpassword"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


# Unauthenticated access


async def test_admin_unauthenticated_redirect(client: AsyncClient) -> None:
    resp = await client.get("/admin/", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert "/login" in resp.headers.get("location", "")
