FROM python:3.11.17-slim

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

# Install curl for container healthchecks
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER 1000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
