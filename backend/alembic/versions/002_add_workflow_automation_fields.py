"""Add risk_score, risk_level, correlation_id, current_step to workflow_events."""
from __future__ import annotations

from typing import ClassVar

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "workflow_events",
        sa.Column("risk_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "workflow_events",
        sa.Column("risk_level", sa.String(10), nullable=True),
    )
    op.add_column(
        "workflow_events",
        sa.Column("correlation_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "workflow_events",
        sa.Column("current_step", sa.String(50), nullable=True),
    )
    op.create_index(
        "ix_workflow_events_correlation_id",
        "workflow_events",
        ["correlation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_events_correlation_id", table_name="workflow_events")
    op.drop_column("workflow_events", "current_step")
    op.drop_column("workflow_events", "correlation_id")
    op.drop_column("workflow_events", "risk_level")
    op.drop_column("workflow_events", "risk_score")