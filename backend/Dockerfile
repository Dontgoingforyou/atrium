# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PATH="/usr/local/bin:$PATH"

WORKDIR /app

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

# Шрифты для поддержки кириллицы в PDF-экспорте (reportlab).
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md alembic.ini ./

# Кэш wheel между сборками на сервере (BuildKit); не раздувает слои финального образа.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install .

COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
