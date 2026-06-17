"""Ad hoc Phase 4 runner: build (or load) the analysis-ready table and run
every `cascade.py`/`trends.py` step (Steps 1-10, plus the Step 9 quarterly
trend), writing a privacy-safe markdown report to `reports/cascade_report.md`.

This is NOT the Phase 7 CLI (`python -m tb_cascade.cli run`) described in
the implementation plan -- that will chain every phase end-to-end once
they all exist. This script just lets you regenerate today's Phase 4
output on demand, the same way `run_qc.py`/`run_derive.py` do for
Phases 2/3.

Every table written here has already passed through
`cascade.suppress_small_cells` (Descriptive Study Plan Sec 11) inside
`cascade.py`/`trends.py` itself -- this script does not re-derive or
bypass that. The one known exception is Step 1's `table1` (the `TableOne`
categorical table), which is not yet suppression-safe -- see
`step1_baseline_table`'s docstring and the tracked follow-up -- so it is
rendered with an explicit caveat rather than silently treated as safe.
`Source_id`/`Nomer`/`IndexCase` are never read or printed by this script;
only the aggregate tables `cascade.py`/`trends.py` already return.

Usage:
    uv run python scripts/run_cascade.py
    uv run python scripts/run_cascade.py --as-of 2026-06-16
    uv run python scripts/run_cascade.py --from-parquet Data/processed/analysis_ready_2026-06-16.parquet
"""

from __future__ import annotations

import argparse
from datetime import date

import pandas as pd

from tb_cascade import cascade, derive, trends
from tb_cascade.config import ROOT_DIR
from tb_cascade.io import load_raw

REPORT_PATH = ROOT_DIR / "reports" / "cascade_report.md"


def _df_md(df: pd.DataFrame) -> str:
    """Render a DataFrame as a markdown table, falling back to a plain
    fixed-width block if `tabulate` (`to_markdown`'s optional dependency)
    isn't installed."""
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return "```\n" + df.to_string(index=False) + "\n```"


def _tableone_block(table1) -> str:
    """Render a `TableOne` via its own pretty-printed `__repr__` inside a
    fixed-width code block, rather than fighting its MultiIndex row/column
    shape into a markdown table."""
    return "```\n" + str(table1) + "\n```"


def _section(lines: list[str], title: str, df: pd.DataFrame, note: str | None = None) -> None:
    lines.append(f"### {title}\n")
    if note:
        lines.append(f"_{note}_\n")
    lines.append(_df_md(df))
    lines.append("")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        default=date.today().isoformat(),
        help="Analysis date (YYYY-MM-DD) Step 8's follow-up maturity and "
        "incidence-rate person-time are computed against. Defaults to today.",
    )
    parser.add_argument(
        "--window-months",
        type=int,
        default=12,
        help="Right-censoring window in months for the persisted `censored` "
        "column when (re)building the analysis-ready table (default: 12). "
        "Step 8 separately recomputes its own 24-month version regardless "
        "of this flag, and this is ignored entirely with --from-parquet.",
    )
    parser.add_argument(
        "--from-parquet",
        default=None,
        help="Load a previously persisted analysis-ready Parquet "
        "(Data/processed/analysis_ready_<run-date>.parquet) instead of "
        "rebuilding it from the raw dataset.",
    )
    args = parser.parse_args()

    if args.from_parquet:
        print(f"Loading analysis-ready table from {args.from_parquet} ...")
        df = pd.read_parquet(args.from_parquet)
    else:
        print("Loading raw data...")
        raw = load_raw()
        print(f"  {len(raw)} rows x {len(raw.columns)} columns")
        print(
            f"Building analysis-ready table (as_of={args.as_of}, "
            f"window_months={args.window_months})..."
        )
        df = derive.build_analysis_table(raw, args.as_of, window_months=args.window_months)
    print(f"  {len(df)} rows x {len(df.columns)} columns")

    print("Running Steps 1-9 (whole cohort) + Step 10 (Source comparison)...")
    step1 = cascade.step1_baseline_table(df)
    step2 = cascade.step2_screening_cascade(df)
    step3 = cascade.step3_diagnostic_outcomes(df)
    step4 = cascade.step4_lti_cascade(df)
    step5 = cascade.step5_regimen_description(df)
    step6 = cascade.step6_adherence_completion(df)
    step7 = cascade.step7_incentive_uptake(df)
    step8 = cascade.step8_followup_outcomes(df, args.as_of)
    step9 = trends.step9_quarterly_trends(df)
    step10 = cascade.step10_site_comparison(df, args.as_of)

    lines: list[str] = []
    lines.append("# TB Cascade Report\n")
    lines.append(
        f"Generated: {date.today().isoformat()} | Analysis date: {args.as_of} | "
        f"n = {len(df)}\n"
    )
    lines.append(
        "All counts/percentages below have small cells (n < 5) suppressed "
        "per Descriptive Study Plan Sec 11, except Table 1 (flagged below). "
        "No row-level identifiers (Source_id/Nomer/IndexCase) appear in "
        "this report -- `Source` site-name labels appear only as an "
        "aggregate stratification dimension.\n"
    )

    lines.append("## Step 1: Baseline population (Table 1)\n")
    lines.append(
        "_Caveat: small-cell suppression is not yet applied to this "
        "categorical table (see Implementation Plan follow-up tracked in "
        "this repo's task list) -- review any small stratum before "
        "sharing this section outside the team._\n"
    )
    lines.append(_tableone_block(step1["table1"]))
    lines.append("")
    _section(lines, "Age (years), median/IQR", step1["age_summary"])
    _section(
        lines,
        "Contacts screened per index case, median/IQR",
        step1["contacts_per_index_case"],
    )

    lines.append("## Step 2: Screening cascade\n")
    lines.append(_df_md(step2))
    lines.append("")

    lines.append("## Step 3: Diagnostic outcomes (among fully evaluated)\n")
    lines.append(_df_md(step3))
    lines.append("")

    lines.append("## Step 4: LTI preventive-treatment cascade\n")
    _section(lines, "Cascade stages", step4["cascade"])
    _section(
        lines,
        "Diagnosis-to-treatment-start delay (days), median/IQR",
        step4["initiation_delay"],
    )
    _section(lines, "Initiated within target window", step4["initiated_within_target"])

    lines.append("## Step 5: Regimen composition (among started)\n")
    lines.append(_df_md(step5))
    lines.append("")

    lines.append("## Step 6: Adherence and completion (among started)\n")
    _section(lines, "Adherence ratio, median/IQR", step6["adherence_summary"])
    _section(lines, "Dose thresholds reached", step6["dose_threshold"])
    _section(lines, "Outcome distribution", step6["outcome_distribution"])

    lines.append("## Step 7: Incentive payment uptake\n")
    _section(lines, "Uptake by incentive", step7["uptake"])
    _section(
        lines,
        "Screening payment delay (days), median/IQR",
        step7["screening_payment_delay"],
    )

    lines.append("## Step 8: Follow-up and final outcomes\n")
    _section(lines, "Re-screened at 1 year", step8["rescreened_1yr"])
    _section(lines, "No TB after 1 year", step8["no_tb_after_1yr"])
    _section(lines, "Re-screened at 24 months", step8["rescreened_24mo"])
    _section(lines, "No TB after 24 months", step8["no_tb_after_24mo"])
    _section(lines, "Final outcome distribution", step8["final_outcome_distribution"])
    _section(
        lines,
        "Final outcome by treatment completion",
        step8["final_outcome_by_completion"],
    )
    _section(
        lines,
        "TB incidence rate (per 100 person-years, among LTI starters)",
        step8["incidence_rate"],
    )

    lines.append("## Step 9: Quarterly trends\n")
    lines.append(_df_md(step9))
    lines.append("")

    lines.append("## Step 10: Site comparison\n")
    lines.append(
        "_Descriptive flagging only, per Sec 7 Step 10 -- not a formal "
        "between-site hypothesis test._\n"
    )
    _section(lines, "Screening cascade by site", step10["screening_cascade"])
    _section(lines, "Diagnostic outcomes by site", step10["diagnostic_outcomes"])
    _section(lines, "LTI cascade by site", step10["lti_cascade"]["cascade"])
    _section(lines, "Initiation delay by site", step10["lti_cascade"]["initiation_delay"])
    _section(
        lines,
        "Initiated within target by site",
        step10["lti_cascade"]["initiated_within_target"],
    )
    _section(lines, "Regimen by site", step10["regimen"])
    _section(
        lines,
        "Adherence summary by site",
        step10["adherence_completion"]["adherence_summary"],
    )
    _section(lines, "Dose thresholds by site", step10["adherence_completion"]["dose_threshold"])
    _section(
        lines,
        "Outcome distribution by site",
        step10["adherence_completion"]["outcome_distribution"],
    )
    _section(lines, "Incentive uptake by site", step10["incentive_uptake"]["uptake"])
    _section(
        lines,
        "Screening payment delay by site",
        step10["incentive_uptake"]["screening_payment_delay"],
    )
    _section(lines, "Re-screened at 1yr by site", step10["followup_outcomes"]["rescreened_1yr"])
    _section(lines, "No TB after 1yr by site", step10["followup_outcomes"]["no_tb_after_1yr"])
    _section(
        lines, "Re-screened at 24mo by site", step10["followup_outcomes"]["rescreened_24mo"]
    )
    _section(lines, "No TB after 24mo by site", step10["followup_outcomes"]["no_tb_after_24mo"])
    _section(
        lines,
        "Final outcome distribution by site",
        step10["followup_outcomes"]["final_outcome_distribution"],
    )
    _section(
        lines,
        "Final outcome by completion by site",
        step10["followup_outcomes"]["final_outcome_by_completion"],
    )
    _section(lines, "Incidence rate by site", step10["followup_outcomes"]["incidence_rate"])

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Privacy-safe report (no row-level values) written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
