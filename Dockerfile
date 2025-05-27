# --------------- `base` stage --------------- 
FROM python:3.13-slim AS base

# Define variables
ARG USER=twyn
ARG GROUP=twyn
ARG WORKDIR=/app
ARG VENV_PATH=${WORKDIR}/.venv

# Set `WORKDIR`
WORKDIR ${WORKDIR}

# Create a non-root user and group
RUN groupadd -g 1001 ${GROUP} && \
    useradd -m -u 1001 -g ${GROUP} -s /bin/bash ${USER}

# Copy all the needed files, setting their user and group ownerships to the ones we just created
COPY --chown=${USER}:${GROUP} src src
COPY --chown=${USER}:${GROUP} pyproject.toml pyproject.toml
COPY --chown=${USER}:${GROUP} README.md README.md
COPY --chown=${USER}:${GROUP} poetry.lock poetry.lock

# --------------- `build` stage --------------- 
FROM base AS build

# Install poetry and set up the virtualenv configs
RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.in-project true && \ 
    poetry config virtualenvs.path ${VENV_PATH}

# Install `twyn` in the virtual environment
RUN poetry install --only main

# --------------- `final` stage --------------- 
FROM base AS final

# Set non-root user and group
USER ${USER}:${GROUP}

# Copy over the virtual environment with all its dependencies and the project installed
COPY --from=build --chown=${USER}:${GROUP} ${VENV_PATH} ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:$PATH"

# Set `ENTRYPOINT`
ENTRYPOINT [ "twyn" ]
