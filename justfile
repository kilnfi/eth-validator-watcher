_default:
    @just --list --unsorted

# Run unit tests
test:
    uv run pytest --exitfirst

# Run linter
lint:
    uv run flake8 eth_validator_watcher tests --ignore=E501

# Local development
dev:
    uv pip install -e .
    uv run eth-validator-watcher --config etc/config.dev.yaml

# Build docker image
docker:
    docker build -t eth-validator-watcher .
