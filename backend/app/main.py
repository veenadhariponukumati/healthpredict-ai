"""Main FastAPI application entry point.

Wires together middleware, routes, dependency injection, and observability.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.db.session import close_db, init_db
from app.api.v1.health import router as health_router
from app.middleware.audit import AuditMiddleware
from app.middleware.cors import create_cors_middleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # ── Startup ──────────────────────────────────────────────────────
    logger.info(
        "starting_application",
        environment=settings.ENVIRONMENT,
        version=__version__,
    )

    # Initialize database
    if settings.ENVIRONMENT in ("development", "testing"):
        await init_db()
        logger.info("database_initialized")

    # OpenTelemetry setup (if configured)
    if settings.OTEL_ENABLED:
        _setup_opentelemetry()

    logger.info("application_started")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    logger.info("shutting_down_application")
    await close_db()
    logger.info("application_stopped")


def _setup_opentelemetry() -> None:
    """Configure OpenTelemetry tracing."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": settings.OTEL_SERVICE_NAME,
            "deployment.environment": settings.ENVIRONMENT,
        })

        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        logger.info("opentelemetry_initialized")
    except Exception as e:
        logger.warning("opentelemetry_init_failed", error=str(e))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="Clinical Readmission Prediction & AI Care Coordination Platform - API Gateway",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
        # Security: disable default 422 handler to use custom one
        validation_error_details=settings.DEBUG,
    )

    # ── Exception Handlers ───────────────────────────────────────────
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": getattr(request.state, "request_id", ""),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                    "request_id": getattr(request.state, "request_id", ""),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            },
        )

    # ── Middleware (order matters) ────────────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # CORS (must be early in the chain)
    create_cors_middleware(app)

    # ── Prometheus metrics ──────────────────────────────────────────
    if settings.ENVIRONMENT != "testing":
        Instrumentator().instrument(app).expose(app)

    # ── Lifecycle timing middleware ──────────────────────────────────
    @app.middleware("http")
    async def add_response_time_header(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        process_time = (time.time() - start) * 1000
        response.headers["X-Response-Time-Ms"] = str(round(process_time, 1))
        response.headers["X-Service-Version"] = __version__
        return response

    # ── Routes ───────────────────────────────────────────────────────
    app.include_router(v1_router)
    app.include_router(health_router)

    logger.info(
        "routes_registered",
        routes=len(app.routes),
        api_prefix=settings.API_PREFIX,
    )

    return app


# Single app instance for ASGI servers
app = create_app()