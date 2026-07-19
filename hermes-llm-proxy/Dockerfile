# hermes-llm-proxy/Dockerfile — multi-stage build optimisé
# Stage 1: deps — install Python wheels (cached tant que requirements.txt inchangé)
# Stage 2: builder — copie le code
# Stage 3: runner — image minimale runtime

# ==== Stage 1: deps ====
FROM python:3.12-slim AS deps

WORKDIR /app

# System deps minimaux (psycopg2-binary n'en a pas besoin, mais cryptography oui pour les wheels)
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

# Install only runtime deps (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copier Python packages depuis le builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copier le code applicatif
COPY --from=builder /app /app

# Créer un user non-root pour la sécurité
RUN useradd --create-home --shell /bin/bash hermes && \
    mkdir -p /data && \
    chown -R hermes:hermes /app /data

USER hermes

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]