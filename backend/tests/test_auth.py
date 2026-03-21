"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test health check endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Test root endpoint."""
    response = await async_client.get("/")
    assert response.status_code == 200
    body = response.text.lower()
    assert "<html" in body
    assert "news day" in body


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    """Test user registration."""
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
        "department": "CSE",
        "year_of_study": 3,
        "college_name": "Test College"
    }
    
    response = await async_client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == user_data["email"]
    assert data["data"]["full_name"] == user_data["full_name"]
    assert data["data"]["department_key"] == user_data["department"]
    assert "password_hash" not in data["data"]


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient):
    """Test registering with duplicate email."""
    user_data = {
        "email": "duplicate@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    # First registration
    response = await async_client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201
    
    # Second registration with same email
    response = await async_client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    """Test successful login."""
    # Register a user first
    user_data = {
        "email": "login@example.com",
        "password": "testpassword123",
        "full_name": "Login Test User"
    }
    
    register_response = await async_client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    
    # Login
    login_data = {
        "email": user_data["email"],
        "password": user_data["password"]
    }
    
    response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient):
    """Test login with invalid credentials."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    
    response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_get_me(async_client: AsyncClient):
    """Test getting current user profile."""
    # Register and login
    user_data = {
        "email": "me@example.com",
        "password": "testpassword123",
        "full_name": "Me Test User"
    }
    
    await async_client.post("/api/v1/auth/register", json=user_data)
    
    login_response = await async_client.post("/api/v1/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    
    token = login_response.json()["access_token"]
    
    # Get me
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_update_me(async_client: AsyncClient):
    """Test updating user profile."""
    # Register and login
    user_data = {
        "email": "update@example.com",
        "password": "testpassword123",
        "full_name": "Update Test User"
    }
    
    await async_client.post("/api/v1/auth/register", json=user_data)
    
    login_response = await async_client.post("/api/v1/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    
    token = login_response.json()["access_token"]
    
    # Update profile
    update_data = {
        "full_name": "Updated Name",
        "department": "ECE",
        "interests": ["ai", "webdev"]
    }
    
    response = await async_client.put(
        "/api/v1/auth/me",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["full_name"] == update_data["full_name"]
    assert data["data"]["department_key"] == update_data["department"]


@pytest.mark.asyncio
async def test_get_user_stats(async_client: AsyncClient):
    """Test getting user stats."""
    # Register and login
    user_data = {
        "email": "stats@example.com",
        "password": "testpassword123",
        "full_name": "Stats Test User"
    }
    
    await async_client.post("/api/v1/auth/register", json=user_data)
    
    login_response = await async_client.post("/api/v1/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    
    token = login_response.json()["access_token"]
    
    # Get stats
    response = await async_client.get(
        "/api/v1/auth/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "total_reads" in data["data"]
    assert "streak_days" in data["data"]
    assert "weekly_goal" in data["data"]


@pytest.mark.asyncio
async def test_change_password(async_client: AsyncClient):
    """Test changing password."""
    # Register and login
    user_data = {
        "email": "changepass@example.com",
        "password": "oldpassword123",
        "full_name": "Change Pass User"
    }
    
    await async_client.post("/api/v1/auth/register", json=user_data)
    
    login_response = await async_client.post("/api/v1/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    
    token = login_response.json()["access_token"]
    
    # Change password
    password_data = {
        "current_password": "oldpassword123",
        "new_password": "newpassword456"
    }
    
    response = await async_client.post(
        "/api/v1/auth/change-password",
        json=password_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"
    
    # Verify old password doesn't work
    old_login = await async_client.post("/api/v1/auth/login", json={
        "email": user_data["email"],
        "password": "oldpassword123"
    })
    assert old_login.status_code == 401
    
    # Verify new password works
    new_login = await async_client.post("/api/v1/auth/login", json={
        "email": user_data["email"],
        "password": "newpassword456"
    })
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_logout(async_client: AsyncClient):
    """Test logout endpoint."""
    # Register and login
    user_data = {
        "email": "logout@example.com",
        "password": "testpassword123",
        "full_name": "Logout Test User"
    }
    
    await async_client.post("/api/v1/auth/register", json=user_data)
    
    login_response = await async_client.post("/api/v1/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    
    token = login_response.json()["access_token"]
    
    # Logout
    response = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_unauthorized_access(async_client: AsyncClient):
    """Test accessing protected endpoint without token."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
