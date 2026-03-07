FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies before copying source (layer caching)
COPY pyproject.toml .
RUN uv pip install --system --no-cache -e ".[dev]"

# Copy application source, Alembic migrations, and tests
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY tests/ ./tests/

# Run as non-root user
RUN useradd --create-home appuser
USER appuser
