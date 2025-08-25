# Repository Guidelines

## Project Structure & Module Organization

- `rest_framework_bulk/`: Core package.
- `rest_framework_bulk/tests/`: Unit tests (e.g., `test_generics.py`) and a minimal Django app under `simple_app/`.
- `tests/`: Test harness with `manage.py` and `settings.py` used to run the suite locally.
- Tooling: `Justfile`, `.github/workflows/ci.yml`, `pyproject.toml`.

## Build, Test, and Development Commands

- `just install`: Install dev dependencies.
- `just lint`: Run ruff style checks.
- `just format`: Format with ruff.
- `just test`: Run tests via `tests/manage.py`.
- `just coverage`: Run tests with coverage report (HTML in `htmlcov/`).
- `just dist`: Build a distribution (via `python -m build`).

Examples:

```
just install
just lint
just test
```

## Coding Style & Naming Conventions

- Python: 4‑space indents, max line length 100 (`ruff` configured via `pyproject.toml`).
- Names: `snake_case` for functions/vars, `CapWords` for classes, modules lower_snake.
- Imports: standard library, third‑party, local (grouped, newline‑separated). Avoid wildcard imports outside package `__init__.py`.
- Keep DRY and match existing patterns in `generics.py`, `mixins.py`, and `serializers.py`.

## Testing Guidelines

- Framework: Django `TestCase` with DRF client utilities.
- Location: add tests under `rest_framework_bulk/tests/` named `test_*.py`.
- Run: `just test` locally; use `just coverage` and keep/raise coverage.

## Commit & Pull Request Guidelines

- Commits: concise, imperative subject (e.g., "fix: handle missing id"), reference issues (`Fixes #34`) when applicable; use `[ci skip]` only for non‑code docs.
- PRs: clear description, rationale, and usage notes; link issues; include tests and docs updates (`README.rst`/docstrings). Show before/after behavior when changing APIs.
- CI: GitHub Actions runs the checks. Ensure it passes.

## DRF Version Notes & Safety

- DRF3 updates: for bulk update, use `BulkSerializerMixin` and set `list_serializer_class = BulkListSerializer`.
- Bulk delete: gate with `allow_bulk_destroy`; prefer filtered querysets to avoid accidental mass deletions.
