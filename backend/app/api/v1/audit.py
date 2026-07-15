"""Audit log routes (read-only, admin-only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.repositories import AuditLogRepository
from app.db.session import get_db_session
from app.middleware.auth import require_permission
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.domain import AuditLogResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    actor_id: str | None = Query(None),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_permission("audit:read")),
):
    """List audit logs with filtering (admin only)."""
    repo = AuditLogRepository(db)
    filters = {}
    if actor_id:
        filters["actor_id"] = actor_id
    if action:
        filters["action"] = action.upper()
    if resource_type:
        filters["resource_type"] = resource_type

    total = await repo.count(filters)
    logs = await repo.get_multi(
        skip=(page - 1) * per_page,
        limit=per_page,
        sort_field="event_timestamp",
        sort_order="desc",
        filters=filters,
    )

    # Convert UUIDs to strings for response serialization
    for log in logs:
        log.id = str(log.id)

    return PaginatedResponse(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=max(1, (total + per_page - 1) // per_page),
        ),
    )


@router.get("/stats")
async def audit_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_permission("audit:read")),
):
    """Get audit log statistics grouped by action."""
    repo = AuditLogRepository(db)
    return {"actions": await repo.count_by_action()}


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_permission("audit:read")),
):
    """Get a single audit log entry."""
    repo = AuditLogRepository(db)
    log = await repo.get(log_id)
    if not log:
        raise NotFoundError(
            message="Audit log not found",
            resource_type="audit_log",
            resource_id=log_id,
        )
    log.id = str(log.id)
    return AuditLogResponse.model_validate(log)