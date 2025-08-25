set shell := ["bash", "-euco", "pipefail"]

default:
    @just --list

# Install dev dependencies
install:
    uv pip install -e .[dev]

# Format code
format:
    uv run ruff format .

# Check formatting without changing files
format-check:
    uv run ruff format --check .

# Lint code
lint:
    uv run ruff check .

# Run tests
test:
    uv run python tests/manage.py test --verbosity=2

# Coverage report
coverage:
    uv run coverage run --source=rest_framework_bulk tests/manage.py test --verbosity=2
    uv run coverage report
    uv run coverage html

# Install git hooks
precommit-install:
    uv run pre-commit install

# Run all pre-commit hooks on all files
precommit-run:
    uv run pre-commit run -a

# Clean build, pyc, and coverage artifacts
clean:
    rm -rf build/ dist/ *.egg-info
    find . -name '__pycache__' -type d -print0 | xargs -0 rm -rf
    find . -name '*.py[co]' -delete
    rm -rf .coverage coverage* tests/.coverage htmlcov/ test/coverage* 

# Build distribution (sdist/wheel)
dist:
    uv run python -m build

