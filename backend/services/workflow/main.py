"""Workflow Service — Temporal + n8n orchestration bridge.

Standalone FastAPI service (port 8004).
Delegates durable execution to Temporal, persists projection to PostgreSQL.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)

# ── Configuration ───────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://app:dev_password@postgres:5432/readmission",
)
TEMPORAL_HOST = os.environ.get("TEMPORAL_HOST", "temporal:7233")
TEMPORAL_TASK_QUEUE = os.environ.get("TEMPORAL_TASK_QUEUE", "care-coordination")
RETRY_INITIAL_INTERVAL = int(os.environ.get("RETRY_INITIAL_INTERVAL", "5"))
RETRY_BACKOFF = float(os.environ.get("RETRY_BACKOFF", "2.0"))
RETRY_MAX_INTERVAL = int(os.environ.get("RETRY_MAX_INTERVAL", "60"))
RETRY_MAX_ATTEMPTS = int(os.environ.get("RETRY_MAX_ATTEMPTS", "3"))


# ── Database helpers ────────────────────────────────────────────────

async def create_workflow_in_db(workflow_data: dict) -> dict:
    """Insert a workflow event into PostgreSQL."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.begin() as conn:
            stmt = text("""
                INSERT INTO workflow_events
                    (id, patient_id, prediction_id, workflow_type, status,
                     retry_count, max_retries, risk_score, risk_level,
                     correlation_id, temporal_workflow_id,
                     triggered_at, completed_at, output_result, error_details)
                VALUES
                    (:id, :patient_id, :prediction_id, :workflow_type, :status,
                     :retry_count, :max_retries, :risk_score, :risk_level,
                     :correlation_id, :temporal_workflow_id,
                     :triggered_at, :completed_at, :output_result, :error_details)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    completed_at = EXCLUDED.completed_at,
                    output_result = EXCLUDED.output_result,
                    error_details = EXCLUDED.error_details
            """)
            await conn.execute(stmt, workflow_data)
        return workflow_data
    finally:
        await engine.dispose()


async def get_workflow_from_db(workflow_id: str) -> dict | None:
    """Fetch a workflow event from PostgreSQL."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.begin() as conn:
            stmt = text("SELECT * FROM workflow_events WHERE id = :id")
            result = await conn.execute(stmt, {"id": workflow_id})
            row = result.fetchone()
            return dict(row._mapping) if row else None
    finally:
        await engine.dispose()


async def get_workflow_by_correlation_id(correlation_id: str) -> dict | None:
    """Fetch a workflow event by correlation_id for idempotency checks."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.begin() as conn:
            stmt = text("SELECT * FROM workflow_events WHERE correlation_id = :cid LIMIT 1")
            result = await conn.execute(stmt, {"cid": correlation_id})
            row = result.fetchone()
            return dict(row._mapping) if row else None
    finally:
        await engine.dispose()


async def list_workflows_from_db(limit: int = 50) -> list[dict]:
    """List recent workflow events from PostgreSQL."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.begin() as conn:
            stmt = text("""
                SELECT * FROM workflow_events
                ORDER BY triggered_at DESC
                LIMIT :limit
            """)
            result = await conn.execute(stmt, {"limit": limit})
            return [dict(r._mapping) for r in result.fetchall()]
    finally:
        await engine.dispose()


async def count_workflows_from_db() -> dict:
    """Get workflow statistics from PostgreSQL."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.begin() as conn:
            stmt = text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'RUNNING') as running,
                    COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed,
                    COUNT(*) FILTER (WHERE status = 'FAILED') as failed
                FROM workflow_events
            """)
            result = await conn.execute(stmt)
            row = result.fetchone()
            return dict(row._mapping) if row else {"total": 0, "running": 0, "completed": 0, "failed": 0}
    finally:
        await engine.dispose()


# ── Temporal client ─────────────────────────────────────────────────

_temporal_client = None


async def get_temporal_client():
    """Get or create the Temporal client singleton."""
    global _temporal_client
    if _temporal_client is None:
        from temporalio.client import Client
        logger.info("connecting_to_temporal", host=TEMPORAL_HOST)
        _temporal_client = await Client.connect(TEMPORAL_HOST)
    return _temporal_client


async def start_temporal_workflow(
    workflow_id: str,
    patient_id: str,
    prediction_id: str,
    risk_score: float,
    risk_level: str,
    correlation_id: str,
    actor_id: str = "system",
    actor_role: str = "clinician",
) -> str:
    """Start HighRiskCareCoordinationWorkflow via Temporal."""
    client = await get_temporal_client()

    from temporalio.client import WorkflowHandle

    # Use correlation_id as idempotency key
    idempotency_key = f"care-coordination-{correlation_id}"

    handle: WorkflowHandle = await client.start_workflow(
        "HighRiskCareCoordinationWorkflow",
        args=[{
            "workflow_id": workflow_id,
            "patient_id": patient_id,
            "prediction_id": prediction_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "correlation_id": correlation_id,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "requested_actions": [
                "care_team_notification",
                "appointment_request",
                "patient_reminder",
            ],
        }],
        id=idempotency_key,
        task_queue=TEMPORAL_TASK_QUEUE,
    )
    return handle.id


# ── Lifespan ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("workflow_service_started",
                temporal_host=TEMPORAL_HOST,
                task_queue=TEMPORAL_TASK_QUEUE)
    yield
    logger.info("workflow_service_shutdown")


app = FastAPI(title="Workflow Service", version="1.0.0", lifespan=lifespan)


# ── Schemas ──────────────────────────────────────────────────────────

class WorkflowTrigger(BaseModel):
    patient_id: str
    risk_score: float
    risk_level: str
    prediction_id: str | None = None
    correlation_id: str | None = None
    workflow_type: str = "HIGH_RISK_CARE_COORDINATION"
    actor_id: str = "system"
    actor_role: str = "clinician"


class WorkflowTriggerResponse(BaseModel):
    workflow_id: str
    temporal_workflow_id: str
    status: str
    correlation_id: str


class WorkflowStatus(BaseModel):
    workflow_id: str
    patient_id: str
    workflow_type: str
    status: str
    retry_count: int = 0
    triggered_at: str
    completed_at: str | None = None
    output_result: dict[str, Any] | None = None
    error_details: dict[str, Any] | None = None
    correlation_id: str | None = None
    current_step: str | None = None
    temporal_workflow_id: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/workflow/trigger", response_model=WorkflowTriggerResponse)
async def trigger_workflow(request: WorkflowTrigger):
    """Trigger a care coordination workflow via Temporal.

    Idempotency: use correlation_id or prediction_id as the idempotency key.
    """
    workflow_id = str(uuid.uuid4())
    triggered_at = datetime.now(timezone.utc)
    correlation_id = request.correlation_id or request.prediction_id or workflow_id

    # Idempotency check — look up existing workflow by correlation_id
    existing = await get_workflow_by_correlation_id(correlation_id)
    if existing is not None:
        return WorkflowTriggerResponse(
            workflow_id=str(existing["id"]),
            temporal_workflow_id=str(existing.get("temporal_workflow_id", "")),
            status=str(existing["status"]),
            correlation_id=correlation_id,
        )

    # Create workflow record in PostgreSQL
    workflow_data = {
        "id": workflow_id,
        "patient_id": request.patient_id,
        "prediction_id": request.prediction_id,
        "workflow_type": request.workflow_type,
        "status": "RUNNING",
        "retry_count": 0,
        "max_retries": RETRY_MAX_ATTEMPTS,
        "risk_score": request.risk_score,
        "risk_level": request.risk_level,
        "correlation_id": correlation_id,
        "temporal_workflow_id": None,
        "triggered_at": triggered_at,
        "completed_at": None,
        "output_result": None,
        "error_details": None,
    }

    await create_workflow_in_db(workflow_data)

    logger.info(
        "workflow_triggered",
        workflow_id=workflow_id,
        patient=request.patient_id,
        risk=request.risk_score,
        correlation_id=correlation_id,
    )

    try:
        temporal_future = await start_temporal_workflow(
            workflow_id=workflow_id,
            patient_id=request.patient_id,
            prediction_id=request.prediction_id or "",
            risk_score=request.risk_score,
            risk_level=request.risk_level,
            correlation_id=correlation_id,
            actor_id=request.actor_id,
            actor_role=request.actor_role,
        )

        # Update temporal_workflow_id in DB
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(DATABASE_URL)
        try:
            async with engine.begin() as conn:
                temporal_wf_id = f"care-coordination-{correlation_id}"
                await conn.execute(
                    text("UPDATE workflow_events SET temporal_workflow_id = :twf WHERE id = :id"),
                    {"twf": temporal_wf_id, "id": workflow_id},
                )
        finally:
            await engine.dispose()

        return WorkflowTriggerResponse(
            workflow_id=workflow_id,
            temporal_workflow_id=temporal_wf_id,
            status="RUNNING",
            correlation_id=correlation_id,
        )

    except Exception as e:
        error_msg = str(e)
        workflow_data.update({
            "status": "FAILED",
            "error_details": json.dumps({"message": error_msg}),
        })
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(DATABASE_URL)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("UPDATE workflow_events SET status = 'FAILED', error_details = :err ::jsonb WHERE id = :id"),
                    {"err": json.dumps({"message": error_msg}), "id": workflow_id},
                )
        finally:
            await engine.dispose()

        logger.error("workflow_trigger_failed", workflow_id=workflow_id, error=error_msg)
        raise HTTPException(status_code=500, detail=f"Workflow trigger failed: {error_msg}")


@app.get("/workflow/{workflow_id}", response_model=WorkflowStatus)
async def get_workflow(workflow_id: str):
    """Get workflow execution status from PostgreSQL."""
    workflow = await get_workflow_from_db(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowStatus(
        workflow_id=str(workflow.get("id", workflow_id)),
        patient_id=str(workflow.get("patient_id", "")),
        workflow_type=workflow.get("workflow_type", "HIGH_RISK_CARE_COORDINATION"),
        status=workflow.get("status", "UNKNOWN"),
        retry_count=workflow.get("retry_count", 0),
        triggered_at=str(workflow.get("triggered_at", "")),
        completed_at=str(workflow.get("completed_at")) if workflow.get("completed_at") else None,
        output_result=workflow.get("output_result"),
        error_details=workflow.get("error_details"),
        correlation_id=str(workflow.get("correlation_id", "")) if workflow.get("correlation_id") else None,
        current_step=workflow.get("current_step"),
        temporal_workflow_id=str(workflow.get("temporal_workflow_id", "")) if workflow.get("temporal_workflow_id") else None,
    )


@app.get("/workflows")
async def list_workflows(limit: int = 50):
    """List recent workflows from PostgreSQL."""
    workflows = await list_workflows_from_db(limit)
    return {"data": workflows, "total": len(workflows)}


@app.get("/workflows/stats")
async def workflow_stats():
    """Get workflow statistics from PostgreSQL."""
    return await count_workflows_from_db()