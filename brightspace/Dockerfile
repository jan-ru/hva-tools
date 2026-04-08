FROM python:3.14-slim

# Install pandoc for PDF export
RUN apt-get update && \
    apt-get install -y --no-install-recommends pandoc && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --no-dev --frozen

# Copy application code and config
COPY brightspace_extractor/ brightspace_extractor/
COPY categories.toml ./

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "brightspace_extractor.api:app", "--host", "0.0.0.0", "--port", "8000"]
