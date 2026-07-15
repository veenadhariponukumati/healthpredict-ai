"""API v1 routes for the Readmission Prediction Platform.

This file aggregates all v1 endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.patients import router as patients_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.models import router as models_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.audit import router as audit_router
from app.api.v1.datasets import router as datasets_router

router = APIRouter(prefix="/api/v1")

# Health endpoints at root level too
router.include_router(health_router, tags=["Health"])
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(patients_router, prefix="/patients", tags=["Patients"])
router.include_router(predictions_router, prefix="/predict", tags=["Predictions"])
router.include_router(predictions_router, prefix="/predictions", tags=["Predictions"])
router.include_router(models_router, prefix="/models", tags=["Models"])
router.include_router(workflows_router, prefix="/workflows", tags=["Workflows"])
router.include_router(audit_router, prefix="/audit", tags=["Audit"])
router.include_router(datasets_router, prefix="/datasets", tags=["Datasets"])