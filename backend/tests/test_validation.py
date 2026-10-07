"""Tests for input validation across endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_max_length(async_client: AsyncClient):
    """Search query exceeding 200 chars should be rejected."""
    long_q = "a" * 201
    resp = await async_client.get(f"/api/v1/feed/search?q={long_q}")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_empty_query(async_client: AsyncClient):
    """Search with empty string should be rejected (min 1 char)."""
    resp = await async_client.get("/api/v1/feed/search?q=")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_feedback_invalid_type(async_client: AsyncClient):
    """Feedback with invalid type should be rejected or require auth."""
    resp = await async_client.post(
        "/api/v1/feed/test-id/feedback",
        json={"feedback_type": "invalid_type", "reason": "test"},
        headers={"Cookie": "access_token=fake"},
    )
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_register_weak_password(async_client: AsyncClient):
    """Registration with password shorter than 8 chars should fail."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@test.com",
            "password": "123",
            "full_name": "Test User",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_email(async_client: AsyncClient):
    """Registration without email should fail validation."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "password": "validpassword123",
            "full_name": "Test User",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(async_client: AsyncClient):
    """Registration with invalid email format should fail."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "validpassword123",
            "full_name": "Test User",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_full_name(async_client: AsyncClient):
    """Registration without full_name should fail validation."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "valid@test.com",
            "password": "validpassword123",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_trending_negative_limit(async_client: AsyncClient):
    """Trending with negative limit should be rejected."""
    resp = await async_client.get("/api/v1/feed/trending?limit=-1")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_trending_zero_limit(async_client: AsyncClient):
    """Trending with zero limit should be rejected (min 1)."""
    resp = await async_client.get("/api/v1/feed/trending?limit=0")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_fields(async_client: AsyncClient):
    """Login without required fields should fail validation."""
    resp = await async_client.post("/api/v1/auth/login", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_password_too_long(async_client: AsyncClient):
    """Registration with password exceeding 128 chars should fail."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@test.com",
            "password": "a" * 129,
            "full_name": "Test User",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_valid_query(async_client: AsyncClient):
    """Search with valid query returns 200 (or xfail if DB unavailable)."""
    resp = await async_client.get("/api/v1/feed/search?q=python")
    assert resp.status_code == 200
