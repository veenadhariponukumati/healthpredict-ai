"""Audit logging middleware — persists auditable actions to PostgreSQL."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import decode_token

logger = get_logger(__name__)

# Actions that should be persisted to audit_logs
AUDITABLE_ACTIONS: dict[str, str] = {
    "POST:/api/v1/predict": "prediction.create",
    "POST:/api/v1/predictions": "prediction.create",
    "PATCH:/api/v1/patients/": "patient.update",
    "PUT:/api/v1/patients/": "patient.update",
    "DELETE:/api/v1/patients/": "patient.delete",
    "POST:/api/v1/auth/register": "auth.register",
    "POST:/api/v1/auth/login": "auth.login",
}

# Paths to always exclude from auditing
SKIP_PATHS = {"/health", "/ready", "/live", "/docs", "/redoc", "/openapi.json", "/metrics"}


def _get_user_id_from_request(request: Request) -> (str, str):
    """Extract user_id and role from the JWT in the Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return "", ""
    token = auth_header[7:]
    try:
        payload = decode_token(token)
        return payload.get("sub", ""), payload.get("role", "")
    except Exception:
        return "", ""


async def create_audit_log(db: AsyncSession, actor_id: str, action: str,
                           resource_type: str, resource_id: str | None = None,
                           status_code: int = 200, metadata_: dict | None = None):
    """Insert an audit log record."""
    stmt = text("""
        INSERT INTO audit_logs (id, actor_id, action, resource_type, resource_id,
                                status_code, metadata, created_at)
        VALUES (:id, :actor_id, :action, :resource_type, :resource_id,
                :status_code, :metadata, :created_at)
    """)
    await db.execute(stmt, {
        "id": str(uuid.uuid4()),
        "actor_id": actor_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id or "",
        "status_code": status_code,
        "metadata": str(metadata_ or {}),
        "created_at": datetime.now(timezone.utc),
    })
    await db.commit()


def _get_resource_id(path: str) -> str | None:
    """Extract resource ID from path patterns like /api/v1/patients/{id}."""
    parts = path.rstrip("/").split("/")
    if len(parts) >= 4 and parts[-2] in ("patients", "predictions", "predict"):
        return parts[-1] if parts[-1] not in ("create", "update", "delete") else None
    return None


def _get_resource_type(path: str) -> str:
    parts = path.rstrip("/").split("/")
    for resource in ("patients", "predictions", "predict", "workflows"):
        if resource in parts:
            return resource
    return "api"


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that persists auditable actions to the audit_logs table."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:  # type: ignore[name-defined]
        # Skip health and docs endpoints
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        # Use the first matching auditable action key
        method = request.method
        path = request.url.path
        action_key = f"{method}:{path}"

        # Check for prefix matches (e.g. PATCH:/api/v1/patients/{id})
        matched_action = None
        for key, action in AUDITABLE_ACTIONS.items():
            if action_key.startswith(key):
                matched_action = action
                break

        # Extract request metadata (before auth runs — user_id may be anonymous)
        request_id = getattr(request.state, "request_id", "unknown")
        ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Log the request
        logger.info(
            "api_request",
            method=method,
            path=path,
            user_id=getattr(request.state, "user_id", "anonymous"),
            request_id=request_id,
            ip_address=ip,
            user_agent=user_agent,
        )

        response = await call_next(request)

        # Log the response
        logger.info(
            "api_response",
            method=method,
            path=path,
            status_code=response.status_code,
            request_id=request_id,
        )

        # Persist audit record for auditable actions on success.
        # Extract user_id and role from JWT in Authorization header.
        user_id, actor_role = _get_user_id_from_request(request)
        if matched_action and response.status_code < 500 and user_id:
            try:
                from sqlalchemy.ext.asyncio import create_async_engine
                from sqlalchemy import text as sql_text
                engine = create_async_engine(settings.DATABASE_URL)
                async with engine.begin() as conn:
                    await conn.execute(sql_text("""
                        INSERT INTO audit_logs (id, actor_id, actor_role, action, resource_type, resource_id,
                                                success, created_at)
                        VALUES (:id, :actor_id, :actor_role, :action, :resource_type, :resource_id,
                                :success, :created_at)
                    """), {
                        "id": str(uuid.uuid4()),
                        "actor_id": user_id,
                        "actor_role": actor_role or "unknown",
                        "action": matched_action,
                        "resource_type": _get_resource_type(path),
                        "resource_id": request.path_params.get("patient_id")
                                       or request.path_params.get("prediction_id")
                                       or _get_resource_id(path) or "",
                        "success": response.status_code < 400,
                        "created_at": datetime.now(timezone.utc),
                    })
                await engine.dispose()
            except Exception as exc:
                logger.warning("audit_persist_failed", error=str(exc))

        return response