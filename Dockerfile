FROM python:3.13-slim

WORKDIR /app

RUN pip install twyn

ENTRYPOINT ["twyn"]
