"""Repository for WorkflowEvent model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.models.workflow_event import WorkflowEvent
from app.db.repositories.base import BaseRepository


class WorkflowEventRepository(BaseRepository[WorkflowEvent]):
    """Repository for WorkflowEvent CRUD operations."""

    def __init__(self, db) -> None:
        super().__init__(WorkflowEvent, db)

    async def get_with_relations(self, id: Any) -> WorkflowEvent | None:
        """Get workflow event with eager-loaded relationships."""
        query = (
            select(WorkflowEvent)
            .options(
                joinedload(WorkflowEvent.patient),
                joinedload(WorkflowEvent.prediction),
            )
            .where(WorkflowEvent.id == id)
        )
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_patient(
        self,
        patient_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[WorkflowEvent]:
        """Get all workflow events for a patient."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            sort_field="triggered_at",
            sort_order="desc",
            filters={"patient_id": patient_id},
        )

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[WorkflowEvent]:
        """Get workflow events by status."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            sort_field="triggered_at",
            sort_order="desc",
            filters={"status": status},
        )

    async def get_pending_retries(self) -> list[WorkflowEvent]:
        """Get workflow events that need retry."""
        return await self.get_multi(
            filters={"status": "RETRYING"},
            sort_field="next_retry_at",
            sort_order="asc",
        )

    async def get_failed_events(self, limit: int = 50) -> list[WorkflowEvent]:
        """Get workflow events that have exhausted retries."""
        return await self.get_multi(
            limit=limit,
            filters={"status": "FAILED"},
            sort_field="triggered_at",
            sort_order="desc",
        )

    async def get_workflow_stats(self) -> dict[str, int]:
        """Get aggregate workflow statistics."""
        events = await self.get_multi(limit=10000)  # Get recent events
        stats: dict[str, int] = {
            "total": len(events),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "retrying": 0,
            "escalated": 0,
        }
        for event in events:
            status = event.status.lower()
            if status in stats:
                stats[status] += 1
        return stats