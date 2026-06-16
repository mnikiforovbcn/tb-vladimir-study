"""Phase 1 - Ingestion.

Reads the raw programmatic-surveillance CSV into a correctly typed
DataFrame, and writes an immutable, dated Parquet snapshot of whatever
input a given pipeline run used.

Dtype map below is built directly from
`Documentation/DataSet Description (English).md` and verified against the
real CSV header (62 columns, see `tests/test_io.py`).

Notes on dtype choices:
- All `0/1` flag columns use the pandas *nullable* ``"boolean"`` dtype
  rather than plain ``bool``, because the source export renders some
  flags as float-formatted text (``"1.0"``, ``"0.0"``) once a column
  contains any missing values, and a small number of flags are
  legitimately missing (e.g., not yet applicable to a given record).
- Numeric ID/count/code columns use nullable ``"Int64"`` for the same
  reason (e.g., ``FinalOutcome`` is blank for records without a recorded
  outcome).
- ``IndexCase`` is read as ``"string"`` rather than an integer type: values
  have meaningful leading zeros (e.g., ``"0107715"``) that a numeric dtype
  would silently destroy.
- ``Source`` is read as ``"category"`` per the implementation plan (a small,
  fixed set of site names).
- All `Date*` columns are parsed as ``datetime64[ns]`` via ``parse_dates``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tb_cascade.config import PROCESSED_DATA_DIR, RAW_DATA_PATH

# --- Column categorization (62 columns total) -------------------------------

# Nullable boolean ("0/1" flags), 39 columns.
BOOLEAN_COLUMNS: list[str] = [
    "Contact",
    "Homeless",
    "PLHIV",
    "Others",
    "TreatGroup_01",
    "TreatGroup_02",
    "TreatGroup_03",
    "Screening",
    "SuspectedTB",
    "DiaskintestPositive",
    "Screening_y",
    "NoTbAfter_y_xray",
    "NoTbAfter_y",
    "Screening_24",
    "NoTbAfter_24",
    "CompleteExaminationTB",
    "ConfirmedDiagnosisTB",
    "LTI",
    "NoTBNoLTI",
    "NoTBLTIunknown",
    "PrevTreatmentRec",
    "PrevTreatmentPresc",
    "PrevTreatmentStart",
    "RegBq",
    "RegMfx",
    "TreatmentCompleted",
    "TreatmentFinished",
    "TBdeveloped",
    "TreatmentStopedMed",
    "TreatmetnNotFinished",
    "TreatmentContinue",
    "OutcomeNotKnown",
    "Take50pc",
    "Take100pc",
    "SuppScreening",
    "Supp50pc",
    "Supp100pc",
    "Supp1yearGr23",
    "Supp1yearGr1",
]

# Nullable integer (IDs, codes, counts), 9 columns.
INT_COLUMNS: list[str] = [
    "Source_id",
    "Nomer",
    "Sex",
    "TargetGroup",
    "TreatGroup",
    "RelationWithSource",
    "DosesTaken",
    "SchemaDoses",
    "FinalOutcome",
]

# Fixed, small value set -> category, 1 column.
CATEGORY_COLUMNS: list[str] = [
    "Source",
]

# Free-text / ID with meaningful leading zeros, 1 column.
STRING_COLUMNS: list[str] = [
    "IndexCase",
]

# Parsed as datetime64[ns] via parse_dates, 12 columns.
DATE_COLUMNS: list[str] = [
    "BirthDate",
    "DateScreening",
    "DateScreening_y",
    "DateCompleteExaminationTB",
    "DatePrevTreatmentStart",
    "DateTreatmentScheme",
    "DateOutcome",
    "DateSuppScreening",
    "DateSupp50pc",
    "DateSupp100pc",
    "DateSupp1yearGr23",
    "DateSupp1yearGr1",
]

EXPECTED_COLUMN_COUNT = 62
assert (
    len(BOOLEAN_COLUMNS)
    + len(INT_COLUMNS)
    + len(CATEGORY_COLUMNS)
    + len(STRING_COLUMNS)
    + len(DATE_COLUMNS)
    == EXPECTED_COLUMN_COUNT
)

DTYPE_MAP: dict[str, str] = {
    **{c: "boolean" for c in BOOLEAN_COLUMNS},
    **{c: "Int64" for c in INT_COLUMNS},
    **{c: "category" for c in CATEGORY_COLUMNS},
    **{c: "string" for c in STRING_COLUMNS},
}


def load_raw(path: Path | str = RAW_DATA_PATH) -> pd.DataFrame:
    """Load the raw programmatic-surveillance CSV into a typed DataFrame.

    Applies the explicit dtype/parse_dates map above so downstream code
    never has to guess a column's type. Boolean and integer flag columns
    use pandas' nullable dtypes so missing values survive the read intact
    (rather than silently upcasting the whole column to float64).

    A small number of records contain a malformed/out-of-range date in a
    `Date*` field (e.g. a transposed-digit year such as "1201-09-20" or
    "201-08-01" - out of pandas' nanosecond-precision Timestamp range).
    When this happens, pandas' C parser cannot bulk-parse the whole
    column and silently leaves it as `object` dtype with raw strings
    instead of raising. To guarantee every `Date*` column comes out as
    `datetime64[ns]` per the implementation plan, any such column is
    re-parsed here with `errors="coerce"`, turning the unparseable value
    into `NaT`. This is a real upstream data-quality issue, not an
    ingestion bug - it is intentionally surfaced as a missing date rather
    than guessed at, so Phase 2 QC can flag it and a reviewer can correct
    it against the source record.
    """
    df = pd.read_csv(
        path,
        dtype=DTYPE_MAP,
        parse_dates=DATE_COLUMNS,
    )
    for col in DATE_COLUMNS:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def snapshot(df: pd.DataFrame, run_date: str) -> Path:
    """Write an immutable Parquet snapshot of ``df`` for a given run.

    The output path is ``Data/processed/raw_snapshot_<run_date>.parquet``.
    This lets every later pipeline stage and report cite the exact dataset
    version a run was built from, independent of the live raw CSV.

    Requires ``pyarrow`` (declared in ``pyproject.toml``).
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DATA_DIR / f"raw_snapshot_{run_date}.parquet"
    df.to_parquet(out_path, index=False)
    return out_path
