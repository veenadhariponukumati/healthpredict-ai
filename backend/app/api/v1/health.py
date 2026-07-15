"""Health check endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_db_session
from app.schemas.common import HealthCheck, ReadinessCheck

router = APIRouter()

_start_time = time.time()


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Basic health check — is the service alive?"""
    return HealthCheck(
        status="healthy",
        version=settings.APP_VERSION,
        uptime_seconds=time.time() - _start_time,
    )


@router.get("/ready", response_model=ReadinessCheck)
async def readiness_check(db: AsyncSession = Depends(get_db_session)):
    """Readiness check — are all dependencies available?"""
    deps = {}

    # Check PostgreSQL
    try:
        start = time.time()
        await db.execute(text("SELECT 1"))
        pg_latency = (time.time() - start) * 1000
        deps["postgres"] = {"status": "up", "latency_ms": round(pg_latency, 1)}
    except Exception as e:
        deps["postgres"] = {"status": "down", "error": str(e)}

    ready = all(d["status"] == "up" for d in deps.values())

    return ReadinessCheck(
        ready=ready,
        dependencies=deps,
    )


@router.get("/live")
async def liveness_check():
    """Liveness check — is the process alive?"""
    return {"alive": True}