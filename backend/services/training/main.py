"""Training Service — model training, HPO, evaluation, and comparison.

Standalone FastAPI service (port 8002).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sklearn.model_selection import train_test_split

from app.core.logging import get_logger, setup_logging
from ml.evaluation.metrics import (
    compare_models,
    compute_all_metrics,
    compute_calibration,
    compute_confusion_matrix,
    find_optimal_threshold,
)
from ml.features.pipeline import FeaturePipeline, generate_sample_patients
from ml.models.trainers import (
    LogisticRegressionModel,
    RandomForestModel,
    XGBoostModel,
    PyTorchNNModel,
    BaseModel,
)

logger = get_logger(__name__)

# Model registry
MODEL_CLASSES: dict[str, type[BaseModel]] = {
    "logistic_regression": LogisticRegressionModel,
    "random_forest": RandomForestModel,
    "xgboost": XGBoostModel,
    "pytorch_nn": PyTorchNNModel,
}

# Training state
training_state: dict[str, Any] = {}

app = FastAPI(title="Training Service", version="1.0.0")


# ── Schemas ──────────────────────────────────────────────────────────

class TrainingConfig(BaseModel):
    dataset_version: str = "v1.0"
    models_to_train: list[str] = [
        "logistic_regression", "random_forest", "xgboost", "pytorch_nn"
    ]
    hyperparameter_trials: dict[str, int] = {
        "logistic_regression": 24,
        "random_forest": 50,
        "xgboost": 80,
        "pytorch_nn": 60,
    }
    cross_validation_folds: int = 5
    test_split: float = 0.15
    random_seed: int = 42
    n_samples: int = 42000


class TrainingStatus(BaseModel):
    experiment_id: str
    status: str
    progress: dict[str, Any]
    started_at: str
    elapsed_seconds: float


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "training_in_progress": training_state.get("status") == "RUNNING",
    }


@app.post("/training/start")
async def start_training(config: TrainingConfig) -> dict[str, Any]:
    """Start a full training run with all 4 model types."""
    experiment_id = str(uuid.uuid4())
    start_time = time.time()

    training_state[experiment_id] = {
        "status": "RUNNING",
        "progress": {},
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # 1. Generate / load dataset
        logger.info("generating_dataset", n_samples=config.n_samples)
        df = generate_sample_patients(config.n_samples, config.random_seed)
        dataset_hash = FeaturePipeline("1.0.0").compute_dataset_hash(df)

        # 2. Feature engineering
        logger.info("building_feature_pipeline")
        pipeline = FeaturePipeline(version=config.dataset_version)

        X = df.drop(columns=["readmitted_30day"])
        y = df["readmitted_30day"].values

        X_transformed = pipeline.fit_transform(X)
        logger.info(
            "pipeline_complete",
            n_features=X_transformed.shape[1],
        )

        # 3. Train/val/test split
        X_temp, X_test, y_temp, y_test = train_test_split(
            X_transformed, y,
            test_size=config.test_split,
            random_state=config.random_seed,
            stratify=y,
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp,
            test_size=0.176,  # ~15% of total for val
            random_state=config.random_seed,
            stratify=y_temp,
        )

        logger.info(
            "data_split",
            train=len(X_train), val=len(X_val), test=len(X_test),
        )

        # 4. Train each model with HPO
        model_results = []

        for model_name in config.models_to_train:
            model_class = MODEL_CLASSES.get(model_name)
            if model_class is None:
                logger.warning("unknown_model", model=model_name)
                continue

            logger.info("training_model", model=model_name)
            model_instance = model_class()
            n_trials = config.hyperparameter_trials.get(model_name, 30)

            # Hyperparameter optimization
            best_params = model_instance.optimize_hyperparameters(
                X_train, y_train, X_val, y_val,
                n_trials=n_trials,
                seed=config.random_seed,
            )

            # Train with best params
            model_instance.fit(X_train, y_train, X_val, y_val, params=best_params)

            # Evaluate on test set
            y_pred = model_instance.predict(X_test)
            y_prob = model_instance.predict_proba(X_test)[:, 1]

            metrics = compute_all_metrics(y_test, y_pred, y_prob)
            cm = compute_confusion_matrix(y_test, y_pred)
            calibration = compute_calibration(y_test, y_prob)
            threshold_analysis = find_optimal_threshold(y_test, y_prob)

            # Measure inference latency
            latency_start = time.time()
            for _ in range(100):
                model_instance.predict_proba(X_test[:1])
            latency_ms = (time.time() - latency_start) / 100 * 1000

            model_size = model_instance.get_model_size_mb()

            model_results.append({
                "model_name": model_name,
                "model_type": model_instance.model_type,
                "metrics": metrics,
                "confusion_matrix": cm,
                "calibration": calibration,
                "threshold_analysis": threshold_analysis,
                "best_params": best_params,
                "feature_importance": model_instance.feature_importance,
                "inference_latency_ms": round(latency_ms, 2),
                "model_size_mb": round(model_size, 2),
            })

            logger.info(
                "model_trained",
                model=model_name,
                f1=metrics["f1_score"],
                roc_auc=metrics["roc_auc"],
            )

            # Save model artifact
            model_dir = Path(f"/models/{experiment_id}/{model_name}")
            model_dir.mkdir(parents=True, exist_ok=True)
            joblib.dump(
                {"model": model_instance.model, "version": model_name},
                model_dir / "model.pkl",
            )

        # 5. Compare and select best model
        comparison = compare_models(model_results)

        # 6. Train best model on full train+val
        best_name = comparison["best_model"]
        best_config = next(
            r for r in model_results if r["model_name"] == best_name
        )
        best_class = MODEL_CLASSES[best_name]
        best_model = best_class()
        best_model.fit(
            np.vstack([X_train, X_val]),
            np.concatenate([y_train, y_val]),
            params=best_config["best_params"],
        )

        # 7. Save final model + pipeline
        output_dir = Path("/models/current")
        output_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(
            {
                "model": best_model.model,
                "version": best_name,
                "metrics": best_config["metrics"],
                "comparison": comparison,
            },
            output_dir / "model.pkl",
        )
        pipeline.save(output_dir / "pipeline.pkl")

        elapsed = time.time() - start_time

        training_state[experiment_id] = {
            "status": "COMPLETED",
            "best_model": best_name,
            "best_f1": best_config["metrics"]["f1_score"],
            "dataset_hash": dataset_hash,
            "comparison": comparison,
            "results": model_results,
            "elapsed_seconds": round(elapsed, 1),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            "training_complete",
            experiment_id=experiment_id,
            best_model=best_name,
            best_f1=best_config["metrics"]["f1_score"],
            elapsed_seconds=round(elapsed, 1),
        )

        return {
            "experiment_id": experiment_id,
            "status": "COMPLETED",
            "best_model": best_name,
            "best_f1": best_config["metrics"]["f1_score"],
            "best_roc_auc": best_config["metrics"]["roc_auc"],
            "comparison": comparison,
            "elapsed_seconds": round(elapsed, 1),
        }

    except Exception as e:
        logger.exception("training_failed", error=str(e))
        training_state[experiment_id] = {"status": "FAILED", "error": str(e)}
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/status/{experiment_id}")
async def get_training_status(experiment_id: str) -> dict[str, Any]:
    """Get the status of a training run."""
    state = training_state.get(experiment_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return state


@app.get("/training/results/{experiment_id}")
async def get_training_results(experiment_id: str) -> dict[str, Any]:
    """Get detailed results of a completed training run."""
    state = training_state.get(experiment_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if state["status"] != "COMPLETED":
        raise HTTPException(status_code=400, detail="Training not yet completed")
    return state