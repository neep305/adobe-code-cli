"""Authentication API integration tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration returns access token."""
    response = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "name": "Test User"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20  # JWT should be reasonably long


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with duplicate email returns error."""
    # First registration
    await client.post("/api/auth/register", json={
        "email": "duplicate@example.com",
        "password": "pass123456",
        "name": "User 1"
    })
    
    # Second registration with same email
    response = await client.post("/api/auth/register", json={
        "email": "duplicate@example.com",
        "password": "differentpass",
        "name": "User 2"
    })
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test registration with invalid email format."""
    response = await client.post("/api/auth/register", json={
        "email": "not-an-email",
        "password": "testpass123",
        "name": "Test User"
    })
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Test registration with password less than 8 characters."""
    response = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "short",
        "name": "Test User"
    })
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_after_register(client: AsyncClient):
    """Test user can login after successful registration."""
    # Register
    reg_response = await client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepass123",
        "name": "New User"
    })
    assert reg_response.status_code == 201
    
    # Login
    login_response = await client.post("/api/auth/login", data={
        "username": "newuser@example.com",
        "password": "securepass123"
    })
    
    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login fails with wrong password."""
    # Register
    await client.post("/api/auth/register", json={
        "email": "user@example.com",
        "password": "correctpass",
        "name": "User"
    })
    
    # Try login with wrong password
    response = await client.post("/api/auth/login", data={
        "username": "user@example.com",
        "password": "wrongpass"
    })
    
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login fails for non-existent user."""
    response = await client.post("/api/auth/login", data={
        "username": "nobody@example.com",
        "password": "anypass"
    })
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_token(client: AsyncClient):
    """Test authenticated endpoint access with valid token."""
    # Register and get token
    reg_response = await client.post("/api/auth/register", json={
        "email": "authuser@example.com",
        "password": "password123",
        "name": "Auth User"
    })
    token = reg_response.json()["access_token"]
    
    # Access protected endpoint
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
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
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_check_auth_status(client: AsyncClient):
    """Test auth status endpoint returns user info."""
    # Register and get token
    reg_response = await client.post("/api/auth/register", json={
        "email": "statususer@example.com",
        "password": "password123",
        "name": "Status User"
    })
    token = reg_response.json()["access_token"]
    
    # Check status
    response = await client.get(
        "/api/auth/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["email"] == "statususer@example.com"
    assert "user_id" in data
