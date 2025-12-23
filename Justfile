default:
    just --list --unsorted

# Run unit tests using pytest
[group("test")]
test:
    uv run pytest

# Linting tasks: format, check, and typecheck
[group("lint")]
lint: format check typecheck

# Run formatting using ruff
[group("lint")]
format:
    uv run ruff format

# Run lint checks using ruff
[group("lint")]
check:
    uv run ruff check --fix

# Run type checking using ty
[group("lint")]
typecheck:
    uv run ty check --exclude docs

# Build documentation using mkdocs
[group("docs")]
docs:
    uv run mkdocs build