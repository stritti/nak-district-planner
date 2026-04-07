FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies before copying source (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source and Alembic migrations
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Add .venv/bin to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run as non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Standard command for backend
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
