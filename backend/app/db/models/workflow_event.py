"""WorkflowEvent model for tracking care coordination workflows."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin
from app.db.session import Base


class WorkflowEvent(TimestampMixin, Base):
    """Care coordination workflow execution event.

    Maps to the `workflow_events` table in the architecture ER diagram.
    Tracks the lifecycle of Temporal + n8n workflow executions.
    """

    __tablename__ = "workflow_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("predictions.id", ondelete="SET NULL"),
        nullable=True,
    )
    workflow_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    temporal_workflow_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    n8n_execution_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    input_payload: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    output_result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    error_details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    patient = relationship(
        "Patient", back_populates="workflow_events", lazy="selectin"
    )
    prediction = relationship(
        "Prediction", back_populates="workflow_events", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowEvent(id={self.id}, type={self.workflow_type}, "
            f"status={self.status})>"
        )