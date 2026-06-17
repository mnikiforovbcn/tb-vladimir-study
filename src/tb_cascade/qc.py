"""Phase 2 - Quality control.

Implements every row-level / cross-column consistency rule from
`Descriptive Study Plan.md` Sec 6 ("Data management and quality
control") as a standalone, independently testable function, then
aggregates them into a single `run_qc(df) -> QCResult`.

Conventions
-----------
Every `check_*` function takes the loaded raw DataFrame (the output of
`tb_cascade.io.load_raw`) and returns a `pandas` nullable-boolean
(`"boolean"` dtype) `Series`, indexed like `df`, where:

- ``True``  -> the rule was checked for this record and violated.
- ``False`` -> the rule was checked for this record and held.
- ``<NA>``  -> the rule does not apply to this record (e.g. an
  outcome-mutual-exclusivity check on a record that never started
  treatment), so it is excluded from both the numerator and the
  denominator when the rule's violation rate is computed.

This third state matters: silently treating "not applicable" as "no
violation" would understate every rule's true denominator and make
violation rates look artificially low.

Which Sec 6 items live where
-----------------------------
- Sec 6 item 1 (import/type-check) -> `schema.py` (pandera), not here.
- Sec 6 item 2 (duplicate check) -> `check_duplicate_registration`.
- Sec 6 item 3 (internal consistency, 5 bullets) -> the
  `check_treatgroup_onehot` / `check_outcome_mutual_exclusivity` /
  `check_date_order` / `check_doses_taken_le_schema` /
  `check_dose_threshold_consistency` / `check_diagnosis_mutual_exclusivity`
  functions below.
- Sec 6 item 4 (missing data audit) -> `missingness_audit`.
- Sec 6 item 5 (age range check) -> `check_age_range`.
- Sec 6 item 6 (censoring flag) -> deliberately NOT here; the
  Implementation Plan assigns `censoring_flag()` to Phase 3
  (`derive.py`), since it produces an analysis variable rather than a
  pass/fail QC violation.

Report-support functions (feed `render_qc_report`, not part of Sec 6
itself):
- `run_qc_by_site` -- the same per-rule totals as `run_qc(df).summary`,
  broken out by `Source` (plus an `ALL_SOURCES` total row per rule), so
  the rendered report can show whether a rule's violations are
  concentrated at one site.
- `date_order_pair_breakdown` -- `check_date_order` collapses four
  pairwise date comparisons into one True/False/NA per record; this
  breaks that back out by adjacent pair (and by site), since a single
  rule-level rate can hide one bad transition driving most of the
  violations.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# --- Internal consistency checks (Descriptive Study Plan Sec 6 item 3) ------


def check_duplicate_registration(df: pd.DataFrame) -> pd.Series:
    """Flag every record sharing a ``Source`` + ``Nomer`` with another record.

    Sec 6 item 2: ``Source`` + ``Nomer`` should uniquely identify a
    registration. Not applicable to records missing either key, since
    uniqueness of an incomplete key cannot be assessed.
    """
    has_key = df["Source"].notna() & df["Nomer"].notna()
    violation = pd.Series(pd.NA, index=df.index, dtype="boolean")
    key_cols = df.loc[has_key, ["Source", "Nomer"]]
    violation.loc[has_key] = key_cols.duplicated(keep=False).to_numpy()
    return violation


def check_treatgroup_onehot(df: pd.DataFrame) -> pd.Series:
    """Flag records where ``TreatGroup_01/02/03`` don't sum to 1 or match ``TreatGroup``.

    Sec 6 item 3, bullet 1. A null in any one of the three one-hot
    flags (while at least one of the four related fields is present)
    is itself treated as a violation, since these flags should always
    be explicitly coded 0/1. Not applicable only when all four related
    fields (``TreatGroup`` and all three one-hot flags) are null.
    """
    onehot_cols = ["TreatGroup_01", "TreatGroup_02", "TreatGroup_03"]
    flags = df[onehot_cols]

    not_applicable = flags.isna().all(axis=1) & df["TreatGroup"].isna()

    f01 = flags["TreatGroup_01"].fillna(False)
    f02 = flags["TreatGroup_02"].fillna(False)
    f03 = flags["TreatGroup_03"].fillna(False)
    onehot_sum = f01.astype("Int64") + f02.astype("Int64") + f03.astype("Int64")

    implied_group = pd.Series(pd.NA, index=df.index, dtype="Int64")
    implied_group = implied_group.mask(f01, 1).mask(f02, 2).mask(f03, 3)
    mismatch = implied_group.ne(df["TreatGroup"])

    any_flag_null = flags.isna().any(axis=1)

    violation = (onehot_sum.ne(1)) | mismatch.fillna(True) | any_flag_null
    violation = violation.astype("boolean")
    violation[not_applicable] = pd.NA
    return violation


def check_outcome_mutual_exclusivity(df: pd.DataFrame) -> pd.Series:
    """Flag treated records where outcome flags aren't mutually exclusive/exhaustive.

    Sec 6 item 3, bullet 2. Applies only to records where
    ``PrevTreatmentStart`` is ``True`` -- the Descriptive Study Plan
    scopes this rule to "among treated individuals".
    """
    outcome_cols = [
        "TreatmentCompleted",
        "TreatmentFinished",
        "TBdeveloped",
        "TreatmentStopedMed",
        "TreatmetnNotFinished",
        "TreatmentContinue",
        "OutcomeNotKnown",
    ]
    applicable = (df["PrevTreatmentStart"] == True).fillna(False)  # noqa: E712

    summed = sum(df[c].fillna(False).astype("Int64") for c in outcome_cols)
    violation = pd.Series(pd.NA, index=df.index, dtype="boolean")
    violation.loc[applicable] = summed.loc[applicable].ne(1).astype("boolean")
    return violation


#: The expected chronological order checked by `check_date_order`, and
#: broken down pairwise by `date_order_pair_breakdown` (Descriptive Study
#: Plan Sec 6 item 3, bullet 3).
DATE_ORDER_SEQUENCE: list[str] = [
    "DateScreening",
    "DateCompleteExaminationTB",
    "DatePrevTreatmentStart",
    "DateTreatmentScheme",
    "DateOutcome",
]


def check_date_order(df: pd.DataFrame) -> pd.Series:
    """Flag records with any reversal in the expected date sequence.

    Sec 6 item 3, bullet 3: ``DateScreening`` <= ``DateCompleteExaminationTB``
    <= ``DatePrevTreatmentStart`` <= ``DateTreatmentScheme`` <= ``DateOutcome``.
    Each consecutive pair is only checked where both dates are present;
    a record with fewer than two populated dates in the sequence is not
    applicable.

    This collapses all four pairwise comparisons in `DATE_ORDER_SEQUENCE`
    into one True/False/NA per record -- enough for a single rule-level
    violation rate, but it hides which specific transition is driving
    it. Use `date_order_pair_breakdown` to see that detail.
    """
    violation = pd.Series(False, index=df.index, dtype="boolean")
    any_pair_checkable = pd.Series(False, index=df.index)

    for earlier, later in zip(DATE_ORDER_SEQUENCE[:-1], DATE_ORDER_SEQUENCE[1:]):
        both_present = df[earlier].notna() & df[later].notna()
        reversed_pair = both_present & (df[earlier] > df[later])
        violation = violation | reversed_pair.astype("boolean")
        any_pair_checkable = any_pair_checkable | both_present

    violation[~any_pair_checkable] = pd.NA
    return violation


def date_order_pair_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Per-adjacent-pair detail behind `check_date_order`, overall and by ``Source``.

    Returns one row per (earlier, later, source) -- including the
    ``ALL_SOURCES`` aggregate -- with the count of records where both
    dates in that pair are present, how many of those are reversed
    (``earlier`` date after ``later`` date), and the resulting reversal
    rate. A high overall `check_date_order` violation rate can come from
    one bad transition or be spread evenly across all four; this is what
    distinguishes the two (e.g. a data-entry problem concentrated in one
    field vs. a sequence assumption that doesn't hold operationally).
    """
    sources = [ALL_SOURCES, *sorted(df["Source"].dropna().unique().tolist())]
    rows = []
    for earlier, later in zip(DATE_ORDER_SEQUENCE[:-1], DATE_ORDER_SEQUENCE[1:]):
        both_present = df[earlier].notna() & df[later].notna()
        reversed_pair = both_present & (df[earlier] > df[later])
        for source in sources:
            mask = (
                pd.Series(True, index=df.index)
                if source == ALL_SOURCES
                else (df["Source"] == source)
            )
            n_both = int((both_present & mask).sum())
            n_reversed = int((reversed_pair & mask).sum())
            rows.append(
                {
                    "earlier": earlier,
                    "later": later,
                    "source": source,
                    "n_both_present": n_both,
                    "n_reversed": n_reversed,
                    "reversal_rate": (n_reversed / n_both) if n_both else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def check_doses_taken_le_schema(df: pd.DataFrame) -> pd.Series:
    """Flag records where ``DosesTaken`` exceeds ``SchemaDoses``.

    Sec 6 item 3, bullet 4 (first half). Applicable only where both
    values are present.
    """
    both_present = df["DosesTaken"].notna() & df["SchemaDoses"].notna()
    violation = pd.Series(pd.NA, index=df.index, dtype="boolean")
    violation.loc[both_present] = (
        df.loc[both_present, "DosesTaken"] > df.loc[both_present, "SchemaDoses"]
    )
    return violation


def check_dose_threshold_consistency(df: pd.DataFrame) -> pd.Series:
    """Flag records where ``Take50pc``/``Take100pc`` disagree with the dose ratio.

    Sec 6 item 3, bullet 4 (second half: "...and consistent with
    Take50pc/Take100pc thresholds"). Three sub-checks, applicable
    whenever at least one of ``Take50pc``/``Take100pc`` is populated:

    1. ``Take100pc`` is True but ``Take50pc`` is explicitly False
       (100% of doses implies at least 50%).
    2. ``Take100pc`` is True but ``DosesTaken`` != ``SchemaDoses``.
    3. ``Take50pc`` is True but ``DosesTaken`` / ``SchemaDoses`` < 0.5.
    """
    applicable = df["Take50pc"].notna() | df["Take100pc"].notna()

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

    violation_bool = violates_implication | violates_100pc_ratio | violates_50pc_ratio
    violation = pd.Series(pd.NA, index=df.index, dtype="boolean")
    violation.loc[applicable] = violation_bool.loc[applicable]
    return violation


def check_diagnosis_mutual_exclusivity(df: pd.DataFrame) -> pd.Series:
    """Flag fully-evaluated records where the four diagnostic branches overlap.

    Sec 6 item 3, bullet 5: ``ConfirmedDiagnosisTB``, ``LTI``,
    ``NoTBNoLTI``, ``NoTBLTIunknown`` should be mutually exclusive (and
    exhaustive) among records with ``CompleteExaminationTB`` True.
    """
    diagnosis_cols = ["ConfirmedDiagnosisTB", "LTI", "NoTBNoLTI", "NoTBLTIunknown"]
    applicable = (df["CompleteExaminationTB"] == True).fillna(False)  # noqa: E712

    summed = sum(df[c].fillna(False).astype("Int64") for c in diagnosis_cols)
    violation = pd.Series(pd.NA, index=df.index, dtype="boolean")
    violation.loc[applicable] = summed.loc[applicable].ne(1).astype("boolean")
    return violation


def check_age_range(df: pd.DataFrame, min_age: float = 0, max_age: float = 100) -> pd.Series:
    """Flag records with an implausible age at screening.

    Sec 6 item 5: age = (``DateScreening`` - ``BirthDate``) in years;
    flag negative ages or ages over ``max_age`` (default 100). This is
    a QC range check only -- the analysis-grade `age_at_screening`
    column (with age bands) is computed independently in
    `derive.py` (Phase 3).
    """
    both_present = df["BirthDate"].notna() & df["DateScreening"].notna()
    age_years = (df["DateScreening"] - df["BirthDate"]).dt.days / 365.25

    violation = pd.Series(pd.NA, index=df.index, dtype="boolean")
    violation.loc[both_present] = (age_years.loc[both_present] < min_age) | (
        age_years.loc[both_present] > max_age
    )
    return violation


# --- Aggregation (Phase 2 step 3) --------------------------------------

CheckFunc = Callable[[pd.DataFrame], pd.Series]

#: Registry of (rule name, function) pairs run by `run_qc`. The name is
#: what shows up in `qc_report.md` and in the `flagged` table's `rule`
#: column.
CHECKS: list[tuple[str, CheckFunc]] = [
    ("duplicate_registration", check_duplicate_registration),
    ("treatgroup_onehot", check_treatgroup_onehot),
    ("outcome_mutual_exclusivity", check_outcome_mutual_exclusivity),
    ("date_order", check_date_order),
    ("doses_taken_le_schema", check_doses_taken_le_schema),
    ("dose_threshold_consistency", check_dose_threshold_consistency),
    ("diagnosis_mutual_exclusivity", check_diagnosis_mutual_exclusivity),
    ("age_range", check_age_range),
]


@dataclass
class QCResult:
    """Output of `run_qc`.

    - ``summary``: one row per rule -- ``rule``, ``n_checked``,
      ``n_violations``, ``violation_rate``.
    - ``flagged``: one row per (rule, record) violation -- ``rule``,
      ``Source``, ``Nomer`` -- i.e. the linkage keys needed to look a
      flagged record up in the raw CSV, deliberately excluding every
      other column so this table stays safe to hand to a reviewer.
    """

    summary: pd.DataFrame
    flagged: pd.DataFrame


def run_qc(df: pd.DataFrame) -> QCResult:
    """Run every rule in `CHECKS` against `df` and aggregate the results."""
    summary_rows = []
    flagged_parts = []

    for name, func in CHECKS:
        result = func(df)
        if result.dtype != "boolean":
            result = result.astype("boolean")

        n_checked = int(result.notna().sum())
        n_violations = int(result.sum())
        violation_rate = (n_violations / n_checked) if n_checked else float("nan")
        summary_rows.append(
            {
                "rule": name,
                "n_checked": n_checked,
                "n_violations": n_violations,
                "violation_rate": violation_rate,
            }
        )

        violated_mask = result.fillna(False)
        if violated_mask.any():
            sub = df.loc[violated_mask, ["Source", "Nomer"]].copy()
            sub.insert(0, "rule", name)
            flagged_parts.append(sub)

    summary = pd.DataFrame(summary_rows)
    flagged = (
        pd.concat(flagged_parts, ignore_index=True)
        if flagged_parts
        else pd.DataFrame(columns=["rule", "Source", "Nomer"])
    )
    return QCResult(summary=summary, flagged=flagged)


def run_qc_by_site(df: pd.DataFrame) -> pd.DataFrame:
    """Same metrics as ``run_qc(df).summary``, broken out by ``Source``.

    Returns one row per (rule, source) -- including an ``ALL_SOURCES``
    total row per rule -- so the rendered report can show each rule's
    overall rate alongside its per-site rates, e.g. to catch a violation
    pattern concentrated at one site. Kept separate from `run_qc` (whose
    `summary`/`flagged` shape is depended on elsewhere) so existing
    callers are unaffected; this recomputes each `CHECKS` function rather
    than reusing `run_qc`'s results, which is cheap at this data scale.
    """
    sources = [ALL_SOURCES, *sorted(df["Source"].dropna().unique().tolist())]
    rows = []
    for name, func in CHECKS:
        result = func(df)
        if result.dtype != "boolean":
            result = result.astype("boolean")

        for source in sources:
            mask = (
                pd.Series(True, index=df.index)
                if source == ALL_SOURCES
                else (df["Source"] == source)
            )
            sub = result.loc[mask]
            n_checked = int(sub.notna().sum())
            n_violations = int(sub.sum())
            violation_rate = (n_violations / n_checked) if n_checked else float("nan")
            rows.append(
                {
                    "rule": name,
                    "source": source,
                    "n_checked": n_checked,
                    "n_violations": n_violations,
                    "violation_rate": violation_rate,
                }
            )
    return pd.DataFrame(rows)


# --- Missingness audit (Phase 2 step 5) ----------------------------------

StructuralRule = Callable[[pd.DataFrame], pd.Series]

#: Heuristic map of column -> precondition under which that column is
#: expected to be POPULATED (i.e. NOT structurally missing), per
#: Descriptive Study Plan Sec 6 item 4 ("missingness is expected to be
#: structural... distinguish structural missingness from data-entry
#: gaps"). A column with no entry here is expected to always be
#: populated, so any null in it is "unexplained" by default.
#:
#: These are deliberately simple, single-upstream-flag heuristics meant
#: to triage the bulk of expected missingness for Phase 2; Phase 8
#: (manual epidemiologist sign-off) is where they get reviewed,
#: confirmed, or refined -- "unexplained" means "no documented
#: structural reason yet", not "confirmed data-entry error".
STRUCTURAL_MISSINGNESS_RULES: dict[str, StructuralRule] = {
    "IndexCase": lambda df: df["Contact"] == True,  # noqa: E712
    "RelationWithSource": lambda df: df["Contact"] == True,  # noqa: E712
    "DateScreening": lambda df: df["Screening"] == True,  # noqa: E712
    "SuspectedTB": lambda df: df["Screening"] == True,  # noqa: E712
    "DiaskintestPositive": lambda df: df["Screening"] == True,  # noqa: E712
    "DateScreening_y": lambda df: df["Screening_y"] == True,  # noqa: E712
    "NoTbAfter_y_xray": lambda df: df["Screening_y"] == True,  # noqa: E712
    "NoTbAfter_y": lambda df: df["Screening_y"] == True,  # noqa: E712
    "NoTbAfter_24": lambda df: df["Screening_24"] == True,  # noqa: E712
    "DateCompleteExaminationTB": lambda df: df["CompleteExaminationTB"] == True,  # noqa: E712
    "ConfirmedDiagnosisTB": lambda df: df["CompleteExaminationTB"] == True,  # noqa: E712
    "LTI": lambda df: df["CompleteExaminationTB"] == True,  # noqa: E712
    "NoTBNoLTI": lambda df: df["CompleteExaminationTB"] == True,  # noqa: E712
    "NoTBLTIunknown": lambda df: df["CompleteExaminationTB"] == True,  # noqa: E712
    "PrevTreatmentRec": lambda df: df["LTI"] == True,  # noqa: E712
    "PrevTreatmentPresc": lambda df: df["PrevTreatmentRec"] == True,  # noqa: E712
    "PrevTreatmentStart": lambda df: df["PrevTreatmentPresc"] == True,  # noqa: E712
    "DatePrevTreatmentStart": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "DateTreatmentScheme": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "RegBq": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "RegMfx": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "TreatmentCompleted": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "TreatmentFinished": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "DateOutcome": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "TBdeveloped": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "TreatmentStopedMed": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "TreatmetnNotFinished": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "TreatmentContinue": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "OutcomeNotKnown": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "DosesTaken": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "SchemaDoses": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "Take50pc": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "Take100pc": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "FinalOutcome": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    # Incentive section: the "did we pay it" flags (`SuppX`) are expected
    # whenever the person reached the eligible cascade stage (even if the
    # answer turns out to be "no, not paid" -- that's a real `False`, not
    # a missing value). The `DateSuppX` payment dates, in turn, are only
    # expected once the corresponding `SuppX` flag is actually `True`.
    "SuppScreening": lambda df: df["Screening"] == True,  # noqa: E712
    "DateSuppScreening": lambda df: df["SuppScreening"] == True,  # noqa: E712
    "Supp50pc": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "DateSupp50pc": lambda df: df["Supp50pc"] == True,  # noqa: E712
    "Supp100pc": lambda df: df["PrevTreatmentStart"] == True,  # noqa: E712
    "DateSupp100pc": lambda df: df["Supp100pc"] == True,  # noqa: E712
    "Supp1yearGr23": lambda df: (df["TreatGroup_02"] == True)  # noqa: E712
    | (df["TreatGroup_03"] == True),  # noqa: E712
    "DateSupp1yearGr23": lambda df: df["Supp1yearGr23"] == True,  # noqa: E712
    "Supp1yearGr1": lambda df: df["TreatGroup_01"] == True,  # noqa: E712
    "DateSupp1yearGr1": lambda df: df["Supp1yearGr1"] == True,  # noqa: E712
}

#: Sentinel used in the `source` column of `missingness_audit`'s,
#: `run_qc_by_site`'s, and `date_order_pair_breakdown`'s output for the
#: all-sites aggregate row, alongside the real `Source` values.
ALL_SOURCES = "__ALL__"


def missingness_audit(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column null-rate table, overall and split by ``Source``.

    Sec 6 item 4. For each column, every null value is classified as
    "structural" (the upstream precondition in
    `STRUCTURAL_MISSINGNESS_RULES` does not hold for that row, so the
    value is expected to be missing) or "unexplained" (no documented
    precondition for that column, or the precondition holds yet the
    value is missing anyway).

    Returns a long-format DataFrame with one row per (column, source)
    pair, where ``source`` includes both the real `Source` values and
    the `ALL_SOURCES` aggregate.
    """
    sources = [ALL_SOURCES, *sorted(df["Source"].dropna().unique().tolist())]
    rows = []

    for col in df.columns:
        is_null = df[col].isna()
        rule = STRUCTURAL_MISSINGNESS_RULES.get(col)
        if rule is not None:
            expected_present = rule(df).fillna(False)
            structural = is_null & ~expected_present
            unexplained = is_null & expected_present
        else:
            structural = pd.Series(False, index=df.index)
            unexplained = is_null

        for source in sources:
            mask = (
                pd.Series(True, index=df.index)
                if source == ALL_SOURCES
                else (df["Source"] == source)
            )
            n_rows = int(mask.sum())
            n_null = int((is_null & mask).sum())
            n_structural = int((structural & mask).sum())
            n_unexplained = int((unexplained & mask).sum())
            rows.append(
                {
                    "column": col,
                    "source": source,
                    "n_rows": n_rows,
                    "n_null": n_null,
                    "null_rate": (n_null / n_rows) if n_rows else float("nan"),
                    "n_structural_null": n_structural,
                    "n_unexplained_null": n_unexplained,
                    "has_structural_rule": rule is not None,
                }
            )

    return pd.DataFrame(rows)


# --- Report rendering (Phase 2 step 4) -----------------------------------


def render_qc_report(
    qc_result: QCResult,
    missingness: pd.DataFrame,
    by_site: pd.DataFrame,
    date_order_detail: pd.DataFrame,
    path: Path,
) -> Path:
    """Render the technical QC appendix referenced in Descriptive Study Plan Sec 12.3.

    Writes a single Markdown file with three sections:

    1. Internal consistency rules -- one row per (rule, site), from
       `run_qc_by_site`, plus a "Total" row per rule. Showing sites
       alongside the total lets a reviewer see whether a rule's
       violations are spread evenly or concentrated at one site --
       ``Source``/site names are aggregate labels, not row-level
       identifiers, so this carries no linkage-key risk.
    2. Date order detail -- the per-adjacent-pair breakdown behind the
       `date_order` rule, from `date_order_pair_breakdown` (all-sites
       only here, to keep this a readable size; call that function
       directly for the per-site detail).
    3. Missingness audit -- the overall (all-sources) missingness table.
       Per-site missingness breakdowns are available in `missingness`
       itself (this report only renders the `ALL_SOURCES` slice, to keep
       the rendered appendix a readable size).
    """
    lines = ["# QC Report", ""]

    lines.append("## Internal consistency rules")
    lines.append("")
    lines.append("| Rule | Site | # checked | # violations | Violation rate |")
    lines.append("|---|---|---|---|---|")
    site_order = [
        ALL_SOURCES,
        *sorted(s for s in by_site["source"].unique() if s != ALL_SOURCES),
    ]
    for name, _ in CHECKS:
        rule_rows = by_site.loc[by_site["rule"] == name].set_index("source")
        for source in site_order:
            if source not in rule_rows.index:
                continue
            row = rule_rows.loc[source]
            site_label = "Total" if source == ALL_SOURCES else source
            rate = "n/a" if pd.isna(row["violation_rate"]) else f"{row['violation_rate']:.2%}"
            lines.append(
                f"| {name} | {site_label} | {row['n_checked']} | "
                f"{row['n_violations']} | {rate} |"
            )
    lines.append("")
    lines.append(f"Total flagged (rule, record) pairs: {len(qc_result.flagged)}.")
    lines.append("")

    lines.append("## Date order detail")
    lines.append("")
    lines.append(
        "Per-adjacent-pair breakdown behind the `date_order` rule above (all "
        "sites) -- a high overall rate concentrated in one row below means "
        "one transition is driving it, rather than reversals being spread "
        "evenly across the whole expected sequence."
    )
    lines.append("")
    lines.append("| Earlier | Later | # both present | # reversed | Reversal rate |")
    lines.append("|---|---|---|---|---|")
    overall_dates = date_order_detail.loc[date_order_detail["source"] == ALL_SOURCES]
    for _, row in overall_dates.iterrows():
        rate = "n/a" if pd.isna(row["reversal_rate"]) else f"{row['reversal_rate']:.2%}"
        lines.append(
            f"| {row['earlier']} | {row['later']} | {row['n_both_present']} | "
            f"{row['n_reversed']} | {rate} |"
        )
    lines.append("")

    lines.append("## Missingness audit (all sites)")
    lines.append("")
    lines.append("| Column | n | # null | Null rate | Structural | Unexplained | Has rule |")
    lines.append("|---|---|---|---|---|---|---|")
    overall = missingness.loc[missingness["source"] == ALL_SOURCES].sort_values(
        "null_rate", ascending=False
    )
    for _, row in overall.iterrows():
        col_name = row["column"]
        lines.append(
            f"| {col_name} | {row['n_rows']} | {row['n_null']} | "
            f"{row['null_rate']:.1%} | {row['n_structural_null']} | "
            f"{row['n_unexplained_null']} | {row['has_structural_rule']} |"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
