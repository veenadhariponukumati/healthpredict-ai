"""MLflow Model Registry adapter implementing ModelRegistryProtocol."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

import mlflow
from mlflow.tracking import MlflowClient

from app.core.config import settings
from app.core.logging import get_logger
from app.interfaces.model_registry import ModelRegistryProtocol

logger = get_logger(__name__)


class MLflowRegistry(ModelRegistryProtocol):
    """MLflow implementation of ModelRegistryProtocol.

    Manages experiment tracking, model versioning, and promotion via MLflow.
    """

    def __init__(
        self,
        tracking_uri: str = "",
        artifact_location: str = "",
    ) -> None:
        self.tracking_uri = tracking_uri or "http://mlflow:5000"
        self.artifact_location = artifact_location or "/mlflow/artifacts"
        self._client: MlflowClient | None = None
        self._initialized = False

    async def init(self) -> None:
        """Initialize MLflow connection."""
        mlflow.set_tracking_uri(self.tracking_uri)
        self._client = MlflowClient()
        self._initialized = True
        logger.info("mlflow_initialized", tracking_uri=self.tracking_uri)

    @property
    def client(self) -> MlflowClient:
        if self._client is None:
            raise RuntimeError("MLflow client not initialized. Call init() first.")
        return self._client

    async def load_production_model(self, model_name: str) -> tuple[Any, str]:
        """Load the current production model from MLflow."""
        try:
            model = mlflow.pyfunc.load_model(
                model_uri=f"models:/{model_name}@production"
            )
            # Get version info
            latest = self.client.get_latest_versions(
                model_name, stages=["Production"]
            )
            version = latest[0].version if latest else "unknown"
            logger.info("loaded_production_model", model=model_name, version=version)
            return model, version
        except Exception as e:
            logger.error("failed_to_load_production_model", error=str(e))
            raise

    async def register_model(
        self,
        model: Any,
        model_name: str,
        version: str,
        metrics: dict[str, float],
        artifacts: list[str],
    ) -> str:
        """Register a model with MLflow."""
        with mlflow.start_run(run_name=f"{model_name}-v{version}") as run:
            run_id = run.info.run_id

            # Log metrics
            for key, value in metrics.items():
                mlflow.log_metric(key, value)

            # Log model
            mlflow.sklearn.log_model(
                sk_model=model,
                artifact_path="model",
                registered_model_name=model_name,
            )

            # Log artifacts
            for artifact_path in artifacts:
                mlflow.log_artifact(artifact_path)

            # Set tags
            mlflow.set_tag("model_version", version)
            mlflow.set_tag("registered_at", datetime.now(timezone.utc).isoformat())

        logger.info(
            "model_registered",
            model=model_name,
            version=version,
            run_id=run_id,
        )
        return run_id

    async def promote_to_production(self, model_name: str, version: str) -> None:
        """Promote a model version to Production."""
        self.client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage="Production",
        )
        # Create or update the "production" alias
        self.client.set_registered_model_alias(
            name=model_name,
            alias="production",
            version=version,
        )
        logger.info("model_promoted_to_production", model=model_name, version=version)

    async def get_model_versions(
        self,
        model_name: str,
        stage: str | None = None,
    ) -> list[dict[str, Any]]:
        """List model versions from MLflow."""
        versions = self.client.search_model_versions(
            f"name='{model_name}'"
        )
        result = []
        for v in versions:
            if stage and v.current_stage != stage:
                continue
            result.append({
                "version": v.version,
                "stage": v.current_stage,
                "run_id": v.run_id,
                "status": v.status,
                "created_at": v.creation_timestamp,
            })
        return result

    async def rollback(self, model_name: str) -> tuple[str, str]:
        """Rollback to the previous production version."""
        versions = self.client.get_latest_versions(
            model_name, stages=["Production"]
        )
        if not versions:
            raise RuntimeError("No production version to rollback from")

        current_version = versions[0].version

        # Find previous version
        all_versions = self.client.search_model_versions(
            f"name='{model_name}'"
        )
        previous = None
        for v in sorted(all_versions, key=lambda x: x.creation_timestamp, reverse=True):
            if v.version != current_version:
                previous = v
                break

        if previous is None:
            raise RuntimeError("No previous version to rollback to")

        # Archive current and restore previous
        self.client.transition_model_version_stage(
            name=model_name,
            version=current_version,
            stage="Archived",
        )
        self.client.transition_model_version_stage(
            name=model_name,
            version=previous.version,
            stage="Production",
        )
        self.client.set_registered_model_alias(
            name=model_name,
            alias="production",
            version=previous.version,
        )

        logger.info(
            "model_rolled_back",
            model=model_name,
            from_version=current_version,
            to_version=previous.version,
        )
        return previous.version, current_version

    async def log_metrics(self, run_id: str, metrics: dict[str, float]) -> None:
        """Log metrics to an existing run."""
        for key, value in metrics.items():
            self.client.log_metric(run_id, key, value)

    async def log_artifact(
        self, run_id: str, local_path: str, artifact_path: str
    ) -> None:
        """Log an artifact to a run."""
        self.client.log_artifact(run_id, local_path, artifact_path)

    async def health(self) -> bool:
        """Check MLflow server availability."""
        try:
            self.client.get_experiment(0)
            return True
        except Exception:
            return False