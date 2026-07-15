"""Request ID middleware — assigns a unique ID to every request."""

from __future__ import annotations

import uuid

from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique request ID to every request.

    The request ID is set on the request state and returned as a response header.
    It is also injected into the structured logging context.
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:  # type: ignore[name-defined]
        # Get or generate request ID
        request_id = request.headers.get(self.header_name, str(uuid.uuid4()))
        request.state.request_id = request_id

        # Add to structured logging context
        import structlog

        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)

        # Set response header
        response.headers[self.header_name] = request_id

        return response