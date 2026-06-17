from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.homestead import Homestead, HomesteadPhoto
from models.host import Host
from models.region import Region

API = "/api/v1"
AUTH = "/api/v1/auth"

REGISTER_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "password": "securepass123",
}


async def _seed(db: AsyncSession) -> Homestead:
    """Insert minimal data and return a homestead."""
    region = Region(name="Carpathians", slug="carpathians")
    host = Host(name="Olha", email="olha@example.com", languages=["Ukrainian"])
    db.add_all([region, host])
    await db.flush()

    homestead = Homestead(
        host_id=host.id,
        region_id=region.id,
        name="Stara Khata",
        description="A cozy village house.",
        price_per_night=1200,
        base_guests=2,
        extra_guest_fee=300,
        max_guests=5,
        cleaning_fee=500,
        bedrooms=2,
        beds=3,
        bathrooms=1,
        rating=4.8,
        review_count=1,
    )
    db.add(homestead)
    await db.flush()

    photo = HomesteadPhoto(
        homestead_id=homestead.id, url="homesteads/1/main.jpg", is_main=True
    )
    db.add(photo)
    await db.commit()
    return homestead


async def _auth_header(client: AsyncClient) -> dict[str, str]:
    """Register a user and return Authorization header."""
    resp = await client.post(f"{AUTH}/register", json=REGISTER_DATA)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Add favourite


async def test_add_favourite(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await _seed(db)
    headers = await _auth_header(client)
    resp = await client.post(f"{API}/favourites/{homestead.id}", headers=headers)
    assert resp.status_code == 201
    assert resp.json()["detail"] == "Added to favourites"


async def test_add_favourite_duplicate(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await _seed(db)
    headers = await _auth_header(client)
    await client.post(f"{API}/favourites/{homestead.id}", headers=headers)
    resp = await client.post(f"{API}/favourites/{homestead.id}", headers=headers)
    assert resp.status_code == 409


async def test_add_favourite_not_found(client: AsyncClient) -> None:
    headers = await _auth_header(client)
    resp = await client.post(f"{API}/favourites/99999", headers=headers)
    assert resp.status_code == 404


async def test_add_favourite_unauthenticated(
    client: AsyncClient, db: AsyncSession
) -> None:
    homestead = await _seed(db)
    resp = await client.post(f"{API}/favourites/{homestead.id}")
    assert resp.status_code == 401


# Remove favourite


async def test_remove_favourite(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await _seed(db)
    headers = await _auth_header(client)
    await client.post(f"{API}/favourites/{homestead.id}", headers=headers)
    resp = await client.delete(f"{API}/favourites/{homestead.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Removed from favourites"


async def test_remove_favourite_not_found(client: AsyncClient) -> None:
    headers = await _auth_header(client)
    resp = await client.delete(f"{API}/favourites/99999", headers=headers)
    assert resp.status_code == 404


# List favourites


async def test_list_favourites_empty(client: AsyncClient) -> None:
    headers = await _auth_header(client)
    resp = await client.get(f"{API}/favourites", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_favourites_with_data(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await _seed(db)
    headers = await _auth_header(client)
    await client.post(f"{API}/favourites/{homestead.id}", headers=headers)

    resp = await client.get(f"{API}/favourites", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == homestead.id
    assert items[0]["is_favourited"] is True


async def test_list_favourites_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/favourites")
    assert resp.status_code == 401
