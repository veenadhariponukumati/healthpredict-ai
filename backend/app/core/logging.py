"""Structured JSON logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging across the application.

    In production, outputs JSON for log aggregation (Datadog, Grafana, etc.).
    In development, outputs colored console for readability.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    if settings.LOG_FORMAT == "json":
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            foreign_pre_chain=shared_processors,
        )
    else:
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            foreign_pre_chain=shared_processors,
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    # Suppress noisy third-party loggers
    for logger_name in ("uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name or __name__)


class LoggerContext:
    """Context manager for adding structured context to all log messages within a scope."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def __enter__(self) -> LoggerContext:
        structlog.contextvars.bind_contextvars(**self.kwargs)
        return self

    def __exit__(self, *args: Any) -> None:
        structlog.contextvars.unbind_contextvars(*self.kwargs.keys())