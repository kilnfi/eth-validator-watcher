FROM python:3.10.7-slim-buster
WORKDIR /code

COPY ./setup.cfg /code/setup.cfg
COPY ./setup.py /code/setup.py
COPY ./eth_validator_watcher /code/eth_validator_watcher

RUN pip install --no-cache-dir --upgrade .

ENTRYPOINT [ "eth-validator-watcher" ] 
