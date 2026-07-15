"""Repository for ModelVersion model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select

from app.db.models.model_version import ModelVersion
from app.db.repositories.base import BaseRepository


class ModelVersionRepository(BaseRepository[ModelVersion]):
    """Repository for ModelVersion CRUD operations."""

    def __init__(self, db) -> None:
        super().__init__(ModelVersion, db)

    async def get_production_model(
        self, model_name: str | None = None
    ) -> ModelVersion | None:
        """Get the current production model."""
        filters: dict[str, Any] = {"stage": "Production"}
        if model_name:
            filters["model_name"] = model_name
        models = await self.get_multi(filters=filters, limit=1)
        return models[0] if models else None

    async def get_models_by_stage(self, stage: str) -> list[ModelVersion]:
        """Get all models at a specific stage."""
        return await self.get_multi(filters={"stage": stage})

    async def get_best_model_by_metric(
        self, metric: str = "f1_score", limit: int = 5
    ) -> list[ModelVersion]:
        """Get the best performing models sorted by a metric."""
        query = select(ModelVersion).order_by(
            getattr(ModelVersion, metric).desc().nullslast()
        ).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def promote_to_production(
        self, model_version_id: str
    ) -> tuple[ModelVersion | None, ModelVersion | None]:
        """Promote a model to production. Archives the previous production model.

        Returns:
            Tuple of (new_production_model, old_archived_model).
        """
        # Get current production model
        old_production = await self.get_production_model()

        # Demote old production to Archived
        if old_production:
            await self.update(
                str(old_production.id),  # type: ignore[arg-type]
                stage="Archived",
                promoted_at=None,
            )

        # Promote new model
        new_production = await self.update(
            model_version_id,
            stage="Production",
            promoted_at=datetime.now(timezone.utc),
        )

        return new_production, old_production

    async def rollback(self) -> ModelVersion | None:
        """Rollback to the most recent staging model.

        Archives current production and promotes the latest staging model.
        """
        # Get current production
        current = await self.get_production_model()

        # Archive current production
        if current:
            await self.update(
                str(current.id),  # type: ignore[arg-type]
                stage="Archived",
                promoted_at=None,
            )

        # Find latest staging model
        staging_models = await self.get_multi(
            filters={"stage": "Staging"},
            sort_field="created_at",
            sort_order="desc",
            limit=1,
        )

        if not staging_models:
            return None

        # Promote staging to production
        return await self.update(
            str(staging_models[0].id),  # type: ignore[arg-type]
            stage="Production",
            promoted_at=datetime.now(timezone.utc),
        )