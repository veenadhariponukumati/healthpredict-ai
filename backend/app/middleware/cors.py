"""CORS middleware configuration."""

from __future__ import annotations

from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings


def create_cors_middleware(app) -> None:
    """Configure CORS middleware for the FastAPI application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-API-Key",
            "X-Forwarded-For",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Response-Time-Ms",
        ],
        max_age=600,  # 10 minutes preflight cache
    )