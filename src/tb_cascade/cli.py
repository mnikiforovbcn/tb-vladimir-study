"""Phase 7 - Automation and CLI.

`python -m tb_cascade.cli run [--as-of YYYY-MM-DD]` chains every phase of
the pipeline end to end -- ingestion (Phase 1) -> schema/QC (Phase 2) ->
derived variables (Phase 3) -> report rendering, which itself calls into
cascade/trend analytics (Phase 4) and visualization (Phase 5) -- and
writes one self-contained, timestamped output folder per run:

    reports/<run_date>/
        qc_report.md            # technical QC appendix (Sec 12.3) -- read this first
        flagged_records.csv     # row-level QC detail -- LOCAL REVIEW ONLY, see below
        data_cleaning/           # Phase 8: Владимир.xlsx / Ковров.xlsx / Муром.xlsx --
                                  # per-site correction lists, LOCAL REVIEW ONLY, see below
        descriptive_report.html # Phase 6 report, English
        descriptive_report.md   # ... gfm copy, for flat-file circulation
        descriptive_report_ru.html / .md   # Russian translation, if its
                                            # template (report/descriptive_report_ru.qmd)
                                            # is present

This module supersedes the three ad hoc Phase 2/3/4 runners
(`scripts/run_qc.py`, `scripts/run_derive.py`, `scripts/run_cascade.py`)
as the one supported end-to-end entry point, but does not replace them --
they remain useful for inspecting a single phase's output in isolation
without a full run (e.g. while iterating on a `cascade.py` change). They
are intentionally left untouched by this change.

Why a `flagged_records.csv` ends up inside a directory this module's own
docstring calls "self-contained": `reports/` as a whole is git-ignored
(see `.gitignore`), so nothing under `reports/<run_date>/` -- including
this file -- ever reaches version control or a public remote on its own.
That is not the same thing as safe-to-share. `flagged_records.csv` carries
full row-level data (per `qc.py`'s `QCResult.flagged` joined back to the
raw row, the same join `scripts/run_qc.py` already performs) and must
never be forwarded, emailed, or copied into a location outside this
machine -- only `qc_report.md` and the rendered report(s) are written
to be shareable. See Descriptive Study Plan Sec 11 and Implementation
Plan Sec 7.

`data_cleaning/`'s per-site workbooks (Phase 8, `cleaning_list.py`) carry
the same kind of record-level detail (`Nomer`) for the same reason
(see that module's docstring) -- they exist to be handed to each site's
own data manager directly, never bundled with the descriptive report or
copied off this machine.

Rendering is delegated to the real `quarto` CLI via `subprocess` (Quarto
is not a Python import-able dependency). Quarto writes a single
document's HTML/gfm output next to its `.qmd` source by default; this
module deliberately does not pass `--output-dir` to redirect that, since
Quarto's own documentation states the flag is not reliably honored for a
standalone (non-project) document render -- there is no `_quarto.yml` in
this repository, so `report/` is not a Quarto project. Instead, this
module renders normally and then moves the resulting output files into
`reports/<run_date>/` itself, which is the workaround Quarto's docs
recommend (a "post-render" move step).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import click

from tb_cascade import cleaning_list, derive, qc, schema
from tb_cascade.config import REPORTS_DIR, ROOT_DIR
from tb_cascade.io import load_raw

REPORT_TEMPLATE_DIR = ROOT_DIR / "report"

#: Every report template this command knows how to render, keyed by the
#: short language tag used in `--lang`/output filenames. New languages
#: (e.g. a future `descriptive_report_xx.qmd`) only need an entry here.
REPORT_TEMPLATES: dict[str, Path] = {
    "en": REPORT_TEMPLATE_DIR / "descriptive_report.qmd",
    "ru": REPORT_TEMPLATE_DIR / "descriptive_report_ru.qmd",
}


@click.group()
def cli() -> None:
    """tb_cascade pipeline commands (Implementation Plan Phase 7)."""


@cli.command()
@click.option(
    "--as-of",
    default=None,
    help="Analysis date (YYYY-MM-DD) Step 8's follow-up maturity, the "
    "incidence-rate person-time calculation, and the censoring window are "
    "all computed against. Defaults to today.",
)
@click.option(
    "--run-date",
    default=None,
    help="Run-date tag used for the output folder (reports/<run-date>/) and "
    "the persisted Parquet filename (Data/processed/analysis_ready_<run-date>.parquet). "
    "Defaults to --as-of, mirroring scripts/run_derive.py's convention.",
)
@click.option(
    "--window-months",
    type=int,
    default=12,
    show_default=True,
    help="Right-censoring window in months for the persisted `censored` "
    "column when building the analysis-ready table (Step 8 separately "
    "recomputes its own 24-month version regardless of this flag).",
)
@click.option(
    "--lang",
    "langs",
    multiple=True,
    type=click.Choice(sorted(REPORT_TEMPLATES)),
    default=(),
    help="Which report language(s) to render (repeatable, e.g. --lang en --lang ru). "
    "Defaults to every language in REPORT_TEMPLATES whose .qmd template exists on disk.",
)
@click.option(
    "--skip-report",
    is_flag=True,
    help="Run ingestion, QC, and derived-variable construction only; skip the "
    "Quarto render step entirely (e.g. for a fast QC-only check, or on a "
    "machine without Quarto installed).",
)
@click.option(
    "--skip-cleaning-list",
    is_flag=True,
    help="Skip writing the per-site data-cleaning workbooks "
    "(reports/<run_date>/data_cleaning/, Phase 8), for symmetry with --skip-report.",
)
def run(
    as_of: str | None,
    run_date: str | None,
    window_months: int,
    langs: tuple[str, ...],
    skip_report: bool,
    skip_cleaning_list: bool,
) -> None:
    """Run the full pipeline (Phases 1-6) and write reports/<run_date>/."""
    as_of = as_of or date.today().isoformat()
    run_date = run_date or as_of
    out_dir = REPORTS_DIR / run_date
    out_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Run date: {run_date} | Analysis date (as_of): {as_of} | Output: {out_dir}")

    # --- Phase 1: ingestion ---------------------------------------------
    click.echo("\n[1/5] Loading raw data...")
    raw = load_raw()
    click.echo(f"  {len(raw)} rows x {len(raw.columns)} columns")

    # --- Phase 2: schema + QC --------------------------------------------
    # Mirrors scripts/run_qc.py exactly (advisory schema check -- print and
    # continue rather than abort the run -- since a schema violation does
    # not by itself mean every downstream table is wrong; the QC report
    # below surfaces the same issues with row-level detail anyway).
    click.echo("\n[2/5] Validating schema...")
    try:
        schema.validate(raw)
        click.echo("  schema OK -- no violations")
    except Exception as exc:  # pandera.errors.SchemaErrors or similar
        click.echo("  schema validation FAILED:")
        click.echo(str(exc))

    click.echo("Running QC rules + missingness audit...")
    qc_result = qc.run_qc(raw)
    audit = qc.missingness_audit(raw)
    by_site = qc.run_qc_by_site(raw)
    date_detail = qc.date_order_pair_breakdown(raw)
    click.echo(f"  Total flagged (rule, record) pairs: {len(qc_result.flagged)}")

    qc_report_path = qc.render_qc_report(
        qc_result, audit, by_site, date_detail, out_dir / "qc_report.md"
    )
    click.echo(f"  QC report written to: {qc_report_path}")

    # `qc_result.flagged` only carries rule/Source/Nomer; joining it back
    # to `raw` (same join scripts/run_qc.py performs) reconstructs full
    # rows for local debugging -- see this module's docstring for why
    # that output must never leave this machine.
    if len(qc_result.flagged):
        per_record_rules = qc_result.flagged.groupby(["Source", "Nomer"], observed=True)[
            "rule"
        ].agg(lambda s: "; ".join(sorted(set(s))))
        review = per_record_rules.reset_index().rename(columns={"rule": "rules_violated"})
        review = review.merge(raw, on=["Source", "Nomer"], how="left")
        review = review.sort_values(["Source", "Nomer"])

        flagged_path = out_dir / "flagged_records.csv"
        review.to_csv(flagged_path, index=False)
        click.echo(
            f"  {len(review)} distinct flagged records (full data, LOCAL "
            f"REVIEW ONLY -- see this module's docstring) written to: {flagged_path}"
        )
    else:
        click.echo("  No flagged records.")

    # --- Phase 8: per-site data-cleaning workbooks ------------------------
    # Reuses `qc_result` (no rules recomputed) -- only repackages it into a
    # Russian-language, per-site, per-problem format the local data managers
    # already know (Excel) instead of another Markdown/CSV report. See
    # `cleaning_list.py`'s docstring for why this is the one record-level,
    # `Nomer`-carrying output this module writes other than `flagged_records.csv`.
    click.echo("\n[3/5] Writing per-site data-cleaning workbooks...")
    if skip_cleaning_list:
        click.echo("  --skip-cleaning-list set: not writing any workbook.")
    else:
        cleaning_paths = cleaning_list.export_cleaning_list(
            raw, out_dir / "data_cleaning", qc_result=qc_result
        )
        for site_name_ru, path in sorted(cleaning_paths.items()):
            click.echo(f"  {site_name_ru}: {path}")

    # --- Phase 3: derived variables --------------------------------------
    click.echo(f"\n[4/5] Building analysis-ready table (window_months={window_months})...")
    analysis_df = derive.build_analysis_table(raw, as_of, window_months=window_months)
    n_derived = len(analysis_df.columns) - len(raw.columns)
    click.echo(
        f"  {len(analysis_df)} rows x {len(analysis_df.columns)} columns "
        f"({len(raw.columns)} raw + {n_derived} derived)"
    )
    analysis_ready_path = derive.persist_analysis_table(analysis_df, run_date)
    click.echo(f"  Analysis-ready Parquet written to: {analysis_ready_path}")

    # --- Phases 4-6: cascade/trend analytics + visualization + report ----
    # (Phases 4 and 5 are exercised inside the .qmd templates themselves --
    # every report section calls cascade.py/trends.py/viz.py directly, per
    # Implementation Plan Phase 6 item 2 -- so this command's own job is
    # just to invoke Quarto with the right parameters and relocate output.)
    if skip_report:
        click.echo("\n[5/5] --skip-report set: not rendering any report.")
        return

    selected_langs = langs or tuple(
        lang for lang, template in REPORT_TEMPLATES.items() if template.exists()
    )
    click.echo(f"\n[5/5] Rendering report(s): {', '.join(selected_langs) or '(none found)'}")
    for lang in selected_langs:
        template = REPORT_TEMPLATES[lang]
        if not template.exists():
            click.echo(f"  Skipping '{lang}': template not found at {template}")
            continue
        _render_report(template, as_of, str(analysis_ready_path), window_months, out_dir)


def _render_report(
    template: Path, as_of: str, analysis_ready_path: str, window_months: int, out_dir: Path
) -> None:
    """Render one `.qmd` template via the real `quarto` CLI, then move its
    HTML/gfm output into `out_dir`.

    Quarto's Jupyter/Papermill-style `-P key:value` parameters override the
    template's own `parameters` cell defaults (`as_of`, `analysis_ready_path`,
    `window_months`) -- the same convention every `descriptive_report*.qmd`
    docstring documents. `--execute-daemon-restart` forces a fresh kernel so
    a module edited on disk since the last render (e.g. `report/i18n_ru.py`)
    is always picked up, rather than silently reusing Quarto's persistent
    kernel cache from a previous run.
    """
    click.echo(f"  Rendering {template.name} ...")
    cmd = [
        "quarto",
        "render",
        str(template),
        "-P",
        f"as_of:{as_of}",
        "-P",
        f"analysis_ready_path:{analysis_ready_path}",
        "-P",
        f"window_months:{window_months}",
        "--execute-daemon-restart",
    ]
    try:
        subprocess.run(cmd, cwd=ROOT_DIR, check=True)
    except FileNotFoundError:
        click.echo(
            "  ERROR: `quarto` was not found on PATH. Install Quarto "
            "(https://quarto.org/docs/get-started/) to render reports, or "
            "re-run with --skip-report to omit this step.",
            err=True,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        click.echo(f"  ERROR: quarto render failed for {template.name} (exit {exc.returncode})", err=True)
        sys.exit(exc.returncode)

    moved = []
    for suffix in (".html", ".md"):
        src = template.with_suffix(suffix)
        if src.exists():
            dest = out_dir / src.name
            shutil.move(str(src), str(dest))
            moved.append(dest.name)
    if moved:
        click.echo(f"  Moved into {out_dir}: {', '.join(moved)}")
    else:
        click.echo(f"  WARNING: no rendered output found next to {template} after render.")


if __name__ == "__main__":
    cli()
