"""Repository for Patient model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select

from app.db.models.patient import Patient
from app.db.repositories.base import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    """Repository for Patient CRUD operations."""

    def __init__(self, db) -> None:
        super().__init__(Patient, db)

    async def get_by_mrn(self, mrn: str) -> Patient | None:
        """Get a patient by Medical Record Number."""
        query = select(Patient).where(Patient.mrn == mrn)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search(
        self,
        query_str: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Patient]:
        """Search patients by name or MRN."""
        search_pattern = f"%{query_str}%"
        query = (
            select(Patient)
            .where(
                or_(
                    Patient.first_name.ilike(search_pattern),
                    Patient.last_name.ilike(search_pattern),
                    Patient.mrn.ilike(search_pattern),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_patients(
        self, skip: int = 0, limit: int = 100
    ) -> list[Patient]:
        """Get all active (not soft-deleted) patients."""
        return await self.get_multi(
            skip=skip, limit=limit, filters={"is_active": True}
        )

    async def get_patients_by_diagnosis(
        self, diagnosis: str, skip: int = 0, limit: int = 100
    ) -> list[Patient]:
        """Get patients with a specific primary diagnosis."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"primary_diagnosis": diagnosis, "is_active": True},
        )

    async def get_patients_by_risk_level(
        self,
        risk_level: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        """Get patients with a specific last-known risk level.

        This is a simplified version. In production, this would join
        against the predictions table to find the latest prediction per patient.
        """
        # For now, return active patients (risk-level filtering will be
        # implemented with the full prediction join in Phase 3)
        return await self.get_active_patients(skip=skip, limit=limit)