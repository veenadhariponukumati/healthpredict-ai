FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Non-root user (created before COPY so --chown can reference it)
RUN useradd -m -u 1000 appuser

# Copy installed packages from builder
COPY --from=builder /usr/local /usr/local

# Copy application code
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser alembic/ alembic/
COPY --chown=appuser:appuser app/ app/
COPY --chown=appuser:appuser --chmod=755 docker-entrypoint.sh .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]