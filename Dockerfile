# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# System deps (often needed for regex engines, spacy, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

# Copy project files
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src

# Install dependencies + CLI
RUN uv sync --frozen --no-dev

# ----------------------------------------------------
# Final runtime image
# ----------------------------------------------------
FROM python:3.12-slim

ENV PATH="/root/.local/bin:$PATH"

# Copy uv + venv from builder
COPY --from=base /root/.local /root/.local
COPY --from=base /app /app

WORKDIR /app

# Default entrypoint to your CLI
ENTRYPOINT ["uv", "run", "veildata"]
CMD ["--help"]
