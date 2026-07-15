"""Rate limiting middleware."""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import RateLimitError


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter.

    In production, this should be replaced with a Redis-based implementation
    using the MessageQueueProtocol interface.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response | JSONResponse:  # type: ignore[name-defined]
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for health endpoints
        if request.url.path in ("/health", "/ready", "/live"):
            return await call_next(request)

        # Determine rate limit based on path
        client_key = self._get_client_key(request)
        limit, window = self._get_rate_limit(request.url.path)

        # Clean old entries
        now = time.time()
        self._requests[client_key] = [
            t for t in self._requests[client_key] if now - t < window
        ]

        # Check rate
        if len(self._requests[client_key]) >= limit:
            retry_after = int(window - (now - self._requests[client_key][0]))
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Try again in {retry_after}s.",
                        "details": {"retry_after_seconds": retry_after},
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                    "Retry-After": str(retry_after),
                },
            )

        # Record request
        self._requests[client_key].append(now)

        # Make the response
        response = await call_next(request)

        # Add rate limit headers
        remaining = limit - len(self._requests[client_key])
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(now + window))

        return response

    def _get_client_key(self, request: Request) -> str:
        """Get a unique key for the client (IP + user ID if available)."""
        forwarded = request.headers.get("X-Forwarded-For", "")
        ip = forwarded.split(",")[0].strip() or request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)
        return f"{user_id or ip}"

    def _get_rate_limit(self, path: str) -> tuple[int, int]:
        """Get (limit, window_seconds) for a given path."""
        if "/auth/" in path:
            return (10, 60)  # 10/minute
        elif "/predict" in path:
            return (100, 60)  # 100/minute
        elif "/training/" in path:
            return (5, 60)  # 5/minute
        elif "/admin/" in path:
            return (50, 60)  # 50/minute
        else:
            return (500, 60)  # Default: 500/minute