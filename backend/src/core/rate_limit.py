"""Simple sliding-window rate limiter for FastAPI dependencies."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class SlidingWindowRateLimiter:
    """Per-key sliding window rate limiter.

    Counts requests within a fixed window (seconds). Returns 429 when
    the count exceeds max_requests.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        window = self._windows[key]
        # Evict expired entries
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self.max_requests:
            return False
        window.append(now)
        return True

    def reset(self) -> None:
        """Clear all rate-limit windows."""
        self._windows.clear()


# Module-level reference to the active limiter (for testing/reset).
active_limiter: SlidingWindowRateLimiter | None = None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that applies per-path rate limiting.

    Only paths matching ``protected_prefixes`` are rate-limited.
    Uses the client IP as the rate-limit key.
    """

    def __init__(
        self,
        app,
        max_requests: int = 30,
        window_seconds: int = 60,
        protected_prefixes: tuple[str, ...] = ("/api/v1/simulation",),
    ) -> None:
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(max_requests, window_seconds)
        self.protected_prefixes = protected_prefixes
        global active_limiter
        active_limiter = self.limiter

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if any(request.url.path.startswith(p) for p in self.protected_prefixes):
            client_ip = request.client.host if request.client else "unknown"
            key = f"{client_ip}:{request.url.path}"
            if not self.limiter.is_allowed(key):
                return Response(
                    content='{"status":"error","detail":"Rate limit exceeded. Try again later."}',
                    status_code=429,
                    media_type="application/json",
                )
        return await call_next(request)
