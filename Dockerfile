ARG PYTHON_IMAGE=3.13-slim

# --------------- `base` stage --------------- 
FROM python:${PYTHON_IMAGE} AS base

# Define global values. Define them as ARG so they are not present in the final image, and so they can be modified
ARG USER=twyn
ARG GROUP=twyn
ARG WORKDIR=/app
ARG VENV_PATH=${WORKDIR}/.venv

WORKDIR ${WORKDIR}

# Create a non-root user and group
RUN groupadd -g 1001 ${GROUP} && \
    useradd -m -u 1001 -g ${GROUP} -s /bin/false ${USER}

# --------------- `build` stage --------------- 
FROM base AS build

# Define stage variables
ARG POETRY_VERSION=2.1.2
ARG POETRY_PLUGIN_EXPORT_VERSION=1.9.0

# These should never change, define as ENV
ENV POETRY_HOME="/opt/poetry"
ENV PATH="${POETRY_HOME}/bin:${PATH}"

# Create venv and upgrade pip
RUN python -m venv ${VENV_PATH} && \
    ${VENV_PATH}/bin/pip install --no-cache-dir --upgrade pip 

# Install poetry and set up the virtualenv configs
RUN apt-get update && apt-get install -y curl \
    && curl -sSL https://install.python-poetry.org | POETRY_VERSION=$POETRY_VERSION python3

RUN poetry self add poetry-plugin-export==${POETRY_PLUGIN_EXPORT_VERSION}

# Copy all the needed files, without write permissions
COPY poetry.lock pyproject.toml ./

# Export dependencies to requirements.txt (no dev deps)
RUN poetry export --without-hashes --only main -f requirements.txt > requirements.txt

# Create and install dependencies in the virtual env
RUN ${VENV_PATH}/bin/pip install --no-cache-dir -r requirements.txt

# --------------- `final` stage --------------- 
FROM base AS final

# Set non-root user and group
USER ${USER}:${GROUP}

# Copy over the virtual environment with all its dependencies and the project installed
COPY --from=build ${WORKDIR}/requirements.txt requirements.txt
ENV PATH="${VENV_PATH}/bin:$PATH"

# Copy venv with all its dependencies along with pyproject.toml
COPY --from=build --chown=${USER}:${GROUP} ${VENV_PATH} ${VENV_PATH}
COPY --from=build --chown=${USER}:${GROUP} ${WORKDIR}/pyproject.toml .

# Copy source code
COPY src src

# Install the CLI tool
RUN $VENV_PATH/bin/pip install --no-cache-dir .

ENTRYPOINT [ "twyn" ]
