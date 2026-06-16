# Analytical Framework Implementation Plan

*Technical plan for building the data pipeline and analysis framework that implements `Descriptive Study Plan.md`. Audience: the engineer(s) building the framework.*

## 1. Purpose and scope

`Descriptive Study Plan.md` specifies *what* needs to be measured (a 10-step screening-to-outcome cascade, baseline characteristics, site/temporal comparisons) and the QC rules the data must satisfy. This document specifies *how* to build that as software: the technology stack, repository layout, and an ordered set of engineering tasks that take `Data/VladKovMur_dataset.csv` from raw CSV to a reproducible set of tables, charts, and a rendered report.

Design goals, in priority order:

1. **Correctness and auditability** — every number in the final report must be traceable to a documented rule and re-derivable by re-running the pipeline.
2. **Reproducibility** — one command regenerates all outputs from the raw CSV; no manual spreadsheet edits.
3. **Low operational overhead** — the dataset is small (7,732 rows × 62 columns); this does not need distributed computing, a database server, or a web application. Favor lightweight, file-based tools over heavyweight infrastructure.

## 2. Technology stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.11+ | Best-supported ecosystem for both data wrangling and statistics; one language end-to-end. |
| Dependency/env management | `uv` (or `poetry`) + `pyproject.toml` | Reproducible, lockfile-based installs; faster than plain pip/venv. |
| Tabular processing | `pandas` 2.x | Standard; sufficient for 7.7K rows. |
| Analytical query layer | `DuckDB` 1.x | Embedded, zero-server SQL engine that reads pandas DataFrames/Parquet directly — lets the team write the cascade and stratification logic as SQL (easier to audit against the variable table in the study plan) without standing up a database. |
| Schema validation | `pandera` | Declarative schema (dtypes, allowed value sets, row-level checks) defined once and enforced on every run; also doubles as machine-readable data dictionary. |
| Data profiling (exploration only) | `ydata-profiling` | One-line exploratory report (distributions, missingness, correlations) for the engineer's own sanity-check during build, not part of the production pipeline. |
| Statistics | `statsmodels`, `scipy` | Wilson/Clopper-Pearson confidence intervals for proportions, chi-square/Kruskal-Wallis for exploratory comparisons. |
| Survival/person-time | `lifelines` | Person-time and incidence-rate calculation for Step 8 (TB incidence), handles right-censoring cleanly. |
| Baseline table ("Table 1") | `tableone` | Purpose-built package for the demographic summary table in Step 1. |
| Visualization | `plotly` (primary), `matplotlib`/`seaborn` (static fallback) | Plotly has a built-in `Funnel` chart type for the cascade visualization and produces interactive HTML; matplotlib for print-ready PNGs embedded in Word/PDF output. |
| Report assembly | `Quarto` | Single source (`.qmd`) renders to HTML, PDF, and Markdown; supports parameterized, repeatable report generation. If avoiding a non-Python CLI dependency is a priority, substitute Jupyter + `papermill` + `nbconvert`. |
| Testing | `pytest` | Unit tests for every QC rule and derived-variable function. |
| Code quality | `ruff` (lint) + `black` (format) + `pre-commit` | Automated, low-effort consistency. |
| Version control | Git | Track code, configs, and report templates (not the raw data export, unless governance allows it — see §8). |
| Orchestration | A `Makefile` (or a `Typer`/`Click` CLI) | The pipeline runs in seconds; a full workflow orchestrator (Airflow/Dagster) is unnecessary overhead at this data scale. |

This is a single-machine, file-based stack deliberately. Nothing here requires a database server, cloud infrastructure, or a scheduler beyond what `Descriptive Study Plan.md`'s scope calls for.

## 3. Repository structure

```
TBPoject/
├── PRD.md
├── Descriptive Study Plan.md
├── Analytical Framework Implementation Plan.md      (this file)
├── Documentation/
│   ├── DataSet Description.docx
│   └── DataSet Description (English).md
├── Data/
│   ├── raw/
│   │   └── VladKovMur_dataset.csv                   (untouched original)
│   └── processed/
│       └── analysis_ready_<run_date>.parquet         (versioned, derived dataset)
├── src/
│   └── tb_cascade/
│       ├── __init__.py
│       ├── config.py          # paths, thresholds (e.g., 30/60-day targets), small-cell suppression limit
│       ├── schema.py          # pandera schema = machine-readable data dictionary
│       ├── io.py               # load raw CSV -> typed DataFrame; write Parquet snapshot
│       ├── qc.py                # Section 6 checks -> qc_flags table + QC report
│       ├── derive.py           # age, adherence ratio, time intervals, cascade-step flags, censoring flag
│       ├── cascade.py           # Steps 1-8, 10: counts, percentages, CIs, stratification
│       ├── trends.py            # Step 9: temporal aggregation
│       ├── viz.py               # all chart-producing functions (return Plotly/matplotlib figure objects)
│       └── cli.py               # `python -m tb_cascade.cli run` entry point
├── notebooks/
│   └── exploration.ipynb        # throwaway exploration only; nothing in notebooks is a dependency of the pipeline
├── tests/
│   ├── test_qc.py
│   ├── test_derive.py
│   └── fixtures/synthetic_rows.csv   # small hand-built rows covering edge cases (missing dates, reversed dates, duplicate Nomer)
├── report/
│   └── descriptive_report.qmd   # parameterized report matching Descriptive Study Plan.md §7 and §9
├── reports/                     # OUTPUT directory, one timestamped subfolder per run
│   └── 2026-06-16/
│       ├── descriptive_report.html
│       ├── qc_report.md
│       ├── figures/*.png
│       └── tables/*.csv
├── pyproject.toml
├── Makefile
└── README.md
```

## 4. Build plan — ordered tasks

### Phase 0 — Project scaffolding
1. `git init`  and first commit already done. Repository name:  https://github.com/mnikiforovbcn/tb-vladimir-study.git
2. add `.gitignore` for `Data/processed/`, `reports/`, virtual env, and notebook checkpoints.
3. `uv init` / create `pyproject.toml`; pin Python 3.11+; add dependencies from §2.
4. Add `pre-commit` config running `ruff` and `black` on commit.
5. Create the folder skeleton from §3 with empty `__init__.py` files.

### Phase 1 — Ingestion (`io.py`)
1. Write `load_raw(path) -> pd.DataFrame` that reads the CSV with an explicit `dtype`/`parse_dates` map built directly from `Documentation/DataSet Description (English).md` (every `0/1` flag as nullable `Int64` or `boolean`, every `date` field as `datetime64[ns]`, `Source` as `category`).
2. Write `snapshot(df, run_date) -> Path` that writes `Data/processed/raw_snapshot_<run_date>.parquet` — an immutable, fast-loading copy of the exact input used for a given run, so every report can cite the dataset version it was built from.
3. Unit test: load the real CSV, assert row count = 7,732 and column count = 62 (regression guard if the source export format changes).

### Phase 2 — Schema and QC (`schema.py`, `qc.py`)
1. Encode the full data dictionary as a `pandera.DataFrameSchema`: value sets for `TargetGroup` (1–4), `RelationWithSource` (45/313/314/348/366), `FinalOutcome` (1–4), boolean ranges for all `0/1` flags, non-negative integer ranges for `DosesTaken`/`SchemaDoses`.
2. Implement each rule from Descriptive Study Plan §6 as a standalone, testable function returning a boolean Series of violations, e.g. `check_treatgroup_onehot(df)`, `check_outcome_mutual_exclusivity(df)`, `check_date_order(df)`, `check_doses_taken_le_schema(df)`, `check_diagnosis_mutual_exclusivity(df)`, `check_duplicate_registration(df)`.
3. Aggregate all checks into `run_qc(df) -> QCResult` (pass/fail counts per rule + a DataFrame of flagged record IDs `Source`+`Nomer`).
4. Render `qc_report.md` (rule name, # records checked, # violations, violation rate) — this becomes the technical appendix referenced in Descriptive Study Plan §12.3.
5. Missingness audit: per-column null-rate table, split by `Source`, with a separate column flagging whether the missingness is "structural" (i.e., conditionally expected given upstream flags, per Descriptive Study Plan §6.4) vs. unexplained.
6. Unit tests using the synthetic fixture file covering each violation type (reversed dates, mismatched one-hot flags, duplicate Nomer, doses-taken > scheduled).

### Phase 3 — Derived variables (`derive.py`)
1. `age_at_screening(df)`: `(DateScreening - BirthDate).days / 365.25`; add `age_band` via fixed-width bins (0–14, 15–24, …, 65+, matching standard epidemiologic age bands).
2. `adherence_ratio(df)`: `DosesTaken / SchemaDoses`, guarded against division by zero/null.
3. `time_intervals(df)`: diagnosis-to-treatment-start days (`DatePrevTreatmentStart - DateCompleteExaminationTB`), and any other interval needed for Step 4's 30/60-day target metric.
4. `cascade_flags(df)`: one boolean/categorical column per cascade node in Steps 2–8 (e.g., `reached_screening`, `reached_suspected`, `reached_full_eval`, `reached_diagnosis`, `eligible_for_lti_tx`, `lti_recommended`, `lti_prescribed`, `lti_started`, `completed_or_finished`), so downstream cascade tables are simple `groupby().mean()` calls rather than repeated boolean logic.
5. `censoring_flag(df, analysis_date, window_months=12)`: marks records enrolled too recently to have a mature outcome, per Descriptive Study Plan §6.6 and §10 (right-censoring limitation).
6. Output a single analysis-ready table; persist as `Data/processed/analysis_ready_<run_date>.parquet`. This is the only input the analytics layer (Phase 4) is allowed to read — keeps "what happened to the raw data" auditable in one place.

### Phase 4 — Cascade and descriptive analytics (`cascade.py`, `trends.py`)
1. Load the analysis-ready Parquet into an in-process DuckDB connection (`duckdb.register`); write the Steps 1–8 and 10 aggregations as parametrized SQL views (one view per step), with `Source`, `TargetGroup`, and calendar year/quarter as optional `GROUP BY` dimensions passed at query time.
2. Wrap each view with a Python helper that adds a Wilson confidence interval column (`statsmodels.stats.proportion.proportion_confint(count, nobs, method="wilson")`) next to every percentage.
3. Build the Step 1 baseline table with `tableone.TableOne`, stratified by `Source`.
4. Build the Step 8 incidence-rate calculation with `lifelines.utils.survival_table_from_events` or a direct person-time sum, applying the `censoring_flag` from Phase 3.
5. `trends.py`: resample enrollment/treatment-start/outcome dates to quarterly buckets for Step 9.
6. Apply small-cell suppression (suppress or footnote any stratified cell with n < 5, per Descriptive Study Plan §11) as the very last step before any table leaves this module — implement as a single `suppress_small_cells(table, threshold=5)` wrapper so it cannot be accidentally skipped.
7. Unit tests: hand-computed expected percentages/CIs on the synthetic fixture, compared against function output.

### Phase 5 — Visualization (`viz.py`)
1. `funnel_chart(cascade_df)` — `plotly.graph_objects.Funnel` for the screening→diagnosis→treatment→completion cascade (overall, and one per `TargetGroup` as small multiples).
2. `outcome_stacked_bar(df, by="Source")` — outcome composition bars (Step 6).
3. `trend_lines(trend_df)` — enrollment/initiation/outcome counts by quarter (Step 9).
4. `site_comparison_table(df)` — Step 10 side-by-side site summary, rendered as a styled DataFrame (`pandas.Styler` or a Plotly table) rather than a chart.
5. Every figure function returns a figure object (not a saved file) and a separate `export(fig, path)` helper saves both a static PNG (`kaleido` for Plotly→PNG) and interactive HTML — static for the embedded report/Word export, interactive for stakeholder review.

### Phase 6 — Report assembly (`report/descriptive_report.qmd`, `report.py`)
1. Author one Quarto document parameterized by `run_date` and `analysis_ready_path`, organized to mirror Descriptive Study Plan §7 (Steps 1–10) and §9 (visualization plan) section-for-section, so a reviewer can check the report against the study plan line by line.
2. Each section calls the Phase 4/5 functions directly (no copy-pasted numbers) — the report is generated code, not hand-edited prose.
3. Render targets: HTML (primary, interactive Plotly embeds) and a static Markdown/PDF version for circulation to reviewers who need a flat file. If a Word deliverable is later required, render to Markdown first and run it through the existing `docx` skill/pipeline rather than maintaining a second template.
4. Auto-prepend a header block stating the data snapshot date, pipeline git commit hash, and row counts in/out of each QC rule, so every report is self-describing.

### Phase 7 — Automation and CLI
1. `cli.py` exposes one command, e.g. `python -m tb_cascade.cli run --as-of 2026-06-16`, chaining Phases 1→6 and writing everything to `reports/<run_date>/`.
2. `Makefile` targets: `make setup` (install deps + pre-commit), `make test` (pytest), `make report` (run the CLI), `make clean` (clear `reports/` and processed Parquet).
3. README documents the one-command run path and how to interpret `qc_report.md` before trusting `descriptive_report.html`.

### Phase 8 — Validation and sign-off
1. Manually spot-check a random sample (~20 records) of automated cascade-step flags against the raw CSV by hand, with an epidemiologist reviewer, before accepting Phase 4 output.
2. Confirm every QC rule in `qc_report.md` either passes or has a documented, accepted explanation (e.g., expected structural missingness).
3. Tag the repository (`git tag v1.0-descriptive`) once the rendered report is approved, so the exact code+data combination behind the approved report is reproducible later.

## 5. Testing strategy summary

| Test type | Tool | Target |
|---|---|---|
| Unit tests | `pytest` | Every QC rule (Phase 2) and derived variable (Phase 3) against the synthetic fixture, including edge cases (nulls, boundary dates, zero `SchemaDoses`) |
| Regression test | `pytest` | Row/column counts on the real raw CSV; alerts if the upstream export format changes |
| Validation (manual) | n/a | Spot-check sample against raw CSV (Phase 8) |
| Report smoke test | `quarto render --execute` in CI or pre-commit | Confirms the report builds end-to-end without runtime errors before merge |

## 6. Data versioning and reproducibility

- Treat `Data/raw/VladKovMur_dataset.csv` as immutable; never edit it in place. Any correction to the source data arrives as a new dated export.
- Every processed Parquet and every report folder is named by `run_date`, so a report can always be traced to the exact input snapshot and the git commit that produced it (embedded in the report header per Phase 6.4).
- Pin all dependency versions via the `uv`/`poetry` lockfile so the pipeline produces identical output on any machine.

## 7. Privacy and output controls

- `Source_id`, `Nomer`, and `IndexCase` are linkage keys, not names/addresses, but should still never appear in any rendered report — only aggregate counts/percentages leave the pipeline (enforced by `suppress_small_cells` in Phase 4.6).
- Keep `Data/raw/` and `Data/processed/` out of git (`.gitignore`); only code, configs, and the report template are version-controlled. If the raw CSV needs to travel with the repo for reproducibility, store it in a private, access-controlled location rather than a public remote.

## 8. Effort estimate

| Phase | Estimate |
|---|---|
| 0 — Scaffolding | 0.5 day |
| 1 — Ingestion | 0.5 day |
| 2 — Schema & QC | 1.5 days |
| 3 — Derived variables | 1.5 days |
| 4 — Cascade analytics | 2 days |
| 5 — Visualization | 1.5 days |
| 6 — Report assembly | 1.5 days |
| 7 — Automation/CLI | 0.5 day |
| 8 — Validation/sign-off | 1 day (depends on epidemiologist availability) |
| **Total** | **~10.5 working days** for one engineer, before iteration on review feedback |
