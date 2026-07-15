"""UploadedDataset model for tracking dataset versions."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import SoftDeleteMixin, TimestampMixin
from app.db.session import Base


class UploadedDataset(SoftDeleteMixin, TimestampMixin, Base):
    """Uploaded dataset for model training.

    Tracks dataset provenance, version, and metadata.
    Used for reproducible training runs.
    """

    __tablename__ = "uploaded_datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    file_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    row_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    column_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    feature_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    target_column: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    dataset_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    upload_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
    )
    positive_class_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<UploadedDataset(id={self.id}, name={self.name}, "
            f"version={self.version})>"
        )