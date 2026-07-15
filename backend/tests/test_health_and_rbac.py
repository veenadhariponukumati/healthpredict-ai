"""Tests for health endpoints, RBAC, and repository layer."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import (
    AuditLogRepository,
    ModelVersionRepository,
    PatientRepository,
    PredictionRepository,
    UserRepository,
    WorkflowEventRepository,
)


class TestHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_readiness(self, client: AsyncClient):
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "dependencies" in data

    @pytest.mark.asyncio
    async def test_liveness(self, client: AsyncClient):
        response = await client.get("/live")
        assert response.status_code == 200
        assert response.json()["alive"] is True


class TestRBAC:
    """Role-based access control tests."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_write_patients(
        self, client: AsyncClient, test_user
    ):
        """Test that viewer role cannot create patients."""
        # Register a viewer
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "viewer@test.org",
                "password": "ViewerPass123!",
                "full_name": "Viewer User",
                "role": "viewer",
            },
        )
        # Login as viewer
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@test.org", "password": "ViewerPass123!"},
        )
        token = resp.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {token}"}

        # Try to create patient
        response = await client.post(
            "/api/v1/patients",
            headers=viewer_headers,
            json={
                "mrn": "MRN-000100",
                "first_name": "Viewer",
                "last_name": "Test",
                "date_of_birth": "1990-01-01",
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_access_audit_logs(
        self, client: AsyncClient, admin_headers
    ):
        """Test that admin can access audit logs."""
        response = await client.get("/api/v1/audit", headers=admin_headers)
        # Should succeed (admin has audit:read permission)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_clinician_cannot_access_audit_logs(
        self, client: AsyncClient, auth_headers
    ):
        """Test that clinician cannot access audit logs."""
        response = await client.get("/api/v1/audit", headers=auth_headers)
        # Should fail (clinician does not have audit:read permission)
        assert response.status_code == 403


class TestRepositories:
    """Repository layer tests."""

    @pytest.mark.asyncio
    async def test_user_repository_create(self, test_session: AsyncSession):
        repo = UserRepository(test_session)
        user = await repo.create(
            email="test@example.com",
            password_hash="hashed",
            full_name="Test User",
            role="viewer",
        )
        assert user.id is not None
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_user_repository_get_by_email(self, test_session: AsyncSession):
        repo = UserRepository(test_session)
        await repo.create(
            email="findme@example.com",
            password_hash="hashed",
            full_name="Find Me",
            role="clinician",
        )
        user = await repo.get_by_email("findme@example.com")
        assert user is not None
        assert user.full_name == "Find Me"

    @pytest.mark.asyncio
    async def test_patient_repository_search(self, test_session: AsyncSession):
        from datetime import date

        repo = PatientRepository(test_session)
        await repo.create(
            mrn="MRN-999999",
            first_name="Searchable",
            last_name="Patient",
            date_of_birth=date(1980, 5, 15),
            age=46,
        )
        results = await repo.search("Searchable")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_prediction_repository_aggregate_stats(
        self, test_session: AsyncSession, sample_patient
    ):
        from datetime import date

        # Create the patient first
        pat_repo = PatientRepository(test_session)
        patient = await pat_repo.create(
            mrn="MRN-888888",
            first_name="Stats",
            last_name="Patient",
            date_of_birth=date(1950, 1, 1),
            age=76,
        )

        repo = PredictionRepository(test_session)
        await repo.create(
            patient_id=patient.id,
            risk_score=0.72,
            risk_level="HIGH",
            confidence=0.89,
            threshold=0.35,
            features={"age": 76},
        )
        await repo.create(
            patient_id=patient.id,
            risk_score=0.15,
            risk_level="LOW",
            confidence=0.75,
            threshold=0.35,
            features={"age": 76},
        )
        stats = await repo.get_aggregate_stats()
        assert stats["total"] >= 2
        assert stats["high_risk"] >= 1

    @pytest.mark.asyncio
    async def test_audit_log_repository_log_event(self, test_session: AsyncSession):
        repo = AuditLogRepository(test_session)
        log = await repo.log_event(
            actor_id="test_user",
            actor_role="admin",
            action="CREATE",
            resource_type="patient",
            resource_id="pat_123",
        )
        assert log.id is not None
        assert log.action == "CREATE"

    @pytest.mark.asyncio
    async def test_model_version_repository_promotion(
        self, test_session: AsyncSession
    ):
        repo = ModelVersionRepository(test_session)

        # Create two model versions
        v1 = await repo.create(
            model_name="test-model",
            model_type="xgboost",
            version="1.0.0",
            stage="Production",
            f1_score=0.81,
        )
        v2 = await repo.create(
            model_name="test-model",
            model_type="xgboost",
            version="2.0.0",
            stage="Staging",
            f1_score=0.85,
        )

        # Promote v2 to production
        new_prod, old_prod = await repo.promote_to_production(str(v2.id))
        assert new_prod is not None
        assert new_prod.stage == "Production"
        assert old_prod is not None
        assert old_prod.stage == "Archived"

    @pytest.mark.asyncio
    async def test_workflow_event_repository_tracking(
        self, test_session: AsyncSession
    ):
        repo = WorkflowEventRepository(test_session)
        event = await repo.create(
            workflow_type="care_coordination",
            status="PENDING",
            input_payload={"patient_id": "pat_123", "risk_score": 0.72},
        )
        assert event.id is not None
        assert event.status == "PENDING"

        # Update to completed
        updated = await repo.update(str(event.id), status="COMPLETED")
        assert updated is not None
        assert updated.status == "COMPLETED"