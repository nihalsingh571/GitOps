# ── Stage 1: Build dependencies ───────────────────────────────────────────────
# We use a full image to compile any C extensions (psycopg2-binary needs this)
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools for C extensions
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install into an isolated prefix so we can copy just the wheels
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: Final slim image ─────────────────────────────────────────────────
# We copy only the installed packages — no compiler, no apt cache, no build tools
FROM python:3.12-slim

# Runtime dependency for psycopg2 (the libpq shared library)
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY main.py .

# Run as non-root for security (Kubernetes PSA best practice)
RUN useradd -m appuser
USER appuser

# Document the port (doesn't publish it — that's done in the K8s Service)
EXPOSE 8000

# Use exec form (not shell form) so signals reach uvicorn correctly
# --host 0.0.0.0 → listen on all interfaces inside the container
# --workers 1    → single worker keeps memory low for local dev
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
