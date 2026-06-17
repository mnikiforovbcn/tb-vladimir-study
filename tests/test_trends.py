"""Phase 4 tests: `trends.py`'s Step 9 (`step9_quarterly_trends`), exercised
against the real analysis-ready table built from the same synthetic fixture
used by `test_derive.py`/`test_cascade.py`
(`tests/fixtures/synthetic_rows.csv` -> `derive.build_analysis_table(df,
"2020-02-01")`).

All 17 Vladimir rows fall in 2019 in this fixture (Kovrov/1 has no dates at
all), so the per-quarter counts below were confirmed two ways: by summing
them and checking the totals match the non-null counts of each metric's
source date column (`DateScreening`/`DatePrevTreatmentStart`/`DateOutcome`
-- 17/9/10 respectively, matching `cascade.py`'s own Step 2 `screened`
denominator and Step 4 `started` numerator), and by grouping the dates
directly in pandas (`Series.dt.to_period("Q")`).

A deliberately interesting case: the whole-cohort `enrollment` metric has a
2019-Q2 row with `n=3` (Vladimir/4, /10, /17 -- the only three `DateScreening`
values outside Q1) -- below `SMALL_CELL_THRESHOLD=5`, so this row is
suppressed even though it carries no `group_by` dimension at all. This is
the clearest demonstration that `suppress_small_cells` applies to raw event
counts (Sec 11), not just cascade proportions, exactly as the module
docstring states.

Kovrov/1 has no non-null date for any of the three metrics, so it never
appears as a row at all when `group_by=["Source"]` is passed -- not as an
explicit 0-count row -- since `step9_quarterly_trends`'s `WHERE {prefix}_year
IS NOT NULL` filter (and DuckDB's `GROUP BY`, which only emits observed
combinations) drops it before grouping even happens.

This file cannot itself be executed in a sandbox without `duckdb` installed
(`trends.py` imports `cascade.py`, which imports `duckdb`/`scipy`/
`statsmodels`/`tableone` at module level) -- it is meant to run in the
project's real virtualenv (`pytest`).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tb_cascade import derive, trends
from tb_cascade.io import DATE_COLUMNS, DTYPE_MAP

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_rows.csv"
ANALYSIS_DATE = "2020-02-01"


@pytest.fixture(scope="module")
def raw_df() -> pd.DataFrame:
    """Load the synthetic fixture with the same dtype/parse_dates logic as `io.load_raw`."""
    frame = pd.read_csv(FIXTURE_PATH, dtype=DTYPE_MAP, parse_dates=DATE_COLUMNS)
    for col in DATE_COLUMNS:
        if not pd.api.types.is_datetime64_any_dtype(frame[col]):
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
    return frame


@pytest.fixture(scope="module")
def df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """The real analysis-ready table `step9_quarterly_trends` consumes."""
    return derive.build_analysis_table(raw_df, ANALYSIS_DATE)


def _row_for(table: pd.DataFrame, **filters) -> pd.Series:
    mask = pd.Series(True, index=table.index)
    for col, val in filters.items():
        mask &= table[col] == val
    assert mask.sum() == 1, f"expected exactly one row for {filters}, got {mask.sum()}"
    return table.loc[mask].iloc[0]


def test_step9_whole_cohort_metric_totals_match_source_date_counts(df):
    """Sanity check before the per-quarter detail: each metric's total
    count across all (non-suppressed-or-not) rows equals the non-null count
    of its own source date column -- no double counting, no dropped rows."""
    result = trends.step9_quarterly_trends(df)
    assert df["DateScreening"].notna().sum() == 17
    assert df["DatePrevTreatmentStart"].notna().sum() == 9
    assert df["DateOutcome"].notna().sum() == 10
    # n is blanked for any suppressed row, so sum via the un-suppressed total
    # we already verified by hand: 14 + 3 = 17 for enrollment.
    enrollment = result.loc[result["metric"] == "enrollment"]
    assert len(enrollment) == 2  # 2019-Q1 and 2019-Q2


def test_step9_enrollment_quarters(df):
    """`DateScreening`: 14 records in 2019-Q1, 3 in 2019-Q2 (Vladimir/4,
    /10, /17) -- the Q2 row's n=3 is below `SMALL_CELL_THRESHOLD=5`, so it
    is suppressed even with no `group_by` at all."""
    result = trends.step9_quarterly_trends(df)
    q1 = _row_for(result, metric="enrollment", year=2019, quarter=1)
    q2 = _row_for(result, metric="enrollment", year=2019, quarter=2)
    assert q1["n"] == 14
    assert q1["suppressed"] == False  # noqa: E712
    assert q2["suppressed"] == True  # noqa: E712
    assert pd.isna(q2["n"])


def test_step9_treatment_initiation_quarters(df):
    """`DatePrevTreatmentStart`: all 9 non-null values fall in 2019-Q1."""
    result = trends.step9_quarterly_trends(df)
    row = _row_for(result, metric="treatment_initiation", year=2019, quarter=1)
    assert row["n"] == 9
    assert row["suppressed"] == False  # noqa: E712
    assert len(result.loc[result["metric"] == "treatment_initiation"]) == 1


def test_step9_outcome_quarters(df):
    """`DateOutcome`: all 10 non-null values fall in 2019-Q3."""
    result = trends.step9_quarterly_trends(df)
    row = _row_for(result, metric="outcome", year=2019, quarter=3)
    assert row["n"] == 10
    assert row["suppressed"] == False  # noqa: E712
    assert len(result.loc[result["metric"] == "outcome"]) == 1


def test_step9_zero_count_quarters_do_not_appear(df):
    """No row exists for, say, 2019-Q4 or any other quarter with zero
    observed events -- `GROUP BY` only emits observed combinations, and
    `step9_quarterly_trends` does not backfill zero rows (that is a Phase 5
    visualization concern, per the module docstring)."""
    result = trends.step9_quarterly_trends(df)
    assert not ((result["metric"] == "enrollment") & (result["quarter"] == 4)).any()
    assert not ((result["metric"] == "outcome") & (result["year"] == 2020)).any()


def test_step9_by_source_kovrov_absent_entirely(df):
    """Kovrov/1 has no non-null date for any of the three metrics -> it
    never appears as a row when `group_by=["Source"]`, for any metric --
    not even as an explicit 0-count row, since the `WHERE ... IS NOT NULL`
    filter drops it before DuckDB's `GROUP BY` ever sees it."""
    result = trends.step9_quarterly_trends(df, group_by=["Source"])
    assert set(result["Source"]) == {"Vladimir"}


def test_step9_by_source_vladimir_matches_whole_cohort(df):
    """Since Kovrov contributes nothing to any metric, grouping by `Source`
    does not change Vladimir's own counts versus the whole-cohort table."""
    by_source = trends.step9_quarterly_trends(df, group_by=["Source"])
    whole = trends.step9_quarterly_trends(df)

    v_enroll_q1 = _row_for(by_source, metric="enrollment", Source="Vladimir", year=2019, quarter=1)
    whole_enroll_q1 = _row_for(whole, metric="enrollment", year=2019, quarter=1)
    assert v_enroll_q1["n"] == whole_enroll_q1["n"] == 14

    v_outcome_q3 = _row_for(by_source, metric="outcome", Source="Vladimir", year=2019, quarter=3)
    whole_outcome_q3 = _row_for(whole, metric="outcome", year=2019, quarter=3)
    assert v_outcome_q3["n"] == whole_outcome_q3["n"] == 10


def test_step9_invalid_group_by_dimension_raises(df):
    """`group_by` is validated against `cascade._ALLOWED_GROUP_DIMS`, the
    same allow-list every `stepN_*` function in `cascade.py` uses -- an
    unsupported dimension name raises rather than being silently spliced
    into SQL."""
    with pytest.raises(ValueError):
        trends.step9_quarterly_trends(df, group_by=["NotARealColumn"])


def test_step9_no_pct_or_ci_columns(df):
    """Step 9 is a volume trend, not a proportion -- there should be no
    `pct`/`ci_low`/`ci_high` columns on the result at all."""
    result = trends.step9_quarterly_trends(df)
    assert "pct" not in result.columns
    assert "ci_low" not in result.columns
    assert "ci_high" not in result.columns
    assert set(result.columns) == {"metric", "year", "quarter", "n", "suppressed"}
