"""Repository for AuditLog model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select

from app.db.models.audit_log import AuditLog
from app.db.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog operations (read-only for production).

    Audit logs are INSERT-only in production. No updates or deletes.
    The base repository's update/delete methods should not be used.
    """

    def __init__(self, db) -> None:
        super().__init__(AuditLog, db)

    async def log_event(
        self,
        actor_id: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
        detail: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log an audit event.

        This is the primary method for creating audit log entries.
        All access to sensitive data should be logged through this method.
        """
        return await self.create(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            detail=detail,
        )

    async def get_by_actor(
        self,
        actor_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Get audit logs for a specific actor."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            sort_field="event_timestamp",
            sort_order="desc",
            filters={"actor_id": actor_id},
        )

    async def get_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Get audit logs for a specific resource."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            sort_field="event_timestamp",
            sort_order="desc",
            filters={
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )

    async def get_by_action(
        self,
        action: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs by action type."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            sort_field="event_timestamp",
            sort_order="desc",
            filters={"action": action},
        )

    async def get_by_time_range(
        self,
        start: datetime,
        end: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs within a time range."""
        query = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.event_timestamp >= start,
                    AuditLog.event_timestamp <= end,
                )
            )
            .order_by(AuditLog.event_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_action(self) -> list[dict[str, Any]]:
        """Get count of audit logs grouped by action."""
        query = select(
            AuditLog.action,
            func.count().label("count"),
        ).group_by(AuditLog.action)
        result = await self.db.execute(query)
        return [
            {"action": row.action, "count": row.count}
            for row in result.all()
        ]