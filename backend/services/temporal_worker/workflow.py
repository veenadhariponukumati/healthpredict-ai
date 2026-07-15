"""HighRiskCareCoordinationWorkflow — Temporal orchestration for automation MVP.

This workflow orchestrates the care-coordination pipeline:
  1. Persist workflow started (PostgreSQL)
  2. Trigger n8n care-team notification
  3. Trigger n8n appointment request
  4. Trigger n8n patient reminder
  5. Persist workflow completed
  6. Write audit event

All external I/O is implemented as Activities — no HTTP, DB, or wall-clock
logic in deterministic workflow code.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import (
        persist_workflow_completed,
        persist_workflow_failed,
        persist_workflow_started,
        persist_workflow_step,
        trigger_n8n_appointment_request,
        trigger_n8n_care_team_notification,
        trigger_n8n_patient_reminder,
        write_audit_event,
    )


# ── Input dataclass ────────────────────────────────────────────────

@dataclass
class CareCoordinationInput:
    workflow_id: str
    patient_id: str
    prediction_id: str
    risk_score: float
    risk_level: str
    correlation_id: str
    actor_id: str = "system"
    actor_role: str = "clinician"
    requested_actions: tuple[str, ...] = (
        "care_team_notification",
        "appointment_request",
        "patient_reminder",
    )


# ── Retry policy constants ─────────────────────────────────────────

N8N_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=3,
    non_retryable_error_types=["AssertionError"],
)


# ── Workflow ───────────────────────────────────────────────────────

@workflow.defn
class HighRiskCareCoordinationWorkflow:
    @workflow.run
    async def run(self, inp: CareCoordinationInput) -> dict[str, Any]:
        wf_id = inp.workflow_id
        n8n_results: list[dict[str, Any]] = []
        final_status = "COMPLETED"
        error_info: dict[str, Any] | None = None

        try:
            # 1. Persist workflow started
            await workflow.execute_activity(
                persist_workflow_started,
                args=[
                    wf_id,
                    inp.patient_id,
                    inp.prediction_id,
                    inp.risk_score,
                    inp.risk_level,
                    inp.correlation_id,
                    workflow.info().workflow_id,
                    {
                        "workflow_id": wf_id,
                        "patient_id": inp.patient_id,
                        "prediction_id": inp.prediction_id,
                        "risk_score": inp.risk_score,
                        "risk_level": inp.risk_level,
                        "correlation_id": inp.correlation_id,
                        "requested_actions": list(inp.requested_actions),
                    },
                ],
                start_to_close_timeout=timedelta(seconds=30),
            )

            # ── Step 2: Care-team notification ──
            await workflow.execute_activity(
                persist_workflow_step,
                args=[wf_id, "care_team_notification"],
                start_to_close_timeout=timedelta(seconds=10),
            )
            care_team_result = await workflow.execute_activity(
                trigger_n8n_care_team_notification,
                args=[_build_payload(inp, "care_team_notification")],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=N8N_RETRY_POLICY,
            )
            n8n_results.append(care_team_result)

            # ── Step 3: Appointment request ──
            await workflow.execute_activity(
                persist_workflow_step,
                args=[wf_id, "appointment_request"],
                start_to_close_timeout=timedelta(seconds=10),
            )
            appointment_result = await workflow.execute_activity(
                trigger_n8n_appointment_request,
                args=[_build_payload(inp, "appointment_request")],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=N8N_RETRY_POLICY,
            )
            n8n_results.append(appointment_result)

            # ── Step 4: Patient reminder ──
            await workflow.execute_activity(
                persist_workflow_step,
                args=[wf_id, "patient_reminder"],
                start_to_close_timeout=timedelta(seconds=10),
            )
            reminder_result = await workflow.execute_activity(
                trigger_n8n_patient_reminder,
                args=[_build_payload(inp, "patient_reminder")],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=N8N_RETRY_POLICY,
            )
            n8n_results.append(reminder_result)

        except Exception as e:
            final_status = "FAILED"
            error_info = {"error": str(e), "step": "unknown"}
            await workflow.execute_activity(
                persist_workflow_failed,
                args=[wf_id, {"error": str(e), "results": n8n_results}],
                start_to_close_timeout=timedelta(seconds=30),
            )
            await workflow.execute_activity(
                write_audit_event,
                args=[
                    inp.actor_id,
                    inp.actor_role,
                    "workflow.failed",
                    "workflow",
                    wf_id,
                    {"error": str(e), "risk_level": inp.risk_level},
                ],
                start_to_close_timeout=timedelta(seconds=10),
            )
            raise

        # ── Success path ──
        output = {
            "status": "COMPLETED",
            "actions_completed": list(inp.requested_actions),
            "n8n_results": n8n_results,
        }

        await workflow.execute_activity(
            persist_workflow_completed,
            args=[wf_id, output],
            start_to_close_timeout=timedelta(seconds=30),
        )

        await workflow.execute_activity(
            write_audit_event,
            args=[
                inp.actor_id,
                inp.actor_role,
                "workflow.completed",
                "workflow",
                wf_id,
                {
                    "risk_level": inp.risk_level,
                    "risk_score": inp.risk_score,
                    "correlation_id": inp.correlation_id,
                },
            ],
            start_to_close_timeout=timedelta(seconds=10),
        )

        return output


# ── Helper ─────────────────────────────────────────────────────────

def _build_payload(inp: CareCoordinationInput, action: str) -> dict[str, Any]:
    return {
        "workflow_id": inp.workflow_id,
        "patient_id": inp.patient_id,
        "prediction_id": inp.prediction_id,
        "correlation_id": inp.correlation_id,
        "risk_score": inp.risk_score,
        "risk_level": inp.risk_level,
        "action": action,
        "timestamp": workflow.info().run_id if hasattr(workflow.info(), "run_id") else "",
    }