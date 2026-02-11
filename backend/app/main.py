"""
ScribeSnap Backend — FastAPI Application Factory
===================================================

What:  Creates and configures the FastAPI application instance.
Why:   Centralizes app configuration, middleware registration, route mounting,
       and lifecycle management in one place.
How:   Factory pattern: create_app() returns a configured FastAPI instance.
Who:   Called by uvicorn to start the server (uvicorn app.main:app).
When:  Once at server startup; the returned app handles all subsequent requests.

Application Architecture:
    ┌─────────────────────────────────────────────────────┐
    │                   FastAPI App                       │
    │                                                     │
    │  Middleware Chain:                                   │
    │  ┌──────────────┐ ┌──────────┐ ┌─────────────────┐ │
    │  │  Rate Limit  │→│ Req ID   │→│  Logging        │ │
    │  └──────────────┘ └──────────┘ └─────────────────┘ │
    │                                                     │
    │  Routes:                                            │
    │  ┌──────────────┐ ┌──────────┐ ┌─────────────────┐ │
    │  │ POST /parse  │ │ GET notes│ │ GET /health     │ │
    │  └──────────────┘ └──────────┘ └─────────────────┘ │
    │                                                     │
    │  Exception Handlers:                                │
    │  ┌──────────────────────────────────────────────┐  │
    │  │ ValidationError→400 │ LLMError→503 │ DB→500 │  │
    │  └──────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────┘

Lifecycle:
    Startup:
    1. Validate configuration (fail fast on missing env vars)
    2. Initialize structured logging
    3. Create storage directories
    4. Log startup complete
    
    Shutdown:
    1. Stop accepting new requests
    2. Dispose database engine (close all connections)
    3. Log shutdown complete
"""

import logging
import sys
import signal
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import dispose_engine
from app.exceptions import (
    ScribeSnapError,
    ValidationError,
    NotFoundError,
    LLMServiceError,
    CircuitBreakerOpenError,
    DatabaseError,
    RateLimitExceededError,
    FileStorageError,
)
from app.middleware.request_id import RequestIDMiddleware, request_id_var
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routes import parse, notes, health

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# Structured Logging Configuration
# ══════════════════════════════════════════════════════════════════════════

def setup_logging() -> None:
    """
    Configure structured JSON logging for the entire application.
    
    What:    Sets up logging with consistent format across all modules.
    Why:     Structured logs are machine-parseable for aggregation tools.
    How:     Configures root logger with JSON-friendly format.
    When:    Called once during app startup (before ANY other initialization).
    
    Format: %(asctime)s [%(levelname)s] %(name)s [%(request_id)s] %(message)s
    
    Why format variables:
        - asctime: ISO timestamp for chronological ordering
        - levelname: Enables severity-based filtering and alerting
        - name: Module name for tracing origin of log entries
        - message: The actual log content
    
    Production upgrade:
        Replace StreamHandler with:
        - python-json-logger for true JSON output
        - Fluentd forwarder for centralized logging
        - Sentry SDK handler for error tracking
    """
    log_format = (
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),  # Docker captures stdout
        ],
        force=True,  # Override any existing logging config
    )

    # Reduce noise from third-party libraries
    # Why: These libraries log at DEBUG/INFO for every operation (very noisy)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ══════════════════════════════════════════════════════════════════════════
# Application Lifespan (Startup & Shutdown)
# ══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle: startup and shutdown procedures.
    
    What:    Runs initialization on startup and cleanup on shutdown.
    Why:     Ensures resources are properly allocated and released.
    How:     AsyncContextManager — code before yield runs on startup,
             code after yield runs on shutdown.
    
    Startup sequence:
        1. Setup structured logging
        2. Validate critical configuration
        3. Create storage directory
        4. Log successful startup
    
    Shutdown sequence:
        1. Dispose database engine (close all pooled connections)
        2. Log shutdown
    
    Why lifespan (not on_event):
        FastAPI's @app.on_event("startup") is deprecated in favor of lifespan.
        Lifespan provides cleaner resource management with context manager pattern.
    """
    # ── Startup ───────────────────────────────────────────────────────────
    setup_logging()
    logger.info("=" * 60)
    logger.info("ScribeSnap Backend starting up...")

    # Validate critical settings — fail fast with clear errors
    # Why here (not in config.py): Config is imported at module level by many modules.
    # Validation here runs after all imports, giving complete context.
    try:
        settings.validate_required_for_production()
    except ValueError as e:
        logger.error("Configuration error: %s", str(e))
        logger.error("Fix the configuration and restart the server.")
        # Don't exit — the server can still respond to health checks
        # and serve the error through API responses

    # Ensure storage directory exists
    from pathlib import Path
    storage = Path(settings.storage_root)
    storage.mkdir(parents=True, exist_ok=True)
    logger.info("Storage directory: %s", storage.resolve())

    logger.info("Server ready at http://%s:%d", settings.backend_host, settings.backend_port)
    logger.info("API docs: http://%s:%d/docs", settings.backend_host, settings.backend_port)
    logger.info("=" * 60)

    yield  # Application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("ScribeSnap Backend shutting down...")

    # Close all database connections gracefully
    # Why: Prevents connection leaks and ensures PostgreSQL frees resources
    await dispose_engine()

    logger.info("Shutdown complete.")


# ══════════════════════════════════════════════════════════════════════════
# Exception Handlers
# ══════════════════════════════════════════════════════════════════════════

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers for consistent error responses.
    
    What:    Maps exception types to HTTP status codes and response formats.
    Why:     Consistent error format across all endpoints without try/except in each route.
    How:     FastAPI's exception_handler decorator intercepts specific exception types.
    
    Handler hierarchy:
        ValidationError         → 400 Bad Request (client can fix the input)
        NotFoundError           → 404 Not Found
        RateLimitExceededError  → 429 Too Many Requests
        FileStorageError        → 500 Internal Server Error
        LLMServiceError         → 503 Service Unavailable (retry later)
        CircuitBreakerOpenError → 503 Service Unavailable (circuit open)
        DatabaseError           → 500 Internal Server Error
        ScribeSnapError (base)  → 500 Internal Server Error (catch-all for custom)
        Exception (fallback)    → 500 Internal Server Error (unexpected errors)
    
    Security: Exception handlers NEVER expose internal details (stack traces,
    file paths, SQL queries) in the API response. Details are logged server-side.
    """

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError):
        """Client sent invalid input — tell them what's wrong and how to fix it."""
        rid = request_id_var.get("")
        logger.warning("[%s] Validation error: %s", rid, exc.message)
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_error",
                "message": exc.message,
                "details": exc.context,
                "request_id": rid,
            },
        )

    @app.exception_handler(NotFoundError)
    async def handle_not_found(request: Request, exc: NotFoundError):
        """Requested resource doesn't exist."""
        rid = request_id_var.get("")
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": exc.message,
                "request_id": rid,
            },
        )

    @app.exception_handler(RateLimitExceededError)
    async def handle_rate_limit(request: Request, exc: RateLimitExceededError):
        """Client exceeded rate limit — tell them when they can retry."""
        rid = request_id_var.get("")
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": exc.message,
                "details": exc.context,
                "request_id": rid,
            },
            headers={"Retry-After": str(exc.retry_after)},
        )

    @app.exception_handler(CircuitBreakerOpenError)
    async def handle_circuit_breaker(request: Request, exc: CircuitBreakerOpenError):
        """Circuit breaker is open — Gemini has been failing too much."""
        rid = request_id_var.get("")
        logger.warning("[%s] Circuit breaker open: %s", rid, exc.message)
        return JSONResponse(
            status_code=503,
            content={
                "error": "service_unavailable",
                "message": exc.message,
                "details": {"recovery_time": exc.recovery_time},
                "request_id": rid,
            },
            headers={"Retry-After": str(exc.recovery_time)},
        )

    @app.exception_handler(LLMServiceError)
    async def handle_llm_error(request: Request, exc: LLMServiceError):
        """Gemini API failed after retries — tell user to try again later."""
        rid = request_id_var.get("")
        logger.error("[%s] LLM service error: %s", rid, exc.message)
        headers = {}
        if exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=503,
            content={
                "error": "llm_service_error",
                "message": exc.message,
                "details": exc.context,
                "request_id": rid,
            },
            headers=headers,
        )

    @app.exception_handler(DatabaseError)
    async def handle_database_error(request: Request, exc: DatabaseError):
        """Database error — generic message to user, details logged server-side."""
        rid = request_id_var.get("")
        # Log full context server-side (NOT in response — security)
        logger.error("[%s] Database error: %s | Context: %s", rid, exc.message, exc.context)
        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "message": "An internal error occurred. Please try again later.",
                "request_id": rid,
            },
        )

    @app.exception_handler(FileStorageError)
    async def handle_file_storage_error(request: Request, exc: FileStorageError):
        """File system error — generic message, details logged."""
        rid = request_id_var.get("")
        logger.error("[%s] File storage error: %s | Context: %s", rid, exc.message, exc.context)
        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "message": exc.message,
                "request_id": rid,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        """
        Catch-all for truly unexpected errors.
        
        Why:    Prevents raw stack traces from reaching the client.
        What:   Returns a generic 500 error with a request ID for support tickets.
        Security: Stack trace is logged server-side ONLY (never in response).
        """
        rid = request_id_var.get("")
        logger.error(
            "[%s] Unexpected error: %s",
            rid,
            str(exc),
            exc_info=True,  # Log full stack trace for debugging
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred. Please try again or contact support.",
                "request_id": rid,
            },
        )


# ══════════════════════════════════════════════════════════════════════════
# Application Factory
# ══════════════════════════════════════════════════════════════════════════

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    What:    Factory function that assembles all application components.
    Why:     Factory pattern enables creating different app configurations
             (e.g., testing vs production) without modifying global state.
    Returns: Fully configured FastAPI instance ready to receive requests.
    
    Why factory (not module-level app):
        1. Testability: Create fresh app instances for each test
        2. Configuration: Different settings for different environments
        3. Import safety: No side effects on import
    """
    app = FastAPI(
        title="ScribeSnap API",
        description=(
            "Production-grade handwritten note parser using Google Gemini Vision API. "
            "Upload images of handwritten notes and get extracted text with high accuracy."
        ),
        version="1.0.0",
        docs_url="/docs",          # Swagger UI at /docs
        redoc_url="/redoc",        # ReDoc at /redoc
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Register Middleware ───────────────────────────────────────────────
    # Order matters! Middleware executes in REVERSE order of addition.
    # By adding in this order: CORS → GZip → Logging → RequestID → RateLimit,
    # the execution order becomes: RateLimit → RequestID → Logging → GZip → CORS
    # (last added = first to execute)

    # CORS — handles preflight OPTIONS requests and adds CORS headers
    # Why: Frontend (localhost:3000) and backend (localhost:8000) are different origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,     # Allow cookies (future: auth)
        allow_methods=["*"],         # Allow all HTTP methods
        allow_headers=["*"],         # Allow all headers
        expose_headers=[             # Headers the browser can read from response
            "X-Request-ID",
            "X-Total-Count",
            "Retry-After",
        ],
    )

    # GZip compression — reduces response size for large JSON payloads
    # Why minimum_size=500: Don't compress small responses (overhead > savings)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Request logging — logs method, path, status, duration
    app.add_middleware(RequestLoggingMiddleware)

    # Request ID — generates unique ID for each request
    app.add_middleware(RequestIDMiddleware)

    # Rate limiting — prevents abuse (first to execute = last added)
    app.add_middleware(RateLimitMiddleware)

    # ── Register Exception Handlers ───────────────────────────────────────
    register_exception_handlers(app)

    # ── Register Routes ───────────────────────────────────────────────────
    app.include_router(parse.router)
    app.include_router(notes.router)
    app.include_router(health.router)

    return app


# ── Application Instance ─────────────────────────────────────────────────
# Why module-level: uvicorn expects `app.main:app` to be importable
# The factory creates it; this assigns it to a module attribute
app = create_app()
