"""AuditLog model for immutable audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import TimestampMixin
from app.db.session import Base


class AuditLog(TimestampMixin, Base):
    """Immutable audit log entry.

    Maps to the `audit_logs` table in the architecture ER diagram.
    Records every access to sensitive data for HIPAA compliance.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    actor_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    actor_role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    detail: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, actor={self.actor_id}, "
            f"action={self.action}, resource={self.resource_type})>"
        )