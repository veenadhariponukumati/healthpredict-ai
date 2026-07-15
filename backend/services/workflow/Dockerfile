FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt httpx temporalio>=1.7.0

COPY services/workflow/ ./
COPY app/core/logging.py app/core/config.py ./app/core/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]