"""Phase 4 - Temporal trends (Step 9).

Step 9 lives in its own module, separate from `cascade.py`, because it
has a different shape from every other step: it is a volume/count
trend over calendar time ("how many enrollments/treatment starts/
outcomes happened in this quarter"), not a cascade proportion,
percentage, or median/IQR summary of a fixed denominator. It still
reuses `cascade.py`'s connection helper, group-by validation, label
recoding, and small-cell suppression machinery rather than reinventing
any of it -- see the Implementation Plan (Phase 4 item 6): "`trends.py`:
resample enrollment/treatment-start/outcome dates to quarterly buckets
for Step 9."

Design notes:
- Counts, not proportions: each row is the number of records whose
  *own* event date falls in that calendar quarter (e.g. how many
  people started treatment in 2020-Q2). There is no Wilson CI here --
  unlike every `stepN_*` function in `cascade.py`, a quarterly count is
  not a share of some fixed denominator, it is the quantity of
  interest itself (Descriptive Study Plan Sec 7 Step 9: "Enrollment,
  treatment initiation, and outcome counts by calendar year/quarter").
- Three metrics, long format: `"enrollment"` (`DateScreening`),
  `"treatment_initiation"` (`DatePrevTreatmentStart`), and `"outcome"`
  (`DateOutcome`) -- the same three date columns `cascade.py`'s
  `_CALENDAR_SOURCE_DATES` already derives `enroll_year`/`treat_start_
  year`/`outcome_year` (etc.) from, reused here rather than
  re-derived, so the two modules can never drift out of sync on what
  "enrollment" or "treatment start" means. One row per (`metric`,
  `group_by`..., `year`, `quarter`), so a trend-line chart (Phase 5
  `viz.trend_lines`) can facet/color by `metric` directly instead of
  needing three separate wide columns.
- Quarters with zero events do not appear as explicit 0-count rows --
  DuckDB's `GROUP BY` only emits observed combinations. A caller
  building a continuous time axis (Phase 5) is responsible for
  reindexing against the full quarter range and filling gaps with 0;
  this module does not conflate "zero events" with "no row for this
  quarter," since those are different claims.
- No hard-coded year filter: the Study Plan's "(2018-2026)" describes
  the expected range of the real dataset, not a filter this module
  imposes -- out-of-range/implausible dates are QC's job
  (`schema.py`/`qc.py`), not this module's.
- Small-cell suppression still applies (Descriptive Study Plan Sec 11)
  even though these are raw event counts rather than cascade
  proportions: a quarter with 1-4 enrollments at the smallest site
  (Murom) is exactly the kind of small, potentially identifying cell
  Sec 11 warns about. Here the count *is* the denominator being
  checked (there is no separate numerator/denominator pair the way
  there is for a proportion), so `suppress_small_cells` is called with
  `n_col="n"` and `value_cols=["n"]`.
- `group_by` may add any non-calendar dimension from
  `cascade._ALLOWED_GROUP_DIMS` (e.g. `["Source"]`) on top of the
  quarter/metric breakdown every row already has. Passing one of the
  *other* metrics' calendar columns (e.g. `group_by=["treat_start_
  year"]` while computing the `"enrollment"` metric) is technically
  allowed by the shared allow-list and is not nonsensical -- it lets a
  caller track, say, enrollment-quarter volume broken out by the
  cohort's eventual treatment-start year -- but it means that row's
  `year`/`quarter` columns and its `treat_start_year` column describe
  two different events; this is left to the caller to interpret
  correctly rather than special-cased here.
"""

from __future__ import annotations

import pandas as pd

from tb_cascade.cascade import (
    _apply_label_maps,
    _validate_group_by,
    connect,
    suppress_small_cells,
)

# --- Step 9: quarterly trends ------------------------------------------------

#: One (metric label, calendar-dimension prefix) pair per Step 9 trend
#: line. The prefix matches `cascade._CALENDAR_SOURCE_DATES`'s keys, so
#: `{prefix}_year`/`{prefix}_quarter` are exactly the columns `connect`
#: already attaches to the registered `analysis` table -- no separate
#: date arithmetic is done here.
_STEP9_METRICS: dict[str, str] = {
    "enrollment": "enroll",
    "treatment_initiation": "treat_start",
    "outcome": "outcome",
}


def step9_quarterly_trends(
    df: pd.DataFrame, group_by: list[str] | None = None
) -> pd.DataFrame:
    """Step 9: enrollment / treatment-initiation / outcome counts by
    calendar year and quarter, per Descriptive Study Plan Sec 7 Step 9
    and Implementation Plan Phase 4 item 6.

    `group_by` may add any dimension from `cascade._ALLOWED_GROUP_DIMS`
    (e.g. `["Source"]`, `["TargetGroup"]`) on top of the quarter/metric
    breakdown every row already has -- see the module docstring for the
    caveat on passing another metric's own calendar column.

    Returns one row per (`metric`, *group_by*, `year`, `quarter`) with
    `n` (count of records whose metric's date falls in that quarter).
    No `pct`/CI columns -- this is a volume trend over time, not a
    proportion of a fixed denominator (see module docstring).
    """
    dims = _validate_group_by(group_by)
    con = connect(df)
    try:
        parts = []
        for metric, prefix in _STEP9_METRICS.items():
            dim_select = "".join(f"{d}, " for d in dims)
            group_cols = [f"{prefix}_year", f"{prefix}_quarter", *dims]
            sql = f"""
                SELECT
                    {prefix}_year AS year,
                    {prefix}_quarter AS quarter,
                    {dim_select}
                    COUNT(*) AS n
                FROM analysis
                WHERE {prefix}_year IS NOT NULL
                GROUP BY {", ".join(group_cols)}
            """
            part = con.execute(sql).fetchdf()
            part["metric"] = metric
            parts.append(part)
        result = pd.concat(parts, ignore_index=True)
    finally:
        con.close()

    result = result[["metric", *dims, "year", "quarter", "n"]]
    result = result.sort_values(["metric", *dims, "year", "quarter"]).reset_index(
        drop=True
    )
    result = _apply_label_maps(result)
    return suppress_small_cells(result, n_col="n", value_cols=["n"])
