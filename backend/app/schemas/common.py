"""Shared Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Standard API Response ───────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response format."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponseWrapper(BaseModel):
    """Wrapper for error responses."""

    error: ErrorResponse


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int = Field(ge=1, default=1)
    per_page: int = Field(ge=1, le=100, default=20)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    data: list[T]
    pagination: PaginationMeta


class SuccessResponse(BaseModel):
    """Generic success response."""

    message: str = "Success"
    data: dict[str, Any] | None = None


# ── Health ──────────────────────────────────────────────────────────

class HealthCheck(BaseModel):
    """Health check response."""

    status: str
    version: str
    uptime_seconds: float


class ReadinessCheck(BaseModel):
    """Readiness check response."""

    ready: bool
    dependencies: dict[str, dict[str, Any]]


# ── Common Filters ──────────────────────────────────────────────────

class BaseFilters(BaseModel):
    """Base query parameters for list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: str | None = Field(default=None, description="Sort field")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")