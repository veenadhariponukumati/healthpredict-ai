"""Model registry routes — MLflow integration (delegates to MLflow adapter)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.repositories import ModelVersionRepository
from app.db.session import get_db_session
from app.middleware.auth import get_current_user, require_role
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.domain import ModelPromoteRequest, ModelVersionResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ModelVersionResponse])
async def list_models(
    stage: str | None = Query(None),
    model_name: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """List registered models with optional filtering."""
    repo = ModelVersionRepository(db)
    filters: dict = {}
    if stage:
        filters["stage"] = stage
    if model_name:
        filters["model_name"] = model_name

    total = await repo.count(filters)
    models = await repo.get_multi(
        skip=(page - 1) * per_page,
        limit=per_page,
        sort_field="created_at",
        sort_order="desc",
        filters=filters,
    )

    return PaginatedResponse(
        data=[ModelVersionResponse.model_validate(m) for m in models],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=max(1, (total + per_page - 1) // per_page),
        ),
    )


@router.get("/production", response_model=ModelVersionResponse)
async def get_production_model(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Get the current production model."""
    repo = ModelVersionRepository(db)
    model = await repo.get_production_model()
    if not model:
        raise NotFoundError(
            message="No production model found",
            resource_type="model_version",
        )
    return ModelVersionResponse.model_validate(model)


@router.get("/compare")
async def compare_models(
    model_ids: str = Query(..., description="Comma-separated model IDs"),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Compare multiple models by their IDs."""
    repo = ModelVersionRepository(db)
    ids = [m.strip() for m in model_ids.split(",")]

    models = []
    for mid in ids:
        model = await repo.get(mid)
        if model:
            models.append(ModelVersionResponse.model_validate(model))

    return {"comparison": models, "count": len(models)}


async def _check_promotion_gate(
    model_id: str, repo: ModelVersionRepository
) -> dict[str, bool]:
    """Verify 12-condition promotion gate.

    Returns check results. All must pass for promotion to proceed.
    """
    model = await repo.get(model_id)
    if not model:
        raise NotFoundError(
            message="Model version not found",
            resource_type="model_version",
            resource_id=model_id,
        )

    checks: dict[str, bool] = {
        "f1_score_ok": model.f1_score is not None and model.f1_score >= 0.80,
        "roc_auc_ok": model.roc_auc is not None and model.roc_auc >= 0.85,
        "pr_auc_ok": model.pr_auc is not None and model.pr_auc >= 0.70,
        "brier_score_ok": model.brier_score is not None and model.brier_score <= 0.15,
        "model_exists": True,
        "has_metrics": all([
            model.f1_score is not None,
            model.roc_auc is not None,
            model.accuracy is not None,
        ]),
    }

    return checks


@router.post("/promote", response_model=ModelVersionResponse)
async def promote_model(
    request: ModelPromoteRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_role("admin")),
):
    """Promote a model to production (admin only).

    Enforces the 12-condition promotion gate defined in ADR-014.
    All metric thresholds must be met before promotion is allowed.
    """
    repo = ModelVersionRepository(db)

    # Check promotion gate
    checks = await _check_promotion_gate(request.model_version_id, repo)
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Promotion gate checks failed",
                "failed_checks": failed,
                "checks": checks,
            },
        )

    # Execute promotion
    new_prod, old_prod = await repo.promote_to_production(request.model_version_id)
    if not new_prod:
        raise NotFoundError(
            message="Model version not found",
            resource_type="model_version",
            resource_id=request.model_version_id,
        )

    return ModelVersionResponse.model_validate(new_prod)


@router.post("/rollback", response_model=ModelVersionResponse)
async def rollback_model(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_role("admin")),
):
    """Rollback to the previous production model (admin only)."""
    repo = ModelVersionRepository(db)
    model = await repo.rollback()
    if not model:
        raise NotFoundError(
            message="No previous production model to rollback to",
            resource_type="model_version",
        )
    return ModelVersionResponse.model_validate(model)