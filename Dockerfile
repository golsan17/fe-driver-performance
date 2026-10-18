# ==============================================================================
# Stage 1: Build & Python Dependencies
# ==============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies if needed for packages compiling C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies to a dedicated prefix and purge unnecessary bytecode
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    find /install -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /install -type f -name "*.pyc" -delete 2>/dev/null || true

# ==============================================================================
# Stage 2: Production Runtime
# ==============================================================================
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

# 1. Install runtime graphics libraries for headless Matplotlib rendering,
#    create non-root system user, and prepare writable temporary directories.
#    Consolidated in a single layer to optimize Docker layer caching and size.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libpng16-16 \
    fontconfig \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && groupadd -r -g 1000 appgroup \
    && useradd -r -u 1000 -g appgroup -d /app -s /sbin/nologin appuser \
    && mkdir -p /tmp/matplotlib /app \
    && chown -R appuser:appgroup /tmp/matplotlib /app

# 2. Copy pre-built Python dependencies from builder stage (invalidates only on requirements change)
COPY --from=builder /install /usr/local

# 3. Copy application code and templates (invalidates on source code change)
COPY --chown=appuser:appgroup main.py models.py visualization.py ./
COPY --chown=appuser:appgroup templates/ ./templates/

# Run container as non-root user
USER appuser

# Expose default port
EXPOSE 8080

# Production Health Check: zero-dependency probe using Python stdlib urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request, os; port = os.environ.get('PORT', '8080'); urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/health')" || exit 1

# Start Uvicorn, evaluating PORT dynamically with exec to ensure SIGTERM signal handling
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
