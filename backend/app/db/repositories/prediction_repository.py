"""Repository for Prediction model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import joinedload

from app.db.models.prediction import Prediction
from app.db.repositories.base import BaseRepository


class PredictionRepository(BaseRepository[Prediction]):
    """Repository for Prediction CRUD operations."""

    def __init__(self, db) -> None:
        super().__init__(Prediction, db)

    async def get_with_relations(self, id: Any) -> Prediction | None:
        """Get prediction with eager-loaded relationships."""
        query = (
            select(Prediction)
            .options(
                joinedload(Prediction.patient),
                joinedload(Prediction.model_version),
                joinedload(Prediction.user),
            )
            .where(Prediction.id == id)
        )
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_patient(
        self,
        patient_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Prediction]:
        """Get all predictions for a patient, newest first."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            sort_field="prediction_timestamp",
            sort_order="desc",
            filters={"patient_id": patient_id},
        )

    async def get_by_risk_level(
        self,
        risk_level: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Prediction]:
        """Get predictions filtered by risk level."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            sort_field="prediction_timestamp",
            sort_order="desc",
            filters={"risk_level": risk_level},
        )

    async def get_latest_for_patient(
        self, patient_id: str
    ) -> Prediction | None:
        """Get the most recent prediction for a patient."""
        query = (
            select(Prediction)
            .where(Prediction.patient_id == patient_id)
            .order_by(Prediction.prediction_timestamp.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_time_range(
        self,
        start: datetime,
        end: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Prediction]:
        """Get predictions within a time range."""
        query = (
            select(Prediction)
            .where(
                and_(
                    Prediction.prediction_timestamp >= start,
                    Prediction.prediction_timestamp <= end,
                )
            )
            .order_by(Prediction.prediction_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_aggregate_stats(
        self, start: datetime | None = None, end: datetime | None = None
    ) -> dict[str, Any]:
        """Get aggregate prediction statistics."""
        query = select(
            func.count(Prediction.id).label("total"),
            func.sum(
                case((Prediction.risk_level == "HIGH", 1), else_=0)
            ).label("high_risk_count"),
            func.sum(
                case((Prediction.risk_level == "CRITICAL", 1), else_=0)
            ).label("critical_count"),
            func.sum(
                case((Prediction.risk_level == "MODERATE", 1), else_=0)
            ).label("moderate_count"),
            func.avg(Prediction.risk_score).label("mean_risk_score"),
            func.avg(Prediction.inference_latency_ms).label("mean_latency_ms"),
        )

        conditions = []
        if start:
            conditions.append(Prediction.prediction_timestamp >= start)
        if end:
            conditions.append(Prediction.prediction_timestamp <= end)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total": row.total or 0,
            "high_risk": row.high_risk_count or 0,
            "critical": row.critical_count or 0,
            "moderate": row.moderate_count or 0,
            "mean_risk_score": float(row.mean_risk_score) if row.mean_risk_score else 0.0,
            "mean_latency_ms": float(row.mean_latency_ms) if row.mean_latency_ms else 0.0,
        }