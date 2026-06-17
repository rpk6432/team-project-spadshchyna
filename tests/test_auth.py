from httpx import AsyncClient

API = "/api/v1/auth"

REGISTER_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "password": "securepass123",
}

LOGIN_DATA = {
    "email": "john@example.com",
    "password": "securepass123",
}


async def _register(client: AsyncClient) -> dict:
    resp = await client.post(f"{API}/register", json=REGISTER_DATA)
    assert resp.status_code == 201
    return resp.json()


# Register


async def test_register_success(client: AsyncClient) -> None:
    data = await _register(client)
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_register_duplicate_email(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(f"{API}/register", json=REGISTER_DATA)
    assert resp.status_code == 409


async def test_register_short_password(client: AsyncClient) -> None:
    body = {**REGISTER_DATA, "password": "short"}
    resp = await client.post(f"{API}/register", json=body)
    assert resp.status_code == 422


async def test_register_invalid_email(client: AsyncClient) -> None:
    body = {**REGISTER_DATA, "email": "not-an-email"}
    resp = await client.post(f"{API}/register", json=body)
    assert resp.status_code == 422


# Login


async def test_login_success(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(f"{API}/login", json=LOGIN_DATA)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(
        f"{API}/login", json={"email": LOGIN_DATA["email"], "password": "wrongpass123"}
    )
    assert resp.status_code == 401


async def test_login_wrong_email(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API}/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )
    assert resp.status_code == 401


# Me


async def test_me_success(client: AsyncClient) -> None:
    data = await _register(client)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    resp = await client.get(f"{API}/me", headers=headers)
    assert resp.status_code == 200
    user = resp.json()
    assert user["email"] == REGISTER_DATA["email"]
    assert user["first_name"] == REGISTER_DATA["first_name"]
    assert user["is_admin"] is False


async def test_me_no_token(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/me")
    assert resp.status_code == 401


async def test_me_invalid_token(client: AsyncClient) -> None:
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    resp = await client.get(f"{API}/me", headers=headers)
    assert resp.status_code == 401


# Refresh


async def test_refresh_success(client: AsyncClient) -> None:
    data = await _register(client)
    resp = await client.post(
        f"{API}/refresh", json={"refresh_token": data["refresh_token"]}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_refresh_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API}/refresh", json={"refresh_token": "nonexistent-token"}
    )
    assert resp.status_code == 401


# Logout


async def test_logout_success(client: AsyncClient) -> None:
    data = await _register(client)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    resp = await client.post(
        f"{API}/logout",
        json={"refresh_token": data["refresh_token"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Logged out"


async def test_logout_refresh_reuse(client: AsyncClient) -> None:
    data = await _register(client)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    await client.post(
        f"{API}/logout",
        json={"refresh_token": data["refresh_token"]},
        headers=headers,
    )
    resp = await client.post(
        f"{API}/refresh", json={"refresh_token": data["refresh_token"]}
    )
    assert resp.status_code == 401
