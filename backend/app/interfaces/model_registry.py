"""Model Registry Protocol interface.

Abstraction over model versioning, storage, and promotion.
Implementations: MLflowRegistry, S3ModelRegistry, GCSModelRegistry.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol


class ModelRegistryProtocol(Protocol):
    """Interface for model storage, versioning, and retrieval.

    The Prediction Service and Training Service load/save models through this
    interface — the underlying registry could be MLflow, S3, or local filesystem.
    """

    async def load_production_model(self, model_name: str) -> tuple[Any, str]:
        """Load the currently promoted production model.

        Returns:
            Tuple of (model, version_string).
        """
        ...

    async def register_model(
        self,
        model: Any,
        model_name: str,
        version: str,
        metrics: dict[str, float],
        artifacts: list[str],
    ) -> str:
        """Register a new model version. Returns registry ID."""
        ...

    async def promote_to_production(self, model_name: str, version: str) -> None:
        """Promote a staging model to production. Demotes previous."""
        ...

    async def get_model_versions(
        self,
        model_name: str,
        stage: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List versions, optionally filtered by stage."""
        ...

    async def rollback(self, model_name: str) -> tuple[str, str]:
        """Rollback to previous production version.

        Returns:
            Tuple of (new_version, old_version).
        """
        ...

    async def log_metrics(self, run_id: str, metrics: dict[str, float]) -> None:
        """Log evaluation metrics for a training run."""
        ...

    async def log_artifact(
        self, run_id: str, local_path: str, artifact_path: str
    ) -> None:
        """Store an artifact associated with a run."""
        ...