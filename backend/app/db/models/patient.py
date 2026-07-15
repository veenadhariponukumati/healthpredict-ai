"""Patient model for synthetic patient records."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Date, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import SoftDeleteMixin, TimestampMixin
from app.db.session import Base


class Patient(SoftDeleteMixin, TimestampMixin, Base):
    """Synthetic patient record.

    Maps to the `patients` table in the architecture ER diagram.
    Contains only synthetic data for development and testing.
    """

    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    mrn: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    date_of_birth: Mapped[Date] = mapped_column(
        Date,
        nullable=False,
    )
    gender: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    primary_diagnosis: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    discharge_disposition: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    insurance_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    previous_admissions_6mo: Mapped[int | None] = mapped_column(
        Integer,
        default=0,
    )
    length_of_stay_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    icu_days: Mapped[int | None] = mapped_column(
        Integer,
        default=0,
    )
    procedure_count: Mapped[int | None] = mapped_column(
        Integer,
        default=0,
    )
    medication_count: Mapped[int | None] = mapped_column(
        Integer,
        default=0,
    )
    comorbidity_score: Mapped[float | None] = mapped_column(
        Float,
        default=0.0,
    )
    lab_results: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    vital_signs: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    social_determinants: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    predictions = relationship("Prediction", back_populates="patient", lazy="selectin")
    workflow_events = relationship(
        "WorkflowEvent", back_populates="patient", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, mrn={self.mrn})>"