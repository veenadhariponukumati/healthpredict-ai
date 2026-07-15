"""Workflow event routes."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.repositories import WorkflowEventRepository
from app.db.session import get_db_session
from app.middleware.auth import get_current_user
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.domain import WorkflowDetailResponse, WorkflowEventResponse

router = APIRouter()

WORKFLOW_SERVICE_URL = os.environ.get(
    "WORKFLOW_SERVICE_URL", "http://workflow:8004"
)


def _uuid_to_str(obj, fields=("id", "patient_id", "prediction_id")):
    """Convert UUID fields to strings on an ORM object in-place."""
    for field in fields:
        val = getattr(obj, field, None)
        if val is not None:
            setattr(obj, field, str(val))
    return obj


# ── Schemas ─────────────────────────────────────────────────────────

class WorkflowTriggerRequest(BaseModel):
    patient_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(..., pattern=r"^(LOW|MODERATE|HIGH|CRITICAL)$")
    prediction_id: str | None = None
    correlation_id: str | None = None


class WorkflowTriggerResponse(BaseModel):
    workflow_id: str
    temporal_workflow_id: str
    status: str
    correlation_id: str


# ── Trigger endpoint ────────────────────────────────────────────────

@router.post("/trigger", response_model=WorkflowTriggerResponse)
async def trigger_care_coordination(
    request: WorkflowTriggerRequest,
    current_user: dict = Depends(get_current_user),
):
    """Trigger care coordination automation for HIGH/CRITICAL risk patients.

    Requires clinician or admin role.
    Idempotent: repeated calls with the same correlation_id return existing workflow.
    """
    # ── RBAC ──────────────────────────────────────────────────────
    user_role = current_user.get("role", "viewer")
    if user_role not in ("admin", "clinician"):
        raise HTTPException(
            status_code=403,
            detail="Only clinicians and administrators can trigger care coordination",
        )

    # ── Risk eligibility ──────────────────────────────────────────
    if request.risk_level not in ("HIGH", "CRITICAL"):
        raise HTTPException(
            status_code=400,
            detail=f"Care coordination requires HIGH or CRITICAL risk level, got {request.risk_level}",
        )

    # ── Call workflow service ─────────────────────────────────────
    correlation_id = request.correlation_id or str(uuid.uuid4())

    payload = {
        "patient_id": request.patient_id,
        "risk_score": request.risk_score,
        "risk_level": request.risk_level,
        "prediction_id": request.prediction_id,
        "correlation_id": correlation_id,
        "actor_id": current_user.get("sub", "system"),
        "actor_role": user_role,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{WORKFLOW_SERVICE_URL}/workflow/trigger",
            json=payload,
        )

    if resp.status_code != 200:
        detail = resp.text[:500]
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Workflow service error: {detail}",
        )

    data = resp.json()
    return WorkflowTriggerResponse(
        workflow_id=data.get("workflow_id", ""),
        temporal_workflow_id=data.get("temporal_workflow_id", ""),
        status=data.get("status", "UNKNOWN"),
        correlation_id=data.get("correlation_id", correlation_id),
    )


@router.get("", response_model=PaginatedResponse[WorkflowEventResponse])
async def list_workflows(
    patient_id: str | None = Query(None),
    workflow_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """List workflow events with filtering."""
    repo = WorkflowEventRepository(db)
    filters = {}
    if patient_id:
        filters["patient_id"] = patient_id
    if workflow_type:
        filters["workflow_type"] = workflow_type
    if status:
        filters["status"] = status.upper()

    total = await repo.count(filters)
    events = await repo.get_multi(
        skip=(page - 1) * per_page,
        limit=per_page,
        sort_field="triggered_at",
        sort_order="desc",
        filters=filters,
    )

    return PaginatedResponse(
        data=[WorkflowEventResponse.model_validate(_uuid_to_str(e)) for e in events],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=max(1, (total + per_page - 1) // per_page),
        ),
    )


@router.get("/stats")
async def workflow_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Get aggregate workflow statistics."""
    repo = WorkflowEventRepository(db)
    stats = await repo.get_workflow_stats()
    return stats


@router.get("/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Get a single workflow event with full details."""
    repo = WorkflowEventRepository(db)
    event = await repo.get_with_relations(workflow_id)
    if not event:
        raise NotFoundError(
            message="Workflow event not found",
            resource_type="workflow",
            resource_id=workflow_id,
        )
    return WorkflowDetailResponse.model_validate(_uuid_to_str(event))