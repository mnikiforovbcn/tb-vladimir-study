"""Phase 3 tests: every `derive.py` function, exercised against the same
hand-built synthetic fixture used by `test_qc.py`
(`tests/fixtures/synthetic_rows.csv`, 18 rows -- see that file's module
docstring for the full list of scenarios it isolates).

A few rows are particularly relevant to derive.py's logic (Source/Nomer):

- Vladimir/1: clean, fully completed cascade -- every derived column
  should resolve to a definite, non-`pd.NA` value.
- Vladimir/4: `DateCompleteExaminationTB` before `DateScreening`
  (reversed pair) -- exercises that `time_intervals` computes each
  consecutive pair independently, so a reversal in one pair does not
  poison an unrelated pair later in the sequence.
- Vladimir/8: outcome flags not mutually exclusive (`TreatmentCompleted`
  and `TBdeveloped` both `True`) -- `cascade_flags.outcome_branch` must
  be `pd.NA` (ambiguous), while `completed_or_finished` is still a
  definite `True`.
- Vladimir/9: outcome flags not exhaustive (all seven `False`) --
  `outcome_branch` is `pd.NA`, `completed_or_finished` is a definite
  `False`, and `final_outcome_category` is independently resolved from
  `FinalOutcome` ("unknown", code 3).
- Vladimir/10: diagnosis flags not mutually exclusive
  (`ConfirmedDiagnosisTB` and `LTI` both `True`) -- `diagnosis_branch` is
  `pd.NA`, but `eligible_for_lti_tx` is still a definite `True` via
  Kleene OR (`LTI` alone is enough), even though `PrevTreatmentRec` is
  blank/unknown on this row.
- Vladimir/11: negative age (`BirthDate` after `DateScreening`).
- Vladimir/12: implausible age (>100 years).
- Vladimir/17: prescribed but never started LTI treatment
  (`PrevTreatmentPresc=True`, `PrevTreatmentStart=False`) -- downstream
  completion/interval columns must be `pd.NA`, not guessed.
- Vladimir/18: only `DateScreening` populated in the date sequence.
- Kovrov/1: fully structural missingness (never screened).

Every expected value below was independently computed against this exact
fixture (loaded with `io`'s dtype/parse_dates logic) via a standalone
script before being hard-coded here, rather than hand-traced from the
CSV text -- the latter is error-prone (see the comma-by-comma mistakes
that had to be fixed in `test_qc.py` during Phase 2).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tb_cascade import derive
from tb_cascade.io import DATE_COLUMNS, DTYPE_MAP

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_rows.csv"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    """Load the synthetic fixture with the same dtype/parse_dates logic as `io.load_raw`."""
    frame = pd.read_csv(FIXTURE_PATH, dtype=DTYPE_MAP, parse_dates=DATE_COLUMNS)
    for col in DATE_COLUMNS:
        if not pd.api.types.is_datetime64_any_dtype(frame[col]):
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
    return frame


def _result_for(df: pd.DataFrame, source: str, nomer: int, series: pd.Series):
    """Pull the result for a specific (Source, Nomer) row, by position."""
    mask = (df["Source"] == source) & (df["Nomer"] == nomer)
    assert mask.sum() == 1, f"expected exactly one row for {source}/{nomer}"
    return series.loc[mask].iloc[0]


# --- age_at_screening -----------------------------------------------------


def test_age_clean_row(df):
    """Vladimir/1: BirthDate 1985-03-10, DateScreening 2019-01-10 ->
    (2019-01-10 - 1985-03-10).days / 365.25 = 33.837... years, banded
    25-34."""
    result = derive.age_at_screening(df)
    age_years = _result_for(df, "Vladimir", 1, result["age_years"])
    age_band = _result_for(df, "Vladimir", 1, result["age_band"])
    assert age_years == pytest.approx(33.83709787816564, abs=1e-9)
    assert age_band == "25-34"


def test_age_band_boundary_15_24(df):
    """Vladimir/18: BirthDate 1995-11-11, DateScreening 2019-06-01 ->
    age ~23.55 years, banded 15-24 (a case close to but inside the
    15-24/25-34 boundary)."""
    result = derive.age_at_screening(df)
    age_years = _result_for(df, "Vladimir", 18, result["age_years"])
    age_band = _result_for(df, "Vladimir", 18, result["age_band"])
    assert age_years == pytest.approx(23.55373032169747, abs=1e-9)
    assert age_band == "15-24"


def test_age_band_35_44(df):
    """Vladimir/17: BirthDate 1979-09-09, DateScreening 2019-05-01 ->
    age ~39.64 years, banded 35-44."""
    result = derive.age_at_screening(df)
    age_band = _result_for(df, "Vladimir", 17, result["age_band"])
    assert age_band == "35-44"


def test_age_negative_is_na_band(df):
    """Vladimir/11: BirthDate 2020-01-01 is after DateScreening
    2019-01-01 -> negative age. `age_years` keeps the (negative) raw
    value -- it isn't this function's job to hide what the data says --
    but `age_band` is `pd.NA` since no real age band fits a negative
    age."""
    result = derive.age_at_screening(df)
    age_years = _result_for(df, "Vladimir", 11, result["age_years"])
    age_band = _result_for(df, "Vladimir", 11, result["age_band"])
    assert age_years == pytest.approx(-0.999315537303217, abs=1e-9)
    assert pd.isna(age_band)


def test_age_implausibly_old_still_banded(df):
    """Vladimir/12: BirthDate 1900-01-01 -> age ~119 years. Implausible,
    but still a coherent positive age, so it is banded into "65+" rather
    than suppressed (the implausibility itself is `qc.check_age_range`'s
    job, not this function's)."""
    result = derive.age_at_screening(df)
    age_years = _result_for(df, "Vladimir", 12, result["age_years"])
    age_band = _result_for(df, "Vladimir", 12, result["age_band"])
    assert age_years == pytest.approx(118.99794661190965, abs=1e-9)
    assert age_band == "65+"


def test_age_missing_date_is_na(df):
    """Kovrov/1: `DateScreening` is blank -> both `age_years` and
    `age_band` are `pd.NA` (BirthDate alone isn't enough)."""
    result = derive.age_at_screening(df)
    age_years = _result_for(df, "Kovrov", 1, result["age_years"])
    age_band = _result_for(df, "Kovrov", 1, result["age_band"])
    assert pd.isna(age_years)
    assert pd.isna(age_band)


# --- adherence_ratio --------------------------------------------------------


def test_adherence_ratio_full_dose(df):
    """Vladimir/1: DosesTaken=180, SchemaDoses=180 -> ratio 1.0."""
    result = derive.adherence_ratio(df)
    assert _result_for(df, "Vladimir", 1, result) == pytest.approx(1.0)


def test_adherence_ratio_over_schema(df):
    """Vladimir/7: DosesTaken=200, SchemaDoses=180 -> ratio 200/180,
    i.e. >1 (the ratio itself does not clip or validate -- that is
    `qc.check_dose_threshold_consistency`'s job)."""
    result = derive.adherence_ratio(df)
    assert _result_for(df, "Vladimir", 7, result) == pytest.approx(200 / 180)


def test_adherence_ratio_partial_dose(df):
    """Vladimir/14: DosesTaken=40, SchemaDoses=180 -> ratio 40/180 = 0.2222..."""
    result = derive.adherence_ratio(df)
    assert _result_for(df, "Vladimir", 14, result) == pytest.approx(40 / 180)


def test_adherence_ratio_na_when_doses_missing(df):
    """Vladimir/10: never started treatment -> `DosesTaken`/`SchemaDoses`
    both blank -> ratio `pd.NA`."""
    result = derive.adherence_ratio(df)
    assert pd.isna(_result_for(df, "Vladimir", 10, result))


def test_adherence_ratio_guards_against_zero_schema_doses():
    """Direct guard check (not in the shared fixture, which has no
    `SchemaDoses=0` row): a record with `SchemaDoses=0` must not raise
    `ZeroDivisionError`/produce `inf`, but resolve to `pd.NA`."""
    tiny = pd.DataFrame(
        {
            "DosesTaken": pd.array([5], dtype="Int64"),
            "SchemaDoses": pd.array([0], dtype="Int64"),
        }
    )
    result = derive.adherence_ratio(tiny)
    assert pd.isna(result.iloc[0])


# --- time_intervals ---------------------------------------------------------


def test_time_intervals_clean_row(df):
    """Vladimir/1: DateScreening 2019-01-10, DateCompleteExaminationTB
    2019-01-20, DatePrevTreatmentStart 2019-01-25, DateTreatmentScheme
    2019-01-25, DateOutcome 2019-07-25 -> 10 / 5 / 0 / 181 days, and the
    5-day diagnosis-to-treatment-start delay is within both the 30- and
    60-day initiation targets."""
    result = derive.time_intervals(df)
    row = {col: _result_for(df, "Vladimir", 1, result[col]) for col in result.columns}
    assert row["days_screening_to_full_eval"] == 10
    assert row["days_full_eval_to_treatment_start"] == 5
    assert row["days_treatment_start_to_treatment_scheme"] == 0
    assert row["days_treatment_scheme_to_outcome"] == 181
    assert row["initiated_within_30d"] == True  # noqa: E712
    assert row["initiated_within_60d"] == True  # noqa: E712


def test_time_intervals_reversed_pair_does_not_poison_others(df):
    """Vladimir/4: `DateCompleteExaminationTB` (2019-03-10) is before
    `DateScreening` (2019-03-20) -- a reversed pair, so
    `days_screening_to_full_eval` is negative (-10). The very next pair,
    `days_full_eval_to_treatment_start` (`DatePrevTreatmentStart`
    2019-03-25 minus `DateCompleteExaminationTB` 2019-03-10 = 15 days),
    is computed independently and is unaffected -- and 15 days is still
    within both initiation targets."""
    result = derive.time_intervals(df)
    row = {col: _result_for(df, "Vladimir", 4, result[col]) for col in result.columns}
    assert row["days_screening_to_full_eval"] == -10
    assert row["days_full_eval_to_treatment_start"] == 15
    assert row["initiated_within_30d"] == True  # noqa: E712
    assert row["initiated_within_60d"] == True  # noqa: E712


def test_time_intervals_na_when_later_date_missing(df):
    """Vladimir/17: prescribed but never started (`PrevTreatmentStart=False`,
    `DatePrevTreatmentStart` blank) -> `days_full_eval_to_treatment_start`
    and the 30/60-day flags are all `pd.NA`, while the earlier,
    independently-computable `days_screening_to_full_eval` (9 days) is
    still populated."""
    result = derive.time_intervals(df)
    row = {col: _result_for(df, "Vladimir", 17, result[col]) for col in result.columns}
    assert row["days_screening_to_full_eval"] == 9
    assert pd.isna(row["days_full_eval_to_treatment_start"])
    assert pd.isna(row["initiated_within_30d"])
    assert pd.isna(row["initiated_within_60d"])


def test_time_intervals_all_na_when_never_screened(df):
    """Kovrov/1: never screened -> every interval column is `pd.NA`."""
    result = derive.time_intervals(df)
    row = result.loc[(df["Source"] == "Kovrov") & (df["Nomer"] == 1)].iloc[0]
    assert row.isna().all()


def test_initiation_flag_na_not_false_when_interval_negative():
    """Direct guard check (no fixture row has a reversed
    full-eval-to-treatment-start pair): if `DatePrevTreatmentStart` comes
    *before* `DateCompleteExaminationTB`, the interval is negative -- a
    date-order QC violation, not a legitimate "missed the 30/60-day
    target" -- so `initiated_within_30d`/`60d` must be `pd.NA`, not `False`."""
    tiny = pd.DataFrame(
        {
            "DateScreening": pd.to_datetime(["2019-01-01"]),
            "DateCompleteExaminationTB": pd.to_datetime(["2019-01-20"]),
            "DatePrevTreatmentStart": pd.to_datetime(["2019-01-10"]),
            "DateTreatmentScheme": pd.to_datetime([pd.NaT]),
            "DateOutcome": pd.to_datetime([pd.NaT]),
        }
    )
    result = derive.time_intervals(tiny)
    assert result.loc[0, "days_full_eval_to_treatment_start"] == -10
    assert pd.isna(result.loc[0, "initiated_within_30d"])
    assert pd.isna(result.loc[0, "initiated_within_60d"])


# --- cascade_flags ------------------------------------------------------------


def test_cascade_flags_clean_row_all_resolved(df):
    """Vladimir/1: fully completed cascade -- every flag/branch column
    resolves to a definite (non-`pd.NA`) value."""
    result = derive.cascade_flags(df)
    row = {col: _result_for(df, "Vladimir", 1, result[col]) for col in result.columns}
    assert row["reached_screening"] == True  # noqa: E712
    assert row["reached_full_eval"] == True  # noqa: E712
    assert row["diagnosis_branch"] == "lti"
    assert row["eligible_for_lti_tx"] == True  # noqa: E712
    assert row["lti_started"] == True  # noqa: E712
    assert row["completed_or_finished"] == True  # noqa: E712
    assert row["outcome_branch"] == "completed"
    assert row["supp_1yr_received"] == True  # noqa: E712
    assert row["rescreened_24mo"] == True  # noqa: E712
    assert row["final_outcome_category"] == "no_tb"
    assert not result.loc[(df["Source"] == "Vladimir") & (df["Nomer"] == 1)].isna().any(
        axis=None
    )


def test_cascade_flags_outcome_not_mutually_exclusive_is_na_branch(df):
    """Vladimir/8: `TreatmentCompleted` and `TBdeveloped` both `True`
    (sum=2) -> `outcome_branch` is `pd.NA` (ambiguous), but
    `completed_or_finished` is still a definite `True` -- it only needs
    `TreatmentCompleted` or `TreatmentFinished`, not exclusivity."""
    result = derive.cascade_flags(df)
    row = {col: _result_for(df, "Vladimir", 8, result[col]) for col in result.columns}
    assert pd.isna(row["outcome_branch"])
    assert row["completed_or_finished"] == True  # noqa: E712


def test_cascade_flags_outcome_not_exhaustive_is_na_branch_but_resolved_final(df):
    """Vladimir/9: all seven Step 6 outcome flags `False` (sum=0) ->
    `outcome_branch` is `pd.NA` and `completed_or_finished` is a
    definite `False`. `final_outcome_category` is derived independently
    from `FinalOutcome=3` -> "unknown", so it still resolves even though
    `outcome_branch` cannot."""
    result = derive.cascade_flags(df)
    row = {col: _result_for(df, "Vladimir", 9, result[col]) for col in result.columns}
    assert pd.isna(row["outcome_branch"])
    assert row["completed_or_finished"] == False  # noqa: E712
    assert row["final_outcome_category"] == "unknown"


def test_cascade_flags_diagnosis_not_mutually_exclusive_but_eligible_resolved(df):
    """Vladimir/10: `ConfirmedDiagnosisTB` and `LTI` both `True` (sum=2)
    -> `diagnosis_branch` is `pd.NA`. `PrevTreatmentRec` is blank on this
    row, but `eligible_for_lti_tx` is still a definite `True`: Kleene OR
    means `LTI=True` alone is enough, regardless of the unknown
    `PrevTreatmentRec`."""
    result = derive.cascade_flags(df)
    row = {col: _result_for(df, "Vladimir", 10, result[col]) for col in result.columns}
    assert pd.isna(row["diagnosis_branch"])
    assert row["eligible_for_lti_tx"] == True  # noqa: E712
    assert pd.isna(row["lti_recommended"])  # PrevTreatmentRec itself is blank


def test_cascade_flags_prescribed_not_started(df):
    """Vladimir/17: `PrevTreatmentPresc=True`, `PrevTreatmentStart=False`
    -> `lti_prescribed` True, `lti_started` False (a definite, raw
    value -- not a guess), and `completed_or_finished` is `pd.NA` since
    treatment was never started (`TreatmentCompleted`/`TreatmentFinished`
    are both blank, and `NA | NA = NA` under Kleene logic)."""
    result = derive.cascade_flags(df)
    row = {col: _result_for(df, "Vladimir", 17, result[col]) for col in result.columns}
    assert row["lti_prescribed"] == True  # noqa: E712
    assert row["lti_started"] == False  # noqa: E712
    assert pd.isna(row["completed_or_finished"])


def test_cascade_flags_never_screened(df):
    """Kovrov/1: never screened -- `Screening=False` and
    `CompleteExaminationTB=False` are both explicit raw values, so
    `reached_screening`/`reached_full_eval` are definite `False`, while
    everything gated behind screening (`reached_suspected`, the
    diagnosis flags, `final_outcome_category`, ...) is `pd.NA`."""
    result = derive.cascade_flags(df)
    row = {col: _result_for(df, "Kovrov", 1, result[col]) for col in result.columns}
    assert row["reached_screening"] == False  # noqa: E712
    assert row["reached_full_eval"] == False  # noqa: E712
    assert pd.isna(row["reached_suspected"])
    assert pd.isna(row["diagnosis_branch"])
    assert pd.isna(row["final_outcome_category"])


def test_final_outcome_labels_cover_all_codes():
    """Direct mapping check: codes 2 ("tb_developed") and 4 ("other")
    are not exercised by any fixture row, so verify the full mapping
    table directly against the data dictionary
    (1=no TB, 2=TB developed, 3=Unknown, 4=Other)."""
    assert derive._FINAL_OUTCOME_LABELS == {
        1: "no_tb",
        2: "tb_developed",
        3: "unknown",
        4: "other",
    }


# --- censoring_flag -----------------------------------------------------------


def test_censoring_flag_mature_with_outcome_not_censored(df):
    """Vladimir/1: DateScreening 2019-01-10, well before the cutoff
    (analysis_date 2020-02-01, window 12 months -> cutoff 2019-02-01),
    and `FinalOutcome` is present -> not censored."""
    result = derive.censoring_flag(df, "2020-02-01", window_months=12)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712


def test_censoring_flag_recent_enrollment_no_outcome_is_censored(df):
    """Vladimir/10: DateScreening 2019-04-01, after the cutoff
    (2019-02-01), and `FinalOutcome` is blank -> censored (not enough
    follow-up time yet to have reached an outcome)."""
    result = derive.censoring_flag(df, "2020-02-01", window_months=12)
    assert _result_for(df, "Vladimir", 10, result) == True  # noqa: E712


def test_censoring_flag_recent_enrollment_but_resolved_not_censored(df):
    """Vladimir/4: DateScreening 2019-03-20, after the cutoff
    (2019-02-01) -- so recently enrolled -- but `FinalOutcome` is
    already present (1) -> the outcome was reached quickly, so this
    record is not censored despite the recent enrollment. This is the
    reason `censoring_flag` checks `FinalOutcome` and not just the
    enrollment-date cutoff."""
    result = derive.censoring_flag(df, "2020-02-01", window_months=12)
    assert _result_for(df, "Vladimir", 4, result) == False  # noqa: E712


def test_censoring_flag_missing_enrollment_date_is_na(df):
    """Kovrov/1: `DateScreening` itself is blank -> `pd.NA` (cannot
    assess), regardless of `analysis_date`/`window_months`."""
    result = derive.censoring_flag(df, "2020-02-01", window_months=12)
    assert pd.isna(_result_for(df, "Kovrov", 1, result))


def test_censoring_flag_window_months_shifts_cutoff(df):
    """Same enrollment dates as above, but a narrower 2-month window with
    an earlier analysis_date (2019-04-15 -> cutoff 2019-02-15) flips
    which records count as "recent": Vladimir/1 (2019-01-10) is still
    before the cutoff (not censored), but Vladimir/10 (2019-04-01, no
    outcome) is after it (censored) -- confirming `window_months` is
    actually used, not a no-op."""
    result = derive.censoring_flag(df, "2019-04-15", window_months=2)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712
    assert _result_for(df, "Vladimir", 10, result) == True  # noqa: E712


# --- build_analysis_table / persist_analysis_table ---------------------------


def test_build_analysis_table_shape_and_no_duplicate_columns(df):
    """The assembled table has the original 62 raw columns plus every
    derived column (2 age + 1 adherence + 6 interval + 24 cascade-flag +
    1 censoring = 34), with no name collisions between raw and derived
    columns."""
    table = derive.build_analysis_table(df, "2020-02-01")
    assert table.shape == (len(df), len(df.columns) + 34)
    assert not table.columns.duplicated().any()


def test_build_analysis_table_preserves_row_count_and_alignment(df):
    """Spot-check that a derived value lands on the correct row after
    concatenation (i.e. nothing got reindexed/shuffled)."""
    table = derive.build_analysis_table(df, "2020-02-01")
    row = table.loc[(table["Source"] == "Vladimir") & (table["Nomer"] == 1)].iloc[0]
    assert row["age_band"] == "25-34"
    assert row["reached_screening"] == True  # noqa: E712
    assert row["adherence_ratio"] == pytest.approx(1.0)


def test_persist_analysis_table_writes_parquet(tmp_path, df, monkeypatch):
    """`persist_analysis_table` writes to
    `Data/processed/analysis_ready_<run_date>.parquet` (mirroring
    `io.snapshot`'s naming) and the file round-trips correctly."""
    monkeypatch.setattr(derive, "PROCESSED_DATA_DIR", tmp_path)
    table = derive.build_analysis_table(df, "2020-02-01")
    out_path = derive.persist_analysis_table(table, "2026-06-17")
    assert out_path == tmp_path / "analysis_ready_2026-06-17.parquet"
    assert out_path.exists()
    round_tripped = pd.read_parquet(out_path)
    assert len(round_tripped) == len(table)
