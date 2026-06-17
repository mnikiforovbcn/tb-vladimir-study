"""Phase 4 - Cascade and descriptive analytics (Steps 1-8, 10).

Reads the single analysis-ready table `derive.build_analysis_table`
produces (raw columns + age/adherence/interval/cascade-flag/censoring
derived columns) and computes the Descriptive Study Plan Sec 7 tables:
population profile (Step 1), screening cascade (Step 2), diagnostic
outcomes (Step 3), LTI preventive-treatment cascade (Step 4), regimen
description (Step 5), adherence/completion (Step 6), incentive uptake
(Step 7), follow-up/final-outcome/incidence-rate (Step 8), and the
cross-site comparison (Step 10). Step 9 (temporal trends) lives in
`trends.py`, which reuses `suppress_small_cells` from here.

Design notes that apply across this module:
- Categorical/count-based cascade percentages (Steps 2-4, 6-8, 10) are
  computed via parametrized DuckDB SQL (`connect`, `_flag_proportion`,
  `_categorical_distribution`), per the Implementation Plan (Phase 4
  item 2): each step function opens its own short-lived in-memory
  DuckDB connection over `df` (a zero-copy `register`, not a real
  import/export), runs one or more SQL aggregations, and closes the
  connection -- there is no shared, long-lived connection state, so
  every step function is a pure, independently testable function of
  `df`. "Parametrized SQL views" (the Plan's phrase) is interpreted
  here as "the aggregation logic is expressed as a parametrized SQL
  SELECT," not as literal `CREATE VIEW` DDL -- nothing here persists
  past a single call, so a literal view would add ceremony with no
  benefit.
- Continuous-variable summaries (median/IQR: age, initiation delay,
  adherence ratio, incentive-payment delay) are computed directly in
  pandas (`_median_iqr`), not via SQL, even though DuckDB does support
  quantile aggregates. Pandas' `Series.quantile`/`.median` are simpler,
  better-tested in this codebase's own test suite, and avoid pinning
  the module to a DuckDB-specific quantile function name -- there is
  no auditability benefit to routing a median through SQL here.
- Every nullable-boolean cascade flag follows the convention already
  established in `qc.py`/`derive.py`: `True`/`False`/`<NA>`, where
  `<NA>` means "not applicable" or "not yet known" and is excluded from
  *both* the numerator and the denominator of any proportion -- never
  coerced to `False`. In SQL this is the
  `COUNT(*) FILTER (WHERE flag IS NOT NULL)` / `FILTER (WHERE flag =
  TRUE)` pattern used throughout `_flag_proportion`.
- Every step function's percentages are expressed as "penetration of
  the stated denominator" (e.g. Step 4's `recommended`/`prescribed`/
  `started` are all a percentage of the *eligible* cohort), not
  "retention from the previous stage" -- this matches how the
  Descriptive Study Plan phrases each step ("among eligible: proportion
  recommended -> prescribed -> started") and keeps every stage's
  percentage independently interpretable.
- `suppress_small_cells` is the mandatory last step before any table
  leaves this module (Implementation Plan item 7 / Descriptive Study
  Plan Sec 11): any row whose group size falls below
  `SMALL_CELL_THRESHOLD` has its denominator *and* every value column
  blanked to `pd.NA` (not just the percentage -- a small raw count is
  itself potentially identifying at the smaller sites) and is flagged
  via a `suppressed` column, rather than being silently dropped. Every
  `stepN_*` function below calls it exactly once, as its final return
  expression.
- `group_by` dimensions are validated against an explicit allow-list
  (`_ALLOWED_GROUP_DIMS`) before being spliced into SQL text, since
  DuckDB's Python API has no parametrized-identifier placeholder (only
  parametrized *values*) -- accepting arbitrary column names into raw
  SQL would be unsafe even though `df` itself is a trusted, internally
  produced table here.
- Coded columns that are really categorical labels under the hood
  (`TargetGroup`, `Sex`, `RelationWithSource`, `TreatGroup`) are
  recoded to readable strings (`_apply_label_maps`) as the second-to-
  last step of every table, so a reader never has to cross-reference
  the data dictionary to interpret a result.
"""

from __future__ import annotations

import duckdb
import pandas as pd
from scipy.stats import chi2
from statsmodels.stats.proportion import proportion_confint
from tableone import TableOne

from tb_cascade import derive

# --- module constants -----------------------------------------------------

#: Minimum group size (denominator) a stratified cell must have to be
#: shown at all, per Descriptive Study Plan Sec 11 ("avoid presenting
#: any stratified cell with very small counts (e.g., <5)").
SMALL_CELL_THRESHOLD: int = 5

#: Default two-sided alpha for every confidence interval in this module
#: (95% CIs), both Wilson (proportions) and exact-Poisson (Step 8's
#: incidence rate).
DEFAULT_CI_ALPHA: float = 0.05

#: Source date column for each calendar dimension `_with_calendar_dims`
#: derives. Kept distinct from `derive._INTERVAL_NODE_LABELS` (a
#: different module, different purpose) even though the underlying
#: dates overlap.
_CALENDAR_SOURCE_DATES: dict[str, str] = {
    "enroll": "DateScreening",
    "treat_start": "DatePrevTreatmentStart",
    "outcome": "DateOutcome",
}

#: Column names any `stepN_*` function's `group_by` may use, spliced
#: directly into SQL `GROUP BY`/`PARTITION BY` clauses -- see the
#: module docstring for why this allow-list exists. Calendar dimensions
#: are computed by `_with_calendar_dims`; `completed_or_finished` is a
#: `derive.cascade_flags` boolean, included so Step 8's final-outcome
#: distribution can stratify by treatment completion (Sec 7 Step 8).
_ALLOWED_GROUP_DIMS: frozenset[str] = frozenset(
    {
        "Source",
        "TargetGroup",
        "Sex",
        "age_band",
        "TreatGroup",
        "completed_or_finished",
        "enroll_year",
        "enroll_quarter",
        "treat_start_year",
        "treat_start_quarter",
        "outcome_year",
        "outcome_quarter",
    }
)

#: Coded raw columns that are really categorical labels, recoded to
#: readable strings by `_apply_label_maps` as a cosmetic last step in
#: every `stepN_*` function. Source: `Documentation/DataSet Description
#: (English).md`.
_LABEL_MAPS: dict[str, dict[int, str]] = {
    "TargetGroup": {1: "Contact", 2: "Homeless", 3: "PLHIV", 4: "Other"},
    "Sex": {1: "Male", 2: "Female"},
    "TreatGroup": {1: "TB treatment", 2: "LTI treatment", 3: "Observation"},
    "RelationWithSource": {
        45: "Colleague",
        313: "Neighbor",
        314: "Other",
        348: "Relative (same household)",
        366: "Healthcare worker",
    },
}


# --- core helpers -----------------------------------------------------------


def _with_calendar_dims(df: pd.DataFrame) -> pd.DataFrame:
    """Year/quarter columns for the three calendar dimensions Steps
    2-8/10 may optionally group by, computed in plain pandas
    (`Series.dt.year`/`.dt.quarter`) before `connect` ever registers
    anything with DuckDB -- this sidesteps any difference between
    DuckDB's `EXTRACT(... FROM ...)` and other SQL dialects, since the
    calendar columns are already plain nullable `Int64` by the time
    DuckDB sees them.

    Returns a 6-column DataFrame (`enroll_year`, `enroll_quarter`,
    `treat_start_year`, `treat_start_quarter`, `outcome_year`,
    `outcome_quarter`) indexed like `df`, `pd.NA` wherever the
    underlying date is missing.
    """
    out: dict[str, pd.Series] = {}
    for prefix, date_col in _CALENDAR_SOURCE_DATES.items():
        col = df[date_col]
        out[f"{prefix}_year"] = col.dt.year.astype("Int64")
        out[f"{prefix}_quarter"] = col.dt.quarter.astype("Int64")
    return pd.DataFrame(out, index=df.index)


def _pandas_frame(df: pd.DataFrame) -> pd.DataFrame:
    """`df` plus its calendar dimensions, for pandas-only (non-DuckDB)
    work that may need to `group_by` a calendar dimension (e.g.
    `treat_start_year`) or compute a one-off column not already on
    `df` (e.g. Step 7's payment-delay days, Step 8's person-time).
    Mirrors what `connect` does for the SQL path, so a `group_by` list
    behaves identically whether a step routes through SQL or stays in
    pandas (`_median_iqr`).
    """
    return pd.concat([df, _with_calendar_dims(df)], axis=1)


def connect(
    df: pd.DataFrame, extra_columns: pd.DataFrame | None = None
) -> duckdb.DuckDBPyConnection:
    """Open an in-process DuckDB connection with `df` registered as the
    `analysis` table, plus its calendar dimensions (`_with_calendar_dims`)
    and any caller-supplied `extra_columns` (e.g. a one-off computed
    eligibility mask a particular step needs in its SQL `WHERE` clause,
    such as a freshly recomputed `censoring_flag`).

    Every `stepN_*` function below opens its own connection via this
    helper rather than sharing one across calls; see the module
    docstring for why. Callers are responsible for `con.close()`-ing
    what they get back (typically in a `try`/`finally`).
    """
    parts = [df, _with_calendar_dims(df)]
    if extra_columns is not None:
        parts.append(extra_columns)
    full = pd.concat(parts, axis=1)
    con = duckdb.connect(":memory:")
    con.register("analysis", full)
    return con


def _validate_group_by(group_by: list[str] | None) -> list[str]:
    """Validate `group_by` dimension names against `_ALLOWED_GROUP_DIMS`
    before they are spliced into SQL `GROUP BY`/`PARTITION BY` clauses.
    Returns `[]` for `None`. Raises `ValueError` listing the unsupported
    name(s) and the full allow-list otherwise.
    """
    dims = list(group_by) if group_by else []
    unknown = sorted(set(dims) - _ALLOWED_GROUP_DIMS)
    if unknown:
        raise ValueError(
            f"Unsupported group_by dimension(s): {unknown}. "
            f"Allowed: {sorted(_ALLOWED_GROUP_DIMS)}"
        )
    return dims


def wilson_ci(
    count: int, nobs: int, alpha: float = DEFAULT_CI_ALPHA
) -> tuple[float, float]:
    """95% (or `1 - alpha`) Wilson score interval for one proportion.

    Thin wrapper around `statsmodels.stats.proportion.proportion_confint`
    (`method="wilson"`), per the Implementation Plan (Phase 4 item 3).
    Returns `(nan, nan)` for `nobs == 0` rather than raising -- callers
    (`_attach_wilson_ci`) may hit an empty stratum after grouping, and
    the interval is undefined there, not zero-width.
    """
    if nobs == 0:
        return (float("nan"), float("nan"))
    low, high = proportion_confint(count, nobs, alpha=alpha, method="wilson")
    return (float(low), float(high))


def _attach_wilson_ci(
    table: pd.DataFrame, alpha: float = DEFAULT_CI_ALPHA
) -> pd.DataFrame:
    """Add `pct`/`ci_low`/`ci_high` columns to a table with `n` (denominator)
    and `count` (numerator) columns -- the shape every `_flag_proportion`/
    `_categorical_distribution` query produces. `nan` in all three for any
    row with `n == 0`.
    """
    table = table.copy()
    n = table["n"].astype("int64")
    count = table["count"].astype("int64")
    pct = pd.Series(float("nan"), index=table.index, dtype="float64")
    ci_low = pd.Series(float("nan"), index=table.index, dtype="float64")
    ci_high = pd.Series(float("nan"), index=table.index, dtype="float64")

    nonzero = n > 0
    pct.loc[nonzero] = count.loc[nonzero] / n.loc[nonzero]
    for idx in table.index[nonzero]:
        lo, hi = wilson_ci(int(count.loc[idx]), int(n.loc[idx]), alpha=alpha)
        ci_low.loc[idx] = lo
        ci_high.loc[idx] = hi

    table["pct"] = pct
    table["ci_low"] = ci_low
    table["ci_high"] = ci_high
    return table


def _flag_proportion(
    con: duckdb.DuckDBPyConnection,
    flag_col: str,
    *,
    where: str = "TRUE",
    group_by: list[str] | None = None,
    table: str = "analysis",
) -> pd.DataFrame:
    """Count/%/Wilson-CI of `flag_col = TRUE`, optionally grouped.

    `flag_col` is normally one of the nullable-boolean columns from
    `derive.cascade_flags` (or a raw boolean column, or a compound SQL
    boolean expression like `"(RegBq AND RegMfx)"` -- it is spliced
    directly into the query, so any valid SQL boolean expression works).
    The denominator (`n`) is every row where `where` holds *and*
    `flag_col` is not null; `<NA>` rows are excluded from both the
    numerator and the denominator, per the nullable-boolean convention
    documented in the module docstring. `where` narrows which rows are
    in scope at all (e.g. `"reached_full_eval = TRUE"` for an "among
    fully evaluated" denominator) and is applied independently of, and
    before, the not-null filter on `flag_col` itself.

    Returns one row per observed `group_by` combination (or a single
    row if `group_by` is empty), with columns `*group_by, n, count, pct,
    ci_low, ci_high`.
    """
    dims = _validate_group_by(group_by)
    dim_select = "".join(f"{d}, " for d in dims)
    group_clause = f"GROUP BY {', '.join(dims)}" if dims else ""
    sql = f"""
        SELECT
            {dim_select}
            COUNT(*) FILTER (WHERE {flag_col} IS NOT NULL) AS n,
            COUNT(*) FILTER (WHERE {flag_col} = TRUE) AS count
        FROM {table}
        WHERE {where}
        {group_clause}
    """
    result = con.execute(sql).fetchdf()
    return _attach_wilson_ci(result)


def _categorical_distribution(
    con: duckdb.DuckDBPyConnection,
    category_col: str,
    *,
    where: str = "TRUE",
    group_by: list[str] | None = None,
    table: str = "analysis",
) -> pd.DataFrame:
    """Count/%/Wilson-CI for every observed value of a categorical column.

    Long format: one row per (`group_by`..., `category_col` value),
    e.g. Step 3's `diagnosis_branch` and Step 6/8's `outcome_branch`/
    `final_outcome_category` distributions. The denominator (`n`) for
    each row's `pct` is the *group's* total non-null `category_col`
    count (so percentages within a group sum to ~100% across its
    category rows), not the count of that category value alone --
    `count` is the category's own count, `n` is the group total it is
    a share of. A category with zero records in a given group simply
    does not appear as a row, rather than appearing as a 0/0 row.
    """
    dims = _validate_group_by(group_by)
    dim_select = "".join(f"{d}, " for d in dims)
    partition = f"PARTITION BY {', '.join(dims)}" if dims else ""
    group_clause = (
        f"GROUP BY {', '.join(dims)}, {category_col}"
        if dims
        else f"GROUP BY {category_col}"
    )
    sql = f"""
        SELECT
            {dim_select}
            {category_col} AS category,
            COUNT(*) AS count,
            SUM(COUNT(*)) OVER ({partition}) AS n
        FROM {table}
        WHERE {where} AND {category_col} IS NOT NULL
        {group_clause}
    """
    result = con.execute(sql).fetchdf()
    return _attach_wilson_ci(result)


def _median_iqr(
    df: pd.DataFrame,
    value_col: str,
    *,
    where: pd.Series | None = None,
    group_by: list[str] | None = None,
) -> pd.DataFrame:
    """Median/IQR summary of a continuous column, optionally grouped.

    Pure pandas (see the module docstring for why median/IQR are not
    routed through DuckDB). `where` is a boolean mask narrowing which
    rows are considered (e.g. `(df["lti_started"] == True).fillna(False)`
    for an "among those started" denominator); rows with a null
    `value_col` are always excluded regardless of `where`. Returns one
    row per observed `group_by` combination (or a single row if
    `group_by` is empty) with `n`, `median`, `q1`, `q3`.
    """
    dims = _validate_group_by(group_by)
    subset = df
    if where is not None:
        subset = subset.loc[where.fillna(False)]
    subset = subset.loc[subset[value_col].notna()]

    if dims:
        grouped = subset.groupby(dims, observed=True, dropna=False)[value_col]
        out = grouped.agg(
            n="count",
            median="median",
            q1=lambda s: s.quantile(0.25),
            q3=lambda s: s.quantile(0.75),
        ).reset_index()
    else:
        out = pd.DataFrame(
            {
                "n": [subset[value_col].count()],
                "median": [subset[value_col].median()],
                "q1": [subset[value_col].quantile(0.25)],
                "q3": [subset[value_col].quantile(0.75)],
            }
        )
    return out


def _poisson_ci(
    events: int, person_years: float, alpha: float = DEFAULT_CI_ALPHA
) -> tuple[float, float]:
    """Exact Poisson confidence interval for a rate, expressed per
    100 person-years (matching `rate_per_100py`).

    Standard chi-square relationship for an exact Poisson CI:
    `lower = chi2.ppf(alpha/2, 2*events) / 2 / person_years`,
    `upper = chi2.ppf(1 - alpha/2, 2*(events + 1)) / 2 / person_years`,
    each then scaled by 100. `events == 0` gives a lower bound of 0
    (no chi-square quantile needed at zero events). Used only by
    `step8_incidence_rate` -- this is *not* the Wilson interval used
    everywhere else in this module, since a rate is not a bounded
    proportion. Returns `(nan, nan)` if `person_years <= 0`.
    """
    if person_years <= 0:
        return (float("nan"), float("nan"))
    lower = 0.0 if events == 0 else chi2.ppf(alpha / 2, 2 * events) / 2 / person_years
    upper = chi2.ppf(1 - alpha / 2, 2 * (events + 1)) / 2 / person_years
    return (float(lower) * 100, float(upper) * 100)


def _apply_label_maps(table: pd.DataFrame) -> pd.DataFrame:
    """Recode any column in `table` that is one of `_LABEL_MAPS`'s coded
    columns (`TargetGroup`, `Sex`, `TreatGroup`, `RelationWithSource`)
    from its raw numeric code to a readable label; every other column
    is untouched. Applied by every `stepN_*` function as a cosmetic step
    before `suppress_small_cells`, so a reader never has to
    cross-reference the data dictionary. Codes not present in the
    mapping, and `pd.NA`, pass through unchanged.
    """
    table = table.copy()
    for col, mapping in _LABEL_MAPS.items():
        if col in table.columns:
            table[col] = table[col].map(mapping).fillna(table[col])
    return table


def suppress_small_cells(
    table: pd.DataFrame,
    threshold: int = SMALL_CELL_THRESHOLD,
    *,
    n_col: str = "n",
    value_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Mandatory last step before any cascade table leaves this module.

    Any row whose denominator (`n_col`) is below `threshold` has `n_col`
    *and* every column in `value_cols` blanked to `pd.NA`, and is
    flagged via a new `suppressed` boolean column, rather than being
    silently dropped -- the row's grouping/label columns (e.g. `Source`,
    `TargetGroup`) stay visible so a reader can see *that* a cell was
    suppressed, but no small count, percentage, rate, or CI leaves the
    module. `n_col` itself is always blanked when small (even if the
    caller does not list it in `value_cols`): a small raw denominator
    is itself potentially identifying at the smaller sites (Sec 11),
    so it cannot be the one column left visible.

    `value_cols` defaults to "every column except `n_col`" if omitted,
    which is only safe for a table with no other label/dimension
    columns -- every `stepN_*` call site in this module passes
    `value_cols` explicitly whenever its table carries `group_by`
    dimensions or a label column (e.g. `stage`, `regimen`, `metric`),
    since auto-detecting "everything but `n_col`" would wrongly blank
    those too.
    """
    if n_col not in table.columns:
        raise KeyError(
            f"suppress_small_cells: table has no column '{n_col}' to suppress on"
        )
    table = table.copy()
    small = table[n_col].fillna(0) < threshold

    cols = list(value_cols) if value_cols is not None else [
        c for c in table.columns if c != n_col
    ]
    if n_col not in cols:
        cols = [n_col, *cols]

    for col in cols:
        table.loc[small, col] = pd.NA
    table["suppressed"] = small
    return table


# --- Step 1: population profile ---------------------------------------------

#: Columns `step1_baseline_table` passes to `tableone.TableOne` as both
#: `columns` and `categorical` -- everything Sec 7 Step 1 asks for
#: besides `Source` (the `groupby`/strata column itself, already a
#: readable site name) and the two median/IQR summaries computed
#: separately below (age, contacts screened per `IndexCase`).
_STEP1_TABLEONE_COLUMNS: list[str] = [
    "TargetGroup",
    "Sex",
    "age_band",
    "RelationWithSource",
]


def step1_baseline_table(
    df: pd.DataFrame, strata: str = "Source"
) -> dict[str, object]:
    """Step 1: population profile (Table 1), stratified by `strata`.

    Per the Implementation Plan (Phase 4 item 4), the categorical part
    (`TargetGroup`, `Sex`, age band, `RelationWithSource`) is built with
    `tableone.TableOne`; the two counts the Study Plan calls out that
    `TableOne` cannot produce on its own -- median/IQR age, and median/
    IQR number of contacts screened per `IndexCase` -- are computed
    separately and returned alongside it. Returns a dict with three
    keys:

    - `"table1"`: the `TableOne` object (stratified by `strata`; print
      it, or use its `.tableone` attribute for the formatted DataFrame).
    - `"age_summary"`: `_median_iqr(df, "age_years")` (not stratified by
      `strata` here -- `table1` already reports age band counts per
      stratum; this is the separate continuous median/IQR the Study
      Plan asks for).
    - `"contacts_per_index_case"`: one row with `n_index_cases`,
      `median`, `q1`, `q3` of the count of records sharing each
      non-null `IndexCase` (a household-cluster size, not a per-person
      measure, so it is not itself `group_by`-able the way the other
      step functions are).

    Known limitation: small-cell suppression (Sec 11) is *not* yet
    applied to `table1` -- `TableOne`'s exact `.tableone` row/column
    MultiIndex shape needs confirming against the installed version
    (tableone 0.9.6) before a safe post-processor can be written
    against it (see the verification follow-up tracked separately).
    `age_summary`/`contacts_per_index_case` *are* suppressed below,
    since both are plain DataFrames with a known `n` column.
    """
    display = _apply_label_maps(
        df[[strata, *_STEP1_TABLEONE_COLUMNS]].copy()
    )
    table1 = TableOne(
        display,
        columns=_STEP1_TABLEONE_COLUMNS,
        categorical=_STEP1_TABLEONE_COLUMNS,
        groupby=strata,
        pval=False,
    )

    age_summary = suppress_small_cells(
        _median_iqr(df, "age_years"), value_cols=["median", "q1", "q3"]
    )

    contacts_per_index = (
        df.loc[df["IndexCase"].notna()].groupby("IndexCase", observed=True).size()
    )
    contacts_summary = suppress_small_cells(
        pd.DataFrame(
            {
                "n": [contacts_per_index.shape[0]],
                "median": [contacts_per_index.median()],
                "q1": [contacts_per_index.quantile(0.25)],
                "q3": [contacts_per_index.quantile(0.75)],
            }
        ),
        value_cols=["median", "q1", "q3"],
    )

    return {
        "table1": table1,
        "age_summary": age_summary,
        "contacts_per_index_case": contacts_summary,
    }


# --- Step 2: screening cascade -----------------------------------------------

#: stage label -> `derive.cascade_flags` column, in cascade order.
_STEP2_STAGES: dict[str, str] = {
    "screened": "reached_screening",
    "suspected_tb": "reached_suspected",
    "diaskintest_positive": "diaskintest_positive",
    "full_eval": "reached_full_eval",
}


def step2_screening_cascade(
    df: pd.DataFrame, group_by: list[str] | None = None
) -> pd.DataFrame:
    """Step 2: screening cascade (screened -> suspected -> Diaskintest
    positive -> fully evaluated), each stage as a percentage of the full
    cohort (no explicit `where` restriction needed stage-to-stage: each
    later-stage flag is already structurally `<NA>` outside the
    previous stage, per `qc.STRUCTURAL_MISSINGNESS_RULES`, so the
    not-null exclusion in `_flag_proportion` narrows the denominator
    correctly on its own). Long format, one row per (`group_by`...,
    `stage`).
    """
    con = connect(df)
    try:
        parts = []
        for label, flag in _STEP2_STAGES.items():
            part = _flag_proportion(con, flag, group_by=group_by)
            part.insert(0, "stage", label)
            parts.append(part)
        result = pd.concat(parts, ignore_index=True)
    finally:
        con.close()
    result = _apply_label_maps(result)
    return suppress_small_cells(result, value_cols=["count", "pct", "ci_low", "ci_high"])


# --- Step 3: diagnostic outcomes ---------------------------------------------


def step3_diagnostic_outcomes(
    df: pd.DataFrame, group_by: list[str] | None = None
) -> pd.DataFrame:
    """Step 3: diagnostic branch among those fully evaluated.

    Distribution of `diagnosis_branch` (the single-label summary of
    `confirmed_active_tb`/`has_lti`/`no_tb_no_lti`/`no_tb_lti_unknown`
    from `derive.cascade_flags` -- `<NA>` if zero or more than one of
    the four raw flags is `True`, so an ambiguous record is excluded
    from this distribution rather than miscounted into one branch).
    `where="reached_full_eval = TRUE"` is added defensively even though
    `diagnosis_branch` is already `<NA>` outside that scope by
    construction, so this stays correct even if that upstream
    invariant is ever violated by a data-quality edge case.
    """
    con = connect(df)
    try:
        result = _categorical_distribution(
            con, "diagnosis_branch", where="reached_full_eval = TRUE", group_by=group_by
        )
    finally:
        con.close()
    result = _apply_label_maps(result)
    return suppress_small_cells(result, value_cols=["count", "pct", "ci_low", "ci_high"])


# --- Step 4: LTI preventive treatment cascade --------------------------------

#: stage label -> `derive.cascade_flags` column, in cascade order. All
#: three stages are percentages of `eligible_for_lti_tx` (Sec 7 Step 4's
#: "among those eligible" denominator), not retention from the previous
#: stage, per the module's "penetration of stated denominator" design
#: note.
_STEP4_STAGES: dict[str, str] = {
    "recommended": "lti_recommended",
    "prescribed": "lti_prescribed",
    "started": "lti_started",
}

#: Programmatic initiation-delay targets (days) Sec 7 Step 4 asks for,
#: matching `derive._INITIATION_TARGET_DAYS` (kept as a separate literal
#: here rather than importing the private constant, since this module
#: only depends on `derive`'s public column names, not its internals).
_STEP4_INITIATION_TARGETS: list[int] = [30, 60]


def step4_lti_cascade(
    df: pd.DataFrame, group_by: list[str] | None = None
) -> dict[str, pd.DataFrame]:
    """Step 4: LTI preventive-treatment cascade, among those eligible.

    Eligibility is `eligible_for_lti_tx` (`LTI` or `PrevTreatmentRec`,
    Kleene-OR'd in `derive.cascade_flags`). Returns a dict with three
    keys:

    - `"cascade"`: long format, one row per (`group_by`..., `stage`),
      `stage` in `recommended`/`prescribed`/`started`, each a percentage
      of the eligible cohort.
    - `"initiation_delay"`: median/IQR of
      `days_full_eval_to_treatment_start` (diagnosis-to-treatment-start
      delay), restricted to those who started (`lti_started = TRUE`) --
      the interval is only meaningful, and only non-null, for that
      subset.
    - `"initiated_within_target"`: long format, one row per
      (`group_by`..., `target_days`), `target_days` in 30/60, the
      percentage of those who started whose delay was within that many
      days (`derive.time_intervals`'s `initiated_within_30d`/`_60d`).
      Restricted to `lti_started = TRUE` defensively, even though both
      flags are already `<NA>` for anyone who did not start.
    """
    con = connect(df)
    try:
        cascade_parts = []
        for label, flag in _STEP4_STAGES.items():
            part = _flag_proportion(
                con, flag, where="eligible_for_lti_tx = TRUE", group_by=group_by
            )
            part.insert(0, "stage", label)
            cascade_parts.append(part)
        cascade = pd.concat(cascade_parts, ignore_index=True)

        target_parts = []
        for target in _STEP4_INITIATION_TARGETS:
            part = _flag_proportion(
                con,
                f"initiated_within_{target}d",
                where="lti_started = TRUE",
                group_by=group_by,
            )
            part.insert(0, "target_days", target)
            target_parts.append(part)
        initiated_within_target = pd.concat(target_parts, ignore_index=True)
    finally:
        con.close()

    cascade = suppress_small_cells(
        _apply_label_maps(cascade), value_cols=["count", "pct", "ci_low", "ci_high"]
    )
    initiated_within_target = suppress_small_cells(
        _apply_label_maps(initiated_within_target),
        value_cols=["count", "pct", "ci_low", "ci_high"],
    )

    started_mask = (df["lti_started"] == True).fillna(False)  # noqa: E712
    initiation_delay = suppress_small_cells(
        _median_iqr(
            _pandas_frame(df),
            "days_full_eval_to_treatment_start",
            where=started_mask,
            group_by=group_by,
        ),
        value_cols=["median", "q1", "q3"],
    )

    return {
        "cascade": cascade,
        "initiation_delay": initiation_delay,
        "initiated_within_target": initiated_within_target,
    }


# --- Step 5: regimen description ---------------------------------------------

#: regimen label -> raw flag column, both among those started on
#: treatment (`lti_started = TRUE`). `RegBq`/`RegMfx` are not mutually
#: exclusive on the raw schema (a regimen could contain both, or
#: neither, drugs), so each is reported as its own independent
#: proportion of the started cohort rather than as a single-label
#: distribution.
_STEP5_REGIMENS: dict[str, str] = {
    "bedaquiline_containing": "RegBq",
    "moxifloxacin_containing": "RegMfx",
}


def step5_regimen_description(
    df: pd.DataFrame, group_by: list[str] | None = None
) -> pd.DataFrame:
    """Step 5: regimen composition among those started on treatment.

    Proportion on a bedaquiline-containing (`RegBq`) and a
    moxifloxacin-containing (`RegMfx`) regimen, each as a percentage of
    `lti_started = TRUE`. Per Sec 7 Step 5 ("by site and by year of
    treatment start"), callers typically pass
    `group_by=["Source", "treat_start_year"]` to show regimen evolution
    over time; both are in `_ALLOWED_GROUP_DIMS` for exactly this case.
    Long format, one row per (`group_by`..., `regimen`).
    """
    con = connect(df)
    try:
        parts = []
        for label, flag in _STEP5_REGIMENS.items():
            part = _flag_proportion(con, flag, where="lti_started = TRUE", group_by=group_by)
            part.insert(0, "regimen", label)
            parts.append(part)
        result = pd.concat(parts, ignore_index=True)
    finally:
        con.close()
    result = _apply_label_maps(result)
    return suppress_small_cells(result, value_cols=["count", "pct", "ci_low", "ci_high"])


# --- Step 6: adherence and completion -----------------------------------------

#: threshold label -> raw flag column, both among those started.
_STEP6_DOSE_THRESHOLDS: dict[str, str] = {
    "reached_50pc": "Take50pc",
    "reached_100pc": "Take100pc",
}


def step6_adherence_completion(
    df: pd.DataFrame, group_by: list[str] | None = None
) -> dict[str, pd.DataFrame]:
    """Step 6: dose adherence and treatment completion, among those started.

    Returns a dict with three keys, all restricted to `lti_started =
    TRUE` (everything in Sec 7 Step 6 is phrased "among those started"):

    - `"adherence_summary"`: median/IQR of `adherence_ratio`
      (`DosesTaken / SchemaDoses`).
    - `"dose_threshold"`: long format, one row per (`group_by`...,
      `threshold`), `threshold` in `reached_50pc`/`reached_100pc`
      (`Take50pc`/`Take100pc`), each a percentage of those started.
    - `"outcome_distribution"`: distribution of `outcome_branch` (the
      single mutually-exclusive label across `TreatmentCompleted`,
      `TreatmentFinished`, and the five non-completion categories) --
      this is already exactly "a single stacked bar per group summing
      to 100% of those started", per Sec 7 Step 6's presentation note,
      with no further reshaping needed.
    """
    con = connect(df)
    try:
        threshold_parts = []
        for label, flag in _STEP6_DOSE_THRESHOLDS.items():
            part = _flag_proportion(con, flag, where="lti_started = TRUE", group_by=group_by)
            part.insert(0, "threshold", label)
            threshold_parts.append(part)
        dose_threshold = pd.concat(threshold_parts, ignore_index=True)

        outcome_distribution = _categorical_distribution(
            con, "outcome_branch", where="lti_started = TRUE", group_by=group_by
        )
    finally:
        con.close()

    dose_threshold = suppress_small_cells(
        _apply_label_maps(dose_threshold),
        value_cols=["count", "pct", "ci_low", "ci_high"],
    )
    outcome_distribution = suppress_small_cells(
        _apply_label_maps(outcome_distribution),
        value_cols=["count", "pct", "ci_low", "ci_high"],
    )

    started_mask = (df["lti_started"] == True).fillna(False)  # noqa: E712
    adherence_summary = suppress_small_cells(
        _median_iqr(
            _pandas_frame(df), "adherence_ratio", where=started_mask, group_by=group_by
        ),
        value_cols=["median", "q1", "q3"],
    )

    return {
        "adherence_summary": adherence_summary,
        "dose_threshold": dose_threshold,
        "outcome_distribution": outcome_distribution,
    }


# --- Step 7: incentive payment uptake -----------------------------------------

#: incentive label -> (`derive.cascade_flags` receipt column, SQL
#: eligibility expression). Eligibility for each incentive is taken
#: directly from `qc.STRUCTURAL_MISSINGNESS_RULES` (the precondition
#: under which the corresponding raw `SuppX` flag is even expected to be
#: populated) rather than re-derived here, so "eligible" means exactly
#: what the rest of the pipeline already means by it:
#: - `screening`: eligible once screened at all.
#: - `dose_50pc`/`dose_100pc`: eligible once LTI treatment started
#:   (the raw `SuppX` flag itself, not `TakeXpc`, records whether the
#:   dose-threshold incentive was actually paid).
#: - `one_year`: eligible once a treatment group is assigned at all --
#:   `Supp1yearGr23`/`Supp1yearGr1` apply to different `TreatGroup`
#:   values (combined into one `supp_1yr_received` flag in
#:   `derive.cascade_flags`), so eligibility is "assigned to *some*
#:   group", via the `TreatGroup_01/02/03` one-hot columns QC already
#:   validates against `TreatGroup`.
_STEP7_INCENTIVES: dict[str, dict[str, str]] = {
    "screening": {
        "flag": "supp_screening_received",
        "eligible_where": "reached_screening = TRUE",
    },
    "dose_50pc": {"flag": "supp_50pc_received", "eligible_where": "lti_started = TRUE"},
    "dose_100pc": {"flag": "supp_100pc_received", "eligible_where": "lti_started = TRUE"},
    "one_year": {
        "flag": "supp_1yr_received",
        "eligible_where": (
            "(TreatGroup_01 = TRUE OR TreatGroup_02 = TRUE OR TreatGroup_03 = TRUE)"
        ),
    },
}


def step7_incentive_uptake(
    df: pd.DataFrame, group_by: list[str] | None = None
) -> dict[str, pd.DataFrame]:
    """Step 7: incentive-payment uptake among those eligible for each.

    Returns a dict with two keys:

    - `"uptake"`: long format, one row per (`group_by`..., `incentive`),
      `incentive` in `screening`/`dose_50pc`/`dose_100pc`/`one_year`,
      each a percentage of its own eligible cohort (see
      `_STEP7_INCENTIVES`).
    - `"screening_payment_delay"`: median/IQR of the delay (days) from
      `DateScreening` to `DateSuppScreening`, among those who received
      the screening incentive. This is the *only* payment delay
      computable from the raw schema: `DateSupp50pc`/`DateSupp100pc`/
      `DateSupp1yearGr23`/`DateSupp1yearGr1` are themselves the payment
      dates, but the raw data has no corresponding "milestone reached"
      date for the 50%/100%/1-year incentives (only the boolean
      `Take50pc`/`Take100pc` flags and the rescreening flags, no dated
      event) -- inventing one would not be a real delay. This is a
      known data-availability limitation, not an oversight.
    """
    con = connect(df)
    try:
        parts = []
        for label, spec in _STEP7_INCENTIVES.items():
            part = _flag_proportion(
                con, spec["flag"], where=spec["eligible_where"], group_by=group_by
            )
            part.insert(0, "incentive", label)
            parts.append(part)
        uptake = pd.concat(parts, ignore_index=True)
    finally:
        con.close()
    uptake = suppress_small_cells(
        _apply_label_maps(uptake), value_cols=["count", "pct", "ci_low", "ci_high"]
    )

    enriched = _pandas_frame(df)
    enriched = enriched.assign(
        supp_screening_delay_days=(
            enriched["DateSuppScreening"] - enriched["DateScreening"]
        ).dt.days
    )
    received_mask = (enriched["supp_screening_received"] == True).fillna(False)  # noqa: E712
    screening_payment_delay = suppress_small_cells(
        _median_iqr(
            enriched, "supp_screening_delay_days", where=received_mask, group_by=group_by
        ),
        value_cols=["median", "q1", "q3"],
    )

    return {"uptake": uptake, "screening_payment_delay": screening_payment_delay}


# --- Step 8: follow-up and final outcomes -------------------------------------


def step8_followup_outcomes(
    df: pd.DataFrame, analysis_date, group_by: list[str] | None = None
) -> dict[str, pd.DataFrame]:
    """Step 8: follow-up rescreening, final outcome, and incidence rate.

    `analysis_date` is required (not read from `df`) so that "sufficient
    follow-up" is evaluated against a caller-controlled, reproducible
    cutoff -- the same value passed to `derive.build_analysis_table`
    should normally be passed here, but this function recomputes its
    own 24-month censoring mask rather than trusting a persisted column
    (see below), so a different `analysis_date` is also safe to pass if
    a report is being regenerated against a later cutoff.

    Sufficient follow-up has two different windows in this Step, per
    Descriptive Study Plan Sec 7 Step 8 ("re-screened at 1 year ... and
    24 months"):
    - 1-year metrics (`rescreened_1yr`, `no_tb_after_1yr`, and the final-
      outcome distribution) use the persisted `censored` column, which
      `derive.build_analysis_table` already bakes in at the default
      `window_months=12`.
    - 24-month metrics (`rescreened_24mo`, `no_tb_after_24mo`) need a
      *freshly* recomputed `derive.censoring_flag(df, analysis_date,
      window_months=24)`, injected via `connect`'s `extra_columns` --
      the persisted `censored` column is always the 12-month version,
      never 24.
    In both cases "sufficient follow-up" means the flag is `False`
    exactly (`<NA>`, an unknown enrollment date, is conservatively
    treated as *not* sufficient, matching `censoring_flag`'s own
    documented Kleene-style caution).

    Returns a dict with five keys:
    - `"rescreened_1yr"` / `"no_tb_after_1yr"`: percentage of the
      1-year-mature cohort.
    - `"rescreened_24mo"` / `"no_tb_after_24mo"`: percentage of the
      24-month-mature cohort.
    - `"final_outcome_distribution"`: distribution of
      `final_outcome_category` among the 1-year-mature cohort, by
      `group_by`.
    - `"final_outcome_by_completion"`: the same distribution, additionally
      stratified by `completed_or_finished` (Sec 7 Step 8: "stratified
      by whether preventive treatment was completed").
    - `"incidence_rate"`: see `step8_incidence_rate`, included here so
      one call returns everything Step 8 asks for.
    """
    censored_24mo = derive.censoring_flag(df, analysis_date, window_months=24)
    extra = pd.DataFrame({"censored_24mo": censored_24mo}, index=df.index)
    con = connect(df, extra_columns=extra)
    try:
        rescreened_1yr = _flag_proportion(
            con, "rescreened_1yr", where="censored = FALSE", group_by=group_by
        )
        no_tb_after_1yr = _flag_proportion(
            con, "no_tb_after_1yr", where="censored = FALSE", group_by=group_by
        )
        rescreened_24mo = _flag_proportion(
            con, "rescreened_24mo", where="censored_24mo = FALSE", group_by=group_by
        )
        no_tb_after_24mo = _flag_proportion(
            con, "no_tb_after_24mo", where="censored_24mo = FALSE", group_by=group_by
        )
        final_outcome_distribution = _categorical_distribution(
            con, "final_outcome_category", where="censored = FALSE", group_by=group_by
        )
        completion_dims = list(dict.fromkeys([*(group_by or []), "completed_or_finished"]))
        final_outcome_by_completion = _categorical_distribution(
            con,
            "final_outcome_category",
            where="censored = FALSE",
            group_by=completion_dims,
        )
    finally:
        con.close()

    value_cols = ["count", "pct", "ci_low", "ci_high"]
    rescreened_1yr = suppress_small_cells(_apply_label_maps(rescreened_1yr), value_cols=value_cols)
    no_tb_after_1yr = suppress_small_cells(_apply_label_maps(no_tb_after_1yr), value_cols=value_cols)
    rescreened_24mo = suppress_small_cells(_apply_label_maps(rescreened_24mo), value_cols=value_cols)
    no_tb_after_24mo = suppress_small_cells(_apply_label_maps(no_tb_after_24mo), value_cols=value_cols)
    final_outcome_distribution = suppress_small_cells(
        _apply_label_maps(final_outcome_distribution), value_cols=value_cols
    )
    final_outcome_by_completion = suppress_small_cells(
        _apply_label_maps(final_outcome_by_completion), value_cols=value_cols
    )

    return {
        "rescreened_1yr": rescreened_1yr,
        "no_tb_after_1yr": no_tb_after_1yr,
        "rescreened_24mo": rescreened_24mo,
        "no_tb_after_24mo": no_tb_after_24mo,
        "final_outcome_distribution": final_outcome_distribution,
        "final_outcome_by_completion": final_outcome_by_completion,
        "incidence_rate": step8_incidence_rate(df, analysis_date, group_by=group_by),
    }


def step8_incidence_rate(
    df: pd.DataFrame, analysis_date, group_by: list[str] | None = None
) -> pd.DataFrame:
    """Step 8: `TBdeveloped` expressed as an incidence rate per 100
    person-years, among those who started LTI preventive treatment.

    Scoped to `lti_started = TRUE` with a known `DateScreening`: this is
    the "LTBI cohort" Sec 7 Step 8 means by "for descriptive comparison
    with published LTBI cohort rates" -- `TBdeveloped`/`FinalOutcome`
    are only structurally expected once treatment has started (see
    `qc.STRUCTURAL_MISSINGNESS_RULES`), so person-time outside that
    cohort would not be interpretable against this rate anyway.

    Person-time per record runs from `DateScreening` to `DateOutcome`
    if an outcome has been recorded, else to `analysis_date` (standard
    right-censoring at the analysis cutoff for anyone without a
    recorded outcome yet, regardless of *why* it is missing -- this
    subsumes, and is simpler than, a separate censoring-window check
    for this one metric). Negative intervals (a reversed-date QC
    violation) are excluded rather than contributing negative
    person-time. `events` is the count of `TBdeveloped = TRUE` in
    scope; the rate's exact-Poisson CI comes from `_poisson_ci`, *not*
    `wilson_ci` (a rate is not a bounded proportion -- see the module
    docstring).

    Returns one row per observed `group_by` combination (or a single
    row if `group_by` is empty), with `n` (cohort size), `events`,
    `person_years`, `rate_per_100py`, `ci_low`, `ci_high`.
    """
    dims = _validate_group_by(group_by)
    enriched = _pandas_frame(df)

    in_scope = (enriched["lti_started"] == True).fillna(False) & enriched[  # noqa: E712
        "DateScreening"
    ].notna()
    end_date = enriched["DateOutcome"].fillna(pd.Timestamp(analysis_date))
    person_years = (end_date - enriched["DateScreening"]).dt.days / 365.25
    in_scope = in_scope & (person_years >= 0)

    events = (enriched["TBdeveloped"] == True).fillna(False)  # noqa: E712

    work = pd.DataFrame(
        {
            "in_scope": in_scope,
            "person_years": person_years,
            "event": events,
        },
        index=enriched.index,
    )
    for dim in dims:
        work[dim] = enriched[dim]
    work = work.loc[work["in_scope"]]

    if dims:
        grouped = work.groupby(dims, observed=True, dropna=False)
        summary = grouped.agg(
            n=("event", "size"),
            events=("event", "sum"),
            person_years=("person_years", "sum"),
        ).reset_index()
    else:
        summary = pd.DataFrame(
            {
                "n": [work.shape[0]],
                "events": [int(work["event"].sum())],
                "person_years": [work["person_years"].sum()],
            }
        )

    rate = pd.Series(float("nan"), index=summary.index, dtype="float64")
    ci_low = pd.Series(float("nan"), index=summary.index, dtype="float64")
    ci_high = pd.Series(float("nan"), index=summary.index, dtype="float64")
    valid = summary["person_years"] > 0
    rate.loc[valid] = (
        summary.loc[valid, "events"] / summary.loc[valid, "person_years"] * 100
    )
    for idx in summary.index[valid]:
        lo, hi = _poisson_ci(
            int(summary.loc[idx, "events"]), float(summary.loc[idx, "person_years"])
        )
        ci_low.loc[idx] = lo
        ci_high.loc[idx] = hi
    summary["rate_per_100py"] = rate
    summary["ci_low"] = ci_low
    summary["ci_high"] = ci_high

    summary = _apply_label_maps(summary)
    return suppress_small_cells(
        summary, value_cols=["events", "person_years", "rate_per_100py", "ci_low", "ci_high"]
    )


# --- Step 10: site comparison --------------------------------------------------


def step10_site_comparison(df: pd.DataFrame, analysis_date) -> dict[str, object]:
    """Step 10: side-by-side `Source` comparison of every Step 2-8 table.

    Per Sec 7 Step 10, this is "descriptive flagging only, not formal
    between-site hypothesis testing" -- accordingly, this function does
    *not* introduce any new aggregation logic of its own. It simply
    re-runs each `step2_*`...`step8_*` function with
    `group_by=["Source"]` (or `["Source"]` appended where a function
    already strata by something else, e.g. Step 6's dose thresholds),
    so every table a reviewer needs for a side-by-side site comparison
    already has `Source` as a column to compare rows across -- a
    reviewer reads each step's table and compares its `Source` rows
    directly, rather than this function flattening heterogeneous
    schemas (counts, medians, rates) into one artificial combined
    table. `viz.site_comparison_table` (Phase 5) is responsible for any
    further rendering into one visual side-by-side layout.

    Returns a dict keyed by step name, mirroring the individual
    `stepN_*` functions' own return shapes (a `DataFrame` for Steps 2/3,
    a `dict` of `DataFrame`s for Steps 4/6/7/8, per their docstrings).
    """
    return {
        "screening_cascade": step2_screening_cascade(df, group_by=["Source"]),
        "diagnostic_outcomes": step3_diagnostic_outcomes(df, group_by=["Source"]),
        "lti_cascade": step4_lti_cascade(df, group_by=["Source"]),
        "regimen": step5_regimen_description(df, group_by=["Source"]),
        "adherence_completion": step6_adherence_completion(df, group_by=["Source"]),
        "incentive_uptake": step7_incentive_uptake(df, group_by=["Source"]),
        "followup_outcomes": step8_followup_outcomes(df, analysis_date, group_by=["Source"]),
    }
