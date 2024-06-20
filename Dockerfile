FROM python:3.12-bookworm as builder
WORKDIR /app

COPY . /app
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --progress-bar off .

ENTRYPOINT [ "python", "/usr/local/bin/eth-validator-watcher" ]
