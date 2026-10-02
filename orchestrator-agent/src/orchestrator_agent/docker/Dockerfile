FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only the project files needed for installation; the local engine dependency
# must be available at the sibling path declared in pyproject.toml.
COPY orchestrator-agent/pyproject.toml orchestrator-agent/uv.lock orchestrator-agent/README.md ./
COPY orchestrator-agent/src/ ./src/
COPY engine/pyproject.toml /engine/pyproject.toml
COPY engine/src/ /engine/src/

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential gcc libffi-dev curl \
 && pip install --no-cache-dir uv \
 && uv sync --locked --no-dev \
 && apt-get purge -y --auto-remove build-essential gcc libffi-dev \
 && rm -rf /var/lib/apt/lists/*

COPY orchestrator-agent/src/orchestrator_agent/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "orchestrator-agent"]