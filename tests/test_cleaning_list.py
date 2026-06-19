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

from datetime import date
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
    output (same rows, same columns -- including the dynamic `Поле N`
    value columns -- same sort order)."""
    qc_result = qc.run_qc(df)
    cleaning_df = cleaning_list.build_cleaning_list(df, qc_result)

    paths = cleaning_list.export_cleaning_list(df, tmp_path, qc_result=qc_result)
    vladimir_path = paths["Владимир"]
    sheet = pd.read_excel(vladimir_path, sheet_name="Список")

    value_columns = [c for c in cleaning_df.columns if c.startswith("Поле ")]
    base_columns = ["Регистрационный номер", "Проблема", "Поле(я)"]
    expected = cleaning_df.loc[
        cleaning_df["Площадка"] == "Владимир", base_columns + value_columns
    ].reset_index(drop=True)

    assert list(sheet.columns) == base_columns + value_columns
    pd.testing.assert_frame_equal(sheet[base_columns], expected[base_columns], check_dtype=False)

    # `Поле N` cells mix dates, numbers, and Cyrillic text by design (see
    # `build_cleaning_list`'s docstring). Excel has no concept of a missing
    # string -- a blank cell round-trips through openpyxl as NaN, not ""
    # -- and openpyxl returns a whole date as `datetime`, not the bare
    # `date` `_format_field_value` produces in memory. Comparing each
    # cell's displayed text sidesteps both without re-testing openpyxl's
    # own type conventions; exact value correctness for these columns
    # against the fixture is already covered directly (no Excel round
    # trip involved) by the tests below.
    def displayed(value: object) -> str:
        if pd.isna(value) or value == "":
            return ""
        if hasattr(value, "date") and callable(value.date):
            value = value.date()
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value)

    for col in value_columns:
        actual_texts = [displayed(v) for v in sheet[col]]
        expected_texts = [displayed(v) for v in expected[col]]
        assert actual_texts == expected_texts, f"{col}: mismatch after export round-trip"


# --- Поле N value columns (corrected-data feature) --------------------------


def test_date_order_value_columns_hold_the_actual_reversed_dates(df):
    """Nomer 4 (Vladimir) has `DateScreening` (2019-03-20) after
    `DateCompleteExaminationTB` (2019-03-10) -- a reversed adjacent pair in
    `qc.DATE_ORDER_SEQUENCE`. `Поле(я)` must name exactly those two fields
    and `Поле 1`/`Поле 2` must hold their actual values (as plain dates,
    not timestamps), in the same order."""
    qc_result = qc.run_qc(df)
    cleaning_df = cleaning_list.build_cleaning_list(df, qc_result)

    row = cleaning_df[
        (cleaning_df["Регистрационный номер"] == 4)
        & (cleaning_df["Проблема"] == cleaning_list.QC_RULE_LABELS_RU["date_order"])
    ]
    assert len(row) == 1
    row = row.iloc[0]

    assert row["Поле(я)"] == "Дата скрининга, Дата завершения обследования на ТБ"
    assert row["Поле 1"] == date(2019, 3, 20)
    assert row["Поле 2"] == date(2019, 3, 10)


def test_doses_taken_le_schema_value_columns_hold_the_actual_doses(df):
    """Nomer 7 (Vladimir) has `DosesTaken`=200 > `SchemaDoses`=180.
    `Поле 1`/`Поле 2` must hold those two raw counts unchanged."""
    qc_result = qc.run_qc(df)
    cleaning_df = cleaning_list.build_cleaning_list(df, qc_result)

    row = cleaning_df[
        (cleaning_df["Регистрационный номер"] == 7)
        & (cleaning_df["Проблема"] == cleaning_list.QC_RULE_LABELS_RU["doses_taken_le_schema"])
    ]
    assert len(row) == 1
    row = row.iloc[0]

    assert row["Поле(я)"] == "Принято доз, Доз по схеме лечения"
    assert row["Поле 1"] == 200
    assert row["Поле 2"] == 180


def test_dose_threshold_consistency_value_columns_render_booleans_in_russian(df):
    """Nomer 13 (Vladimir) has `Take100pc`=True but `Take50pc`=False --
    `Take100pc` implies `Take50pc`, so this is a `dose_threshold_
    consistency` violation narrowed to just those two boolean fields.
    Both must render as "Да"/"Нет", not as raw 0/1 or True/False."""
    qc_result = qc.run_qc(df)
    cleaning_df = cleaning_list.build_cleaning_list(df, qc_result)

    row = cleaning_df[
        (cleaning_df["Регистрационный номер"] == 13)
        & (cleaning_df["Проблема"] == cleaning_list.QC_RULE_LABELS_RU["dose_threshold_consistency"])
    ]
    assert len(row) == 1
    row = row.iloc[0]

    assert row["Поле(я)"] == "Принято ≥50% доз, Принято 100% доз"
    assert row["Поле 1"] == "Нет"
    assert row["Поле 2"] == "Да"


def test_value_column_count_equals_widest_violation_field_list(df):
    """The dynamic `Поле N` column count must equal the largest number of
    fields any single rule in this result implicates.
    `outcome_mutual_exclusivity`'s static 7-field `RULE_FIELDS` entry
    (Nomer 8/9 trigger it, per `test_qc.py`'s docstring) is wider than any
    narrowed `date_order`/`dose_threshold_consistency` field list can get
    in this fixture, so it should be the ceiling."""
    qc_result = qc.run_qc(df)
    cleaning_df = cleaning_list.build_cleaning_list(df, qc_result)

    assert "outcome_mutual_exclusivity" in set(qc_result.flagged["rule"])
    expected = len(cleaning_list.RULE_FIELDS["outcome_mutual_exclusivity"])

    value_columns = [c for c in cleaning_df.columns if c.startswith("Поле ")]
    assert value_columns == [f"Поле {i}" for i in range(1, expected + 1)]


def test_short_violation_rows_blank_out_unused_trailing_value_columns(df):
    """A 2-field violation (`doses_taken_le_schema`, Nomer 7) sharing a
    result with a 7-field violation (`outcome_mutual_exclusivity`) must
    have blank cells in `Поле 3` onward, not raise or misalign."""
    qc_result = qc.run_qc(df)
    cleaning_df = cleaning_list.build_cleaning_list(df, qc_result)

    row = cleaning_df[
        (cleaning_df["Регистрационный номер"] == 7)
        & (cleaning_df["Проблема"] == cleaning_list.QC_RULE_LABELS_RU["doses_taken_le_schema"])
    ].iloc[0]

    trailing_columns = [c for c in cleaning_df.columns if c.startswith("Поле ")][2:]
    assert len(trailing_columns) > 0  # otherwise this test isn't exercising anything
    for col in trailing_columns:
        assert row[col] == ""
