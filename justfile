_default:
    @just --list --unsorted

# Run unit tests
test:
    uv run pytest
