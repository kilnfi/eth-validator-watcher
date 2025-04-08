FROM python:3.12-bookworm as builder

RUN pip install uv

WORKDIR /app

COPY eth_validator_watcher /app/eth_validator_watcher
COPY pyproject.toml /app/pyproject.toml
COPY setup.py /app/setup.py
COPY README.md /app/README.md
COPY tests /app/tests
COPY build.py /app/build.py

RUN uv venv /virtualenv && . /virtualenv/bin/activate && uv pip install -e .
    
FROM python:3.12-slim-bookworm

COPY --from=builder /virtualenv /virtualenv
COPY --from=builder /app /app
ENV PATH="/virtualenv/bin:$PATH"

WORKDIR /app

ENTRYPOINT [ "eth-validator-watcher" ]
   