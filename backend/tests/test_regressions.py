"""Regression coverage for real auth and feed failures, not expected failures."""
import pytest
from datetime import timedelta
from app.core.security import create_access_token


async def login_user(client, email="regression@example.com"):
    data = {"email": email, "password": "testpassword123", "full_name": "Regression", "department": "CSE"}
    assert (await client.post("/api/v1/auth/register", json=data)).status_code == 201
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": data["password"]})
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_refresh_works_without_access_cookie(async_client):
    await login_user(async_client)
    async_client.cookies.delete("access_token")
    response = await async_client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(async_client):
    tokens = await login_user(async_client)
    async_client.cookies.clear()
    response = await async_client.post("/api/v1/auth/refresh", headers={"Authorization": "Bearer " + tokens["access_token"]})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookies_without_live_access(async_client):
    await login_user(async_client)
    async_client.cookies.delete("access_token")
    response = await async_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert async_client.cookies.get("refresh_token") is None


@pytest.mark.asyncio
async def test_profile_preferences_persist(async_client):
    await login_user(async_client)
    prefs = {"interests": ["ai", "webdev"], "graduation_year": 2027,
             "content_preferences": {"research": True}, "notification_settings": {"email_digest": False}}
    response = await async_client.put("/api/v1/auth/me", json=prefs)
    assert response.status_code == 200
    for key, value in prefs.items():
        assert response.json()["data"][key] == value


@pytest.mark.asyncio
async def test_reset_password_sqlite_timezone(async_client, db_session):
    await login_user(async_client)
    from app.services.auth_service import AuthService
    service = AuthService(db_session)
    token = await service.generate_reset_token("regression@example.com")
    db_session.expire_all()
    response = await async_client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "replacement123"})
    assert response.status_code == 200
    again = await async_client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "replacement456"})
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_personalized_feed_not_public_cache(async_client):
    response = await async_client.get("/api/v1/feed/personalized")
    assert response.status_code == 200
    assert "public" not in response.headers.get("cache-control", "")

@pytest.mark.asyncio
async def test_populated_feed_source_links_and_saved_articles(async_client, db_session):
    from app.models import Source, RawContent, ProcessedContent
    from datetime import datetime, timezone
    source = Source(id=1, name="Test source", source_type="rss", url="https://example.com", department_tags=["CSE"])
    db_session.add(source)
    await db_session.flush()
    raw = RawContent(source_id=1, original_url="https://example.com/article", original_content="Original article", content_hash="regression-hash")
    db_session.add(raw)
    await db_session.flush()
    item = ProcessedContent(raw_content_id=raw.id, title="Python research for India students", category="technology", status="published", department_tags=["CSE"], visualizations={"geo_relevance_score":80,"student_actionability_score":80}, attractiveness_score=95, published_at=datetime.now(timezone.utc))
    db_session.add(item)
    await db_session.commit()
    from app.services.cache_service import get_cache
    await get_cache().invalidate("feed:*")
    for endpoint in ("trending?department=CSE", "search?q=Python"):
        response = await async_client.get("/api/v1/feed/"+endpoint)
        assert response.status_code == 200
        payload = response.json()
        entries = payload if isinstance(payload, list) else payload["data"]["items"] if isinstance(payload.get("data"), dict) else payload["items"]
        assert entries[0]["original_url"] == raw.original_url
    await login_user(async_client)
    assert (await async_client.post(f"/api/v1/feed/{item.id}/save")).status_code == 200
    saved = await async_client.get("/api/v1/feed/saved")
    assert saved.status_code == 200
    assert "private" in saved.headers["cache-control"]
    assert raw.original_url in saved.text


@pytest.mark.asyncio
async def test_skills_seed_and_tracking(async_client, db_session):
    from sqlalchemy import select
    from app.models import SkillRanking
    await login_user(async_client)
    response = await async_client.get("/api/v1/skills/CSE")
    assert response.status_code == 200
    assert response.json()["skills"]
    assert (await db_session.execute(select(SkillRanking))).scalars().first() is not None
    assert (await async_client.post("/api/v1/skills/track", json={"skill_name":"Python"})).status_code == 200
    response = await async_client.get("/api/v1/skills/CSE")
    assert "Python" in response.json()["tracked_skills"]
    assert response.headers["cache-control"] == "private, no-store"


def test_database_url_normalizes_query_and_driver():
    from app.database_url import async_database_config
    url, args = async_database_config("postgresql://u:p@localhost/db?sslmode=require&application_name=news")
    assert url == "postgresql+asyncpg://u:p@localhost/db?application_name=news"
    assert args["ssl"].check_hostname


def test_production_config_rejects_placeholder_secrets():
    from app.config import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", SECRET_KEY="your-secret-key-change-in-production", JWT_SECRET_KEY="jwt-secret-key-change-in-production")
