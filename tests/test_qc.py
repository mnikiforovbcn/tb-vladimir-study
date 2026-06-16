"""Phase 2 tests: every QC rule, `run_qc`, `missingness_audit`, and
`render_qc_report`, exercised against the hand-built synthetic fixture.

The fixture (`tests/fixtures/synthetic_rows.csv`) has 18 rows, each
constructed to isolate exactly one scenario:

- Nomer 1: clean, fully completed cascade -- every check should resolve
  to `False` (no violations) wherever applicable.
- Nomer 2 (x2, same Source+Nomer): duplicate registration.
- Nomer 4: reversed dates (`DateCompleteExaminationTB` before `DateScreening`).
- Nomer 5: one-hot sum == 1 but mismatches `TreatGroup`.
- Nomer 6: one-hot sum != 1 (two flags set).
- Nomer 7: `DosesTaken` > `SchemaDoses`.
- Nomer 8: outcome flags not mutually exclusive (sum = 2).
- Nomer 9: outcome flags not exhaustive (sum = 0).
- Nomer 10: diagnosis branches not mutually exclusive (sum = 2).
- Nomer 11: implausible age (negative -- born after screening).
- Nomer 12: implausible age (> 100 years).
- Nomer 13: `Take100pc=True` but `Take50pc=False` (implication violation).
- Nomer 14: `Take50pc=True` but dose ratio < 0.5 (threshold violation).
- Nomer 15: unexplained missingness (`IndexCase`/`RelationWithSource`/
  `DatePrevTreatmentStart` blank despite their upstream flags being True).
- Kovrov/Nomer 1: fully structural missingness (never screened).
- Nomer 17: prescribed but never started treatment.
- Nomer 18: only `DateScreening` populated in the date sequence.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tb_cascade import qc
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
    """Pull the check result for a specific (Source, Nomer) row, by position."""
    mask = (df["Source"] == source) & (df["Nomer"] == nomer)
    assert mask.sum() == 1, f"expected exactly one row for {source}/{nomer}"
    return series.loc[mask].iloc[0]


# --- check_duplicate_registration -------------------------------------


def test_duplicate_registration_flags_both_rows(df):
    result = qc.check_duplicate_registration(df)
    dup_mask = (df["Source"] == "Vladimir") & (df["Nomer"] == 2)
    assert dup_mask.sum() == 2
    assert result.loc[dup_mask].eq(True).all()


def test_duplicate_registration_clean_row_is_false(df):
    result = qc.check_duplicate_registration(df)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712


# --- check_treatgroup_onehot --------------------------------------------


def test_treatgroup_onehot_clean_row_is_false(df):
    result = qc.check_treatgroup_onehot(df)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712


def test_treatgroup_onehot_mismatch_flagged(df):
    result = qc.check_treatgroup_onehot(df)
    assert _result_for(df, "Vladimir", 5, result) == True  # noqa: E712


def test_treatgroup_onehot_sum_not_one_flagged(df):
    result = qc.check_treatgroup_onehot(df)
    assert _result_for(df, "Vladimir", 6, result) == True  # noqa: E712


def test_treatgroup_onehot_not_applicable_when_all_null(df):
    result = qc.check_treatgroup_onehot(df)
    assert pd.isna(_result_for(df, "Vladimir", 11, result))


# --- check_outcome_mutual_exclusivity ------------------------------------


def test_outcome_mutual_exclusivity_clean_row_is_false(df):
    result = qc.check_outcome_mutual_exclusivity(df)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712


def test_outcome_mutual_exclusivity_sum_two_flagged(df):
    result = qc.check_outcome_mutual_exclusivity(df)
    assert _result_for(df, "Vladimir", 8, result) == True  # noqa: E712


def test_outcome_mutual_exclusivity_sum_zero_flagged(df):
    result = qc.check_outcome_mutual_exclusivity(df)
    assert _result_for(df, "Vladimir", 9, result) == True  # noqa: E712


def test_outcome_mutual_exclusivity_not_applicable_if_not_started(df):
    result = qc.check_outcome_mutual_exclusivity(df)
    assert pd.isna(_result_for(df, "Vladimir", 17, result))


# --- check_date_order ----------------------------------------------------


def test_date_order_clean_row_is_false(df):
    result = qc.check_date_order(df)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712


def test_date_order_reversed_dates_flagged(df):
    result = qc.check_date_order(df)
    assert _result_for(df, "Vladimir", 4, result) == True  # noqa: E712


def test_date_order_not_applicable_with_single_date(df):
    result = qc.check_date_order(df)
    assert pd.isna(_result_for(df, "Vladimir", 18, result))


# --- check_doses_taken_le_schema ------------------------------------------


def test_doses_taken_le_schema_clean_row_is_false(df):
    result = qc.check_doses_taken_le_schema(df)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712


def test_doses_taken_exceeds_schema_flagged(df):
    result = qc.check_doses_taken_le_schema(df)
    assert _result_for(df, "Vladimir", 7, result) == True  # noqa: E712


def test_doses_taken_not_applicable_if_not_started(df):
    result = qc.check_doses_taken_le_schema(df)
    assert pd.isna(_result_for(df, "Vladimir", 17, result))


# --- check_dose_threshold_consistency -------------------------------------


def test_dose_threshold_clean_row_is_false(df):
    result = qc.check_dose_threshold_consistency(df)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712


def test_dose_threshold_implication_violation_flagged(df):
    result = qc.check_dose_threshold_consistency(df)
    assert _result_for(df, "Vladimir", 13, result) == True  # noqa: E712


def test_dose_threshold_ratio_violation_flagged(df):
    result = qc.check_dose_threshold_consistency(df)
    assert _result_for(df, "Vladimir", 14, result) == True  # noqa: E712


# --- check_diagnosis_mutual_exclusivity ------------------------------------


def test_diagnosis_mutual_exclusivity_clean_row_is_false(df):
    result = qc.check_diagnosis_mutual_exclusivity(df)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712


def test_diagnosis_mutual_exclusivity_sum_two_flagged(df):
    result = qc.check_diagnosis_mutual_exclusivity(df)
    assert _result_for(df, "Vladimir", 10, result) == True  # noqa: E712


def test_diagnosis_mutual_exclusivity_not_applicable_if_not_examined(df):
    result = qc.check_diagnosis_mutual_exclusivity(df)
    assert pd.isna(_result_for(df, "Vladimir", 11, result))


# --- check_age_range -------------------------------------------------------


def test_age_range_clean_row_is_false(df):
    result = qc.check_age_range(df)
    assert _result_for(df, "Vladimir", 1, result) == False  # noqa: E712


def test_age_range_negative_age_flagged(df):
    result = qc.check_age_range(df)
    assert _result_for(df, "Vladimir", 11, result) == True  # noqa: E712


def test_age_range_over_max_flagged(df):
    result = qc.check_age_range(df)
    assert _result_for(df, "Vladimir", 12, result) == True  # noqa: E712


def test_age_range_not_applicable_without_both_dates(df):
    result = qc.check_age_range(df)
    assert pd.isna(_result_for(df, "Kovrov", 1, result))


# --- run_qc ----------------------------------------------------------------


def test_run_qc_summary_has_one_row_per_check(df):
    result = qc.run_qc(df)
    assert len(result.summary) == len(qc.CHECKS)
    assert set(result.summary["rule"]) == {name for name, _ in qc.CHECKS}


def test_run_qc_summary_counts_match_fixture_design(df):
    result = qc.run_qc(df)
    by_rule = result.summary.set_index("rule")
    assert by_rule.loc["duplicate_registration", "n_violations"] == 2
    assert by_rule.loc["treatgroup_onehot", "n_violations"] == 2
    assert by_rule.loc["outcome_mutual_exclusivity", "n_violations"] == 2
    assert by_rule.loc["date_order", "n_violations"] == 1
    assert by_rule.loc["doses_taken_le_schema", "n_violations"] == 1
    assert by_rule.loc["dose_threshold_consistency", "n_violations"] == 2
    assert by_rule.loc["diagnosis_mutual_exclusivity", "n_violations"] == 1
    assert by_rule.loc["age_range", "n_violations"] == 2


def test_run_qc_flagged_excludes_other_columns(df):
    result = qc.run_qc(df)
    assert list(result.flagged.columns) == ["rule", "Source", "Nomer"]
    assert len(result.flagged) == int(result.summary["n_violations"].sum())


def test_run_qc_flagged_contains_expected_record(df):
    result = qc.run_qc(df)
    hits = result.flagged[
        (result.flagged["rule"] == "date_order")
        & (result.flagged["Source"] == "Vladimir")
        & (result.flagged["Nomer"] == 4)
    ]
    assert len(hits) == 1


# --- missingness_audit -------------------------------------------------------


def test_missingness_audit_has_all_sources_aggregate(df):
    audit = qc.missingness_audit(df)
    assert qc.ALL_SOURCES in audit["source"].unique()
    assert "Vladimir" in audit["source"].unique()
    assert "Kovrov" in audit["source"].unique()


def test_missingness_audit_all_sources_row_count_matches_df(df):
    audit = qc.missingness_audit(df)
    one_col = audit[(audit["column"] == "Nomer") & (audit["source"] == qc.ALL_SOURCES)]
    assert one_col["n_rows"].iloc[0] == len(df)


def test_missingness_audit_kovrov_never_screened_is_structural(df):
    """Kovrov/Nomer 1 never reached screening; DateScreening should be
    classified as structurally missing there, not unexplained."""
    audit = qc.missingness_audit(df)
    row = audit[(audit["column"] == "DateScreening") & (audit["source"] == "Kovrov")].iloc[0]
    assert row["n_null"] == 1
    assert row["n_structural_null"] == 1
    assert row["n_unexplained_null"] == 0


def test_missingness_audit_unexplained_case_detected(df):
    """Nomer 15: PrevTreatmentStart=True but DatePrevTreatmentStart is
    blank -- the precondition holds, so this is unexplained, not structural."""
    audit = qc.missingness_audit(df)
    row = audit[
        (audit["column"] == "DatePrevTreatmentStart") & (audit["source"] == qc.ALL_SOURCES)
    ].iloc[0]
    assert row["n_unexplained_null"] >= 1


def test_missingness_audit_column_without_rule_is_never_structural(df):
    audit = qc.missingness_audit(df)
    rows = audit[(audit["column"] == "Sex") & (audit["source"] == qc.ALL_SOURCES)]
    assert rows["has_structural_rule"].iloc[0] == False  # noqa: E712
    assert rows["n_structural_null"].iloc[0] == 0


# --- render_qc_report --------------------------------------------------------


def test_render_qc_report_writes_file(df, tmp_path):
    result = qc.run_qc(df)
    audit = qc.missingness_audit(df)
    out_path = tmp_path / "qc_report.md"

    returned = qc.render_qc_report(result, audit, out_path)

    assert returned == out_path
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert "# QC Report" in text
    assert "## Internal consistency rules" in text
    assert "## Missingness audit (all sites)" in text
    for name, _ in qc.CHECKS:
        assert name in text


def test_render_qc_report_excludes_linkage_keys(df, tmp_path):
    """Privacy constraint (Descriptive Study Plan Sec 11 / Implementation Plan
    Sec 7): the rendered report must never carry row-level Source_id/Nomer/
    IndexCase values -- only aggregate rule and column names."""
    result = qc.run_qc(df)
    audit = qc.missingness_audit(df)
    out_path = tmp_path / "qc_report.md"
    qc.render_qc_report(result, audit, out_path)

    text = out_path.read_text(encoding="utf-8")
    consistency_section = text.split("## Missingness audit")[0]
    # No individual Nomer/IndexCase values (e.g. the flagged "4" or
    # "IDX0001") should appear as row-level identifiers in the rules
    # section. "IndexCase"/"RelationWithSource" may legiti