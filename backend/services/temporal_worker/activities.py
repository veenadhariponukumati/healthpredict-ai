"""Temporal SDK activities for HighRiskCareCoordinationWorkflow.

Network and database operations are Activities, not inlined in workflow code.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import os

import httpx

from temporalio import activity

# ── Configuration (overridable via env in Docker) ──────────────────
N8N_BASE_URL: str = os.environ.get("N8N_BASE_URL", "http://n8n:5678/webhook")
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://app:dev_password@postgres:5432/readmission",
)
N8N_INTEGRATION_SECRET: str = os.environ.get(
    "N8N_INTEGRATION_SECRET", "dev-integration-secret"
)

# ── Logging helper ─────────────────────────────────────────────────
def _log(msg: str, **kw: Any) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    extra = " ".join(f"{k}={v}" for k, v in kw.items())
    print(f"[activity] {ts} {msg} {extra}")


# ── PostgreSQL helper ──────────────────────────────────────────────
async def _run_db(sql: str, params: dict[str, Any]) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(sql), params)
    finally:
        await engine.dispose()


# ── Activities ─────────────────────────────────────────────────────

@activity.defn
async def persist_workflow_started(
    workflow_id: str,
    patient_id: str,
    prediction_id: str,
    risk_score: float,
    risk_level: str,
    correlation_id: str,
    temporal_workflow_id: str,
    input_payload: dict[str, Any],
) -> None:
    """Insert the initial workflow event row."""
    _log("persist_workflow_started", wf=workflow_id)
    await _run_db(
        """
        INSERT INTO workflow_events
            (id, patient_id, prediction_id, workflow_type, status,
             risk_score, risk_level, correlation_id,
             temporal_workflow_id, input_payload,
             retry_count, max_retries, triggered_at)
        VALUES
            (:id, :patient_id, :prediction_id, :workflow_type, :status,
             :risk_score, :risk_level, :correlation_id,
             :temporal_workflow_id, :input_payload ::jsonb,
             :retry_count, :max_retries, :triggered_at)
        ON CONFLICT (id) DO NOTHING
        """,
        {
            "id": workflow_id,
            "patient_id": patient_id,
            "prediction_id": prediction_id,
            "workflow_type": "HIGH_RISK_CARE_COORDINATION",
            "status": "RUNNING",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "correlation_id": correlation_id,
            "temporal_workflow_id": temporal_workflow_id,
            "input_payload": json.dumps(input_payload),
            "retry_count": 0,
            "max_retries": 3,
            "triggered_at": datetime.now(timezone.utc),
        },
    )


@activity.defn
async def persist_workflow_step(
    workflow_id: str,
    step_name: str,
) -> None:
    """Update the current step for a running workflow."""
    _log("persist_workflow_step", wf=workflow_id, step=step_name)
    await _run_db(
        """
        UPDATE workflow_events
        SET current_step = :step
        WHERE id = :id
        """,
        {"id": workflow_id, "step": step_name},
    )


@activity.defn
async def persist_workflow_completed(
    workflow_id: str,
    output_result: dict[str, Any],
) -> None:
    """Mark workflow as COMPLETED with output result."""
    _log("persist_workflow_completed", wf=workflow_id)
    await _run_db(
        """
        UPDATE workflow_events
        SET status = 'COMPLETED',
            completed_at = :completed_at,
            output_result = :output_result ::jsonb,
            current_step = 'done'
        WHERE id = :id
        """,
        {
            "id": workflow_id,
            "completed_at": datetime.now(timezone.utc),
            "output_result": json.dumps(output_result),
        },
    )


@activity.defn
async def persist_workflow_failed(
    workflow_id: str,
    error_details: dict[str, Any],
) -> None:
    """Mark workflow as FAILED."""
    _log("persist_workflow_failed", wf=workflow_id)
    await _run_db(
        """
        UPDATE workflow_events
        SET status = 'FAILED',
            completed_at = :completed_at,
            error_details = :error_details ::jsonb
        WHERE id = :id
        """,
        {
            "id": workflow_id,
            "completed_at": datetime.now(timezone.utc),
            "error_details": json.dumps(error_details),
        },
    )


@activity.defn
async def write_audit_event(
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    detail: dict[str, Any] | None = None,
) -> None:
    """Write an audit log entry."""
    _log("write_audit_event", action=action, resource=resource_id)
    await _run_db(
        """
        INSERT INTO audit_logs
            (id, actor_id, actor_role, action, resource_type, resource_id, detail, success, event_timestamp)
        VALUES
            (:id, :actor_id, :actor_role, :action, :resource_type, :resource_id, :detail ::jsonb, :success, :event_timestamp)
        """,
        {
            "id": str(uuid.uuid4()),
            "actor_id": actor_id,
            "actor_role": actor_role,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "detail": json.dumps(detail) if detail else "{}",
            "success": True,
            "event_timestamp": datetime.now(timezone.utc),
        },
    )


@activity.defn
async def trigger_n8n_care_team_notification(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Call n8n care-team-notification webhook."""
    _log("trigger_n8n_care_team", wf=payload.get("workflow_id", ""))
    return await _call_n8n("care-team-notification", payload)


@activity.defn
async def trigger_n8n_appointment_request(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Call n8n follow-up-appointment-request webhook."""
    _log("trigger_n8n_appointment", wf=payload.get("workflow_id", ""))
    return await _call_n8n("follow-up-appointment-request", payload)


@activity.defn
async def trigger_n8n_patient_reminder(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Call n8n patient-reminder webhook."""
    _log("trigger_n8n_reminder", wf=payload.get("workflow_id", ""))
    return await _call_n8n("patient-reminder", payload)


# ── Shared n8n caller ──────────────────────────────────────────────

async def _call_n8n(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Call an n8n webhook endpoint and validate the response."""
    url = f"{N8N_BASE_URL}/{action}"
    headers = {
        "Content-Type": "application/json",
    }
    if N8N_INTEGRATION_SECRET:
        headers["X-Integration-Secret"] = N8N_INTEGRATION_SECRET

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(
            f"n8n webhook {action} returned HTTP {resp.status_code}: {resp.text[:500]}"
        )

    body = resp.json()

    # Validate the response contract
    if not isinstance(body, dict):
        raise RuntimeError(f"n8n {action}: expected JSON object, got {type(body).__name__}")
    if body.get("success") is not True:
        raise RuntimeError(f"n8n {action}: success=false, error={body.get('error', 'unknown')}")

    return body