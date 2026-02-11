"""
ScribeSnap Backend — Application Configuration
================================================

What:  Centralized configuration management using Pydantic Settings.
Why:   Type-safe environment variable loading with validation on startup.
       Fails fast if required vars are missing — prevents runtime surprises.
How:   Pydantic Settings reads from environment variables (or .env file),
       validates types/ranges, and provides a singleton `settings` object.
Who:   Imported by every module that needs configuration values.
When:  Loaded once at module import time; validated before app starts.

Design Decision:
    We use pydantic-settings instead of raw os.getenv() because:
    1. Type coercion is automatic (str → int, str → bool)
    2. Validation happens at startup, not when the value is first used
    3. IDE autocomplete works for all config values
    4. Documentation is embedded in the field definitions
    Alternative considered: python-decouple — less type safety, no validation
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings have sensible defaults for development.
    Production deployments MUST override security-sensitive values
    (DATABASE_URL, GEMINI_API_KEY, CORS_ORIGINS).
    
    Attributes are grouped by concern for readability.
    """

    # ── Database ──────────────────────────────────────────────────────────
    # What: Async PostgreSQL connection string using asyncpg driver
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    # Why asyncpg: Fastest async PostgreSQL driver, native prepared statements
    database_url: str = Field(
        default="postgresql+asyncpg://scribesnap:scribesnap_secret@localhost:5432/scribesnap",
        description="Async PostgreSQL connection URL"
    )

    # What: Connection pool sizing controls concurrent database operations
    # Why 20: Handles typical concurrent request load without exhausting DB connections
    # Trade-off: Higher = more concurrent queries, but more DB memory usage
    # Valid range: 5-100 (PostgreSQL default max_connections is 100)
    db_pool_size: int = Field(default=20, ge=5, le=100)

    # What: Extra connections beyond pool_size for traffic spikes
    # Why 10: Provides 50% headroom above pool_size for burst traffic
    # Trade-off: Higher = better spike handling but risk of DB overload
    db_max_overflow: int = Field(default=10, ge=0, le=50)

    # What: Validates connections before use by sending a lightweight query
    # Why True: Catches stale connections (e.g., after DB restart) before they cause errors
    # Trade-off: Adds ~1ms per query but prevents cryptic "connection reset" errors
    db_pool_pre_ping: bool = Field(default=True)

    # ── Google Gemini ─────────────────────────────────────────────────────
    # What: API key for Google Generative AI (Gemini Vision)
    # Required: YES — core functionality depends on this
    # How to obtain: https://aistudio.google.com/app/apikey
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for vision-based text extraction"
    )

    # What: Which Gemini model to use for handwriting recognition
    # Options: gemini-1.5-flash (faster, cheaper), gemini-1.5-pro (higher quality)
    # Trade-off: flash is ~10x cheaper but may struggle with messy handwriting
    gemini_model: str = Field(default="gemini-1.5-flash")

    # ── File Storage ──────────────────────────────────────────────────────
    # What: Root directory for uploaded images, relative to backend CWD
    # Why relative: Works in both Docker (mounted volume) and local development
    storage_root: str = Field(default="./storage")

    # What: Maximum allowed file size in bytes
    # Default: 10MB = 10 * 1024 * 1024 = 10485760
    # Why 10MB: Balances quality (high-res photos) with resource usage (memory, network)
    # Valid range: 1MB to 50MB
    max_file_size: int = Field(default=10_485_760, ge=1_048_576, le=52_428_800)

    # ── CORS ──────────────────────────────────────────────────────────────
    # What: Allowed origins for cross-origin requests
    # Why restrictive: Only our frontend should access the API
    # Format: Comma-separated URLs (parsed by validator below)
    cors_origins: str = Field(default="http://localhost:3000")

    @property
    def cors_origins_list(self) -> List[str]:
        """
        What: Splits comma-separated CORS origins into a list.
        Why property: CORS middleware expects a list, but env vars are strings.
        """
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ── Server ────────────────────────────────────────────────────────────
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000, ge=1024, le=65535)

    # What: Controls verbosity of structured JSON logging
    # Valid: DEBUG, INFO, WARNING, ERROR, CRITICAL
    # Trade-off: DEBUG = maximum visibility but high volume; INFO = balanced
    log_level: str = Field(default="INFO")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensures log level is a valid Python logging level name."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"Invalid log_level '{v}'. Must be one of: {valid_levels}")
        return upper

    # ── Retry Configuration ───────────────────────────────────────────────
    # What: Tenacity retry settings for Gemini API calls
    # Why exponential backoff: Prevents overwhelming a recovering service
    # Why jitter: Prevents thundering herd when multiple workers retry simultaneously
    retry_max_attempts: int = Field(default=3, ge=1, le=10)
    retry_min_wait: int = Field(default=2, ge=1, le=30)
    retry_max_wait: int = Field(default=10, ge=5, le=120)

    # ── Circuit Breaker ───────────────────────────────────────────────────
    # What: Prevents cascade failures when Gemini is down
    # How: After N consecutive failures, stop trying for M seconds
    # Why: Gives the upstream service time to recover without our requests piling up
    cb_failure_threshold: int = Field(default=5, ge=2, le=20)
    cb_recovery_timeout: int = Field(default=60, ge=10, le=300)

    # ── Rate Limiting ─────────────────────────────────────────────────────
    # What: Per-IP sliding window rate limit
    # Why: Prevents abuse and DoS without requiring authentication
    rate_limit_requests: int = Field(default=100, ge=10, le=10000)
    rate_limit_window: int = Field(default=3600, ge=60, le=86400)  # seconds

    # ── Pydantic Settings Config ──────────────────────────────────────────
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,  # DATABASE_URL and database_url both work
    }

    def validate_required_for_production(self) -> None:
        """
        What:  Validates that critical settings are configured.
        When:  Called during app startup (lifespan).
        Why:   Fail fast with clear error messages instead of cryptic runtime failures.
        How:   Checks each required field and raises ValueError with guidance.
        """
        errors = []
        if not self.gemini_api_key or self.gemini_api_key == "your_gemini_api_key_here":
            errors.append(
                "GEMINI_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            )
        if errors:
            raise ValueError(
                "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )


# Singleton instance — imported throughout the application
# Why singleton: Configuration is immutable after startup; no need for multiple instances
settings = Settings()
