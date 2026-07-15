"""ModelVersion model for tracking registered ML models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin
from app.db.session import Base


class ModelVersion(TimestampMixin, Base):
    """Registered model version in the model registry.

    Maps to the `model_versions` table in the architecture ER diagram.
    Mirrors MLflow model registry state for query performance.
    """

    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    mlflow_experiment_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    mlflow_run_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    model_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="None",
        index=True,
    )
    accuracy: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    precision: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    recall: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    f1_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    roc_auc: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    pr_auc: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    brier_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    inference_latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    model_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    hyperparameters_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    feature_importance: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    artifact_uri: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    pipeline_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    training_duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    n_features: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    n_samples: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    dataset_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    trained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    predictions = relationship(
        "Prediction", back_populates="model_version", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<ModelVersion(id={self.id}, name={self.model_name}, "
            f"version={self.version}, stage={self.stage})>"
        )