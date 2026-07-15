"""Base repository with common CRUD operations."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base import TimestampMixin

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository with common database operations.

    All specific repositories inherit from this to ensure consistent
    query patterns across the application.
    """

    def __init__(self, model: type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def get(self, id: Any) -> ModelType | None:
        """Get a record by primary key."""
        query = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_field: str | None = None,
        sort_order: str = "desc",
        filters: dict[str, Any] | None = None,
    ) -> list[ModelType]:
        """Get multiple records with pagination and optional filtering."""
        query = select(self.model)

        if filters:
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    query = query.where(column == value)

        # Sorting
        if sort_field and hasattr(self.model, sort_field):
            sort_col = getattr(self.model, sort_field)
            query = query.order_by(
                sort_col.desc() if sort_order == "desc" else sort_col.asc()
            )
        elif hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())  # type: ignore[attr-defined]

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, id: Any, **kwargs: Any
    ) -> ModelType | None:
        """Update a record by primary key. Returns None if not found."""
        instance = await self.get(id)
        if instance is None:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.db.flush()
        return instance

    async def delete(self, id: Any, soft: bool = True) -> bool:
        """Delete a record. Soft delete by default.

        Soft delete sets is_active = False for models with SoftDeleteMixin.
        Hard delete removes the record permanently.
        """
        instance = await self.get(id)
        if instance is None:
            return False

        if soft and hasattr(instance, "is_active"):
            instance.is_active = False  # type: ignore[attr-defined]
            await self.db.flush()
        else:
            await self.db.delete(instance)
            await self.db.flush()

        return True

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count records, optionally filtered."""
        query = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    query = query.where(column == value)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def exists(self, **kwargs: Any) -> bool:
        """Check if a record exists matching the given filters."""
        query = select(self.model)
        for field, value in kwargs.items():
            column = getattr(self.model, field, None)
            if column is not None:
                query = query.where(column == value)

        query = query.limit(1)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None