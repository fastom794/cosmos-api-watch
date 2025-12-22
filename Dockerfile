FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry 2.2.1 (using pip)
RUN pip install --no-cache-dir poetry==2.2.1

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock README.md ./

# Copy source code
COPY src ./src

# Create in-project venv
RUN poetry config virtualenvs.in-project true

# Install deps (prod only)
RUN poetry install --only main --no-interaction --no-ansi


# ==========================

FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copy in-project venv
COPY --from=builder /app/.venv /app/.venv

# Add it to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy code and env files
COPY src ./src
COPY .env* ./

CMD ["gunicorn", "cosmos_api_watch.api.routes:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000"]

