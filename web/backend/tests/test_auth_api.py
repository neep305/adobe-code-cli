"""Authentication API integration tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration returns access token."""
    response = await client.post(
        "/api/auth/register",
        json={
            "login_id": "test@example.com",
            "password": "testpass123",
            "name": "Test User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20


@pytest.mark.asyncio
async def test_register_legacy_email_key_ok(client: AsyncClient):
    """Legacy clients may still POST { email, name, password }."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "legacy-key-user",
            "password": "x",
            "name": "Legacy",
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_plain_id_ok(client: AsyncClient):
    """Login ID is not required to be an email shape."""
    response = await client.post(
        "/api/auth/register",
        json={
            "login_id": "not-an-email-id",
            "password": "x",
            "name": "Plain Id User",
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_short_password_ok(client: AsyncClient):
    """Password min length is 1."""
    response = await client.post(
        "/api/auth/register",
        json={
            "login_id": "shortpw@example.com",
            "password": "a",
            "name": "Short Password User",
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_duplicate_login_id(client: AsyncClient):
    """Test registration with duplicate ID returns error."""
    await client.post(
        "/api/auth/register",
        json={
            "login_id": "duplicate@example.com",
            "password": "pass123456",
            "name": "User 1",
        },
    )

    response = await client.post(
        "/api/auth/register",
        json={
            "login_id": "duplicate@example.com",
            "password": "differentpass",
            "name": "User 2",
        },
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_missing_field_422(client: AsyncClient):
    """Missing required JSON field yields 422."""
    response = await client.post(
        "/api/auth/register",
        json={"login_id": "only@example.com", "name": "No Password"},
    )
    assert response.status_code == 422
    detail = response.json().get("detail")
    assert isinstance(detail, list)


@pytest.mark.asyncio
async def test_register_password_too_long_422(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={
            "login_id": "longpw@example.com",
            "password": "x" * 101,
            "name": "User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_whitespace_only_id_422(client: AsyncClient):
    """Whitespace-only ID is rejected after strip."""
    response = await client.post(
        "/api/auth/register",
        json={
            "login_id": "   ",
            "password": "secret",
            "name": "N",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_after_register(client: AsyncClient):
    """Test user can login after successful registration."""
    reg_response = await client.post(
        "/api/auth/register",
        json={
            "login_id": "newuser@example.com",
            "password": "securepass123",
            "name": "New User",
        },
    )
    assert reg_response.status_code == 201

    login_response = await client.post(
        "/api/auth/login",
        data={
            "username": "newuser@example.com",
            "password": "securepass123",
        },
    )

    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login fails with wrong password."""
    await client.post(
        "/api/auth/register",
        json={
            "login_id": "user@example.com",
            "password": "correctpass",
            "name": "User",
        },
    )

    response = await client.post(
        "/api/auth/login",
        data={
            "username": "user@example.com",
            "password": "wrongpass",
        },
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login fails for non-existent user."""
    response = await client.post(
        "/api/auth/login",
        data={
            "username": "nobody@example.com",
            "password": "anypass",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_json_body_422(client: AsyncClient):
    """Login expects form body, not JSON."""
    response = await client.post(
        "/api/auth/login",
        json={"username": "a@b.com", "password": "x"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_current_user_with_token(client: AsyncClient):
    """Test authenticated endpoint access with valid token."""
    reg_response = await client.post(
        "/api/auth/register",
        json={
            "login_id": "authuser@example.com",
            "password": "password123",
            "name": "Auth User",
        },
    )
    token = reg_response.json()["access_token"]

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "authuser@example.com"
    assert data["name"] == "Auth User"
    assert data["role"] == "user"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_current_user_without_token(client: AsyncClient):
    """Test authenticated endpoint access without token fails."""
    response = await client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    """Test authenticated endpoint access with invalid token fails."""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_check_auth_status(client: AsyncClient):
    """Test auth status endpoint returns user info."""
    reg_response = await client.post(
        "/api/auth/register",
        json={
            "login_id": "statususer@example.com",
            "password": "password123",
            "name": "Status User",
        },
    )
    token = reg_response.json()["access_token"]

    response = await client.get(
        "/api/auth/status",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["email"] == "statususer@example.com"
    assert "user_id" in data
