"""SQLAlchemy model mixins and shared columns."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Mixin adding created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin adding soft-delete support."""

    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        nullable=False,
    )


class AuditMetadataMixin:
    """Mixin for audit tracking columns."""

    created_by: Mapped[str | None] = mapped_column(
        nullable=True,
        index=True,
    )
    updated_by: Mapped[str | None] = mapped_column(
        nullable=True,
    )