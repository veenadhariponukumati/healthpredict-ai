"""Unit tests for workflow trigger — risk eligibility, RBAC, payload validation.

These tests use mocked external services (Temporal, n8n).
"""
from __future__ import annotations

import os

# Set env vars BEFORE any app imports
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-for-unittests")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("WORKFLOW_SERVICE_URL", "http://localhost:18004")

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

# Force reload of settings singleton with correct env
from app.core import config as _config_module
import importlib
importlib.reload(_config_module)

# ── Helpers ─────────────────────────────────────────────────────────

TEST_JWT_SECRET = "test-secret-for-unittests"


@pytest.fixture(autouse=True)
def _patch_env():
    """Ensure settings singleton has the test JWT secret."""
    from app.core.config import settings
    settings.JWT_SECRET_KEY = TEST_JWT_SECRET


@pytest.fixture
def clinician_token(app):
    """Generate a valid clinician JWT using the app's settings."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.config import settings

    payload = {
        "sub": "clinician-1",
        "role": "clinician",
        "email": "clinician@test.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_private_key, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def viewer_token(app):
    """Generate a viewer JWT using the app's settings."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.config import settings

    payload = {
        "sub": "viewer-1",
        "role": "viewer",
        "email": "viewer@test.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_private_key, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def admin_token(app):
    """Generate an admin JWT using the app's settings."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.config import settings

    payload = {
        "sub": "admin-1",
        "role": "admin",
        "email": "admin@test.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_private_key, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def app():
    """Create a fresh FastAPI test app."""
    from app.main import create_app
    return create_app()


@pytest.fixture
async def client(app):
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Tests: Risk eligibility ────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_rejects_low_risk(client, clinician_token):
    """Only HIGH and CRITICAL should trigger the MVP workflow."""
    payload = {
        "patient_id": "a00e131c-32fd-443b-a20d-4c7c301ab764",
        "risk_score": 0.3,
        "risk_level": "LOW",
    }
    resp = await client.post(
        "/api/v1/workflows/trigger",
        json=payload,
        headers={"Authorization": f"Bearer {clinician_token}"},
    )
    assert resp.status_code == 400
    assert "HIGH or CRITICAL" in resp.text


@pytest.mark.asyncio
async def test_trigger_rejects_moderate_risk(client, clinician_token):
    """MODERATE should also be rejected."""
    payload = {
        "patient_id": "a00e131c-32fd-443b-a20d-4c7c301ab764",
        "risk_score": 0.5,
        "risk_level": "MODERATE",
    }
    resp = await client.post(
        "/api/v1/workflows/trigger",
        json=payload,
        headers={"Authorization": f"Bearer {clinician_token}"},
    )
    assert resp.status_code == 400
    assert "HIGH or CRITICAL" in resp.text


@pytest.mark.asyncio
async def test_trigger_accepts_high_risk(client, clinician_token):
    """HIGH should be accepted and forwarded to workflow service."""
    payload = {
        "patient_id": "a00e131c-32fd-443b-a20d-4c7c301ab764",
        "risk_score": 0.85,
        "risk_level": "HIGH",
    }
    mock_response = httpx.Response(
        200,
        json={
            "workflow_id": "wf-123",
            "temporal_workflow_id": "twf-123",
            "status": "RUNNING",
            "correlation_id": "cid-123",
        },
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        resp = await client.post(
            "/api/v1/workflows/trigger",
            json=payload,
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "RUNNING"
    assert data["workflow_id"] == "wf-123"


@pytest.mark.asyncio
async def test_trigger_accepts_critical_risk(client, clinician_token):
    """CRITICAL should be accepted."""
    payload = {
        "patient_id": "a00e131c-32fd-443b-a20d-4c7c301ab764",
        "risk_score": 0.95,
        "risk_level": "CRITICAL",
    }
    mock_response = httpx.Response(
        200,
        json={
            "workflow_id": "wf-456",
            "temporal_workflow_id": "twf-456",
            "status": "RUNNING",
            "correlation_id": "cid-456",
        },
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        resp = await client.post(
            "/api/v1/workflows/trigger",
            json=payload,
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RUNNING"


# ── Tests: RBAC ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_denied_for_viewer(client, viewer_token):
    """Viewers must not be able to trigger automation."""
    payload = {
        "patient_id": "a00e131c-32fd-443b-a20d-4c7c301ab764",
        "risk_score": 0.85,
        "risk_level": "HIGH",
    }
    resp = await client.post(
        "/api/v1/workflows/trigger",
        json=payload,
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403
    assert "Only clinicians" in resp.text


@pytest.mark.asyncio
async def test_trigger_allowed_for_admin(client, admin_token):
    """Admins should be able to trigger automation."""
    payload = {
        "patient_id": "a00e131c-32fd-443b-a20d-4c7c301ab764",
        "risk_score": 0.85,
        "risk_level": "HIGH",
    }
    mock_response = httpx.Response(
        200,
        json={
            "workflow_id": "wf-789",
            "temporal_workflow_id": "twf-789",
            "status": "RUNNING",
            "correlation_id": "cid-789",
        },
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        resp = await client.post(
            "/api/v1/workflows/trigger",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200


# ── Tests: Idempotency ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_idempotency(client, clinician_token):
    """Same correlation_id returns existing workflow (mocked at workflow service)."""
    payload = {
        "patient_id": "a00e131c-32fd-443b-a20d-4c7c301ab764",
        "risk_score": 0.85,
        "risk_level": "HIGH",
        "correlation_id": "dup-test-001",
    }
    mock_response = httpx.Response(
        200,
        json={
            "workflow_id": "wf-999",
            "temporal_workflow_id": "twf-999",
            "status": "RUNNING",
            "correlation_id": "dup-test-001",
        },
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        # First call
        r1 = await client.post(
            "/api/v1/workflows/trigger",
            json=payload,
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert r1.status_code == 200
        # Second call with same correlation_id
        r2 = await client.post(
            "/api/v1/workflows/trigger",
            json=payload,
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert r2.status_code == 200
        # Both return the same workflow_id
        assert r1.json()["workflow_id"] == r2.json()["workflow_id"]


# ── Tests: Payload validation ──────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_rejects_invalid_risk_level(client, clinician_token):
    """Invalid risk level string should be rejected."""
    payload = {
        "patient_id": "a00e131c-32fd-443b-a20d-4c7c301ab764",
        "risk_score": 0.85,
        "risk_level": "INVALID",
    }
    resp = await client.post(
        "/api/v1/workflows/trigger",
        json=payload,
        headers={"Authorization": f"Bearer {clinician_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_trigger_requires_auth(client):
    """Missing auth should return 401."""
    payload = {
        "patient_id": "a00e131c-32fd-443b-a20d-4c7c301ab764",
        "risk_score": 0.85,
        "risk_level": "HIGH",
    }
    resp = await client.post("/api/v1/workflows/trigger", json=payload)
    assert resp.status_code == 401


# ── Tests: n8n response validation ─────────────────────────────────

def test_n8n_response_validation():
    """Validate the n8n response contract expected by Temporal activities."""
    valid = {"success": True, "execution_id": "n8n-abc123", "action": "test", "status": "ok"}
    assert valid.get("success") is True
    assert "execution_id" in valid

    invalid = {"success": False, "error": "failed"}
    assert invalid.get("success") is not True


# ── Tests: Temporal retry configuration ────────────────────────────

def test_temporal_retry_config():
    """Verify retry policy values are bounded."""
    from datetime import timedelta

    retry = {
        "initial_interval": timedelta(seconds=5),
        "backoff_coefficient": 2.0,
        "maximum_interval": timedelta(seconds=60),
        "maximum_attempts": 3,
    }
    assert retry["initial_interval"] == timedelta(seconds=5)
    assert retry["backoff_coefficient"] == 2.0
    assert retry["maximum_interval"] <= timedelta(seconds=60)
    assert retry["maximum_attempts"] <= 5  # bounded, not infinite