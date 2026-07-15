"""Tests for patient endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestPatients:
    """Patient CRUD endpoint tests."""

    @pytest.mark.asyncio
    async def test_create_patient(self, client: AsyncClient, auth_headers):
        """Test creating a patient."""
        response = await client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "mrn": "MRN-000010",
                "first_name": "Jane",
                "last_name": "Smith",
                "date_of_birth": "1965-08-22",
                "gender": "F",
                "primary_diagnosis": "Diabetes Type 2",
                "previous_admissions_6mo": 2,
                "length_of_stay_days": 7,
                "comorbidity_score": 5.0,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["mrn"] == "MRN-000010"
        assert data["first_name"] == "Jane"
        assert data["age"] == 61  # 2026 - 1965

    @pytest.mark.asyncio
    async def test_create_patient_duplicate_mrn(
        self, client: AsyncClient, auth_headers, sample_patient
    ):
        """Test creating a patient with duplicate MRN."""
        response = await client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "mrn": "MRN-000001",
                "first_name": "Duplicate",
                "last_name": "Patient",
                "date_of_birth": "1990-01-01",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_get_patient(self, client: AsyncClient, auth_headers, sample_patient):
        """Test getting a patient by ID."""
        response = await client.get(
            f"/api/v1/patients/{sample_patient.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mrn"] == "MRN-000001"
        assert data["first_name"] == "John"

    @pytest.mark.asyncio
    async def test_get_patient_not_found(self, client: AsyncClient, auth_headers):
        """Test getting a non-existent patient."""
        response = await client.get(
            "/api/v1/patients/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_patients(self, client: AsyncClient, auth_headers, sample_patient):
        """Test listing patients."""
        response = await client.get(
            "/api/v1/patients",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert "pagination" in data
        assert data["pagination"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_update_patient(
        self, client: AsyncClient, auth_headers, sample_patient
    ):
        """Test updating a patient."""
        response = await client.patch(
            f"/api/v1/patients/{sample_patient.id}",
            headers=auth_headers,
            json={"primary_diagnosis": "Updated Diagnosis"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["primary_diagnosis"] == "Updated Diagnosis"

    @pytest.mark.asyncio
    async def test_delete_patient_admin(
        self, client: AsyncClient, admin_headers, sample_patient
    ):
        """Test soft-deleting a patient (admin only)."""
        response = await client.delete(
            f"/api/v1/patients/{sample_patient.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_patient_forbidden_for_clinician(
        self, client: AsyncClient, auth_headers, test_user
    ):
        """Test that clinicians cannot delete patients."""
        # First create a patient as clinician
        create_resp = await client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "mrn": "MRN-000020",
                "first_name": "Delete",
                "last_name": "Test",
                "date_of_birth": "2000-01-01",
            },
        )
        patient_id = create_resp.json()["id"]

        # Try to delete (should be forbidden — clinicians can't delete)
        response = await client.delete(
            f"/api/v1/patients/{patient_id}",
            headers=auth_headers,
        )
        assert response.status_code == 403