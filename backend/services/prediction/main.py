"""Prediction Service — model inference, SHAP explanations, and risk scoring.

Standalone FastAPI service (port 8001).
"""

from __future__ import annotations

import time
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.core.logging import get_logger, setup_logging
from ml.explainability.shap_explainer import ShapExplainer
from ml.features.pipeline import FeaturePipeline

logger = get_logger(__name__)

# ── State ────────────────────────────────────────────────────────────
model = None
pipeline = None
explainer = None
model_version = "not_loaded"
feature_names: list[str] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, pipeline, explainer, model_version, feature_names
    setup_logging()

    # Load model from MLflow registry (or local cache), falling back to the
    # bundled dev model shipped with the service image.
    model_path = Path("/models/current/model.pkl")
    pipeline_path = Path("/models/current/pipeline.pkl")
    bundled_model_path = Path("/app/models/random_forest.pkl")

    if model_path.exists():
        import joblib
        data = joblib.load(model_path)
        model = data["model"]
        model_version = data.get("version", "unknown")
        logger.info("model_loaded", version=model_version, source="cache")
    elif bundled_model_path.exists():
        import joblib
        model = joblib.load(bundled_model_path)
        model_version = "bundled-dev"
        logger.info("model_loaded", version=model_version, source="bundled")

    if pipeline_path.exists():
        pipeline = FeaturePipeline.load(pipeline_path)
        feature_names = pipeline.feature_names

    if model is not None and feature_names:
        explainer = ShapExplainer(model, feature_names)
        logger.info("shap_explainer_initialized")

    yield

    logger.info("prediction_service_shutdown")


app = FastAPI(
    title="Prediction Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Schemas ──────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    patient_id: str
    features: dict[str, float]
    generate_explanation: bool = True


class PredictionResponse(BaseModel):
    prediction_id: str
    risk_score: float
    risk_level: str
    confidence: float
    threshold: float
    model_version: str
    model_name: str
    timestamp: str
    latency_ms: int


class FeatureImportance(BaseModel):
    feature: str
    value: float
    shap_value: float
    contribution: str


class ExplanationResponse(BaseModel):
    shap_values: dict[str, float]
    base_value: float
    top_features: list[FeatureImportance]


class FullPredictionResponse(PredictionResponse):
    explanation: ExplanationResponse | None = None


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_version": model_version,
    }


@app.get("/ready")
async def readiness():
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {
        "ready": True,
        "model_loaded": True,
        "model_version": model_version,
    }


@app.post("/predict", response_model=FullPredictionResponse)
async def predict(request: PredictionRequest):
    global model, pipeline, explainer
    start = time.time()

    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Prepare features
    if pipeline is not None:
        import pandas as pd
        df = pd.DataFrame([request.features])
        X = pipeline.transform(df)
    else:
        X = np.array([list(request.features.values())])

    # Infer
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        risk_score = float(proba[0, 1])
    else:
        risk_score = float(model.predict(X)[0])

    # Determine risk level
    threshold = 0.35
    if risk_score >= 0.65:
        risk_level = "CRITICAL"
    elif risk_score >= threshold:
        risk_level = "HIGH"
    elif risk_score >= 0.20:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    # Confidence = distance from 0.5 (normalized)
    confidence = float(1.0 - abs(risk_score - 0.5) * 2)

    import uuid
    from datetime import datetime, timezone

    latency_ms = int((time.time() - start) * 1000)

    response = FullPredictionResponse(
        prediction_id=str(uuid.uuid4()),
        risk_score=risk_score,
        risk_level=risk_level,
        confidence=confidence,
        threshold=threshold,
        model_version=model_version,
        model_name="readmission-predictor",
        timestamp=datetime.now(timezone.utc).isoformat(),
        latency_ms=latency_ms,
    )

    # SHAP explanation
    if request.generate_explanation and explainer is not None:
        explanation_start = time.time()
        shap_result = explainer.compute_local(X[0], feature_names)
        shap_result["computation_time_ms"] = int(
            (time.time() - explanation_start) * 1000
        )

        response.explanation = ExplanationResponse(
            shap_values=shap_result["shap_values"],
            base_value=shap_result["base_value"],
            top_features=[
                FeatureImportance(**f) for f in shap_result["top_features"]
            ],
        )

    return response


@app.post("/predict/batch")
async def batch_predict(requests: list[PredictionRequest]):
    """Batch prediction endpoint."""
    results = []
    for req in requests:
        result = await predict(req)
        results.append(result)
    return {
        "predictions": results,
        "count": len(results),
    }