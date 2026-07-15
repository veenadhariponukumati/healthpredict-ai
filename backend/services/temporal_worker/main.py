"""Temporal Worker — registers workflows and activities.

Connects to Temporal server and starts the worker loop.
"""
from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

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
from workflow import HighRiskCareCoordinationWorkflow

TEMPORAL_HOST = os.environ.get("TEMPORAL_HOST", "localhost:7233")
TASK_QUEUE = os.environ.get("TEMPORAL_TASK_QUEUE", "care-coordination")


async def main() -> None:
    print(f"[worker] Connecting to Temporal at {TEMPORAL_HOST}")
    client = await Client.connect(TEMPORAL_HOST)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[HighRiskCareCoordinationWorkflow],
        activities=[
            persist_workflow_started,
            persist_workflow_completed,
            persist_workflow_failed,
            persist_workflow_step,
            trigger_n8n_care_team_notification,
            trigger_n8n_appointment_request,
            trigger_n8n_patient_reminder,
            write_audit_event,
        ],
    )

    print(f"[worker] Registered HighRiskCareCoordinationWorkflow on queue '{TASK_QUEUE}'")
    print("[worker] Starting worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())