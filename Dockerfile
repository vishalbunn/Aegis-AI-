# Aegis AI — production Docker image
# Multi-stage build keeps the final image small (~200MB).

# ─── Stage 1: build ──────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install into a system-wide prefix that any user can read.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: runtime ────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder into the runtime image's site-packages.
# /install is world-readable, so the non-root user can use them.
COPY --from=builder /install /usr/local

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY eval/ ./eval/
COPY tests/ ./tests/
COPY pytest.ini .

# Non-root user for security
RUN useradd -m -u 1000 aegis && chown -R aegis:aegis /app
USER aegis

# Defaults (override via .env or docker-compose)
ENV AEGIS_DEBATER_MODEL=llama-3.1-8b-instant
ENV AEGIS_JUDGE_MODEL=llama-3.1-8b-instant
ENV AEGIS_CACHE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/admin/health', timeout=5)" || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]