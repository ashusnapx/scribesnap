"""
ScribeSnap Backend — Rate Limiting Middleware
===============================================

What:  Per-IP sliding window rate limiter to prevent abuse.
Why:   Protects the API from DoS attacks and API quota exhaustion.
How:   Tracks request counts per IP in memory using a sliding window algorithm.
Who:   Applied to every request via Starlette middleware.
When:  First in the middleware chain (rejects abuse before any processing).

Algorithm: Sliding Window Counter
    How it works:
    1. Each IP gets a list of request timestamps
    2. On each request, remove timestamps older than the window
    3. If remaining count >= limit, reject with 429
    4. Otherwise, add current timestamp and allow through
    
    Why sliding window (not fixed window):
    - Fixed window: 100 req/hr resets at :00 → can burst 200 at :59/:00 boundary
    - Sliding window: Always counts last N seconds → smooth rate enforcement
    
    Time complexity: O(k) where k = number of requests in window (amortized O(1))
    Space complexity: O(n × k) where n = unique IPs, k = requests per IP

Production Upgrade Path:
    This in-memory implementation works for single-process deployments.
    For multi-worker/multi-instance:
    → Replace with Redis-backed rate limiter (e.g., redis INCR with TTL)
    → Why Redis: Shared state across workers/instances, atomic operations
    → How: Use MULTI/EXEC for atomic window operations
    → Libraries: fastapi-limiter, slowapi (Redis-backed)
"""

import logging
import time
from collections import defaultdict
from typing import Dict, List

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter.
    
    Configuration (from settings):
        rate_limit_requests: Max requests per window (default: 100)
        rate_limit_window: Window duration in seconds (default: 3600 = 1 hour)
    
    Excluded paths:
        - /health: Health checks should never be rate-limited
        - /docs, /openapi.json: API documentation should always be accessible
    
    Thread Safety:
        This implementation is safe for single-process async (uvicorn).
        NOT safe for multi-process (gunicorn with multiple workers).
        See Production Upgrade Path in module docstring.
    
    Response on rate limit:
        HTTP 429 Too Many Requests
        Retry-After header: Seconds until oldest request expires from window
        Response body: JSON error with message and retry guidance
    """

    # Paths excluded from rate limiting
    # Why: Health checks and docs should always be reachable
    EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # What: Dict mapping IP → list of request timestamps
        # Why defaultdict: Automatically creates empty list for new IPs
        self._requests: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Get client IP address
        # Why: Rate limiting is per-IP to prevent individual abuse
        # Caveat: Behind a proxy, this may be the proxy's IP
        # Solution: Configure X-Forwarded-For header parsing in production
        client_ip = (
            getattr(request.client, "host", "unknown")
            if request.client
            else "unknown"
        )

        now = time.time()
        window_start = now - settings.rate_limit_window

        # ── Sliding Window: Clean old entries ─────────────────────────────
        # Remove request timestamps that are outside the current window
        # Why: Prevents unbounded memory growth
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip] if ts > window_start
        ]

        # ── Check rate limit ──────────────────────────────────────────────
        if len(self._requests[client_ip]) >= settings.rate_limit_requests:
            # Calculate when the oldest request in the window will expire
            oldest = self._requests[client_ip][0]
            retry_after = int(oldest + settings.rate_limit_window - now) + 1

            logger.warning(
                "Rate limit exceeded for IP %s: %d requests in %ds window",
                client_ip,
                len(self._requests[client_ip]),
                settings.rate_limit_window,
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Please wait {retry_after} seconds before retrying.",
                    "details": {"retry_after": retry_after},
                },
                headers={
                    # Standard HTTP header telling clients when to retry
                    "Retry-After": str(retry_after),
                },
            )

        # ── Record this request ───────────────────────────────────────────
        self._requests[client_ip].append(now)

        # ── Periodic cleanup of inactive IPs ──────────────────────────────
        # Why: Prevents memory leak from accumulated IPs that are no longer active
        # When: Every 1000th request (amortized O(1) cost)
        if sum(len(v) for v in self._requests.values()) % 1000 == 0:
            self._cleanup_inactive_ips(window_start)

        return await call_next(request)

    def _cleanup_inactive_ips(self, window_start: float) -> None:
        """
        Remove IPs that have no requests within the current window.
        
        What:    Prevents memory leak from accumulated inactive IP entries.
        When:    Called periodically (every ~1000 requests).
        Why:     Without cleanup, the dict grows unboundedly with unique IPs.
        """
        inactive_ips = [
            ip for ip, timestamps in self._requests.items()
            if not timestamps or max(timestamps) < window_start
        ]
        for ip in inactive_ips:
            del self._requests[ip]

        if inactive_ips:
            logger.debug("Cleaned up %d inactive IP entries", len(inactive_ips))
