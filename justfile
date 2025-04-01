_default:
    @just --list --unsorted

# Run unit tests
test:
    uv run pytest

# Run linter
lint:
    uv run flake8 --ignore=E501
