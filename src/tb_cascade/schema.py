"""Phase 2 - Schema.

Pandera ``DataFrameSchema`` encoding the full data dictionary in
``Documentation/DataSet Description (English).md``. This is the
machine-readable counterpart to that document: every column's dtype,
nullability, and allowed value set/range is declared once here and
enforced on every pipeline run via :func:`validate`.

Scope note: this module only validates each *column in isolation*
(dtype, value set, range). Row-level / cross-column consistency rules
(date ordering, one-hot sums, mutual exclusivity, duplicate keys) are
NOT encoded here -- those live in ``qc.py`` as standalone, individually
testable functions, per the Phase 2 plan in
``Analytical Framework Implementation Plan.md``.
"""

from __future__ import annotations

import pandas as pd
import pandera as pa

# --- Per-column value sets, straight from the data dictionary ---------------

SOURCE_VALUES: list[str] = ["Vladimir", "Murom", "Kovrov"]
SOURCE_ID_VALUES: list[int] = [1, 2, 3]  # 1=Vladimir, 2=Murom, 3=Kovrov
SEX_VALUES: list[int] = [1, 2]  # 1=male, 2=female
TARGET_GROUP_VALUES: list[int] = [1, 2, 3, 4]  # contact/homeless/PLHIV/other
TREAT_GROUP_VALUES: list[int] = [1, 2, 3]  # TB treatment/LTI treatment/observation
RELATION_WITH_SOURCE_VALUES: list[int] = [45, 313, 314, 348, 366]
FINAL_OUTCOME_VALUES: list[int] = [1, 2, 3, 4]

# All `0/1` flag columns share the same constraint: nullable boolean.
# (39 columns -- matches `io.BOOLEAN_COLUMNS`.)
_BOOLEAN_FLAG_COLUMNS: list[str] = [
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

# All `Date*` columns: parsed as datetime64[ns] by `io.load_raw`, all
# conditionally/structurally missing depending on cascade progress.
# (12 columns -- matches `io.DATE_COLUMNS`.)
_DATE_COLUMNS: list[str] = [
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


def _boolean_columns() -> dict[str, pa.Column]:
    return {
        name: pa.Column("boolean", nullable=True, coerce=False)
        for name in _BOOLEAN_FLAG_COLUMNS
    }


def _date_columns() -> dict[str, pa.Column]:
    return {
        name: pa.Column("datetime64[ns]", nullable=True, coerce=False)
        for name in _DATE_COLUMNS
    }


# --- The schema ---------------------------------------------------------

RAW_SCHEMA = pa.DataFrameSchema(
    {
        # --- Identification --------------------------------------------
        "Source_id": pa.Column(
            "Int64", pa.Check.isin(SOURCE_ID_VALUES), nullable=True
        ),
        "Source": pa.Column(
            "category", pa.Check.isin(SOURCE_VALUES), nullable=False
        ),
        "Nomer": pa.Column("Int64", nullable=False),
        "IndexCase": pa.Column("string", nullable=True),
        # --- Demographics -------------------------------------------------
        "Sex": pa.Column("Int64", pa.Check.isin(SEX_VALUES), nullable=True),
        # --- Risk group -----------------------------------------------------
        "TargetGroup": pa.Column(
            "Int64", pa.Check.isin(TARGET_GROUP_VALUES), nullable=True
        ),
        "RelationWithSource": pa.Column(
            "Int64", pa.Check.isin(RELATION_WITH_SOURCE_VALUES), nullable=True
        ),
        # --- Treatment group -------------------------------------------------
        "TreatGroup": pa.Column(
            "Int64", pa.Check.isin(TREAT_GROUP_VALUES), nullable=True
        ),
        # --- Adherence / counts ------------------------------------------------
        "DosesTaken": pa.Column("Int64", pa.Check.ge(0), nullable=True),
        "SchemaDoses": pa.Column("Int64", pa.Check.ge(0), nullable=True),
        # --- Final outcome -----------------------------------------------------
        "FinalOutcome": pa.Column(
            "Int64", pa.Check.isin(FINAL_OUTCOME_VALUES), nullable=True
        ),
        **_boolean_columns(),
        **_date_columns(),
    },
    strict=True,
    coerce=False,
)

assert len(RAW_SCHEMA.columns) == EXPECTED_COLUMN_COUNT, (
    f"schema.py declares {len(RAW_SCHEMA.columns)} columns, "
    f"expected {EXPECTED_COLUMN_COUNT}"
)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Validate ``df`` against :data:`RAW_SCHEMA`, returning it unchanged.

    Uses lazy validation: every column/value violation across the whole
    DataFrame is collected and reported together in a single
    ``pandera.errors.SchemaErrors`` exception (with a ``.failure_cases``
    DataFrame), rather than stopping at the first failure. This matters
    here because failing fast on the first bad value would hide every
    other problem in the same run.
    """
    return RAW_SCHEMA.validate(df, lazy=True)
