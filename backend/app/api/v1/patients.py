"""Patient CRUD endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateError, NotFoundError
from app.db.repositories import PatientRepository
from app.db.session import get_db_session
from app.middleware.auth import get_current_user, require_permission, require_role
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.domain import PatientCreate, PatientResponse, PatientUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[PatientResponse])
async def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    diagnosis: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """List patients with pagination and optional filtering."""
    repo = PatientRepository(db)

    filters = {}
    if diagnosis:
        filters["primary_diagnosis"] = diagnosis

    total = await repo.count(filters)
    patients = await repo.get_multi(
        skip=(page - 1) * per_page,
        limit=per_page,
        sort_field=sort_by,
        sort_order=sort_order,
        filters=filters,
    )

    # Convert UUIDs to strings for response serialization
    for p in patients:
        p.id = str(p.id)

    return PaginatedResponse(
        data=[PatientResponse.model_validate(p) for p in patients],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=max(1, (total + per_page - 1) // per_page),
        ),
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Get a single patient by ID."""
    repo = PatientRepository(db)
    patient = await repo.get(patient_id)
    if not patient or not patient.is_active:
        raise NotFoundError(
            message="Patient not found",
            resource_type="patient",
            resource_id=patient_id,
        )
    patient.id = str(patient.id)
    return PatientResponse.model_validate(patient)


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    request: PatientCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_permission("patients:write")),
):
    """Create a new patient record."""
    repo = PatientRepository(db)

    # Check for duplicate MRN
    existing = await repo.get_by_mrn(request.mrn)
    if existing:
        raise DuplicateError(
            message="Patient with this MRN already exists",
            resource_type="patient",
            field="mrn",
            value=request.mrn,
        )

    # Compute age from date_of_birth
    today = date.today()
    age = (
        today.year - request.date_of_birth.year
        - ((today.month, today.day) < (request.date_of_birth.month, request.date_of_birth.day))
    )

    patient = await repo.create(
        **request.model_dump(),
        age=age,
    )
    patient.id = str(patient.id)
    return PatientResponse.model_validate(patient)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    request: PatientUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_permission("patients:write")),
):
    """Update an existing patient record."""
    repo = PatientRepository(db)
    patient = await repo.update(patient_id, **request.model_dump(exclude_unset=True))
    if not patient:
        raise NotFoundError(
            message="Patient not found",
            resource_type="patient",
            resource_id=patient_id,
        )
    patient.id = str(patient.id)
    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: str,
    soft: bool = True,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_role("admin")),
):
    """Soft-delete a patient record (admin only)."""
    repo = PatientRepository(db)
    deleted = await repo.delete(patient_id, soft=soft)
    if not deleted:
        raise NotFoundError(
            message="Patient not found",
            resource_type="patient",
            resource_id=patient_id,
        )
    return {"message": "Patient deleted successfully"}