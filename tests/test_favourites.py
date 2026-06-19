from conftest import API, auth_header, seed_homestead
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Add favourite


async def test_add_favourite(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await seed_homestead(db)
    headers = await auth_header(client)
    resp = await client.post(f"{API}/favourites/{homestead.id}", headers=headers)
    assert resp.status_code == 201
    assert resp.json()["detail"] == "Added to favourites"


async def test_add_favourite_duplicate(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await seed_homestead(db)
    headers = await auth_header(client)
    await client.post(f"{API}/favourites/{homestead.id}", headers=headers)
    resp = await client.post(f"{API}/favourites/{homestead.id}", headers=headers)
    assert resp.status_code == 409


async def test_add_favourite_not_found(client: AsyncClient) -> None:
    headers = await auth_header(client)
    resp = await client.post(f"{API}/favourites/99999", headers=headers)
    assert resp.status_code == 404


async def test_add_favourite_unauthenticated(
    client: AsyncClient, db: AsyncSession
) -> None:
    homestead = await seed_homestead(db)
    resp = await client.post(f"{API}/favourites/{homestead.id}")
    assert resp.status_code == 401


# Remove favourite


async def test_remove_favourite(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await seed_homestead(db)
    headers = await auth_header(client)
    await client.post(f"{API}/favourites/{homestead.id}", headers=headers)
    resp = await client.delete(f"{API}/favourites/{homestead.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Removed from favourites"


async def test_remove_favourite_not_found(client: AsyncClient) -> None:
    headers = await auth_header(client)
    resp = await client.delete(f"{API}/favourites/99999", headers=headers)
    assert resp.status_code == 404


# List favourites


async def test_list_favourites_empty(client: AsyncClient) -> None:
    headers = await auth_header(client)
    resp = await client.get(f"{API}/favourites", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_favourites_with_data(client: AsyncClient, db: AsyncSession) -> None:
    homestead = await seed_homestead(db)
    headers = await auth_header(client)
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
