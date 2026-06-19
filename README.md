# TB Cascade Analytical Framework

Data pipeline and analysis framework implementing `Descriptive Study Plan.md` for the Vladimir Oblast TB preventive treatment program dataset (`Data/raw/VladKovMur_dataset.csv`).

See `Analytical Framework Implementation Plan.md` for the full technical plan and build phases.

## Setup

Requires [`uv`](https://docs.astral.sh/uv/) (installs and manages Python 3.11+ automatically if not already present) and, to render reports, [Quarto](https://quarto.org/docs/get-started/).

```
uv lock                    # resolve and pin dependencies (writes/updates uv.lock)
uv sync --extra dev        # create .venv and install runtime + dev deps (pytest, ruff, black, pre-commit)
uv run pre-commit install  # install the pre-commit git hook (.pre-commit-config.yaml)
```

`--extra dev` matters: `pytest` and the other dev tools live under `[project.optional-dependencies] dev` in `pyproject.toml`, which `uv sync` does **not** install by default. Without it, `uv run pytest` will silently fall back to any `pytest` it finds elsewhere on your PATH -- which won't have this project's dependencies (e.g. pandas) available, and will fail with a confusing `ModuleNotFoundError`.

Verify the environment:

```
uv run python -c "import pandas, duckdb, pandera, lifelines, papermill; print('ok')"
uv run pytest
```

A `Makefile` (`make setup`/`make test`/`make report`/`make clean`) wraps the commands on this page as shortcuts -- convenient on Linux/macOS/CI, but `make` is not installed by default on Windows, and the Makefile's `rm`/`touch` calls additionally need a Unix-style shell (e.g. Git Bash) on PATH to work even once `make` itself is installed. The `uv run ...` commands throughout this README work everywhere, including plain Windows PowerShell, with no extra setup, so they're what's documented here; treat `make` as an optional convenience if your environment already has it.

## Running the full pipeline

```
uv run python -m tb_cascade.cli run --as-of 2026-06-16
```

This is the one-command path through Phases 1-6 (ingestion -> schema/QC -> derived variables -> cascade/trend analytics -> visualization -> report rendering), implemented by `src/tb_cascade/cli.py`. `--as-of` defaults to today and is the analysis date used for follow-up maturity, incidence-rate person-time, and the censoring window.

Other flags: `--run-date` (tag the output folder/Parquet independently of `--as-of`, e.g. when re-running against the same analysis date), `--window-months` (default 12), `--lang en`/`--lang ru` (repeatable; defaults to every report template found under `report/`), `--skip-report` (run ingestion/QC/derive only, no Quarto render -- useful for a fast QC-only check or on a machine without Quarto installed), `--skip-cleaning-list` (skip writing the per-site data-cleaning workbooks, for symmetry with `--skip-report`).

Report rendering passes `-P key:value` parameters to `quarto render`, which requires the `papermill` package (installed via `uv sync --extra dev`, see Setup). Without it, the render step fails with `ERROR: The papermill package is required for processing --execute-params`; either re-run `uv sync --extra dev` to pick it up, or pass `--skip-report` to skip rendering entirely.

Each run writes a single self-contained folder, `reports/<run_date>/`:

| File | Contents | Shareable? |
|---|---|---|
| `qc_report.md` | Technical QC appendix: rule violation rates by site, date-order reversal detail, missingness audit | Yes |
| `flagged_records.csv` | Every QC-flagged row, full data, joined back from the raw export | **No -- local review only, see below** |
| `data_cleaning/Владимир.xlsx`, `Ковров.xlsx`, `Муром.xlsx` | Phase 8: per-site, Russian-language correction list (registration number, problem, field(s)) for that site's data manager | **No -- local review only, see below** |
| `descriptive_report.html` / `.md` | Phase 6 report (English) | Yes |
| `descriptive_report_ru.html` / `.md` | Russian translation, if `report/descriptive_report_ru.qmd` is present | Yes |

`reports/` is git-ignored, so none of this reaches version control on its own -- but "not in git" is not the same thing as "safe to share." `flagged_records.csv` and the `data_cleaning/` workbooks carry row-level identifiers (`Source`/`Nomer`) and must never be forwarded, emailed, or copied off this machine. Only `qc_report.md` and the rendered report(s) are written to be circulated.

### Read `qc_report.md` before trusting `descriptive_report.html`

`descriptive_report.html` presents cascade percentages as if the underlying data were clean; `qc_report.md` is what tells you whether that's actually true for this run. It has three sections:

1. **Internal consistency rules** -- each rule's violation rate, overall and by site. A rule with a high rate concentrated at one site (rather than spread evenly across all three) points to a site-specific data-entry or export problem, not a population difference -- worth resolving, or at least footnoting, before reading too much into a cross-site comparison in the main report.
2. **Date order detail** -- which specific adjacent date pair (e.g. screening before enrollment) is driving any `date_order` violations. A reversal concentrated in one transition usually means a single field is being entered inconsistently, not that the whole date sequence is unreliable.
3. **Missingness audit** -- null rate per column, split into `Structural` (expected, e.g. a field that only applies to one `TargetGroup`) and `Unexplained`. A high `Unexplained` count on a column the descriptive report relies on (e.g. an outcome or treatment-start date) means that report's denominator for that section is smaller, and possibly biased, in a way the headline percentage alone won't show.

None of this blocks the report from rendering -- schema/QC violations are advisory by design, since one bad rule doesn't necessarily invalidate every other table. The judgment call of whether a given violation rate is acceptable for this run is left to the reader of `qc_report.md`, which is why it is written first and is meant to be read first.

## Other commands

```
uv run pytest   # run the test suite
```

Clear generated output (`reports/`, keeping `.gitkeep`, and `Data/processed/` -- never touches `Data/raw/`):

```
# macOS/Linux/Git Bash
rm -rf reports/* Data/processed/*
touch reports/.gitkeep

# Windows PowerShell
Remove-Item -Recurse -Force reports\*, Data\processed\*
New-Item reports\.gitkeep -ItemType File -Force | Out-Null
```

(`make clean` runs the macOS/Linux/Git Bash version above; see the Setup section's note on `make`.)

## Status

Phases 0-8 of `Analytical Framework Implementation Plan.md` are complete: ingestion (`io.py`), schema/QC (`schema.py`, `qc.py`), derived variables (`derive.py`), cascade/trend analytics (`cascade.py`, `trends.py`), visualization (`viz.py`), report assembly (`report/descriptive_report*.qmd`), the `cli.py`/`Makefile` automation in this document, and the per-site, Russian-language data-cleaning list for local data managers (`cleaning_list.py`, wired into `cli.py`'s run command, tested in `tests/test_cleaning_list.py`). One item remains: Phase 9 (manual validation and sign-off).
