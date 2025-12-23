FROM python:3.12

ARG DEBIAN_FRONTEND=noninteractive
ARG BUILD_UID=10000
ARG BUILD_GID=10000
ARG BUILD_USER=worker

ENV UV_HTTP_TIMEOUT=300

RUN apt update && apt install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.6 /uv /uvx /bin/

RUN groupadd --gid ${BUILD_GID} ${BUILD_USER} \
    && useradd --create-home --shell /bin/bash \
       --uid ${BUILD_UID} --gid ${BUILD_GID} ${BUILD_USER}

USER ${BUILD_USER}
WORKDIR /home/${BUILD_USER}/app

ENV PATH="/home/${BUILD_USER}/.local/bin:${PATH}" \
    PYTHONPATH="/home/${BUILD_USER}/app"

COPY --chown=${BUILD_UID}:${BUILD_GID} uv.lock pyproject.toml ./
RUN uv sync --locked

COPY --chown=${BUILD_UID}:${BUILD_GID} . .

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]




