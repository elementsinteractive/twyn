FROM python:3.13-slim

ARG USER=twyn
ARG GROUP=twyn

WORKDIR /app

RUN pip install twyn

RUN groupadd -g 1001 ${GROUP} && \
    useradd -m -u 1001 -g ${GROUP} -s /bin/bash ${USER}

USER ${USER}:${GROUP}

ENTRYPOINT ["twyn"]
