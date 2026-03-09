"""Tests for security headers and access controls."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Health endpoint returns 200 or 503."""
    resp = await async_client.get("/health")
    assert resp.status_code in (200, 503)


@pytest.mark.asyncio
async def test_security_headers_present(async_client: AsyncClient):
    """All responses should include security headers."""
    resp = await async_client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "SAMEORIGIN"
    assert "x-xss-protection" in resp.headers


@pytest.mark.asyncio
async def test_csp_on_html(async_client: AsyncClient):
    """HTML responses should have Content-Security-Policy."""
    resp = await async_client.get("/")
    csp = resp.headers.get("content-security-policy", "")
    if resp.headers.get("content-type", "").startswith("text/html"):
        assert "default-src" in csp


@pytest.mark.asyncio
async def test_protected_endpoints_require_auth(async_client: AsyncClient):
    """Saved-articles endpoint requires authentication."""
    resp = await async_client.get("/api/v1/feed/saved")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_endpoints_require_admin(async_client: AsyncClient):
    """Admin pipeline endpoint rejects unauthenticated requests."""
    resp = await async_client.post("/api/v1/pipeline/run")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_cache_stats_endpoint(async_client: AsyncClient):
    """Health cache endpoint returns structured data."""
    resp = await async_client.get("/api/v1/health/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data or "backend_type" in data


@pytest.mark.asyncio
async def test_correlation_id_header(async_client: AsyncClient):
    """Responses should include X-Request-ID."""
    resp = await async_client.get("/health")
    assert "x-request-id" in resp.headers


@pytest.mark.asyncio
async def test_save_article_requires_auth(async_client: AsyncClient):
    """Saving an article requires authentication."""
    resp = await async_client.post("/api/v1/feed/test-id/save")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_save_requires_auth(async_client: AsyncClient):
    """Removing a saved article requires authentication."""
    resp = await async_client.delete("/api/v1/feed/test-id/save")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_feedback_requires_auth(async_client: AsyncClient):
    """Submitting feedback requires authentication."""
    resp = await async_client.post(
        "/api/v1/feed/test-id/feedback",
        json={"feedback_type": "like"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_scraper_endpoints_require_admin(async_client: AsyncClient):
    """Scraper admin endpoints reject unauthenticated requests."""
    resp = await async_client.get("/api/v1/scrapers/status")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_pipeline_cache_invalidate_requires_admin(async_client: AsyncClient):
    """Cache invalidation endpoint requires admin auth."""
    resp = await async_client.post("/api/v1/pipeline/cache/invalidate")
    assert resp.status_code in (401, 403)
