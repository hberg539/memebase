FROM ghcr.io/astral-sh/uv:python3.14-alpine

WORKDIR /app

RUN apk add --no-cache ffmpeg

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY main.py config.default.toml ./
COPY src/ src/
COPY templates/ templates/
COPY static/ static/

ENV MEMEBASE_DEBUG=0

EXPOSE 5000

CMD [".venv/bin/python", "main.py"]
