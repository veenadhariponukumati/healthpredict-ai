"""Dataset upload routes — manages training dataset lifecycle."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.repositories import UploadedDatasetRepository
from app.db.session import get_db_session
from app.middleware.auth import get_current_user, require_permission
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.domain import DatasetResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """List uploaded datasets for model training."""
    repo = UploadedDatasetRepository(db)
    filters: dict = {"is_active": True}
    if status:
        filters["upload_status"] = status.upper()

    total = await repo.count(filters)
    datasets = await repo.get_multi(
        skip=(page - 1) * per_page,
        limit=per_page,
        sort_field="created_at",
        sort_order="desc",
        filters=filters,
    )

    return PaginatedResponse(
        data=[DatasetResponse.model_validate(d) for d in datasets],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=max(1, (total + per_page - 1) // per_page),
        ),
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Get a single dataset record by ID."""
    repo = UploadedDatasetRepository(db)
    dataset = await repo.get(dataset_id)
    if not dataset or not dataset.is_active:
        raise NotFoundError(
            message="Dataset not found",
            resource_type="dataset",
            resource_id=dataset_id,
        )
    return DatasetResponse.model_validate(dataset)