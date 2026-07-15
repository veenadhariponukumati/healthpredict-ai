"""PostgreSQL Feature Store adapter implementing FeatureStoreProtocol."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.interfaces.feature_store import FeatureStoreProtocol

logger = get_logger(__name__)


class PostgreSQLFeatureStore(FeatureStoreProtocol):
    """PostgreSQL implementation of FeatureStoreProtocol.

    Stores precomputed feature vectors in the feature_store table.
    Uses materialized views for efficient batch retrieval.
    """

    def __init__(self) -> None:
        self._pipeline_version: str = "1.0.0"

    async def _get_session(self) -> AsyncSession:
        """Get a database session."""
        async with async_session_factory() as session:
            return session

    async def get_features(
        self, patient_id: str, pipeline_version: str
    ) -> pd.DataFrame:
        """Retrieve features for a single patient."""
        async with async_session_factory() as session:
            query = text("""
                SELECT feature_vector, pipeline_version, computed_at
                FROM feature_store
                WHERE patient_id = :patient_id
                  AND pipeline_version = :pipeline_version
                ORDER BY version DESC
                LIMIT 1
            """)
            result = await session.execute(
                query,
                {
                    "patient_id": patient_id,
                    "pipeline_version": pipeline_version,
                },
            )
            row = result.fetchone()
            if row is None:
                raise ValueError(
                    f"Features not found for patient {patient_id} "
                    f"at pipeline {pipeline_version}"
                )
            features = pd.DataFrame([row[0]])
            return features

    async def store_features(
        self,
        patient_id: str,
        pipeline_version: str,
        features: pd.DataFrame,
        target: float | None = None,
    ) -> str:
        """Store computed features for a patient."""
        async with async_session_factory() as session:
            feature_json = json.loads(features.to_json(orient="records"))[0]

            query = text("""
                INSERT INTO feature_store
                    (patient_id, pipeline_version, feature_vector, target, is_labeled, computed_at)
                VALUES
                    (:patient_id, :pipeline_version, :feature_vector, :target, :is_labeled, :computed_at)
                RETURNING id
            """)
            result = await session.execute(
                query,
                {
                    "patient_id": patient_id,
                    "pipeline_version": pipeline_version,
                    "feature_vector": json.dumps(feature_json),
                    "target": target,
                    "is_labeled": target is not None,
                    "computed_at": datetime.now(timezone.utc),
                },
            )
            record_id = str(result.scalar())
            await session.commit()
            return record_id

    async def get_batch_features(
        self, patient_ids: list[str], pipeline_version: str
    ) -> pd.DataFrame:
        """Retrieve features for multiple patients."""
        async with async_session_factory() as session:
            query = text("""
                SELECT DISTINCT ON (patient_id) patient_id, feature_vector
                FROM feature_store
                WHERE patient_id = ANY(:patient_ids)
                  AND pipeline_version = :pipeline_version
                ORDER BY patient_id, version DESC
            """)
            result = await session.execute(
                query,
                {
                    "patient_ids": patient_ids,
                    "pipeline_version": pipeline_version,
                },
            )
            rows = result.fetchall()
            if not rows:
                return pd.DataFrame()

            records = []
            for row in rows:
                record = {"patient_id": row[0]}
                record.update(row[1])
                records.append(record)

            return pd.DataFrame(records)

    async def get_latest_pipeline_version(self) -> str:
        """Get the most recent pipeline version."""
        async with async_session_factory() as session:
            query = text("""
                SELECT pipeline_version
                FROM feature_store
                ORDER BY computed_at DESC
                LIMIT 1
            """)
            result = await session.execute(query)
            row = result.fetchone()
            if row:
                self._pipeline_version = row[0]
            return self._pipeline_version

    async def health(self) -> bool:
        """Check feature store availability."""
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception:
            return False