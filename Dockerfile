FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    XDG_DATA_HOME=/data

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "psalter.web.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
