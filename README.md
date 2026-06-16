# TB Cascade Analytical Framework

Data pipeline and analysis framework implementing `Descriptive Study Plan.md` for the Vladimir Oblast TB preventive treatment program dataset (`Data/raw/VladKovMur_dataset.csv`).

See `Analytical Framework Implementation Plan.md` for the full technical plan and build phases. This README will be filled in with run instructions as the pipeline (`src/tb_cascade/`) is built out (Phase 7).

## Setup

Requires [`uv`](https://docs.astral.sh/uv/) (installs and manages Python 3.11+ automatically if not already present).

```
uv lock      # resolve and pin dependencies (writes/updates uv.lock)
uv sync      # create .venv and install the locked dependencies
```

Verify the environment:

```
uv run python -c "import pandas, duckdb, pandera, lifelines; print('ok')"
```

## Status

Phase 0 (project scaffolding) complete: package skeleton, `pyproject.toml`, `pre-commit` config, and a locked/verified `uv` environment (`uv.lock`, Python 3.13). Pipeline modules (`src/tb_cascade/*.py`) are not yet implemented.
