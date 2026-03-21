"""Test configuration and fixtures."""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings, get_settings
from app.api.v1.auth import limiter as auth_limiter
from app.main import app
from app.models import Base, get_db

# Test database URL — fall back to SQLite when PostgreSQL is unavailable
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/newsletter_test")
SQLITE_FALLBACK_URL = "sqlite+aiosqlite:///./test_newsletter.db"

_db_available = False


def _build_engine(url: str):
    return create_async_engine(url, echo=False, future=True)


test_engine = _build_engine(TEST_DATABASE_URL)

# Create test session factory
TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override database dependency for testing."""
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Override the get_db dependency
app.dependency_overrides[get_db] = override_get_db

# Disable rate limits in tests to avoid cross-test interference.
app.state.limiter = Limiter(key_func=get_remote_address, enabled=False)
auth_limiter.enabled = False


@pytest_asyncio.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Create test database tables. Falls back to SQLite if PostgreSQL is unavailable."""
    global test_engine, TestingSessionLocal, _db_available

    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        _db_available = True
    except Exception:
        # PostgreSQL unavailable — switch to SQLite so DB-dependent tests can run
        await test_engine.dispose()
        test_engine = _build_engine(SQLITE_FALLBACK_URL)
        TestingSessionLocal.configure(bind=test_engine)
        try:
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            _db_available = True
        except Exception:
            yield
            return

    yield

    # Clean up
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()
    except Exception:
        pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for testing."""
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client
