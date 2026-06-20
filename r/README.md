# tbcascade

R implementation of the TB preventive treatment cascade descriptive study (see
`../Descriptive Study Plan.md` and `../PRD.md`). Self-contained package living
alongside the existing Python implementation (`../src/tb_cascade/`); the two
never share code, dependencies, or output directories.

## One-command run

```sh
Rscript scripts/run.R
```

This chains ingestion -> QC -> derived variables -> the descriptive report,
and writes everything for the run into `reports/<run-date>/`:

- `qc_report.md` -- Section 6 data-quality findings (schema conformance,
  cross-field checks, date-order violations, missingness by column)
- `descriptive_report.html` -- the full Step 1-10 report (primary format)
- `descriptive_report.md` + `descriptive_report_files/` -- the same report as
  GFM Markdown with linked (not embedded) figure PNGs

Useful flags (see `Rscript scripts/run.R --help`):

- `--run-date YYYY-MM-DD` -- analysis date used for age calculation,
  right-censoring, and the output directory name (default: today)
- `--csv-path PATH` -- override the raw registry CSV (default:
  `../Data/raw/VladKovMur_dataset.csv`)
- `--output-dir PATH` -- override the output directory (default:
  `reports/<run-date>/`)
- `--formats html,gfm` -- which report formats to render

If `make` is available (Linux/macOS/CI/WSL), `make report` does the same
thing; `make setup` restores the renv library and `make test` runs the
testthat suite. On a bare Windows install without `make`, use the `Rscript`
commands directly (see below).

## Reading `qc_report.md`

No row is ever dropped because of a QC finding -- every check in Section 6
is diagnostic, not a filter. Flagged rows still flow into the analysis
table; the report's own QC section and `qc_report.md` exist so a reader can
distinguish **structural** patterns (e.g. non-contact target groups have no
index-case columns by design) from genuine **data-entry** issues (e.g.
`DateOutcome` preceding `DateTreatmentScheme`) before drawing conclusions
from the cascade numbers downstream.

## Development

```sh
Rscript -e "renv::restore(prompt = FALSE)"   # install pinned dependencies
Rscript -e "devtools::test('.')"             # run the testthat suite
Rscript -e "devtools::load_all('.')"         # interactive use
```

### renv quirk: Suggests-only tools

`devtools`, `roxygen2`, `optparse`, `quarto`, `withr`, and `testthat` are
dev/CLI tools declared under `Suggests` in `DESCRIPTION`, not `Imports`. This
project's `renv/settings.json` scopes dependency snapshots to
`Imports`/`Depends`/`LinkingTo` (the runtime-only set), so these six are
deliberately never written into `renv.lock` -- the lockfile stays scoped to
what the package actually needs to run, not the tools used to build/test it.

The tradeoff: if the renv project library is ever wiped or rebuilt from
scratch, `renv::restore()` will not reinstall them (there's nothing in the
lockfile to restore), and any command that needs one of them (`scripts/run.R`
needs `optparse` and `quarto`; `devtools::test()` needs `testthat`) will fail
with "there is no package called '...'". If that happens, reinstall the set
directly:

```sh
Rscript -e "renv::install(c('optparse', 'quarto', 'devtools', 'roxygen2', 'withr', 'testthat'), prompt = FALSE)"
```

(`make setup` does this automatically.) Widening
`package.dependency.fields` to include `Suggests` is **not** a fix -- it
applies recursively across the whole dependency tree, not just this
package's own `Suggests`, and pulls in hundreds of unrelated transitive
packages.

## Layout

```
R/            package source (io, schema, qc, derive, cascade, trends, viz)
tests/        testthat suite + synthetic fixtures
report/       descriptive_report.qmd (parameterized: run_date, analysis_ready_path)
scripts/run.R CLI: ingestion -> QC -> derive -> report, in one command
reports/      per-run outputs (gitignored except .gitkeep)
```

Outputs from this package never land in the Python side's `Data/processed/`
or root `reports/`; R-generated data snapshots go to `../Data/processed/r/`,
rendered reports to `r/reports/`.
