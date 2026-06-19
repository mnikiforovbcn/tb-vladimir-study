"""Phase 8 - Data cleaning list.

Repackages `qc.run_qc(df)`'s record-level flagged table into a per-site,
Russian-language list a local data manager can act on directly: for
every QC rule violation, which patient (`Nomer`), which field(s) caused
it, and -- via the `Поле 1`, `Поле 2`, ... columns -- what those
field(s) currently contain, so the data manager sees the actual value
to correct, not just its name. This module does not re-implement or
duplicate any `qc.py` rule logic -- `qc.CHECKS` stays the single source
of truth for *whether* a record violates a rule; this module only
answers *which field(s)* are implicated and *what they currently hold*,
for display, and only ever reads `qc.run_qc`'s output plus the raw `df`
it was computed from.

Two rules need a small per-record helper rather than a static
`RULE_FIELDS` lookup, since `qc.py` only exposes an aggregate breakdown
for them: `date_order` (`qc.check_date_order` collapses four adjacent
date-pair comparisons into one boolean; `_date_order_record_fields`
recomputes those same per-pair comparisons -- the same
`both_present`/`reversed_pair` expressions `qc.check_date_order` and
`qc.date_order_pair_breakdown` already each compute independently --
just keeping the column names instead of collapsing them) and
`dose_threshold_consistency` (`qc.check_dose_threshold_consistency` has
three independent sub-checks that can each fire on their own;
`_dose_threshold_record_fields` recomputes the same three sub-check
expressions to narrow the field list to whichever actually fired).

Privacy (Implementation Plan Sec 7, Phase 8 item 6): unlike every other
pipeline output, this list is *deliberately* record-level and carries
`Nomer` -- an explicit, documented exception to the "linkage keys never
appear in any rendered report" rule, justified because the recipient is
the local data manager who already holds the underlying patient records.
`export_cleaning_list` writes only to `reports/<run_date>/data_cleaning/`
(covered by the existing `reports/*` `.gitignore` rule) -- callers must
never copy this output to `report/` or any other tracked/shared path.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd

from tb_cascade import qc
from tb_cascade.config import ROOT_DIR
from tb_cascade.io import BOOLEAN_COLUMNS, DATE_COLUMNS


def _load_i18n_labels() -> ModuleType:
    """Load `report/i18n_labels.py` directly by file path.

    `report/` has no `__init__.py` -- it is not a package -- so this
    cannot be a normal `import` statement. `report/i18n_ru.py` (the
    descriptive report's presentation layer) is importable as a bare
    module only because Quarto/Jupyter sets the `.qmd`'s own directory
    as kernel cwd; that trick doesn't apply here, since this module runs
    under `cli.py` (cwd = repo root) or pytest. Loading by path avoids
    both relying on cwd and mutating `sys.path` globally.
    """
    path = ROOT_DIR / "report" / "i18n_labels.py"
    spec = importlib.util.spec_from_file_location("i18n_labels", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Could not load i18n_labels.py from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_i18n_labels = _load_i18n_labels()
QC_RULE_LABELS_RU: dict[str, str] = _i18n_labels.QC_RULE_LABELS_RU
SITE_LABELS_RU: dict[str, str] = _i18n_labels.SITE_LABELS_RU
FIELD_LABELS_RU: dict[str, str] = _i18n_labels.FIELD_LABELS_RU


#: Static field(s) each `qc.CHECKS` rule implicates, read directly off
#: each `check_*` function's own columns. `date_order` and
#: `dose_threshold_consistency` are handled per-record instead (see
#: `_date_order_record_fields` / `_dose_threshold_record_fields` below);
#: their entries here are the fallback used only if a flagged (Source,
#: Nomer) can't be found in `df` (so `build_cleaning_list` always has
#: *something* to show rather than raising).
RULE_FIELDS: dict[str, list[str]] = {
    "duplicate_registration": ["Source", "Nomer"],
    "treatgroup_onehot": ["TreatGroup", "TreatGroup_01", "TreatGroup_02", "TreatGroup_03"],
    "outcome_mutual_exclusivity": [
        "TreatmentCompleted",
        "TreatmentFinished",
        "TBdeveloped",
        "TreatmentStopedMed",
        "TreatmetnNotFinished",
        "TreatmentContinue",
        "OutcomeNotKnown",
    ],
    "date_order": list(qc.DATE_ORDER_SEQUENCE),
    "doses_taken_le_schema": ["DosesTaken", "SchemaDoses"],
    "dose_threshold_consistency": ["Take50pc", "Take100pc", "DosesTaken", "SchemaDoses"],
    "diagnosis_mutual_exclusivity": [
        "ConfirmedDiagnosisTB",
        "LTI",
        "NoTBNoLTI",
        "NoTBLTIunknown",
    ],
    "age_range": ["BirthDate", "DateScreening"],
}


def _date_order_record_fields(df: pd.DataFrame) -> dict[tuple, list[str]]:
    """Per-(Source, Nomer) list of the specific `qc.DATE_ORDER_SEQUENCE`
    columns involved in a reversed adjacent pair.

    Mirrors `qc.check_date_order`'s pairwise comparison exactly (the same
    expression `qc.date_order_pair_breakdown` also recomputes
    independently, rather than `check_date_order` exposing it), just
    keeping each pair's column names instead of collapsing every pair
    into one rule-level boolean.
    """
    sequence = qc.DATE_ORDER_SEQUENCE
    pair_hits = []
    for earlier, later in zip(sequence[:-1], sequence[1:]):
        both_present = df[earlier].notna() & df[later].notna()
        reversed_pair = both_present & (df[earlier] > df[later])
        pair_hits.append((earlier, later, reversed_pair))

    result: dict[tuple, list[str]] = {}
    for idx in df.index:
        cols: list[str] = []
        for earlier, later, reversed_pair in pair_hits:
            if bool(reversed_pair.loc[idx]):
                cols.extend([earlier, later])
        if cols:
            key = (df.at[idx, "Source"], df.at[idx, "Nomer"])
            result[key] = list(dict.fromkeys(cols))  # de-dup, preserve order
    return result


def _dose_threshold_record_fields(df: pd.DataFrame) -> dict[tuple, list[str]]:
    """Per-(Source, Nomer) narrowed field list for
    `dose_threshold_consistency`, mirroring `qc.check_dose_threshold_
    consistency`'s three independent sub-checks exactly, so the field
    list only includes the sub-check(s) that actually fired for that
    record rather than always all four columns.
    """
    ratio_computable = (
        df["SchemaDoses"].notna() & (df["SchemaDoses"] > 0) & df["DosesTaken"].notna()
    )
    ratio = (df["DosesTaken"] / df["SchemaDoses"]).where(ratio_computable)

    take100_true = (df["Take100pc"] == True).fillna(False)  # noqa: E712
    take50_true = (df["Take50pc"] == True).fillna(False)  # noqa: E712
    take50_false = (df["Take50pc"] == False).fillna(False)  # noqa: E712

    violates_implication = take100_true & take50_false
    violates_100pc_ratio = take100_true & ratio_computable & (
        df["DosesTaken"] != df["SchemaDoses"]
    )
    violates_50pc_ratio = take50_true & ratio_computable & (ratio < 0.5)

    result: dict[tuple, list[str]] = {}
    for idx in df.index:
        cols: list[str] = []
        if bool(violates_implication.loc[idx]):
            cols.extend(["Take50pc", "Take100pc"])
        if bool(violates_100pc_ratio.loc[idx]):
            cols.extend(["Take100pc", "DosesTaken", "SchemaDoses"])
        if bool(violates_50pc_ratio.loc[idx]):
            cols.extend(["Take50pc", "DosesTaken", "SchemaDoses"])
        if cols:
            key = (df.at[idx, "Source"], df.at[idx, "Nomer"])
            result[key] = list(dict.fromkeys(cols))
    return result


def _fields_ru(fields: list[str]) -> str:
    """Comma-joined Russian label(s) for a list of raw column names. Every
    name in `RULE_FIELDS`/the two per-record helpers above has a
    `FIELD_LABELS_RU` entry (enforced by `tests/test_cleaning_list.py`),
    so `.get(col, col)`'s fallback should never actually fire in
    practice -- it exists only so a future rule added to `qc.py` without
    a matching label fails loudly as a wrong-looking English string in
    the workbook, rather than raising and blocking the whole export.
    """
    return ", ".join(FIELD_LABELS_RU.get(col, col) for col in fields)


#: Raw column names formatted specially by `_format_field_value` below,
#: read directly off `io.py`'s own categorization rather than duplicated
#: here, so a future dtype change to either list is picked up for free.
_BOOLEAN_FIELDS = set(BOOLEAN_COLUMNS)
_DATE_FIELDS = set(DATE_COLUMNS)


def _format_field_value(column: str, value: object) -> object:
    """Render one raw `df` cell for display in a `Поле N` column.

    A local data manager works in Excel, not pandas, so the raw dtype a
    value happens to be stored as is translated into something they can
    read directly: `Source` is translated via `SITE_LABELS_RU` (matching
    `Площадка`'s own translation, rather than showing the English site
    name a second time); every `io.BOOLEAN_COLUMNS` flag becomes "Да"/
    "Нет" (a bare 0/1 or True/False means nothing on its own in a
    Russian-language sheet); every `io.DATE_COLUMNS` field is narrowed
    from `datetime64[ns]` to a plain date (every `Date*` column in this
    dataset is date-only -- the time-of-day component is always midnight
    and would just be visual noise in Excel). Everything else (raw
    codes, counts, `Nomer` itself) passes through unchanged. Missing
    (`pd.isna`) becomes a blank cell in every case.
    """
    if pd.isna(value):
        return ""
    if column == "Source":
        return SITE_LABELS_RU.get(value, value)
    if column in _BOOLEAN_FIELDS:
        return "Да" if bool(value) else "Нет"
    if column in _DATE_FIELDS:
        return value.date() if hasattr(value, "date") else value
    return value


def _build_row_lookup(df: pd.DataFrame) -> pd.DataFrame:
    """`df` indexed by (`Source`, `Nomer`), one row per key, for O(1)
    field-value lookups in `build_cleaning_list`.

    `drop=False`: `duplicate_registration`'s own `RULE_FIELDS` entry is
    `["Source", "Nomer"]` -- the two columns being set as the index here
    -- so a lookup row must still expose them as ordinary columns too,
    or `_values_for` raises `KeyError` looking up the very fields that
    rule cares about.

    A genuine `duplicate_registration` violation means more than one
    `df` row shares a key; keeping only the first occurrence is a
    pre-existing limitation of keying by (`Source`, `Nomer`) at all (see
    this module's docstring -- `cli.py`'s `flagged_records.csv` join has
    the same property), not one introduced by adding value columns.
    """
    first_occurrence = ~df.duplicated(subset=["Source", "Nomer"], keep="first")
    return df.loc[first_occurrence].set_index(["Source", "Nomer"], drop=False)


def _values_for(record: pd.Series | None, fields: list[str]) -> list[object]:
    """Formatted values of `fields` from one `df` row -- the data behind
    `Поле 1`, `Поле 2`, ... in the same order as `_fields_ru(fields)`'s
    labels. `record` is `None` only if the (`Source`, `Nomer`) key isn't
    in `_build_row_lookup`'s result, which should not happen in practice
    since every flagged record came from this same `df` -- defensive
    only, so a lookup gap shows blank cells rather than raising.
    """
    if record is None:
        return ["" for _ in fields]
    return [_format_field_value(field, record[field]) for field in fields]


def build_cleaning_list(df: pd.DataFrame, qc_result: qc.QCResult) -> pd.DataFrame:
    """One row per (record, violated rule), ready for Russian display.

    Columns: ``Площадка`` (Russian site name), ``Регистрационный номер``
    (`Nomer`), ``Проблема`` (Russian rule label), ``Поле(я)`` (Russian
    field label(s), comma-joined), then ``Поле 1``, ``Поле 2``, ... --
    the actual current value of each field named in ``Поле(я)``, in the
    same order, formatted for display (see `_format_field_value`). A
    record violating multiple rules gets one row per rule, not one
    collapsed row, so every row is a single, actionable cause. Sorted by
    site, then rule, then `Nomer` -- `export_cleaning_list` slices this
    by site, so each site's sheet comes out already sorted by
    ``Проблема`` then ``Регистрационный номер`` for free.

    The number of ``Поле N`` columns is the largest number of fields any
    single violation in this result implicates (e.g.
    `outcome_mutual_exclusivity`'s 7 flags is normally the ceiling);
    rows needing fewer are blank in the unused trailing columns. The
    same columns are reused across every rule rather than each rule
    getting its own named value columns, so a sheet sorted by
    ``Проблема`` still reads as one consistent table.

    Joins `qc_result.flagged` back to `df` by (`Source`, `Nomer`) to
    recover the per-record field detail for `date_order` and
    `dose_threshold_consistency`, and the field values themselves for
    every rule -- the same join key `cli.py` already uses to rebuild
    `flagged_records.csv`. As with that existing join, a genuine
    duplicate (`Source`, `Nomer`) pair (itself a `duplicate_registration`
    violation) means those rows share one lookup entry; this is a
    pre-existing limitation of keying by (`Source`, `Nomer`) at all, not
    one introduced here.
    """
    flagged = qc_result.flagged
    base_columns = ["Площадка", "Регистрационный номер", "Проблема", "Поле(я)"]
    if flagged.empty:
        return pd.DataFrame(columns=base_columns)

    date_fields = _date_order_record_fields(df)
    dose_fields = _dose_threshold_record_fields(df)

    def fields_for(row: pd.Series) -> list[str]:
        rule, key = row["rule"], (row["Source"], row["Nomer"])
        if rule == "date_order":
            return date_fields.get(key, RULE_FIELDS[rule])
        if rule == "dose_threshold_consistency":
            return dose_fields.get(key, RULE_FIELDS[rule])
        return RULE_FIELDS[rule]

    row_lookup = _build_row_lookup(df)
    field_lists: list[list[str]] = []
    value_lists: list[list[object]] = []
    for _, row in flagged.iterrows():
        fields = fields_for(row)
        field_lists.append(fields)
        key = (row["Source"], row["Nomer"])
        record = row_lookup.loc[key] if key in row_lookup.index else None
        value_lists.append(_values_for(record, fields))

    n_value_cols = max((len(values) for values in value_lists), default=0)
    value_columns = [f"Поле {i}" for i in range(1, n_value_cols + 1)]

    # `Source` is categorical (`io.CATEGORY_COLUMNS`); cast to plain `str`
    # before mapping so the result is an ordinary string column rather than
    # carrying any categorical-dtype edge cases into the workbook.
    source_str = flagged["Source"].astype(str)
    out = pd.DataFrame(
        {
            "Площадка": source_str.map(SITE_LABELS_RU).fillna(source_str),
            "Регистрационный номер": flagged["Nomer"],
            "Проблема": flagged["rule"].map(QC_RULE_LABELS_RU).fillna(flagged["rule"]),
            "Поле(я)": [_fields_ru(fields) for fields in field_lists],
            "_rule": flagged["rule"],
            "_source": flagged["Source"],
        }
    )
    for col_idx, col_name in enumerate(value_columns):
        out[col_name] = [
            values[col_idx] if col_idx < len(values) else "" for values in value_lists
        ]

    out = out.sort_values(["_source", "_rule", "Регистрационный номер"]).reset_index(drop=True)
    return out[base_columns + value_columns]


def export_cleaning_list(
    df: pd.DataFrame,
    out_dir: Path,
    qc_result: qc.QCResult | None = None,
) -> dict[str, Path]:
    """Write one `.xlsx` workbook per site into `out_dir`.

    File names are the site's Russian name via `SITE_LABELS_RU` (e.g.
    `Владимир.xlsx`), each a single sheet sorted by ``Проблема`` then
    ``Регистрационный номер`` (already true of `build_cleaning_list`'s
    output once narrowed to one site), with a frozen header row and
    autofilter enabled -- a data manager filters to one problem type and
    works straight down the `Nomer` list against their local records, no
    code or rest-of-pipeline access needed. The per-site sheet omits
    ``Площадка`` (every row in a given file is the same site by
    construction, so the column would be redundant clutter).

    `qc_result` is computed via `qc.run_qc(df)` if not supplied --
    callers that already have one (e.g. `cli.py`, which needs it for
    `qc_report.md` anyway) should pass it to avoid recomputing every
    `qc.CHECKS` rule a second time.

    Returns a `{site_name_ru: path}` dict, one entry per site that
    appears in `df["Source"]` -- including sites with zero violations,
    which get a workbook containing only the header row, so a data
    manager can tell "nothing to fix" apart from "report never ran."

    See this module's docstring for the privacy rationale (Phase 8 item
    6): `out_dir` must always resolve under `reports/<run_date>/
    data_cleaning/`, never `report/` or any tracked/shared path.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_result = qc_result if qc_result is not None else qc.run_qc(df)
    cleaning_df = build_cleaning_list(df, qc_result)

    # `Поле 1`, `Поле 2`, ... are computed across the *whole* result (not
    # per site) by `build_cleaning_list`, so every site's sheet has the
    # same number of value columns even if that site happens not to have
    # the specific violation that needed the most fields.
    base_columns = {"Площадка", "Регистрационный номер", "Проблема", "Поле(я)"}
    value_columns = [c for c in cleaning_df.columns if c not in base_columns]
    sheet_columns = ["Регистрационный номер", "Проблема", "Поле(я)", *value_columns]
    written: dict[str, Path] = {}

    sites = sorted(df["Source"].dropna().unique().tolist())
    for source in sites:
        site_name_ru = SITE_LABELS_RU.get(source, source)
        site_rows = cleaning_df.loc[cleaning_df["Площадка"] == site_name_ru, sheet_columns]

        path = out_dir / f"{site_name_ru}.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            site_rows.to_excel(writer, sheet_name="Список", index=False)
            worksheet = writer.sheets["Список"]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for col_idx, col_name in enumerate(sheet_columns, start=1):
                width = max(len(col_name), *(site_rows[col_name].astype(str).map(len).tolist() or [0]))
                worksheet.column_dimensions[worksheet.cell(row=1, column=col_idx).column_letter].width = (
                    min(width + 2, 60)
                )
        written[site_name_ru] = path

    return written
