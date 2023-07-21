FROM python:3.11-slim

WORKDIR /app

RUN pip install twyn

ENTRYPOINT ["twyn", "run", "-vv"]
