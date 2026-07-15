"""Repository for UploadedDataset model."""

from __future__ import annotations

from typing import Any

from app.db.models.uploaded_dataset import UploadedDataset
from app.db.repositories.base import BaseRepository


class UploadedDatasetRepository(BaseRepository[UploadedDataset]):
    """Repository for UploadedDataset CRUD operations."""

    def __init__(self, db) -> None:
        super().__init__(UploadedDataset, db)

    async def get_by_name(self, name: str) -> UploadedDataset | None:
        """Get dataset by name."""
        datasets = await self.get_multi(filters={"name": name}, limit=1)
        return datasets[0] if datasets else None

    async def get_by_hash(self, dataset_hash: str) -> UploadedDataset | None:
        """Get dataset by its SHA-256 hash."""
        datasets = await self.get_multi(
            filters={"dataset_hash": dataset_hash}, limit=1
        )
        return datasets[0] if datasets else None

    async def get_active_datasets(
        self, skip: int = 0, limit: int = 50
    ) -> list[UploadedDataset]:
        """Get all active (not soft-deleted) datasets."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            sort_field="created_at",
            sort_order="desc",
            filters={"is_active": True},
        )

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 50
    ) -> list[UploadedDataset]:
        """Get datasets by upload status."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"upload_status": status},
        )