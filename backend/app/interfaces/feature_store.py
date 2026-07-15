"""Feature Store Protocol interface.

Abstraction over feature storage and retrieval.
Implementations: PostgreSQLFeatureStore, FeastFeatureStore, RedisFeatureStore.
"""

from __future__ import annotations

from typing import Optional, Protocol

import pandas as pd


class FeatureStoreProtocol(Protocol):
    """Interface for feature storage and retrieval.

    Business logic imports this protocol, not the implementation.
    The implementation is injected at startup via ServiceContainer.
    """

    async def get_features(
        self, patient_id: str, pipeline_version: str
    ) -> pd.DataFrame:
        """Retrieve precomputed features for a patient at a pipeline version."""
        ...

    async def store_features(
        self,
        patient_id: str,
        pipeline_version: str,
        features: pd.DataFrame,
        target: Optional[float] = None,
    ) -> str:
        """Store computed features. Returns feature record ID."""
        ...

    async def get_batch_features(
        self, patient_ids: list[str], pipeline_version: str
    ) -> pd.DataFrame:
        """Batch feature retrieval for cohort scoring."""
        ...

    async def get_latest_pipeline_version(self) -> str:
        """Return the most recent feature pipeline version."""
        ...

    async def health(self) -> bool:
        """Liveness check."""
        ...