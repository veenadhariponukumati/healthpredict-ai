"""Initial migration: create all foundation tables.

Revision ID: 001
Revises: None
Create Date: 2026-07-20
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ── Users ────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer", index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Patients ─────────────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mrn", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("primary_diagnosis", sa.String(255), nullable=True, index=True),
        sa.Column("discharge_disposition", sa.String(100), nullable=True),
        sa.Column("insurance_type", sa.String(50), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("previous_admissions_6mo", sa.Integer(), server_default="0"),
        sa.Column("length_of_stay_days", sa.Integer(), nullable=True),
        sa.Column("icu_days", sa.Integer(), server_default="0"),
        sa.Column("procedure_count", sa.Integer(), server_default="0"),
        sa.Column("medication_count", sa.Integer(), server_default="0"),
        sa.Column("comorbidity_score", sa.Float(), server_default="0.0"),
        sa.Column("lab_results", postgresql.JSONB(), nullable=True),
        sa.Column("vital_signs", postgresql.JSONB(), nullable=True),
        sa.Column("social_determinants", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_patients_name", "patients", ["last_name", "first_name"])

    # ── Model Versions ───────────────────────────────────────────────
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mlflow_experiment_id", sa.Integer(), nullable=True),
        sa.Column("mlflow_run_id", sa.String(50), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=False, index=True),
        sa.Column("model_type", sa.String(30), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False, server_default="None", index=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("roc_auc", sa.Float(), nullable=True),
        sa.Column("pr_auc", sa.Float(), nullable=True),
        sa.Column("brier_score", sa.Float(), nullable=True),
        sa.Column("inference_latency_ms", sa.Float(), nullable=True),
        sa.Column("model_description", sa.Text(), nullable=True),
        sa.Column("hyperparameters_json", postgresql.JSONB(), nullable=True),
        sa.Column("feature_importance", postgresql.JSONB(), nullable=True),
        sa.Column("artifact_uri", sa.String(500), nullable=True),
        sa.Column("pipeline_version", sa.String(20), nullable=True),
        sa.Column("training_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("n_features", sa.Integer(), nullable=True),
        sa.Column("n_samples", sa.Integer(), nullable=True),
        sa.Column("dataset_hash", sa.String(64), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_model_versions_name_version", "model_versions", ["model_name", "version"])

    # ── Predictions ──────────────────────────────────────────────────
    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=False, index=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("shap_values", postgresql.JSONB(), nullable=True),
        sa.Column("base_value", sa.Float(), nullable=True),
        sa.Column("llm_explanation", postgresql.JSONB(), nullable=True),
        sa.Column("llm_explanation_version", sa.String(20), nullable=True),
        sa.Column("inference_latency_ms", sa.Integer(), nullable=True),
        sa.Column("feature_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prediction_timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_predictions_risk_level_partial", "predictions", ["risk_level", "prediction_timestamp"],
                     postgresql_where=sa.text("risk_level IN ('HIGH', 'CRITICAL')"))

    # ── Workflow Events ──────────────────────────────────────────────
    op.create_table(
        "workflow_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("workflow_type", sa.String(30), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING", index=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("temporal_workflow_id", sa.String(100), nullable=True),
        sa.Column("n8n_execution_id", sa.String(100), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(), nullable=True),
        sa.Column("output_result", postgresql.JSONB(), nullable=True),
        sa.Column("error_details", postgresql.JSONB(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_events_pending", "workflow_events", ["status", "triggered_at"],
                     postgresql_where=sa.text("status IN ('PENDING', 'RUNNING', 'RETRYING')"))

    # ── Audit Logs ───────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_id", sa.String(100), nullable=False, index=True),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("action", sa.String(20), nullable=False, index=True),
        sa.Column("resource_type", sa.String(20), nullable=False, index=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("detail", postgresql.JSONB(), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Uploaded Datasets ────────────────────────────────────────────
    op.create_table(
        "uploaded_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("feature_count", sa.Integer(), nullable=True),
        sa.Column("target_column", sa.String(100), nullable=True),
        sa.Column("dataset_hash", sa.String(64), nullable=True, index=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("upload_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("positive_class_ratio", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("uploaded_datasets")
    op.drop_table("audit_logs")
    op.drop_table("workflow_events")
    op.drop_table("predictions")
    op.drop_table("model_versions")
    op.drop_table("patients")
    op.drop_table("users")