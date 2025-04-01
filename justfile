_default:
    @just --list --unsorted

# Run unit tests
test:
    uv run pytest

# Run linter
lint:
    uv run flake8 eth_validator_watcher tests --ignore=E501

# Local development
dev:
    uv run python -m eth_validator_watcher --config etc/config.dev.yaml

# Build docker image
docker:
    docker build -t eth-validator-watcher .
