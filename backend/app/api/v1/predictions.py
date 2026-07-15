"""Prediction routes — delegates to Prediction Service (port 8001)."""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.repositories import PredictionRepository
from app.db.session import get_db_session
from app.middleware.auth import get_current_user
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.domain import (
    BatchPredictionRequest,
    PredictionDetailResponse,
    PredictionRequest,
    PredictionResponse,
)

router = APIRouter()
PREDICTION_SERVICE_URL = os.environ.get(
    "PREDICTION_SERVICE_URL", "http://127.0.0.1:8001"
)


def _uuid_to_str(obj, fields=("id", "patient_id", "user_id", "model_version_id")):
    """Convert UUID fields to strings on an ORM object in-place."""
    for field in fields:
        val = getattr(obj, field, None)
        if val is not None:
            setattr(obj, field, str(val))
    return obj


@router.post("", response_model=PredictionDetailResponse)
async def predict(
    request: PredictionRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Generate a readmission risk prediction by calling the Prediction Service.

    The Prediction Service handles:
    - Feature preprocessing (pipeline v2.3+)
    - Model inference (production model from MLflow)
    - SHAP explainability
    - Risk scoring

    Response includes risk_score, risk_level, confidence, and SHAP explanation.
    """
    repo = PredictionRepository(db)

    # Call Prediction Service
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{PREDICTION_SERVICE_URL}/predict",
                json={
                    "patient_id": request.patient_id,
                    "features": request.features,
                    "generate_explanation": request.generate_explanation,
                },
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Prediction service error: {resp.text}",
                )
            prediction_result = resp.json()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Prediction service unavailable: {exc}",
        )

    # Persist prediction to database
    prediction = await repo.create(
        patient_id=request.patient_id,
        risk_score=prediction_result["risk_score"],
        risk_level=prediction_result["risk_level"],
        confidence=prediction_result.get("confidence", 0.0),
        threshold=prediction_result.get("threshold", 0.35),
        features=request.features,
        shap_values=prediction_result.get("explanation", {}),
        inference_latency_ms=prediction_result.get("latency_ms") or prediction_result.get("inference_latency_ms"),
        user_id=current_user["user_id"],
    )

    _uuid_to_str(prediction)
    return PredictionDetailResponse.model_validate(prediction)


@router.post("/batch")
async def batch_predict(
    request: BatchPredictionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Batch prediction — delegates to Prediction Service batch endpoint."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{PREDICTION_SERVICE_URL}/predict/batch",
                json=[p for p in request.patients],
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Batch prediction error: {resp.text}",
                )
            return resp.json()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Prediction service unavailable: {exc}",
        )


@router.get("", response_model=PaginatedResponse[PredictionResponse])
async def list_predictions(
    patient_id: str | None = Query(None),
    risk_level: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """List predictions with optional filtering."""
    repo = PredictionRepository(db)

    filters = {}
    if patient_id:
        filters["patient_id"] = patient_id
    if risk_level:
        filters["risk_level"] = risk_level.upper()

    total = await repo.count(filters)
    predictions = await repo.get_multi(
        skip=(page - 1) * per_page,
        limit=per_page,
        sort_field="prediction_timestamp",
        sort_order="desc",
        filters=filters,
    )

    # Convert UUIDs to strings for response serialization
    for p in predictions:
        _uuid_to_str(p)

    return PaginatedResponse(
        data=[PredictionResponse.model_validate(p) for p in predictions],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=max(1, (total + per_page - 1) // per_page),
        ),
    )


@router.get("/{prediction_id}", response_model=PredictionDetailResponse)
async def get_prediction(
    prediction_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Get a single prediction with full details."""
    repo = PredictionRepository(db)
    prediction = await repo.get_with_relations(prediction_id)
    if not prediction:
        raise NotFoundError(
            message="Prediction not found",
            resource_type="prediction",
            resource_id=prediction_id,
        )
    _uuid_to_str(prediction)
    return PredictionDetailResponse.model_validate(prediction)


@router.get("/dashboard/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Get dashboard summary statistics."""
    repo = PredictionRepository(db)
    stats = await repo.get_aggregate_stats()

    # Get current production model info
    from app.db.repositories import ModelVersionRepository
    model_repo = ModelVersionRepository(db)
    production_model = await model_repo.get_production_model()

    return {
        "total_predictions": stats["total"],
        "high_risk": stats["high_risk"],
        "critical": stats["critical"],
        "moderate": stats["moderate"],
        "mean_risk_score": stats["mean_risk_score"],
        "current_model": production_model.model_name if production_model else "none",
        "current_model_version": production_model.version if production_model else "none",
    }