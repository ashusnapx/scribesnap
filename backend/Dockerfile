# =============================================================================
# ScribeSnap Backend Dockerfile
# =============================================================================
# What:  Multi-stage Docker build for the FastAPI backend.
# Why:   Multi-stage reduces final image size by separating build and runtime.
# How:   Stage 1 installs build dependencies; Stage 2 copies only runtime files.
# When:  Built by docker-compose or CI/CD pipeline.
#
# Image size comparison:
#   Single-stage: ~1.2GB (includes gcc, build tools)
#   Multi-stage:  ~400MB (only runtime dependencies)
#
# Security: Runs as non-root user (appuser) in production
# =============================================================================

# ── Stage 1: Builder ─────────────────────────────────────────────────────
# Purpose: Install system dependencies and Python packages
FROM python:3.12-slim AS builder

# What: Install system packages required for building Python extensions
# Why: python-magic needs libmagic; asyncpg needs build tools
# Note: These are BUILD dependencies — not needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# What: Copy and install Python dependencies separately for Docker layer caching
# Why: requirements.txt changes less often than source code
#      → Docker reuses this layer when only code changes (faster rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────────────────
# Purpose: Minimal image with only runtime dependencies
FROM python:3.12-slim AS runtime

# What: Install only runtime system dependencies
# Why: libmagic is needed at runtime for MIME type detection (python-magic)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# What: Create non-root user for security
# Why: Running as root inside containers is a security risk
#      If the container is compromised, root access = full host access
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# What: Copy installed Python packages from builder stage
# Why: Only copies the site-packages, not build tools (smaller image)
COPY --from=builder /root/.local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /root/.local/bin /usr/local/bin

# What: Copy application source code
COPY . .

# What: Create storage directory and set ownership
# Why: The app needs to write uploaded files here
RUN mkdir -p /app/storage && chown -R appuser:appuser /app

# What: Switch to non-root user
USER appuser

# What: Expose the API port
EXPOSE 8000

# What: Health check for Docker orchestration
# Why: Docker (and k8s) use health checks to determine container health
# Frequency: Every 30s, timeout 10s, 3 retries before "unhealthy"
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# What: Start uvicorn with production settings
# Why uvicorn: ASGI server optimized for async Python apps
# --host 0.0.0.0: Listen on all interfaces (required inside Docker)
# --workers 1: Single worker (sufficient for single-user app)
# --log-level info: Standard logging for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
