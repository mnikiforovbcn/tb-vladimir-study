"""Phase 8 tests: `cleaning_list.py`'s `RULE_FIELDS` mapping,
`build_cleaning_list`, and `export_cleaning_list`, exercised against the
same synthetic fixture used by `test_qc.py` (see that module's docstring
for what each of its 18 rows isolates).

Four things this file must establish, per Implementation Plan Phase 8
item 8:

1. Every `qc.CHECKS` rule has a `RULE_FIELDS` entry (parametrized over
   `qc.CHECKS` itself, so a new rule added to `qc.py` without a matching
   entry here fails loudly instead of silently falling back to the raw
   English rule name in a workbook).
2. Every triggered rule and field resolves to a Russian label -- none
   falling back to raw English -- both statically (every `RULE_FIELDS`
   column has a `FIELD_LABELS_RU` entry) and dynamically (no fallback
   actually fires against the real fixture's flagged records).
3. A record violating multiple rules produces one row per rule, not one
   collapsed row. The fixture's 18 rows are each deliberately
   single-violation by design (see `test_qc.py`'s docstring), so this
   needs one synthetic multi-violation record built specifically for
   this test, layered on top of the fixture's already-clean Nomer 1 row.
4. Per-site row counts in `build_cleaning_list`'s output reconcile
   exactly with `qc.run_qc_by_site`'s own per-site violation counts --
   i.e. repackaging into Russian/per-site form never drops or duplicates
   a (rule, record) violation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tb_cascade import cleaning_list, qc
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


# --- RULE_FIELDS coverage (item 1 + static half of item 2) -----------------


@pytest.mark.parametrize("rule_name", [name for name, _ in qc.CHECKS])
def test_every_check_has_rule_fields_entry(rule_name):
    """Every `qc.CHECKS` rule must have a non-empty `RULE_FIELDS` entry."""
    assert rule_name in cleaning_list.RULE_FIELDS
    assert len(cleaning_list.RULE_FIELDS[rule_name]) > 0


@pytest.mark.parametrize("rule_name", [name for name, _ in qc.CHECKS])
def test_every_check_has_a_qc_rule_label(rule_name):
    """Every `qc.CHECKS` rule must resolve to a Russian `Проблема` label."""
    assert rule_name in cleaning_list.QC_RULE_LABELS_RU


def test_qc_rule_labels_cover_exactly_the_checks_registry():
    """No stale labels left behind, and nothing missing either -- the key
    sets should match exactly."""
    assert set(cleaning_list.QC_RULE_LABELS_RU) == {name for name, _ in qc.CHECKS}


@pytest.mark.parametrize("rule_name", [name for name, _ in qc.CHECKS])
def test_every_rule_field_has_a_field_label(rule_name):
    """Every column `RULE_FIELDS` lists for a rule must have a
    `FIELD_LABELS_RU` entry, so `_fields_ru`'s `.get(col, col)` fallback
    never actually fires for a known rule/field combination."""
    for col in cleaning_list.RULE_FIELDS[rule_name]:
        assert col in cleaning_list.FIELD_LABELS_RU, (
            f"{rule_name!r} references column {col!r} with no FIELD_LABELS_RU entry"
        )


def test_site_labels_cover_fixture_sites(df):
    """Every `Source` value actually present in the fixture must resolve
    to a Russian site name (the fixture only has Vladimir/Kovrov, but
    `SITE_LABELS_RU` is expected to cover all three real sites)."""
    for source in df["Source"].dropna().unique():
        assert source in cleaning_list.SITE_LABELS_RU


# --- Dynamic no-fallback check against the real fixture (item 2) -----------


def test_build_cleaning_list_never_falls_back_to_raw_english(df):
    """Every `Проблема`/`Площадка` value in the real fixture's cleaning
    list must be a known Russian label -- i.e. `.map(...).fillna` in
    `build_cleaning_list` never actually had to fall back to the raw
    `rule`/`Source` value -- and no raw (English) column name from
    `RULE_FIELDS` leaks into any `Поле(я)` cell, i.e. `_fields_ru`'s
    `.get(col, col)` never had to fall back either.

    Checking for substring leakage rather than splitting `Поле(я)` cells
    on ", " and comparing tokens against `FIELD_LABELS_RU.values()`:
    several Russian field labels themselves contain an internal ", "
    (e.g. the `LTI`/`NoTBNoLTI` diagnosis labels), which would make a
    naive token-by-token comparison fail on correctly-translated output.
    Raw column names are plain ASCII identifiers (`DosesTaken`,
    `BirthDate`, ...) that cannot otherwise appear inside Cyrillic label
    text, so a substring check is unambiguous here.
    """
    qc_result = qc.run_qc(df)
    cleaning_df = cleaning_list.build_cleaning_list(df, qc_result)
    assert len(cleaning_df) > 0  # the fixture has several deliberate violations

    valid_problems = set(cleaning_list.QC_RULE_LABELS_RU.values())
    valid_sites = set(cleaning_list.SITE_LABELS_RU.values())

    assert set(cleaning_df["Проблема"]) <= valid_problems
    assert set(cleaning_df["Площадка"]) <= valid_sites

    all_fields_text = " | ".join(cleaning_df["Поле(я)"])
    raw_columns = {col for cols in cleaning_list.RULE_FIELDS.values() for col in cols}
    for col in raw_columns:
        assert col not in all_fields_text, f"raw column name {col!r} leaked into Поле(я)"


# --- Multi-rule-violation record -> one row per rule (item 3) --------------


@pytest.fixture
def df_with_multi_violation_record(df) -> pd.DataFrame:
    """The fixture's own rows are each single-violation by design (see
    `test_qc.py`'s docstring), so this builds one extra record -- a copy
    of the clean Vladimir/Nomer 1 baseline (which passes every applicable
    check) -- and breaks it in exactly two independent, unrelated ways:
    an implausible age (`age_range`) and a `TreatGroup_01/02/03` one-hot
    sum of 2 instead of 1 (`treatgroup_onehot`). Everything else about
    the row stays clean, so exactly these two rules -- and no others --
    should fire for it.
    """
    baseline = df[(df["Source"] == "Vladimir") & (df["Nomer"] == 1)].copy()
    assert len(baseline) == 1
    extra = baseline.copy()
    extra["Nomer"] = 9001

    # Break age_range: implausible age (> 100 years at screening).
    extra["BirthDate"] = pd.Timestamp("1900-01-01")

    # Break treatgroup_onehot: the clean baseline row already has
    # TreatGroup=2/TreatGroup_02=True; also setting TreatGroup_01=True
    # makes the one-hot sum 2 instead of 1.
    extra["TreatGroup_01"] = True

    return pd.concat([df, extra], ignore_index=True)


def test_multi_violation_record_produces_one_row_per_rule(df_with_multi_violation_record):
    extended = df_with_multi_violation_record
    qc_result = qc.run_qc(extended)

    flagged_for_record = qc_result.flagged[
        (qc_result.flagged["Source"] == "Vladimir") & (qc_result.flagged["Nomer"] == 9001)
    ]
    assert set(flagged_for_record["rule"]) == {"age_range", "treatgroup_onehot"}

    cleaning_df = cleaning_list.build_cleaning_list(extended, qc_result)
    rows_for_record = cleaning_df[cleaning_df["Регистрационный номер"] == 9001]

    assert len(rows_for_record) == 2
    assert set(rows_for_record["Проблема"]) == {
        cleaning_list.QC_RULE_LABELS_RU["age_range"],
        cleaning_list.QC_RULE_LABELS_RU["treatgroup_onehot"],
    }
    # Every row for this record is still tagged to the right site.
    assert (rows_for_record["Площадка"] == "Владимир").all()


# --- Per-site row counts reconcile with run_qc_by_site (item 4) ------------


def test_per_site_row_counts_reconcile_with_run_qc_by_site(df):
    """Summed across rules, `run_qc_by_site`'s per-site `n_violations`
    must equal `build_cleaning_list`'s per-site row count exactly --
    repackaging into Russian/per-site form must never drop or duplicate
    a single (rule, record) violation."""
    qc_result = qc.run_qc(df)
    cleaning_df = cleaning_list.build_cleaning_list(df, qc_result)
    by_site = qc.run_qc_by_site(df)

    for source in df["Source"].dropna().unique():
        expected = int(by_site.loc[by_site["source"] == source, "n_violations"].sum())
        site_label = cleaning_list.SITE_LABELS_RU[source]
        actual = int((cleaning_df["Площадка"] == site_label).sum())
        assert actual == expected, f"{source}: expected {expected} rows, got {actual}"

    # And the grand total matches len(qc_result.flagged) exactly (no rows
    # silently dropped for a site with no SITE_LABELS_RU entry, etc.).
    assert len(cleaning_df) == len(qc_result.flagged)


def test_build_cleaning_list_empty_when_no_violations():
    """A DataFrame whose `qc.run_qc` finds nothing should produce a
    zero-row (but correctly-columned) cleaning list, not raise."""
    empty_result = qc.QCResult(
        summary=pd.DataFrame(columns=["rule", "n_checked", "n_violations", "violation_rate"]),
        flagged=pd.DataFrame(columns=["rule", "Source", "Nomer"]),
    )
    cleaning_df = cleaning_list.build_cleaning_list(pd.DataFrame(), empty_result)
    assert list(cleaning_df.columns) == ["Площадка", "Регистрационный номер", "Проблема", "Поле(я)"]
    assert len(cleaning_df) == 0


# --- export_cleaning_list ----------------------------------------------------


def test_export_cleaning_list_writes_one_workbook_per_site(df, tmp_path):
    paths = cleaning_list.export_cleaning_list(df, tmp_path)
    expected_sites = {cleaning_list.SITE_LABELS_RU[s] for s in df["Source"].dropna().unique()}
    assert set(paths) == expected_sites
    for path in paths.values():
        assert path.exists()
        assert path.suffix == ".xlsx"


def test_export_cleaning_list_sheet_contents_match_build_cleaning_list(df, tmp_path):
    """Round-trip one site's workbook back through `openpyxl`/pandas and
    confirm it matches the corresponding slice of `build_cleaning_list`'s
    output (same rows, same columns, same sort order)."""
    qc_result = qc.run_qc(df)
    cleaning_df = cleaning_list.build_cleaning_list(df, qc_result)

    paths = cleaning_list.export_cleaning_list(df, tmp_path, qc_result=qc_result)
    vladimir_path = paths["Владимир"]

    sheet = pd.read_excel(vladimir_path, sheet_name="Список")
    expected = cleaning_df.loc[
        cleaning_df["Площадка"] == "Владимир",
        ["Регистрационный номер", "Проблема", "Поле(я)"],
    ].reset_index(drop=True)

    pd.testing.assert_frame_equal(sheet, expected, check_dtype=False)
