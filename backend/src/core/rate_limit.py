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
    Read-only monitoring polls (GET on run status/state endpoints) are
    exempt: the command UI polls them at ~1 Hz, which would otherwise
    trip the limiter mid-run and surface false failures to operators
    (Phase 10A-BE). Expensive POST execution endpoints remain limited.

    Uses the client IP as the rate-limit key.
    """

    # GET paths under protected prefixes that are exempt from limiting.
    _EXEMPT_READ_EXACT = ("/api/v1/simulation/state",)
    _EXEMPT_READ_SUFFIXES = ("/status", "/state")

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

    def _is_exempt_read(self, path: str, method: str) -> bool:
        """True for cheap read-only monitoring polls that must never be throttled."""
        if method != "GET":
            return False
        if any(path == exact for exact in self._EXEMPT_READ_EXACT):
            return True
        if not any(path.startswith(p) for p in self.protected_prefixes):
            return False
        return any(path.endswith(suffix) for suffix in self._EXEMPT_READ_SUFFIXES)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if any(request.url.path.startswith(p) for p in self.protected_prefixes):
            if not self._is_exempt_read(request.url.path, request.method):
                client_ip = request.client.host if request.client else "unknown"
                key = f"{client_ip}:{request.url.path}"
                if not self.limiter.is_allowed(key):
                    return Response(
                        content='{"status":"error","detail":"Rate limit exceeded. Try again later."}',
                        status_code=429,
                        media_type="application/json",
                    )
        return await call_next(request)
