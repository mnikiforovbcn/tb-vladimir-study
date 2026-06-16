# TB Cascade Analytical Framework

Data pipeline and analysis framework implementing `Descriptive Study Plan.md` for the Vladimir Oblast TB preventive treatment program dataset (`Data/raw/VladKovMur_dataset.csv`).

See `Analytical Framework Implementation Plan.md` for the full technical plan and build phases. This README will be filled in with run instructions as the pipeline (`src/tb_cascade/`) is built out (Phase 7).

## Setup

Requires [`uv`](https://docs.astral.sh/uv/) (installs and manages Python 3.11+ automatically if not already present).

```
uv lock              # resolve and pin dependencies (writes/updates uv.lock)
uv sync --extra dev  # create .venv and install runtime + dev deps (pytest, ruff, black, pre-commit)
```

`--extra dev` matters: `pytest` and the other dev tools live under `[project.optional-dependencies] dev` in `pyproject.toml`, which `uv sync` does **not** install by default. Without it, `uv run pytest` will silently fall back to any `pytest` it finds elsewhere on your PATH -- which won't have this project's dependencies (e.g. pandas) available, and will fail with a confusing `ModuleNotFoundError`.

Verify the environment:

```
uv run python -c "import pandas, duckdb, pandera, lifelines; print('ok')"
uv run pytest
```

## Status

Phase 0 (project scaffolding) and Phase 1 (ingestion, `src/tb_cascade/io.py`) complete: package skeleton, `pyproject.toml`, `pre-commit` config, a locked/verified `uv` environment (`uv.lock`, Python 3.13), and `load_raw()`/`snapshot()` for the raw CSV with tests in `tests/test_io.py`. Remaining pipeline modules (`schema.py`, `qc.py`, `derive.py`, `cascade.py`, `trends.py`, `viz.py`, `cli.py`) are not yet implemented.
