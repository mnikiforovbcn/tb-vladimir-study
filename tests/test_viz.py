"""Phase 5 tests: every `viz.py` chart/table function (Implementation Plan
Phase 5 item 10), exercised two ways per function, per the plan's own
item 10 text:

1. Against the real analysis-ready table built from the same synthetic
   fixture used by `test_cascade.py`/`test_trends.py`
   (`tests/fixtures/synthetic_rows.csv` ->
   `derive.build_analysis_table(df, "2020-02-01")`), feeding the real
   `cascade.py`/`trends.py` output straight into the matching `viz.py`
   function. `viz.py` never recomputes a number itself, so these tests
   check only what `viz.py` does with already-verified upstream output
   (shape it into the right trace/table types, order things correctly,
   attach a caption) -- not the underlying counts/percentages, which
   `test_cascade.py`/`test_trends.py` already cover. Where a real
   fixture number is asserted here (e.g. `trend_lines`'s quarterly
   counts), it is copied from those files' own hand-verified numbers,
   not re-derived.
2. Against a hand-built "deliberately all-suppressed" table -- every row
   `suppressed=True`, value columns already `pd.NA` -- asserting the
   call does not raise and that the suppressed rows are excluded from
   the plotted trace/table data itself (an empty trace, or zero
   rendered rows), not merely hidden by some display property.

`export()` is tested separately: a real PNG and HTML file must land on
disk with nonzero size (pytest's `tmp_path` fixture).

This file cannot itself be executed in a sandbox without `duckdb`/`scipy`/
`statsmodels`/`tableone`/`kaleido` installed (`viz.py` imports `cascade.py`
at module level, which imports all four; `export` additionally needs a
working `kaleido`) -- it is meant to run in the project's real virtualenv
(`pytest`).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from tb_cascade import cascade, derive, trends, viz
from tb_cascade.cascade import _STEP2_STAGES
from tb_cascade.io import DATE_COLUMNS, DTYPE_MAP

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_rows.csv"
ANALYSIS_DATE = "2020-02-01"


@pytest.fixture(scope="module")
def raw_df() -> pd.DataFrame:
    """Load the synthetic fixture with the same dtype/parse_dates logic as `io.load_raw`."""
    frame = pd.read_csv(FIXTURE_PATH, dtype=DTYPE_MAP, parse_dates=DATE_COLUMNS)
    for col in DATE_COLUMNS:
        if not pd.api.types.is_datetime64_any_dtype(frame[col]):
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
    return frame


@pytest.fixture(scope="module")
def df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """The real analysis-ready table every `viz.py` test below renders from."""
    return derive.build_analysis_table(raw_df, ANALYSIS_DATE)


@pytest.fixture(scope="module")
def step1(df: pd.DataFrame) -> dict:
    return cascade.step1_baseline_table(df)


@pytest.fixture(scope="module")
def step2_whole_cohort(df: pd.DataFrame) -> pd.DataFrame:
    return cascade.step2_screening_cascade(df)


@pytest.fixture(scope="module")
def step2_by_target_group(df: pd.DataFrame) -> pd.DataFrame:
    return cascade.step2_screening_cascade(df, group_by=["TargetGroup"])


@pytest.fixture(scope="module")
def step6_outcome_by_source(df: pd.DataFrame) -> pd.DataFrame:
    return cascade.step6_adherence_completion(df, group_by=["Source"])["outcome_distribution"]


@pytest.fixture(scope="module")
def step9_trend_df(df: pd.DataFrame) -> pd.DataFrame:
    return trends.step9_quarterly_trends(df)


@pytest.fixture(scope="module")
def step10(df: pd.DataFrame) -> dict:
    return cascade.step10_site_comparison(df, ANALYSIS_DATE)


def _all_suppressed_table(n_rows: int = 2) -> pd.DataFrame:
    """A minimal generic table with `n_rows` rows, every one already
    suppressed -- used wherever a test only needs *some* table with a
    `suppressed` column (e.g. `site_comparison_table`'s sub-tables,
    which `_dataframe_to_table` renders column-agnostically), not a
    specific step's real schema."""
    return pd.DataFrame(
        {
            "label": [f"row{i}" for i in range(n_rows)],
            "n": [pd.NA] * n_rows,
            "suppressed": [True] * n_rows,
        }
    )


def _all_suppressed_step10_dict() -> dict:
    """A `step10_site_comparison`-shaped dict, every leaf table all-
    suppressed. Built from `viz._STEP10_TITLES`'s own key structure
    (rather than re-listing all dozen sub-table names a second time)
    so this fixture can't silently drift out of sync with `site_
    comparison_table`'s real input contract."""
    fake: dict = {}
    for key, titles in viz._STEP10_TITLES.items():
        if isinstance(titles, dict):
            fake[key] = {sub_key: _all_suppressed_table() for sub_key in titles}
        else:
            fake[key] = _all_suppressed_table()
    return fake


def _assert_all_tables_empty(value) -> None:
    """Recursively assert every `go.Figure` reachable from `value` (a
    plain figure, or a dict/nested dict of figures, matching `viz.py`'s
    own "mirror the input shape" return convention) has zero rendered
    table rows and still carries a caption."""
    if isinstance(value, dict):
        for v in value.values():
            _assert_all_tables_empty(v)
        return
    assert isinstance(value, go.Figure)
    cells = value.data[0].cells.values
    if cells:
        assert len(cells[0]) == 0
    assert value.layout.annotations


# --- Item 3: Step 2 screening cascade funnel -----------------------------------


def test_funnel_chart_happy_path(step2_whole_cohort):
    """Whole-cohort numbers from `test_cascade.py::test_step2_whole_cohort`:
    all four stages have n >= 5, so none are suppressed and all four
    appear, in `cascade._STEP2_STAGES` order regardless of input order."""
    fig = viz.funnel_chart(step2_whole_cohort)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert isinstance(fig.data[0], go.Funnel)
    assert list(fig.data[0].y) == ["Screened", "Suspected TB", "Diaskintest positive", "Fully evaluated"]
    assert fig.layout.annotations[0].text == "No cells suppressed (n = 4)."


def test_funnel_chart_all_suppressed():
    fake = pd.DataFrame(
        {
            "stage": list(_STEP2_STAGES),
            "n": [pd.NA] * 4,
            "count": [pd.NA] * 4,
            "pct": [pd.NA] * 4,
            "ci_low": [pd.NA] * 4,
            "ci_high": [pd.NA] * 4,
            "suppressed": [True] * 4,
        }
    )
    fig = viz.funnel_chart(fake)
    assert len(fig.data[0].y) == 0
    assert len(fig.data[0].x) == 0
    assert fig.layout.annotations[0].text == "4 of 4 cells suppressed (n < 5) per Descriptive Study Plan Sec 11."


def test_funnel_chart_wrong_stages_raises(step2_whole_cohort):
    bad = step2_whole_cohort.loc[step2_whole_cohort["stage"] != "screened"]
    with pytest.raises(ValueError):
        viz.funnel_chart(bad)


# --- Item 4: per-group funnel small multiples ----------------------------------


def test_funnel_chart_by_group_happy_path(step2_by_target_group):
    n_groups = step2_by_target_group["TargetGroup"].dropna().nunique()
    fig = viz.funnel_chart_by_group(step2_by_target_group, group_col="TargetGroup")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == n_groups
    for trace in fig.data:
        assert isinstance(trace, go.Funnel)
        assert len(trace.y) <= 4
    assert fig.layout.annotations


def test_funnel_chart_by_group_all_suppressed():
    rows = [
        {
            "stage": stage,
            "TargetGroup": group,
            "n": pd.NA,
            "count": pd.NA,
            "pct": pd.NA,
            "ci_low": pd.NA,
            "ci_high": pd.NA,
            "suppressed": True,
        }
        for group in ("Contact", "Homeless")
        for stage in _STEP2_STAGES
    ]
    fake = pd.DataFrame(rows)
    fig = viz.funnel_chart_by_group(fake, group_col="TargetGroup")
    assert len(fig.data) == 2
    for trace in fig.data:
        assert len(trace.y) == 0
    # `make_subplots(subplot_titles=...)` adds one annotation per facet
    # title (e.g. "Contact", "Homeless") ahead of the suppression
    # caption, which `_add_suppression_caption` appends last via
    # `add_annotation` -- so the caption is the *last* annotation, not
    # the first, on this faceted figure (unlike every other chart in
    # this module, which has no other annotations to begin with).
    assert fig.layout.annotations[-1].text == "8 of 8 cells suppressed (n < 5) per Descriptive Study Plan Sec 11."


# --- Item 5: outcome composition stacked bar -----------------------------------


def test_outcome_stacked_bar_happy_path(step6_outcome_by_source):
    """From `test_cascade.py::test_step6_outcome_distribution_excludes_
    ambiguous_branches`: n=8, count=8, pct=1.0, single category
    `"completed"`, not suppressed; with `group_by=["Source"]`, every one
    of those 8 records is `Source="Vladimir"` (Kovrov never reaches
    `lti_started=True`), so exactly one bar, one trace."""
    fig = viz.outcome_stacked_bar(step6_outcome_by_source, group_by=["Source"])
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert isinstance(fig.data[0], go.Bar)
    assert fig.data[0].name == "Completed (100% of doses)"
    assert list(fig.data[0].x) == ["Vladimir"]
    assert list(fig.data[0].y) == [1.0]
    assert fig.layout.annotations[0].text == "No cells suppressed (n = 1)."


def test_outcome_stacked_bar_all_suppressed():
    fake = pd.DataFrame(
        {
            "category": ["completed"],
            "count": [pd.NA],
            "n": [pd.NA],
            "pct": [pd.NA],
            "ci_low": [pd.NA],
            "ci_high": [pd.NA],
            "suppressed": [True],
            "Source": ["Vladimir"],
        }
    )
    fig = viz.outcome_stacked_bar(fake, group_by=["Source"])
    assert len(fig.data) == 0
    assert fig.layout.annotations[0].text == "1 of 1 cell suppressed (n < 5) per Descriptive Study Plan Sec 11."


def test_outcome_stacked_bar_unknown_category_raises(step6_outcome_by_source):
    bad = step6_outcome_by_source.copy()
    bad["category"] = "not_a_real_branch"
    with pytest.raises(ValueError):
        viz.outcome_stacked_bar(bad, group_by=["Source"])


# --- Item 6: Step 9 quarterly trend lines --------------------------------------


def test_trend_lines_happy_path(step9_trend_df):
    """From `test_trends.py`: enrollment has 2019-Q1 (n=14, not
    suppressed) and 2019-Q2 (n=3, suppressed); treatment_initiation has
    only 2019-Q1 (n=9, not suppressed); outcome has only 2019-Q3 (n=10,
    not suppressed). The combined quarter range is 2019-Q1..Q3, so:
    enrollment plots Q1=14 and a zero-filled Q3=0 (Q2 dropped, it was
    suppressed, not a true gap); treatment_initiation plots Q1=9 and
    zero-filled Q2=0/Q3=0; outcome plots zero-filled Q1=0/Q2=0 and
    Q3=10. This is the central zero-fill-vs-suppression-drop behavior
    `trend_lines` exists to get right."""
    fig = viz.trend_lines(step9_trend_df)
    assert len(fig.data) == 3
    by_name = {trace.name: trace for trace in fig.data}

    assert list(by_name["Enrollment"].y) == [14, 0]
    assert list(by_name["Treatment initiation"].y) == [9, 0, 0]
    assert list(by_name["Outcome"].y) == [0, 0, 10]

    assert fig.layout.annotations[0].text == "1 of 4 cells suppressed (n < 5) per Descriptive Study Plan Sec 11."


def test_trend_lines_all_suppressed():
    """All three metrics present, each with exactly one suppressed row
    in the same single quarter -- no metric has any other quarter to
    zero-fill from, so every metric is dropped entirely rather than
    falling back to a flat zero line."""
    fake = pd.DataFrame(
        {
            "metric": ["enrollment", "treatment_initiation", "outcome"],
            "year": [2019, 2019, 2019],
            "quarter": [1, 1, 1],
            "n": [pd.NA, pd.NA, pd.NA],
            "suppressed": [True, True, True],
        }
    )
    fig = viz.trend_lines(fake)
    assert len(fig.data) == 0
    assert fig.layout.annotations[0].text == "3 of 3 cells suppressed (n < 5) per Descriptive Study Plan Sec 11."


def test_trend_lines_wrong_columns_raises(step9_trend_df):
    bad = step9_trend_df.assign(extra_col=1)
    with pytest.raises(ValueError):
        viz.trend_lines(bad)


# --- Item 7: Step 1 baseline table ----------------------------------------------


def test_baseline_table_happy_path(step1):
    """From `test_cascade.py`: age_summary n=17/median=33.8/q1=30.9/q3=33.8
    (rounded to 1 decimal by `_summary_row_to_table`), not suppressed;
    contacts_per_index_case n=14/median=q1=q3=1.0, not suppressed."""
    result = viz.baseline_table(step1)
    assert set(result.keys()) == {"table1", "age_summary", "contacts_per_index_case"}

    assert result["table1"].layout.title.text == "Baseline characteristics by Source (Table 1)"
    assert result["table1"].layout.annotations[0].text == viz._TABLE1_SUPPRESSION_CAVEAT

    age_cells = result["age_summary"].data[0].cells.values
    assert [c[0] for c in age_cells] == ["17", "33.8", "30.9", "33.8"]
    assert result["age_summary"].layout.annotations[0].text == "No cells suppressed (n = 1)."

    contacts_cells = result["contacts_per_index_case"].data[0].cells.values
    assert [c[0] for c in contacts_cells] == ["14", "1.0", "1.0", "1.0"]
    assert result["contacts_per_index_case"].layout.annotations[0].text == "No cells suppressed (n = 1)."


def test_baseline_table_all_suppressed_summary_rows(step1):
    fake_step1 = {
        "table1": step1["table1"],
        "age_summary": pd.DataFrame({"n": [pd.NA], "median": [pd.NA], "q1": [pd.NA], "q3": [pd.NA], "suppressed": [True]}),
        "contacts_per_index_case": pd.DataFrame(
            {"n": [pd.NA], "median": [pd.NA], "q1": [pd.NA], "q3": [pd.NA], "suppressed": [True]}
        ),
    }
    result = viz.baseline_table(fake_step1)
    for key in ("age_summary", "contacts_per_index_case"):
        cells = result[key].data[0].cells.values
        assert len(cells[0]) == 0
        assert result[key].layout.annotations[0].text == "1 of 1 cell suppressed (n < 5) per Descriptive Study Plan Sec 11."


def test_baseline_table_missing_key_raises():
    with pytest.raises(KeyError):
        viz.baseline_table({})


# --- Item 8: Step 10 site comparison tables -------------------------------------


def test_site_comparison_table_happy_path(step10):
    result = viz.site_comparison_table(step10)
    assert set(result.keys()) == set(step10.keys())

    for key, value in step10.items():
        if isinstance(value, dict):
            assert set(result[key].keys()) == set(value.keys())
        else:
            assert isinstance(result[key], go.Figure)

    assert result["screening_cascade"].layout.title.text == "Screening cascade by site"
    assert result["lti_cascade"]["initiation_delay"].layout.title.text == "Initiation delay by site"
    assert result["followup_outcomes"]["incidence_rate"].layout.title.text == "Incidence rate by site"

    sc_df = step10["screening_cascade"]
    sc_fig = result["screening_cascade"]
    assert list(sc_fig.data[0].header.values) == list(sc_df.columns)
    n_dropped = int(sc_df["suppressed"].astype(bool).sum())
    assert len(sc_fig.data[0].cells.values[0]) == len(sc_df) - n_dropped


def test_site_comparison_table_all_suppressed():
    result = viz.site_comparison_table(_all_suppressed_step10_dict())
    _assert_all_tables_empty(result)


def test_site_comparison_table_missing_key_raises():
    with pytest.raises(KeyError):
        viz.site_comparison_table({})


# --- Item 9: figure export -------------------------------------------------------


def test_export_writes_nonzero_png_and_html(tmp_path):
    fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
    result = viz.export(fig, tmp_path / "nested" / "chart")

    assert result["png"].exists() and result["png"].stat().st_size > 0
    assert result["html"].exists() and result["html"].stat().st_size > 0
