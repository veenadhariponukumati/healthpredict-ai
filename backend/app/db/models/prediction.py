"""Prediction model for readmission risk inference results."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin
from app.db.session import Base


class Prediction(TimestampMixin, Base):
    """Readmission risk prediction result.

    Maps to the `predictions` table (partitioned by prediction_timestamp).
    """

    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    features: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    shap_values: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    base_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    llm_explanation: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    llm_explanation_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    inference_latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    feature_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    prediction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    patient = relationship("Patient", back_populates="predictions", lazy="selectin")
    model_version = relationship(
        "ModelVersion", back_populates="predictions", lazy="selectin"
    )
    user = relationship("User", back_populates="predictions", lazy="selectin")
    workflow_events = relationship(
        "WorkflowEvent", back_populates="prediction", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction(id={self.id}, patient={self.patient_id}, "
            f"risk={self.risk_score:.2f}, level={self.risk_level})>"
        )