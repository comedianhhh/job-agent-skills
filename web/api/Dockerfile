# Build context is the repo root (jobs-mcp is a path dependency): docker build -f web/api/Dockerfile .
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/
WORKDIR /srv
COPY mcp/jobs-mcp /srv/mcp/jobs-mcp
COPY web/api /srv/web/api
WORKDIR /srv/web/api
RUN uv sync --no-dev --frozen || uv sync --no-dev
ENV CAREER_DIR=/career PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "--factory", "tracker_api.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
