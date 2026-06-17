"""Ad hoc Phase 3 runner: load the real raw dataset, build the
analysis-ready table (age/age_band, adherence ratio, time intervals,
cascade-step flags, censoring flag), and persist it as
`Data/processed/analysis_ready_<run_date>.parquet`.

This is NOT the Phase 7 CLI (`python -m tb_cascade.cli run`) described in
the implementation plan -- that will chain every phase end-to-end once
they all exist. This script just lets you regenerate today's Phase 3
output on demand.

Usage:
    uv run python scripts/run_derive.py
    uv run python scripts/run_derive.py --as-of 2026-06-16
    uv run python scripts/run_derive.py --as-of 2026-06-16 --run-date 2026-06-16
"""

from __future__ import annotations

import argparse
from datetime import date

from tb_cascade.derive import build_analysis_table, persist_analysis_table
from tb_cascade.io import load_raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        default=date.today().isoformat(),
        help="Analysis date (YYYY-MM-DD) the censoring window is computed against. "
        "Defaults to today.",
    )
    parser.add_argument(
        "--run-date",
        default=None,
        help="Run-date tag used in the output filename "
        "(Data/processed/analysis_ready_<run-date>.parquet). Defaults to --as-of.",
    )
    parser.add_argument(
        "--window-months",
        type=int,
        default=12,
        help="Right-censoring window in months (default: 12).",
    )
    args = parser.parse_args()
    run_date = args.run_date or args.as_of

    print("Loading raw data...")
    df = load_raw()
    print(f"  {len(df)} rows x {len(df.columns)} columns")

    print(f"Building analysis-ready table (as_of={args.as_of}, window_months={args.window_months})...")
    analysis_df = build_analysis_table(df, args.as_of, window_months=args.window_months)
    n_derived = len(analysis_df.columns) - len(df.columns)
    print(f"  {len(analysis_df)} rows x {len(analysis_df.columns)} columns "
          f"({len(df.columns)} raw + {n_derived} derived)")

    out_path = persist_analysis_table(analysis_df, run_date)
    print(f"Analysis-ready Parquet written to: {out_path}")


if __name__ == "__main__":
    main()
