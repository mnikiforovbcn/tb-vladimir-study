"""Phase 3 - Derived variables.

Computes the analysis-grade variables that sit on top of the validated raw
table (`schema.validate`'d output of `io.load_raw`) but are not themselves
part of the raw data: age and age band, dose-adherence ratio, cascade time
intervals, one boolean/categorical flag per cascade node (Descriptive Study
Plan Sec 7, Steps 2-8), and a right-censoring flag (Sec 6 item 6, Sec 10).

`build_analysis_table` assembles all of these alongside the raw columns
into a single analysis-ready DataFrame, and `persist_analysis_table` writes
it to `Data/processed/analysis_ready_<run_date>.parquet`. Per the
Implementation Plan, that file is the *only* input Phase 4 (cascade/trend
analytics) is allowed to read -- every derived column downstream traces
back to one auditable place.

Design notes that apply across this module:
- Every function is a pure function of `df`; nothing here mutates its
  input or depends on global state besides the constants defined below.
- Wherever a value can't be computed (a required raw field is missing,
  or -- for ratios/flags built from multiple columns -- the inputs are
  ambiguous), the result is `pd.NA`/`pd.NaT` rather than a guessed value.
  Analysts downstream should be able to tell "not applicable/unknown"
  apart from a real zero or "no".
- Boolean combinations (`|`) are done directly on pandas nullable
  `"boolean"` columns so Kleene three-valued logic applies automatically:
  e.g. `True | NA = True` (eligible, full stop) but `False | NA = NA`
  (still unresolved), which is the behaviour an epidemiologic cascade
  needs and plain Python `or`/`.fillna(False)` would get wrong.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tb_cascade import qc
from tb_cascade.config import PROCESSED_DATA_DIR

# --- age_at_screening ---------------------------------------------------

#: Fixed-width epidemiologic age bands per the Implementation Plan
#: (Phase 3 item 1): 0-14, 15-24, ..., 65+. `pd.cut` bin edges are
#: upper-bound-inclusive, so -inf/inf are used as the outer edges and the
#: interior edges are the band boundaries themselves.
_AGE_BIN_EDGES: list[float] = [-float("inf"), 14, 24, 34, 44, 54, 64, float("inf")]
_AGE_BIN_LABELS: list[str] = [
    "0-14",
    "15-24",
    "25-34",
    "35-44",
    "45-54",
    "55-64",
    "65+",
]


def age_at_screening(df: pd.DataFrame) -> pd.DataFrame:
    """Compute age at screening (years) and its fixed-width band.

    `age_years` = (`DateScreening` - `BirthDate`).days / 365.25, matching
    the formula already used by `qc.check_age_range` (that function is a
    QC range check only; this is the analysis-grade column it points to).

    `age_band` buckets `age_years` into the bands in `_AGE_BIN_LABELS`.
    It is left `pd.NA` when age itself is missing, *and* when age is
    negative (`BirthDate` after `DateScreening` -- already an impossible
    value flagged by `check_age_range`; this function does not invent a
    band for a value it cannot place in any real age group). Implausibly
    *old* ages (e.g. >100, also flagged by `check_age_range`) are still
    banded into "65+" here, since unlike a negative age they are at least
    a coherent (if suspect) age.

    Returns a two-column DataFrame (`age_years`, `age_band`) indexed like
    `df`, ready to be concatenated onto it.
    """
    both_present = df["BirthDate"].notna() & df["DateScreening"].notna()

    age_years = pd.Series(pd.NA, index=df.index, dtype="Float64")
    raw_years = (df["DateScreening"] - df["BirthDate"]).dt.days / 365.25
    age_years.loc[both_present] = raw_years.loc[both_present]

    age_band = pd.Series(pd.NA, index=df.index, dtype="string")
    bandable = both_present & (age_years >= 0)
    bandable = bandable.fillna(False)
    cut = pd.cut(
        age_years.loc[bandable].astype("float64"),
        bins=_AGE_BIN_EDGES,
        labels=_AGE_BIN_LABELS,
        right=True,
    )
    age_band.loc[bandable] = cut.astype("string")

    return pd.DataFrame({"age_years": age_years, "age_band": age_band}, index=df.index)


# --- adherence_ratio ------------------------------------------------------


def adherence_ratio(df: pd.DataFrame) -> pd.Series:
    """Compute the dose-adherence ratio `DosesTaken / SchemaDoses`.

    Guarded against division by zero/null per the Implementation Plan
    (Phase 3 item 2): the ratio is `pd.NA` unless both `DosesTaken` and
    `SchemaDoses` are present and `SchemaDoses` is strictly positive.
    """
    computable = (
        df["SchemaDoses"].notna()
        & (df["SchemaDoses"] > 0).fillna(False)
        & df["DosesTaken"].notna()
    )

    ratio = pd.Series(pd.NA, index=df.index, dtype="Float64", name="adherence_ratio")
    ratio.loc[computable] = (
        df.loc[computable, "DosesTaken"] / df.loc[computable, "SchemaDoses"]
    ).astype("float64")
    return ratio


# --- time_intervals ---------------------------------------------------------

#: Short labels for the dates in `qc.DATE_ORDER_SEQUENCE`, used to name the
#: interval columns below (e.g. `days_full_eval_to_treatment_start`).
_INTERVAL_NODE_LABELS: dict[str, str] = {
    "DateScreening": "screening",
    "DateCompleteExaminationTB": "full_eval",
    "DatePrevTreatmentStart": "treatment_start",
    "DateTreatmentScheme": "treatment_scheme",
    "DateOutcome": "outcome",
}

#: Programmatic initiation-delay targets used for Step 4's target metric
#: (Descriptive Study Plan Sec 7 Step 4: proportion initiated within 30/60
#: days of the diagnostic evaluation that made them eligible).
_INITIATION_TARGET_DAYS: list[int] = [30, 60]


def time_intervals(df: pd.DataFrame) -> pd.DataFrame:
    """Compute cascade time intervals (days) between consecutive milestones.

    One `days_<earlier>_to_<later>` column per consecutive pair in
    `qc.DATE_ORDER_SEQUENCE` -- the same canonical date sequence
    `check_date_order`/`date_order_pair_breakdown` already validate, so
    the interval columns line up exactly with what QC calls a "pair" and
    nothing here can drift out of sync with that ordering.

    This always includes `days_full_eval_to_treatment_start`, the
    diagnosis-to-treatment-start interval the Implementation Plan calls
    out by name (`DatePrevTreatmentStart - DateCompleteExaminationTB`).
    From that interval, `initiated_within_30d` / `initiated_within_60d`
    are derived: `pd.NA` if the interval itself is unavailable, `pd.NA`
    (not `False`) if the interval is negative (a reversed-date QC
    violation -- not a legitimate "missed the target" case), else
    whether the delay was within 30/60 days respectively.

    An interval is only computed where both its endpoint dates are
    present; otherwise it is `pd.NA` (nullable `"Int64"` days).
    """
    columns: dict[str, pd.Series] = {}
    for earlier, later in zip(qc.DATE_ORDER_SEQUENCE[:-1], qc.DATE_ORDER_SEQUENCE[1:]):
        label = f"days_{_INTERVAL_NODE_LABELS[earlier]}_to_{_INTERVAL_NODE_LABELS[later]}"
        both_present = df[earlier].notna() & df[later].notna()
        delta = pd.Series(pd.NA, index=df.index, dtype="Int64")
        delta.loc[both_present] = (
            df.loc[both_present, later] - df.loc[both_present, earlier]
        ).dt.days
        columns[label] = delta

    delay = columns["days_full_eval_to_treatment_start"]
    on_time_computable = delay.notna() & (delay >= 0).fillna(False)
    for target in _INITIATION_TARGET_DAYS:
        flag = pd.Series(pd.NA, index=df.index, dtype="boolean")
        flag.loc[on_time_computable] = (delay.loc[on_time_computable] <= target).to_numpy()
        columns[f"initiated_within_{target}d"] = flag

    return pd.DataFrame(columns, index=df.index)


# --- cascade_flags ------------------------------------------------------------

#: FinalOutcome code -> label, straight from the data dictionary
#: (1=no TB, 2=TB developed, 3=Unknown, 4=Other).
_FINAL_OUTCOME_LABELS: dict[int, str] = {
    1: "no_tb",
    2: "tb_developed",
    3: "unknown",
    4: "other",
}


def _recode(series: pd.Series, mapping: dict) -> pd.Series:
    """Recode a coded column into string labels via `mapping`, keeping
    `pd.NA` for missing values and for any value not present in `mapping`.
    """
    result = pd.Series(pd.NA, index=series.index, dtype="string")
    has_value = series.notna()
    result.loc[has_value] = series.loc[has_value].map(mapping).astype("string")
    return result


def _single_label(df: pd.DataFrame, flag_to_label: dict[str, str]) -> pd.Series:
    """Recode a set of mutually-exclusive 0/1 flag columns into one string
    label per record: the label for whichever flag is the single `True`
    among the group. `pd.NA` if zero or more than one flag is `True` --
    i.e. not applicable / not yet resolved, or an existing
    mutual-exclusivity QC violation (see `qc.check_diagnosis_mutual_exclusivity`
    / `qc.check_outcome_mutual_exclusivity`). This function reports that
    ambiguity as missing rather than guessing which label is "right".
    """
    cols = list(flag_to_label)
    flags_true = df[cols].fillna(False)
    n_true = flags_true.sum(axis=1)

    result = pd.Series(pd.NA, index=df.index, dtype="string")
    for col, label in flag_to_label.items():
        single = (n_true == 1) & flags_true[col]
        result = result.mask(single, label)
    return result


def cascade_flags(df: pd.DataFrame) -> pd.DataFrame:
    """One boolean/categorical column per cascade node, Steps 2-8.

    Per the Implementation Plan (Phase 3 item 4), this turns the
    structural cascade logic already encoded in
    `qc.STRUCTURAL_MISSINGNESS_RULES` into named, analysis-ready columns,
    so cascade tables downstream are plain `groupby().mean()` calls
    instead of repeated boolean logic. Covers every node named in
    Descriptive Study Plan Sec 7 Steps 2-8:

    - Step 2 (screening cascade): `reached_screening`, `reached_suspected`,
      `diaskintest_positive`, `reached_full_eval`.
    - Step 3 (diagnostic outcomes, mutually exclusive among the fully
      evaluated): `confirmed_active_tb`, `has_lti`, `no_tb_no_lti`,
      `no_tb_lti_unknown`, plus `diagnosis_branch` (single label summarizing
      the four).
    - Step 4 (LTI preventive-treatment cascade): `eligible_for_lti_tx`
      (`LTI` or `PrevTreatmentRec`, per the Plan's own eligibility
      definition), `lti_recommended`, `lti_prescribed`, `lti_started`.
    - Step 6 (adherence/completion): `completed_or_finished`
      (`TreatmentCompleted` or `TreatmentFinished`), plus `outcome_branch`
      (single label across the seven mutually exclusive Step 6 outcome
      flags). Step 5 (`RegBq`/`RegMfx`) is a regimen attribute, not a
      progression node, so it is not duplicated here.
    - Step 7 (incentive uptake): `supp_screening_received`,
      `supp_50pc_received`, `supp_100pc_received`, `supp_1yr_received`
      (`Supp1yearGr23` or `Supp1yearGr1`, whichever applies to the
      record's treatment group).
    - Step 8 (follow-up/final outcome): `rescreened_1yr`, `no_tb_after_1yr`,
      `rescreened_24mo`, `no_tb_after_24mo`, plus `final_outcome_category`
      (`FinalOutcome` recoded to a label).

    All boolean columns reuse the raw nullable `"boolean"` flags directly
    (aliased or OR'd via Kleene logic), so a value of `pd.NA` here means
    exactly what it means on the underlying raw column: not yet known or
    not applicable, never a guessed `False`.
    """
    cols: dict[str, pd.Series] = {}

    # Step 2 - screening cascade.
    cols["reached_screening"] = df["Screening"]
    cols["reached_suspected"] = df["SuspectedTB"]
    cols["diaskintest_positive"] = df["DiaskintestPositive"]
    cols["reached_full_eval"] = df["CompleteExaminationTB"]

    # Step 3 - diagnostic branch (mutually exclusive among fully evaluated).
    cols["confirmed_active_tb"] = df["ConfirmedDiagnosisTB"]
    cols["has_lti"] = df["LTI"]
    cols["no_tb_no_lti"] = df["NoTBNoLTI"]
    cols["no_tb_lti_unknown"] = df["NoTBLTIunknown"]
    cols["diagnosis_branch"] = _single_label(
        df,
        {
            "ConfirmedDiagnosisTB": "confirmed_tb",
            "LTI": "lti",
            "NoTBNoLTI": "no_tb_no_lti",
            "NoTBLTIunknown": "no_tb_lti_unknown",
        },
    )

    # Step 4 - LTI preventive-treatment cascade.
    cols["eligible_for_lti_tx"] = df["LTI"] | df["PrevTreatmentRec"]
    cols["lti_recommended"] = df["PrevTreatmentRec"]
    cols["lti_prescribed"] = df["PrevTreatmentPresc"]
    cols["lti_started"] = df["PrevTreatmentStart"]

    # Step 6 - adherence and completion.
    cols["completed_or_finished"] = df["TreatmentCompleted"] | df["TreatmentFinished"]
    cols["outcome_branch"] = _single_label(
        df,
        {
            "TreatmentCompleted": "completed",
            "TreatmentFinished": "finished",
            "TBdeveloped": "tb_developed",
            "TreatmentStopedMed": "stopped_med",
            "TreatmetnNotFinished": "not_finished",
            "TreatmentContinue": "continuing",
            "OutcomeNotKnown": "unknown",
        },
    )

    # Step 7 - incentive payment uptake.
    cols["supp_screening_received"] = df["SuppScreening"]
    cols["supp_50pc_received"] = df["Supp50pc"]
    cols["supp_100pc_received"] = df["Supp100pc"]
    cols["supp_1yr_received"] = df["Supp1yearGr23"] | df["Supp1yearGr1"]

    # Step 8 - follow-up and final outcome.
    cols["rescreened_1yr"] = df["Screening_y"]
    cols["no_tb_after_1yr"] = df["NoTbAfter_y"]
    cols["rescreened_24mo"] = df["Screening_24"]
    cols["no_tb_after_24mo"] = df["NoTbAfter_24"]
    cols["final_outcome_category"] = _recode(df["FinalOutcome"], _FINAL_OUTCOME_LABELS)

    return pd.DataFrame(cols, index=df.index)


# --- censoring_flag -----------------------------------------------------------


def censoring_flag(
    df: pd.DataFrame, analysis_date, window_months: int = 12
) -> pd.Series:
    """Flag records that cannot yet have a mature outcome (right-censoring).

    Per Descriptive Study Plan Sec 6.6/Sec 10: data collection is ongoing,
    so records enrolled close to `analysis_date` have not had the full
    `window_months` (default 12, per the Implementation Plan's signature)
    to reach a final outcome. A record is `True` (censored) if *both*:

    1. `DateScreening` (enrollment) falls within `window_months` of
       `analysis_date` -- i.e. after `analysis_date - window_months`, and
    2. `FinalOutcome` is still missing.

    Condition 2 matters: a record enrolled recently but that already has
    a recorded `FinalOutcome` reached its outcome quickly and is not
    censored, regardless of how close to `analysis_date` it was enrolled.
    This is the standard survival-analysis meaning of "censored" (no
    event observed, not enough follow-up time) rather than a bare
    enrollment-date cutoff, and is what Phase 4's incidence-rate
    calculation (Sec 7 Step 8) needs to exclude/handle correctly.

    `pd.NA` if `DateScreening` itself is missing (enrollment date unknown
    -- cannot assess).
    """
    analysis_ts = pd.Timestamp(analysis_date)
    cutoff = analysis_ts - pd.DateOffset(months=window_months)

    enrollment = df["DateScreening"]
    has_date = enrollment.notna()

    flag = pd.Series(pd.NA, index=df.index, dtype="boolean", name="censored")
    recently_enrolled = enrollment.loc[has_date] > cutoff
    has_outcome = df.loc[has_date, "FinalOutcome"].notna()
    flag.loc[has_date] = (recently_enrolled & ~has_outcome).to_numpy()
    return flag


# --- build_analysis_table / persist_analysis_table ---------------------------


def build_analysis_table(
    df: pd.DataFrame, analysis_date, window_months: int = 12
) -> pd.DataFrame:
    """Assemble the single analysis-ready table (Implementation Plan item 6).

    Concatenates every derived-variable group from this module onto the
    raw columns of `df`: `age_at_screening` (age_years, age_band),
    `adherence_ratio`, `time_intervals`, `cascade_flags`, and
    `censoring_flag` (computed against `analysis_date`/`window_months`).

    This is meant to be the *only* table Phase 4 (cascade/trend analytics)
    reads from -- everything it needs should already be a column here,
    so no analysis code re-derives cascade logic independently.
    """
    age = age_at_screening(df)
    adherence = adherence_ratio(df)
    intervals = time_intervals(df)
    flags = cascade_flags(df)
    censored = censoring_flag(df, analysis_date, window_months=window_months)

    return pd.concat([df, age, adherence, intervals, flags, censored], axis=1)


def persist_analysis_table(df: pd.DataFrame, run_date: str) -> Path:
    """Write an immutable Parquet snapshot of the analysis-ready table.

    The output path is `Data/processed/analysis_ready_<run_date>.parquet`,
    mirroring `io.snapshot`'s naming convention for the raw snapshot.
    Requires `pyarrow` (declared in `pyproject.toml`).
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DATA_DIR / f"analysis_ready_{run_date}.parquet"
    df.to_parquet(out_path, index=False)
    return out_path
