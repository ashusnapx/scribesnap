"""
ScribeSnap Backend — Health Check Route
=========================================

What:  Health check endpoint for monitoring and load balancer probes.
Why:   Production systems need health checks to determine if the service can handle
       traffic. Load balancers use this to route away from unhealthy instances.
How:   Checks critical dependencies (database, Gemini API) and returns status.
Who:   Called by Docker health checks, load balancers, and monitoring systems.
When:  Periodically (e.g., every 30 seconds by Docker, every 10 seconds by LB).

Health Check Philosophy:
    A service is only "healthy" if it can handle requests end-to-end.
    That means ALL critical dependencies must be operational:
    - Database: Must be reachable for storing parse results
    - Gemini API: Must be reachable for parsing images (or circuit breaker status)
    
    Status levels:
    - healthy:   All dependencies operational (HTTP 200)
    - degraded:  Non-critical dependencies down (HTTP 200, but flag for monitoring)
    - unhealthy: Critical dependencies down (HTTP 503, stop routing traffic)
"""

import logging
import time

from fastapi import APIRouter

from app import __version__
from app.schemas.note import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

# Track when the service started for uptime reporting
# Why module-level: Initialized once when the module loads; doesn't change
_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description=(
        "Returns the health status of the backend service and its dependencies. "
        "Used by Docker health checks and load balancers to determine if the service "
        "can handle traffic."
    ),
)
async def health_check() -> HealthResponse:
    """
    Check the health of the service and all dependencies.
    
    What:    Probes database and Gemini connectivity, returns aggregate status.
    How:     Runs lightweight checks (not full operations) against each dependency.
    
    Check details:
        Database: Executes SELECT 1 to verify connection and query execution
        Gemini: Calls list_models() to verify API key and connectivity
    
    Why lightweight checks:
        - Health checks run every 10-30 seconds
        - Full operations (image parse, complex queries) would waste resources
        - SELECT 1 and list_models are essentially free
    
    Returns:
        HealthResponse with status for each dependency and uptime.
    """
    db_status = "connected"
    gemini_status = "available"
    overall = "healthy"

    # ── Check Database ────────────────────────────────────────────────────
    try:
        from app.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "disconnected"
        overall = "unhealthy"
        logger.warning("Health check: database unreachable: %s", str(e))

    # ── Check Gemini API ──────────────────────────────────────────────────
    try:
        from app.services.gemini_service import gemini_service
        # Check circuit breaker state first
        if gemini_service.circuit_breaker.state == "open":
            gemini_status = "circuit_open"
            overall = "degraded" if overall != "unhealthy" else overall
        else:
            is_available = await gemini_service.health_check()
            if not is_available:
                gemini_status = "unavailable"
                overall = "degraded" if overall != "unhealthy" else overall
    except Exception as e:
        gemini_status = "unavailable"
        overall = "degraded" if overall != "unhealthy" else overall
        logger.warning("Health check: Gemini unreachable: %s", str(e))

    return HealthResponse(
        status=overall,
        version=__version__,
        database=db_status,
        gemini=gemini_status,
        uptime_seconds=round(time.time() - _start_time, 2),
    )
