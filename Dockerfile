FROM python:3.12-slim

# Make uv install into system Python, not a venv
ENV UV_SYSTEM_PYTHON=1

# Install uv globally
COPY --from=ghcr.io/astral-sh/uv:0.4.28 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies into system Python (including uvicorn)
RUN uv sync --locked

# Copy the entire project
COPY . .

EXPOSE 8080

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
FROM python:3.12

LABEL name="Omniscient MCP OCR Tool"
LABEL maintainer="Moxoff"

# Avoid interactive dialogs when using apt
# (default answers are selected)
ARG DEBIAN_FRONTEND=noninteractive

# Add build arguments for user and group ids
ARG BUILD_UID=10000
ARG BUILD_GID=10000
ARG BUILD_USER=worker
ARG SERVER_PORT=8001
ENV SERVER_PORT=${SERVER_PORT}

ENV UV_HTTP_TIMEOUT=300

RUN apt update && apt install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/*

# Install uv/uvx
COPY --from=ghcr.io/astral-sh/uv:0.9.6 /uv /uvx /bin/

# Add non-root user for running the application
RUN groupadd --gid ${BUILD_GID} ${BUILD_USER} \
    && useradd --create-home --shell /bin/bash --uid ${BUILD_UID} --gid ${BUILD_GID} ${BUILD_USER}

# Switch to non-root user
USER ${BUILD_USER}

# Go to application folder
WORKDIR /home/${BUILD_USER}/app

# Add user bin folder to path and python path
ENV PATH="/home/${BUILD_USER}/.local/bin:${PATH}" \
    PYTHONPATH="/home/${BUILD_USER}/app"

# Copy lock
COPY --chown=${BUILD_UID}:${BUILD_GID} ./uv.lock ./pyproject.toml ./

# Install python dependencies
RUN uv sync --locked

# Copy application files
COPY --chown=${BUILD_UID}:${BUILD_GID} . .

# Expose server port
EXPOSE ${SERVER_PORT}

# Default command: run uvicorn on the FastMCP ASGI app
CMD ["sh", "-c", "uv run fastmcp run src/server.py:mcp --transport streamable-http --host 0.0.0.0 --port ${SERVER_PORT}"]


