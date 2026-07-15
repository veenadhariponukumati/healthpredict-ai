"""Test configuration and fixtures."""
import os
os.environ.setdefault('JWT_SECRET_KEY', 'test-secret-for-unittests')
os.environ.setdefault('JWT_ALGORITHM', 'HS256')

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base  # noqa: F401 — re-exported for test fixtures
from app.db.repositories import UserRepository
from app.db.session import get_db_session
from app.main import create_app

# Use SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create the test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh test database session per test."""
    # Use a connection-level transaction for isolation
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def app(test_session):
    """Create a test application instance with the test database."""
    application = create_app()

    async def override_get_db():
        yield test_session

    application.dependency_overrides[get_db_session] = override_get_db
    return application


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(test_session):
    """Create a test clinician user."""
    repo = UserRepository(test_session)
    user = await repo.create(
        email="clinician@test.org",
        password_hash=hash_password("Password123!"),
        full_name="Dr. Test Clinician",
        role="clinician",
        is_active=True,
    )
    return user


@pytest_asyncio.fixture
async def test_admin(test_session):
    """Create a test admin user."""
    repo = UserRepository(test_session)
    user = await repo.create(
        email="admin@test.org",
        password_hash=hash_password("AdminPass123!"),
        full_name="Admin User",
        role="admin",
        is_active=True,
    )
    return user


@pytest_asyncio.fixture
async def auth_headers(client, test_user):
    """Get authorization headers for a clinician user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "clinician@test.org", "password": "Password123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client, test_admin):
    """Get authorization headers for an admin user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.org", "password": "AdminPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_patient(test_session):
    """Create a sample patient for testing."""
    from app.db.repositories import PatientRepository

    repo = PatientRepository(test_session)
    from datetime import date

    patient = await repo.create(
        mrn="MRN-000001",
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1950, 1, 15),
        age=76,
        gender="M",
        primary_diagnosis="Congestive Heart Failure",
        previous_admissions_6mo=3,
        length_of_stay_days=14,
        comorbidity_score=7.5,
    )
    return patient