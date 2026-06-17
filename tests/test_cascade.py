"""Phase 4 tests: every `cascade.py` step function, exercised against the
real analysis-ready table built from the same synthetic fixture used by
`test_qc.py`/`test_derive.py` (`tests/fixtures/synthetic_rows.csv` ->
`derive.build_analysis_table(df, "2020-02-01")`).

Every expected value below was independently computed by re-implementing
`cascade.py`'s SQL-based helpers (`_flag_proportion`, `_categorical_
distribution`, `_median_iqr`, `wilson_ci`) in pure pandas/Python and running
them against the *real* output of `derive.build_analysis_table` -- not
hand-traced from the raw CSV text, and not a re-derivation of `derive.py`'s
own logic (that is `test_derive.py`'s job; this file trusts `derive.py`'s
already-tested output and checks only what `cascade.py` does with it). The
Wilson interval was reimplemented from its closed-form definition (matching
`statsmodels.stats.proportion.proportion_confint(method="wilson")`); the one
incidence-rate exact-Poisson upper bound used here (`step8_incidence_rate`,
2 degrees of freedom at zero events) has a closed form too, since a
chi-square distribution with 2 degrees of freedom is exactly
`Exponential(mean=2)`: `ppf(p) = -2*ln(1-p)`.

A few rows/quirks worth calling out, since they drive several assertions
below:

- Vladimir/15: `lti_started=True` but `DatePrevTreatmentStart` itself is
  blank (a data-quality quirk in the fixture, not a derive.py bug) ->
  `days_full_eval_to_treatment_start` and `initiated_within_30d`/`_60d` are
  all `pd.NA` for this row. This is why Step 4's `initiated_within_target`
  and `initiation_delay` have `n=9` even though `started` (Step 4's
  `cascade` table) has `n=12`/`count=10` -- the started-cohort headcount and
  the interval-dependent denominator are not the same thing.
- Vladimir/8 and Vladimir/9: `outcome_branch` is `pd.NA` (not mutually
  exclusive / not exhaustive respectively, per `test_derive.py`) -- both are
  excluded from Step 6's `outcome_distribution`, which is why it has
  `n=8` against a `lti_started=True` cohort of 10.
  Vladimir/9 additionally has `FinalOutcome=3` ("unknown") and is *not*
  censored at 1 year, so it still appears in Step 8's
  `final_outcome_distribution` (`category="unknown"`) despite `outcome_
  branch` being unresolved -- the two are independent.
- Kovrov/1: `reached_screening`/`reached_full_eval` are both definite
  `False` (not `pd.NA`), so Kovrov appears as an explicit `count=0` row in
  Step 2's `group_by=["Source"]` table for those two stages -- but is
  *absent* entirely from `suspected_tb`/`diaskintest_positive` (those flags
  are `pd.NA` for an unscreened record, so the row is excluded from `n`,
  not shown as 0/0).
- `_categorical_distribution`-backed tables (Step 3's `diagnosis_branch`,
  Step 6's `outcome_distribution`, Step 8's `final_outcome_distribution`/
  `final_outcome_by_completion`) all alias their category column to a
  literal `"category"` column in the SQL, regardless of which underlying
  column was distributed -- not `"diagnosis_branch"`/`"outcome_branch"`/etc.
  Tests below look up rows by `category`, matching the real SQL shape.

This file cannot itself be executed in a sandbox without `duckdb`/`scipy`/
`statsmodels`/`tableone` installed (`cascade.py` imports all four at module
level) -- it is meant to run in the project's real virtualenv (`pytest`).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tb_cascade import cascade, derive
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
    """The real analysis-ready table every `stepN_*` function consumes --
    built once per module via the actual `derive.build_analysis_table`,
    not a hand-rolled stand-in."""
    return derive.build_analysis_table(raw_df, ANALYSIS_DATE)


def _row_for(table: pd.DataFrame, **filters) -> pd.Series:
    """Pull the one row matching every column=value filter in `filters`,
    e.g. `_row_for(result, stage="screened")` or
    `_row_for(result, Source="Vladimir", stage="screened")`."""
    mask = pd.Series(True, index=table.index)
    for col, val in filters.items():
        mask &= table[col] == val
    assert mask.sum() == 1, f"expected exactly one row for {filters}, got {mask.sum()}"
    return table.loc[mask].iloc[0]


def _assert_prop(row: pd.Series, n: int, count: int, pct: float, ci: tuple[float, float]):
    assert row["n"] == n
    assert row["count"] == count
    assert row["pct"] == pytest.approx(pct, abs=1e-9)
    assert row["ci_low"] == pytest.approx(ci[0], abs=1e-9)
    assert row["ci_high"] == pytest.approx(ci[1], abs=1e-9)


# --- Step 1: baseline table ---------------------------------------------------


def test_step1_age_summary(df):
    """Median/IQR of `age_years` over all 17 non-missing ages (Kovrov/1's
    is `pd.NA`), unstratified."""
    result = cascade.step1_baseline_table(df)["age_summary"]
    row = result.iloc[0]
    assert row["n"] == 17
    assert row["median"] == pytest.approx(33.83709787816564, abs=1e-9)
    assert row["q1"] == pytest.approx(30.882956878850102, abs=1e-9)
    assert row["q3"] == pytest.approx(33.83709787816564, abs=1e-9)
    assert not row["suppressed"]


def test_step1_contacts_per_index_case(df):
    """14 of the 18 rows have a non-null `IndexCase`, every one of them
    unique in this fixture -> 14 clusters of size 1 each, so the
    cluster-size median/IQR collapses to 1.0/1.0/1.0 -- a degenerate but
    still structurally correct check (`n_index_cases=14` is the value that
    actually exercises real logic here)."""
    result = cascade.step1_baseline_table(df)["contacts_per_index_case"]
    row = result.iloc[0]
    assert row["n"] == 14
    assert row["median"] == pytest.approx(1.0)
    assert row["q1"] == pytest.approx(1.0)
    assert row["q3"] == pytest.approx(1.0)
    assert not row["suppressed"]


def test_step1_table1_is_tableone_instance(df):
    """Smoke test only -- `TableOne`'s exact `.tableone` shape is not
    independently re-verified here (see cascade.py's own documented
    follow-up on small-cell suppression for `table1`)."""
    from tableone import TableOne

    result = cascade.step1_baseline_table(df)
    assert isinstance(result["table1"], TableOne)


# --- Step 2: screening cascade -------------------------------------------------


def test_step2_whole_cohort(df):
    result = cascade.step2_screening_cascade(df)
    _assert_prop(
        _row_for(result, stage="screened"),
        18, 17, 0.9444444444444444, (0.7424269921812741, 0.990124809021697),
    )
    _assert_prop(
        _row_for(result, stage="suspected_tb"),
        17, 12, 0.7058823529411765, (0.4686688993346016, 0.8672001038970478),
    )
    _assert_prop(
        _row_for(result, stage="diaskintest_positive"),
        17, 13, 0.7647058823529411, (0.5273820188043501, 0.9044495567791988),
    )
    _assert_prop(
        _row_for(result, stage="full_eval"),
        18, 12, 0.6666666666666666, (0.43749467295945105, 0.837212252491663),
    )


def test_step2_by_source_kovrov_appears_as_zero_count(df):
    """Kovrov's `reached_screening`/`reached_full_eval` are definite
    `False`, not `pd.NA` -- so Kovrov shows up as an explicit n=1/count=0
    row, not suppressed (n=1 < 5, so it *should* be suppressed -- see the
    dedicated suppression test below; this test checks the pre-suppression
    semantics by reading `count`/`pct` only where not suppressed)."""
    result = cascade.step2_screening_cascade(df, group_by=["Source"])
    kovrov_screened = _row_for(result, Source="Kovrov", stage="screened")
    vladimir_screened = _row_for(result, Source="Vladimir", stage="screened")
    # Kovrov's n=1 < SMALL_CELL_THRESHOLD=5 -> suppressed (n/count/pct/CI blanked).
    assert kovrov_screened["suppressed"] == True  # noqa: E712
    assert pd.isna(kovrov_screened["n"])
    assert vladimir_screened["suppressed"] == False  # noqa: E712
    _assert_prop(vladimir_screened, 17, 17, 1.0, (0.8156818649911483, 1.0))

    kovrov_full_eval = _row_for(result, Source="Kovrov", stage="full_eval")
    vladimir_full_eval = _row_for(result, Source="Vladimir", stage="full_eval")
    assert kovrov_full_eval["suppressed"] == True  # noqa: E712
    _assert_prop(
        vladimir_full_eval, 17, 12, 0.7058823529411765,
        (0.4686688993346016, 0.8672001038970478),
    )


def test_step2_by_source_kovrov_zero_denominator_when_flag_itself_na(df):
    """`suspected_tb`/`diaskintest_positive` are `pd.NA` for Kovrov/1 (never
    screened), so its `n`/`count` -- computed via `COUNT(*) FILTER (...)`
    over the group -- are both 0 for these stages. Unlike
    `_categorical_distribution` (which filters `category_col IS NOT NULL`
    in the `WHERE` clause *before* `GROUP BY`, so an all-null group never
    appears at all), `_flag_proportion`'s `GROUP BY` runs over every row
    matching `where` regardless of `flag_col`'s nullness -- the FILTER
    aggregates just both come out 0 for an all-null group. So Kovrov
    *does* get a row here (confirmed against real DuckDB output, not the
    sandbox pandas re-implementation this was first drafted against), and
    n=0 < SMALL_CELL_THRESHOLD=5 suppresses it to all-NA -- the same shape
    as the `screened`/`full_eval` stages in the test above."""
    result = cascade.step2_screening_cascade(df, group_by=["Source"])

    suspected = result.loc[result["stage"] == "suspected_tb"]
    assert set(suspected["Source"]) == {"Vladimir", "Kovrov"}
    kovrov_suspected = _row_for(result, Source="Kovrov", stage="suspected_tb")
    assert kovrov_suspected["suppressed"] == True  # noqa: E712
    assert pd.isna(kovrov_suspected["n"])

    diaskin = result.loc[result["stage"] == "diaskintest_positive"]
    assert set(diaskin["Source"]) == {"Vladimir", "Kovrov"}
    kovrov_diaskin = _row_for(result, Source="Kovrov", stage="diaskintest_positive")
    assert kovrov_diaskin["suppressed"] == True  # noqa: E712
    assert pd.isna(kovrov_diaskin["n"])


# --- Step 3: diagnostic outcomes -----------------------------------------------


def test_step3_diagnosis_branch_whole_cohort(df):
    """Among the 12 fully-evaluated records, only Vladimir/10 has an
    ambiguous (`pd.NA`) `diagnosis_branch` (both `ConfirmedDiagnosisTB` and
    `LTI` true) -- excluded from `n`, leaving a single observed category,
    `"lti"`, at 11/11."""
    result = cascade.step3_diagnostic_outcomes(df)
    assert set(result["category"]) == {"lti"}
    row = _row_for(result, category="lti")
    _assert_prop(row, 11, 11, 1.0, (0.7411670330319684, 1.0))


# --- Step 4: LTI preventive-treatment cascade ----------------------------------


def test_step4_cascade_stages(df):
    """`eligible_for_lti_tx=TRUE` covers 12 records; `recommended`/
    `prescribed` (`lti_recommended`/`lti_prescribed`) are non-null for only
    11 of those 12 (Vladimir/10's `lti_recommended` is itself `pd.NA` --
    `PrevTreatmentRec` blank, per `test_derive.py`), while `started`
    (`lti_started`) is non-null for the full 12 -- different stages, same
    `where`, different null patterns, hence different `n`."""
    result = cascade.step4_lti_cascade(df)["cascade"]
    _assert_prop(_row_for(result, stage="recommended"), 11, 11, 1.0, (0.7411670330319684, 1.0))
    _assert_prop(_row_for(result, stage="prescribed"), 11, 11, 1.0, (0.7411670330319684, 1.0))
    _assert_prop(
        _row_for(result, stage="started"), 12, 10, 0.8333333333333334,
        (0.5519691377470266, 0.9530348578161463),
    )


def test_step4_initiation_delay_excludes_missing_start_date(df):
    """10 records have `lti_started=True`, but Vladimir/15's
    `DatePrevTreatmentStart` is itself blank -> `days_full_eval_to_
    treatment_start` is `pd.NA` for that one row, so the median/IQR here is
    over n=9, not 10: eight records (Vladimir/1,5,6,7,8,9,13,14) at exactly
    5 days plus Vladimir/4 at 15 days. Sorted, the middle (5th of 9) value
    is still 5, and both quartiles land on a run of 5s too, so median/q1/q3
    are all 5.0 despite the one 15-day outlier."""
    result = cascade.step4_lti_cascade(df)["initiation_delay"]
    row = result.iloc[0]
    assert row["n"] == 9
    assert row["median"] == pytest.approx(5.0)
    assert row["q1"] == pytest.approx(5.0)
    assert row["q3"] == pytest.approx(5.0)


def test_step4_initiated_within_target(df):
    """Both the 30- and 60-day initiation targets are restricted to
    `lti_started=TRUE` (n=12 eligible by `cascade`'s denominator, but the
    flag itself is non-null for only 9 -- the same Vladimir/15 exclusion as
    `initiation_delay`), and all 9 of those met both targets."""
    result = cascade.step4_lti_cascade(df)["initiated_within_target"]
    for target in (30, 60):
        row = _row_for(result, target_days=target)
        _assert_prop(row, 9, 9, 1.0, (0.7008549515804559, 1.0))


# --- Step 5: regimen description -----------------------------------------------


def test_step5_regimen(df):
    """Among the 10 started records, none are bedaquiline-containing and
    all 10 are moxifloxacin-containing in this fixture."""
    result = cascade.step5_regimen_description(df)
    _assert_prop(
        _row_for(result, regimen="bedaquiline_containing"), 10, 0, 0.0,
        (0.0, 0.2775327998628892),
    )
    _assert_prop(
        _row_for(result, regimen="moxifloxacin_containing"), 10, 10, 1.0,
        (0.7224672001371107, 0.9999999999999999),
    )


# --- Step 6: adherence and completion ------------------------------------------


def test_step6_dose_thresholds(df):
    result = cascade.step6_adherence_completion(df)["dose_threshold"]
    _assert_prop(
        _row_for(result, threshold="reached_50pc"), 10, 9, 0.9,
        (0.5958499732047615, 0.9821237869049271),
    )
    _assert_prop(
        _row_for(result, threshold="reached_100pc"), 10, 8, 0.8,
        (0.49016247153664183, 0.9433178485456247),
    )


def test_step6_adherence_summary(df):
    """`adherence_ratio` (`DosesTaken / SchemaDoses`) among the 10 started
    records: nine rows are exactly 1.0, one (Vladimir/7) is 200/180 > 1, and
    one (Vladimir/14) is 40/180 < 1 -- median collapses to 1.0 regardless."""
    result = cascade.step6_adherence_completion(df)["adherence_summary"]
    row = result.iloc[0]
    assert row["n"] == 10
    assert row["median"] == pytest.approx(1.0)
    assert row["q1"] == pytest.approx(1.0)
    assert row["q3"] == pytest.approx(1.0)


def test_step6_outcome_distribution_excludes_ambiguous_branches(df):
    """Vladimir/8 (not mutually exclusive) and Vladimir/9 (not exhaustive)
    both have `outcome_branch = pd.NA` -- excluded, leaving n=8 (not 10) of
    the started cohort, all `"completed"`."""
    result = cascade.step6_adherence_completion(df)["outcome_distribution"]
    assert set(result["category"]) == {"completed"}
    row = _row_for(result, category="completed")
    _assert_prop(row, 8, 8, 1.0, (0.6755924351161198, 1.0))


# --- Step 7: incentive uptake --------------------------------------------------


def test_step7_uptake(df):
    result = cascade.step7_incentive_uptake(df)["uptake"]
    _assert_prop(_row_for(result, incentive="screening"), 17, 17, 1.0, (0.8156818649911483, 1.0))
    _assert_prop(
        _row_for(result, incentive="dose_50pc"), 10, 10, 1.0,
        (0.7224672001371107, 0.9999999999999999),
    )
    _assert_prop(
        _row_for(result, incentive="dose_100pc"), 10, 10, 1.0,
        (0.7224672001371107, 0.9999999999999999),
    )
    _assert_prop(
        _row_for(result, incentive="one_year"), 12, 10, 0.8333333333333334,
        (0.5519691377470266, 0.9530348578161463),
    )


def test_step7_screening_payment_delay(df):
    """All 17 screened records were paid the next day (`DateSuppScreening`
    - `DateScreening` = 1 day), except Vladimir/2's second (duplicate-Nomer)
    row, whose payment date precedes its screening date (-1 day) -- the
    median/IQR is still 1.0/1.0/1.0 since only one of 17 is an outlier."""
    result = cascade.step7_incentive_uptake(df)["screening_payment_delay"]
    row = result.iloc[0]
    assert row["n"] == 17
    assert row["median"] == pytest.approx(1.0)
    assert row["q1"] == pytest.approx(1.0)
    assert row["q3"] == pytest.approx(1.0)


# --- Step 8: follow-up and final outcomes --------------------------------------


def test_step8_rescreened_and_no_tb_1yr(df):
    result = cascade.step8_followup_outcomes(df, ANALYSIS_DATE)
    _assert_prop(
        result["rescreened_1yr"].iloc[0], 13, 10, 0.7692307692307693,
        (0.49743624053272495, 0.9182047128150143),
    )
    _assert_prop(
        result["no_tb_after_1yr"].iloc[0], 10, 10, 1.0,
        (0.7224672001371107, 0.9999999999999999),
    )


def test_step8_rescreened_and_no_tb_24mo(df):
    """24-month maturity uses a freshly recomputed `censoring_flag(...,
    window_months=24)`, not the persisted (12-month) `censored` column --
    only 10 records are 24-month-mature (vs. 13 at 12 months), and all 10
    were rescreened with no TB."""
    result = cascade.step8_followup_outcomes(df, ANALYSIS_DATE)
    _assert_prop(
        result["rescreened_24mo"].iloc[0], 10, 10, 1.0,
        (0.7224672001371107, 0.9999999999999999),
    )
    _assert_prop(
        result["no_tb_after_24mo"].iloc[0], 10, 10, 1.0,
        (0.7224672001371107, 0.9999999999999999),
    )


def test_step8_final_outcome_distribution(df):
    """Among the 13 1-year-mature records, only 10 have a non-null
    `final_outcome_category` (Vladimir/2 and /11/12 do not) -- 9 `"no_tb"`,
    1 `"unknown"` (Vladimir/9, `FinalOutcome=3`)."""
    result = cascade.step8_followup_outcomes(df, ANALYSIS_DATE)["final_outcome_distribution"]
    _assert_prop(
        _row_for(result, category="no_tb"), 10, 9, 0.9,
        (0.5958499732047615, 0.9821237869049271),
    )
    _assert_prop(
        _row_for(result, category="unknown"), 10, 1, 0.1,
        (0.017876213095072896, 0.4041500267952385),
    )


def test_step8_final_outcome_by_completion(df):
    """Stratified by `completed_or_finished`: the single
    `completed_or_finished=False` record (Vladimir/9) is 100% `"unknown"`
    within its own stratum (n=1, itself small-cell-suppressed); the 9
    `completed_or_finished=True` records are 100% `"no_tb"`."""
    result = cascade.step8_followup_outcomes(df, ANALYSIS_DATE)["final_outcome_by_completion"]
    not_completed = _row_for(result, completed_or_finished=False, category="unknown")
    assert not_completed["suppressed"] == True  # noqa: E712
    completed = _row_for(result, completed_or_finished=True, category="no_tb")
    assert completed["suppressed"] == False  # noqa: E712
    _assert_prop(completed, 9, 9, 1.0, (0.7008549515804559, 1.0))


def test_step8_incidence_rate_zero_events(df):
    """10 records started LTI treatment with a known `DateScreening`;
    `TBdeveloped` is `False` for all 10 in this fixture -> 0 events over
    1953 days (9 records at 196 days + Vladimir/4 at 189) = 5.347022587268993
    person-years, rate 0.0/100py. With 0 events, `_poisson_ci`'s lower bound
    is exactly 0 (no chi-square quantile needed); the upper bound uses
    `chi2.ppf(0.975, 2)`, which has a closed form since chi-square with 2
    degrees of freedom is `Exponential(mean=2)`: `-2*ln(0.025) = 7.3777589...`,
    giving `ci_high = 7.3777589.../2/person_years*100 = 68.98941221787584`."""
    result = cascade.step8_followup_outcomes(df, ANALYSIS_DATE)["incidence_rate"]
    row = result.iloc[0]
    assert row["n"] == 10
    assert row["events"] == 0
    assert row["person_years"] == pytest.approx(5.347022587268993, abs=1e-9)
    assert row["rate_per_100py"] == pytest.approx(0.0)
    assert row["ci_low"] == pytest.approx(0.0)
    assert row["ci_high"] == pytest.approx(68.98941221787584, abs=1e-4)
    assert row["ci_low"] <= row["rate_per_100py"] <= row["ci_high"]


def test_step8_incidence_rate_matches_standalone_function(df):
    """`step8_followup_outcomes`'s `"incidence_rate"` key is exactly
    `step8_incidence_rate`'s own return value -- not a separately
    recomputed approximation."""
    via_followup = cascade.step8_followup_outcomes(df, ANALYSIS_DATE)["incidence_rate"]
    standalone = cascade.step8_incidence_rate(df, ANALYSIS_DATE)
    pd.testing.assert_frame_equal(
        via_followup.reset_index(drop=True), standalone.reset_index(drop=True)
    )


# --- Step 10: site comparison ---------------------------------------------------


def test_step10_returns_all_seven_steps(df):
    result = cascade.step10_site_comparison(df, ANALYSIS_DATE)
    assert set(result.keys()) == {
        "screening_cascade",
        "diagnostic_outcomes",
        "lti_cascade",
        "regimen",
        "adherence_completion",
        "incentive_uptake",
        "followup_outcomes",
    }


def test_step10_composes_step2_with_source_group_by(df):
    """Step 10 does not reimplement any aggregation -- it is exactly
    `step2_screening_cascade(df, group_by=["Source"])` (and so on for every
    other step), so its `screening_cascade` table must be identical to
    calling Step 2 directly with the same `group_by`."""
    via_step10 = cascade.step10_site_comparison(df, ANALYSIS_DATE)["screening_cascade"]
    standalone = cascade.step2_screening_cascade(df, group_by=["Source"])
    pd.testing.assert_frame_equal(
        via_step10.reset_index(drop=True), standalone.reset_index(drop=True)
    )


# --- core helpers, tested directly ----------------------------------------------


def test_wilson_ci_zero_nobs_returns_nan():
    low, high = cascade.wilson_ci(0, 0)
    assert pd.isna(low)
    assert pd.isna(high)


def test_wilson_ci_known_value():
    """10/10 at the 95% Wilson interval -- a simple, well-known case
    cross-checked against the closed-form formula independently of
    `statsmodels`."""
    low, high = cascade.wilson_ci(10, 10)
    assert low == pytest.approx(0.7224672001371107, abs=1e-9)
    assert high == pytest.approx(0.9999999999999999, abs=1e-9)


def test_suppress_small_cells_blanks_below_threshold():
    """Direct unit test of the mandatory last step: a row with n=3 (<5) has
    every value column *and* `n` itself blanked to `pd.NA`, plus a
    `suppressed=True` flag; a row with n=5 (the threshold itself, not below
    it) is left untouched."""
    table = pd.DataFrame(
        {"group": ["a", "b"], "n": [3, 5], "count": [2, 4], "pct": [0.667, 0.8]}
    )
    result = cascade.suppress_small_cells(table, value_cols=["count", "pct"])
    small = result.loc[result["group"] == "a"].iloc[0]
    large = result.loc[result["group"] == "b"].iloc[0]
    assert small["suppressed"] == True  # noqa: E712
    assert pd.isna(small["n"])
    assert pd.isna(small["count"])
    assert pd.isna(small["pct"])
    assert large["suppressed"] == False  # noqa: E712
    assert large["n"] == 5
    assert large["count"] == 4


def test_suppress_small_cells_missing_n_col_raises():
    table = pd.DataFrame({"count": [1, 2]})
    with pytest.raises(KeyError):
        cascade.suppress_small_cells(table)
