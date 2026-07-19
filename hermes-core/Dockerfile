# hermes-core/Dockerfile — multi-stage build optimisé
# Service : orchestrateur Hermes (Phase 2 du plan)
# Stack : FastAPI + SQLAlchemy async + Alembic + httpx pool + gunicorn

# ==== Stage 1: deps ====
FROM python:3.12-slim AS deps

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ==== Stage 2: builder ====
FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=deps /install /usr/local
COPY . .

# ==== Stage 3: runner ====
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

RUN useradd --create-home --shell /bin/bash hermes && \
    mkdir -p /var/lib/hermes-core/attachments && \
    chown -R hermes:hermes /app /var/lib/hermes-core

USER hermes

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD curl -f http://localhost:8002/health || exit 1

# Gunicorn + uvicorn workers (2 workers pour paralleliser SSE fan-out)
CMD ["gunicorn", "main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8002", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]