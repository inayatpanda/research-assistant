FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install -e .

ENV STORAGE_DIR=/data/storage \
    DATABASE_URL=sqlite+aiosqlite:////data/research.db \
    HOST=0.0.0.0 \
    PORT=8787

VOLUME ["/data"]
EXPOSE 8787

CMD ["sh", "-c", "alembic upgrade head && uvicorn research_api.main:app --host $HOST --port $PORT"]
