FROM python:3.14.7-slim

# Install the same uv version used by CI to keep builds reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies before copying source (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source and Alembic migrations
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Install the project itself (no dev group) so importlib.metadata reports the
# real application version instead of the "0.0.0" fallback.
RUN uv sync --frozen --no-dev

# Install curl for container healthchecks
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# `uv run` must never sync at container start: that would download and install
# the dev dependency group (pytest, ...) into production containers.
ENV PATH="/app/.venv/bin:$PATH" \
    UV_NO_SYNC=1

# /app/beat holds the Celery beat schedule; a fresh named volume mounted there
# inherits this ownership, so the non-root scheduler can write to it.
RUN useradd --create-home --uid 1000 appuser && mkdir -p /app/beat && chown -R appuser:appuser /app
USER 1000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
