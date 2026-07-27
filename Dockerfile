# Single image for both the Streamlit app and the ingestion job; the
# command run (see docker-compose.yml) determines which one executes.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501

CMD ["streamlit", "run", "src/app/main.py", "--server.address=0.0.0.0", "--server.port=8501"]
