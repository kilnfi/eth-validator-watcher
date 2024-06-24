FROM python:3.12-bookworm as builder

RUN pip install poetry

WORKDIR /app

COPY eth_validator_watcher /app/eth_validator_watcher
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
COPY poetry.lock /app/poetry.lock
COPY tests /app/tests
COPY build.py /app/build.py

RUN poetry build
RUN poetry install

ENTRYPOINT [ "poetry", "run", "eth-validator-watcher" ]
