"""Tests for authentication endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestAuth:
    """Authentication endpoint tests."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test the health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient):
        """Test user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.org",
                "password": "SecurePass123!",
                "full_name": "New User",
                "role": "clinician",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "newuser@test.org"
        assert data["user"]["role"] == "clinician"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "clinician@test.org",
                "password": "SecurePass123!",
                "full_name": "Duplicate User",
                "role": "clinician",
            },
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "clinician@test.org", "password": "Password123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "clinician@test.org"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user):
        """Test login with invalid password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "clinician@test.org", "password": "WrongPassword!"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.org", "password": "Password123!"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user):
        """Test token refresh."""
        # Login first
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "clinician@test.org", "password": "Password123!"},
        )
        refresh_token = login.json()["refresh_token"]

        # Refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_protected_route_no_token(self, client: AsyncClient):
        """Test accessing a protected route without a token."""
        response = await client.get("/api/v1/patients")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_with_token(self, client: AsyncClient, auth_headers):
        """Test accessing a protected route with a valid token."""
        response = await client.get("/api/v1/patients", headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient, auth_headers):
        """Test logout endpoint."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, auth_headers):
        """Test password change."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "Password123!",
                "new_password": "NewPassword456!",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"