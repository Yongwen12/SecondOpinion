FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
COPY frontend ./frontend

RUN python -m pip install --upgrade pip && python -m pip install .

ENV SECONDOPINION_DATABASE_URL=postgresql+psycopg://secondopinion:secondopinion@db:5432/secondopinion \
    SECONDOPINION_SERVER_ARTIFACT_ROOT=/srv/secondopinion/artifacts \
    SECONDOPINION_SCORING_MEMORY=/srv/secondopinion/data/normalized/scoring_memory_external_full_lite_v0.1.jsonl

EXPOSE 8000

CMD ["uvicorn", "secondopinion.server.api:app", "--host", "0.0.0.0", "--port", "8000"]
