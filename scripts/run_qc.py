"""Ad hoc Phase 2 runner: load the real raw dataset, validate the schema,
run all QC rules + the missingness audit, and write `reports/qc_report.md`.

This is NOT the Phase 7 CLI (`python -m tb_cascade.cli run`) described in
the implementation plan -- that will chain every phase end-to-end once
they all exist. This script just lets you inspect real Phase 1/2 output
today.

Usage:
    uv run python scripts/run_qc.py
"""

from __future__ import annotations

from pathlib import Path

from tb_cascade import qc, schema
from tb_cascade.config import ROOT_DIR
from tb_cascade.io import load_raw

REPORT_PATH = ROOT_DIR / "reports" / "qc_report.md"
FLAGGED_PATH = ROOT_DIR / "reports" / "flagged_records.csv"


def main() -> None:
    print(f"Loading raw data...")
    df = load_raw()
    print(f"  {len(df)} rows x {len(df.columns)} columns")

    print("Validating schema...")
    try:
        schema.validate(df)
        print("  schema OK -- no violations")
    except Exception as exc:  # pandera.errors.SchemaErrors or similar
        print("  schema validation FAILED:")
        print(exc)

    print("Running QC rules + missingness audit...")
    result = qc.run_qc(df)
    audit = qc.missingness_audit(df)
    by_site = qc.run_qc_by_site(df)
    date_detail = qc.date_order_pair_breakdown(df)

    print("\nQC rule summary:")
    print(result.summary.to_string(index=False))
    print(f"\nTotal flagged (rule, record) pairs: {len(result.flagged)}")

    out_path = qc.render_qc_report(result, audit, by_site, date_detail, REPORT_PATH)
    print(f"Privacy-safe report (no row-level values) written to: {out_path}")

    # `result.flagged` deliberately carries only `rule`/`Source`/`Nomer` (see
    # qc.QCResult) so it's safe to print/share on its own. To actually look
    # at the problem records, join those keys back to the full row. This
    # output DOES contain row-level patient data -- keep it local, use it
    # only to track down and correct source records, and don't pass it into
    # any report that leaves this machine (Descriptive Study Plan Sec 11).
    if len(result.flagged):
        per_record_rules = result.flagged.groupby(["Source", "Nomer"], observed=True)["rule"].agg(
            lambda s: "; ".join(sorted(set(s)))
        )
        review = per_record_rules.reset_index().rename(columns={"rule": "rules_violated"})
        review = review.merge(df, on=["Source", "Nomer"], how="left")
        review = review.sort_values(["Source", "Nomer"])

        FLAGGED_PATH.parent.mkdir(parents=True, exist_ok=True)
        review.to_csv(FLAGGED_PATH, index=False)
        print(
            f"{len(review)} distinct flagged records (full data, for local "
            f"review only) written to: {FLAGGED_PATH}"
        )
    else:
        print("No flagged records.")


if __name__ == "__main__":
    main()
