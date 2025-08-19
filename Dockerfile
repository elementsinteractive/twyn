ARG PYTHON_IMAGE=3.13-slim@sha256:1020ca463dc51c26bbad49de85dbb2986d93b71050102f3fa2a7f0fc4c2ea81e

# --------------- `base` stage --------------- 
FROM python:${PYTHON_IMAGE} AS base

# Define global values. Define them as ARG so they are not present in the final image, and so they can be modified
ARG USER=twyn
ARG GROUP=twyn
ARG WORKDIR=/app
ARG VENV_PATH=${WORKDIR}/.venv
ARG BIN_PATH=${VENV_PATH}/bin

WORKDIR ${WORKDIR}

# Create a non-root user and group
RUN groupadd -g 1001 ${GROUP} && \
    useradd -m -u 1001 -g ${GROUP} -s /bin/false ${USER}

# --------------- `build` stage --------------- 
FROM base AS build

# Define stage variables
ARG UV_VERSION 0.8.0
# Install curl for uv installation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Create a fake VERSION file, so that we don't break the cache because of a mismatch in that file
RUN echo "v0.0.0" > VERSION

RUN UV_PROJECT_ENVIRONMENT=${VENV_PATH} uv venv
RUN ${BIN_PATH}/python -m ensurepip

# Copy dependency files
COPY uv.lock pyproject.toml ./

# Install dependencies using uv (only dependencies, not the project itself)
RUN UV_PROJECT_ENVIRONMENT=${VENV_PATH} uv sync --inexact --frozen --all-extras --no-install-project --compile-bytecode

# --------------- `final` stage --------------- 
FROM base AS final

# Copy the virtual environment from build stage 
COPY --from=build --chown=${USER}:${GROUP} ${VENV_PATH} ${VENV_PATH}

# Set PATH to use the virtual environment
ENV PATH="${BIN_PATH}:$PATH"

# Copy needed files to install the package
COPY --from=build --chown=${USER}:${GROUP} ${WORKDIR}/pyproject.toml .
COPY --chown=${USER}:${GROUP} README.md README.md
COPY --chown=${USER}:${GROUP} src src

# Copy the real VERSION file
COPY --chown=${USER}:${GROUP} VERSION .

# Install the CLI tool (dependencies already installed in venv) 
RUN ${BIN_PATH}/pip3 install --no-deps .

USER ${USER}:${GROUP}

ENTRYPOINT [ "twyn" ]
