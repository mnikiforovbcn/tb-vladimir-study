"""Phase 5 - Visualization (viz.py).

This module turns `cascade.py`/`trends.py`'s tables into Plotly figures
and presentation tables for the Descriptive Study Plan Sec 9 chart list.
It never recomputes a percentage, count, CI, or suppression decision
itself -- every number plotted here was already produced and privacy-
checked upstream, so this module's only job is rendering.

Item 2 of the Phase 5 plan: shared cross-cutting helpers, written first
so the chart functions in items 3-8 don't each invent their own
convention for site colors or for handling suppressed cells.

Design notes:
- `_SITE_COLORS` is the single fixed `Source` -> color mapping reused by
  every chart that plots `Source` as a dimension (per-site small
  multiples, `outcome_stacked_bar`, `trend_lines`, `site_comparison_
  table`), so a given site is always the same color across every figure
  in the eventual report -- a reader should never have to re-learn the
  color legend chart-to-chart. Keys match `schema.SOURCE_VALUES` exactly
  (`Source` is already a readable site-name string in the analysis-ready
  table, never a numeric code, so no separate label map is needed here
  the way `cascade._LABEL_MAPS` is needed for `TargetGroup`/`Sex`/
  `TreatGroup`).
- Suppressed-cell policy (Implementation Plan Phase 5 item 2): every
  table handed to this module has already been through
  `cascade.suppress_small_cells` and carries a `suppressed` boolean
  column, with that row's value columns already blanked to `pd.NA`.
  Two things follow, and both are implemented once here rather than
  per chart function:
    1. `_drop_suppressed` removes `suppressed=True` rows from the data
       actually handed to a Plotly trace -- letting Plotly plot a row
       whose values are `pd.NA` would render a gap/zero/break that a
       reader could misread as a real measured zero, rather than "this
       cell was hidden."  Grouping/label columns are not touched, and
       the rows are never deleted from the table you'd render in a
       caption count -- only from the geometry.
    2. `_add_suppression_caption` attaches a one-line caption to the
       figure stating how many cells were suppressed, mirroring the
       privacy note `run_cascade.py` already prepends to
       `cascade_report.md` -- here scoped per-chart (since one report
       mixes charts with very different suppression rates) rather than
       once per report. The caption is emitted even when nothing was
       suppressed: a reviewer seeing "no cells suppressed" is itself
       useful information, not a degenerate case to skip silently.
"""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from tb_cascade.cascade import _LABEL_MAPS, _STEP2_STAGES, SMALL_CELL_THRESHOLD

#: Fixed `Source` -> color mapping, reused anywhere `Source` is a
#: plotted dimension. Keys match `schema.SOURCE_VALUES` exactly
#: (`["Vladimir", "Murom", "Kovrov"]`).
_SITE_COLORS: dict[str, str] = {
    "Vladimir": "#1f77b4",  # blue
    "Murom": "#2ca02c",  # green
    "Kovrov": "#ff7f0e",  # orange
}

#: Shared Plotly annotation style for `_add_suppression_caption`, so
#: every chart's caption sits in the same place with the same look
#: (small, gray, below the plot area) rather than each chart function
#: picking its own position.
_CAPTION_ANNOTATION_STYLE: dict = dict(
    xref="paper",
    yref="paper",
    x=0,
    y=-0.18,
    xanchor="left",
    yanchor="top",
    showarrow=False,
    align="left",
    font=dict(size=10, color="#666666"),
)


def _drop_suppressed(df: pd.DataFrame, *, suppressed_col: str = "suppressed") -> pd.DataFrame:
    """Exclude `suppressed=True` rows (per `cascade.suppress_small_cells`)
    from the data passed to a Plotly trace.

    The row's value columns are already `pd.NA` at this point -- this
    just removes the row from plotted geometry entirely, rather than
    letting Plotly render `NA` as a gap or a literal zero. Does not
    mutate `df`; returns a new, reindexed DataFrame.

    Raises `KeyError` if `suppressed_col` is missing, since that means
    the table was never run through `suppress_small_cells` and plotting
    it directly would risk showing an un-vetted small cell.
    """
    if suppressed_col not in df.columns:
        raise KeyError(
            f"_drop_suppressed: '{suppressed_col}' column not found -- was this "
            "table run through cascade.suppress_small_cells?"
        )
    return df.loc[~df[suppressed_col].astype(bool)].reset_index(drop=True)


def _suppression_caption(df: pd.DataFrame, *, suppressed_col: str = "suppressed") -> str:
    """One-line caption stating how many cells this chart's underlying
    table suppressed, mirroring the privacy note `run_cascade.py`
    prepends to `cascade_report.md` (Descriptive Study Plan Sec 11).

    Always returns a caption, including the zero-suppressed case.
    Counts rows in `df` as given (before `_drop_suppressed`), so the
    denominator in the caption is the full table, not just what's
    plotted.
    """
    if suppressed_col not in df.columns:
        raise KeyError(
            f"_suppression_caption: '{suppressed_col}' column not found -- was "
            "this table run through cascade.suppress_small_cells?"
        )
    n_suppressed = int(df[suppressed_col].astype(bool).sum())
    n_total = len(df)
    if n_suppressed == 0:
        return f"No cells suppressed (n = {n_total})."
    # Pluralization keys off `n_total` (the "of N cells" denominator),
    # not `n_suppressed` -- "1 of 3 cells suppressed" is grammatically
    # plural because there are 3 cells total, even though only 1 of
    # them was suppressed. "1 of 1 cell suppressed" is the only
    # singular case.
    cell_word = "cell" if n_total == 1 else "cells"
    return (
        f"{n_suppressed} of {n_total} {cell_word} suppressed (n < "
        f"{SMALL_CELL_THRESHOLD}) per Descriptive Study Plan Sec 11."
    )


def _add_suppression_caption(
    fig: go.Figure, df: pd.DataFrame, *, suppressed_col: str = "suppressed"
) -> go.Figure:
    """Attach `_suppression_caption`'s text to `fig` as a small gray
    annotation below the plot area, in the shared `_CAPTION_ANNOTATION_
    STYLE` position so every chart function in this module gets the
    same caption convention "for free" rather than reinventing
    placement/styling.

    Mutates `fig` in place (via `add_annotation`) and returns it, so a
    chart function can end with `return _add_suppression_caption(fig, df)`.
    """
    caption = _suppression_caption(df, suppressed_col=suppressed_col)
    fig.add_annotation(text=caption, **_CAPTION_ANNOTATION_STYLE)
    return fig


# --- Item 3: Step 2 screening cascade funnel ---------------------------------

#: Human-readable label per `cascade._STEP2_STAGES` key, for the funnel's
#: y-axis -- the raw keys (`"suspected_tb"`, `"diaskintest_positive"`)
#: are SQL-friendly identifiers, not presentation text.
_STEP2_STAGE_LABELS: dict[str, str] = {
    "screened": "Screened",
    "suspected_tb": "Suspected TB",
    "diaskintest_positive": "Diaskintest positive",
    "full_eval": "Fully evaluated",
}


def _validate_step2_stages(cascade_df: pd.DataFrame, *, caller: str, group_col: str | None) -> None:
    """Shared guard for `funnel_chart`/`funnel_chart_by_group`: the input
    must have exactly one row per `cascade._STEP2_STAGES` stage (times
    one per observed `group_col` value, if given) -- catches a caller
    accidentally passing the wrong step's table, or the wrong shape of
    this one (e.g. missing/extra `group_by`), before it silently
    produces a malformed figure.
    """
    actual_stages = set(cascade_df["stage"]) if "stage" in cascade_df.columns else set()
    expected_stages = set(_STEP2_STAGES)
    if actual_stages != expected_stages:
        raise ValueError(
            f"{caller}: expected stages {sorted(expected_stages)}, got "
            f"{sorted(actual_stages)} -- is this cascade.step2_screening_"
            f"cascade(df{f', group_by=[{group_col!r}]' if group_col else ''})?"
        )
    if group_col is None:
        if len(cascade_df) != len(_STEP2_STAGES):
            raise ValueError(
                f"{caller}: expected exactly {len(_STEP2_STAGES)} rows (one "
                f"per stage, no group_by), got {len(cascade_df)} rows."
            )
    else:
        if group_col not in cascade_df.columns:
            raise KeyError(
                f"{caller}: '{group_col}' column not found -- was this "
                f"cascade.step2_screening_cascade(df, group_by=['{group_col}'])?"
            )
        n_groups = cascade_df[group_col].nunique(dropna=True)
        if len(cascade_df) != len(_STEP2_STAGES) * n_groups:
            raise ValueError(
                f"{caller}: expected exactly one row per (stage, {group_col}) "
                f"combination ({len(_STEP2_STAGES)} stages x {n_groups} "
                f"groups = {len(_STEP2_STAGES) * n_groups} rows), got "
                f"{len(cascade_df)} rows."
            )


def _step2_funnel_trace(plotted: pd.DataFrame) -> go.Funnel:
    """Build the one `go.Funnel` trace shared by `funnel_chart` (item 3)
    and `funnel_chart_by_group` (item 4) -- both render the same
    per-stage funnel geometry/hover/text convention, just arranged into
    a different figure layout (single figure vs. subplot grid), per the
    plan's "distinct layout problem, not a parameter tweak" framing.

    `plotted` must already be ordered per `cascade._STEP2_STAGES` and
    have had `_drop_suppressed` applied -- this helper does neither, so
    each caller's own ordering/filtering step runs first.
    """
    customdata = plotted[["n", "count", "ci_low", "ci_high"]].astype(float)
    return go.Funnel(
        y=[_STEP2_STAGE_LABELS[s] for s in plotted["stage"]],
        x=plotted["pct"],
        customdata=customdata,
        # cascade.py's `pct`/`ci_low`/`ci_high` are 0-1 fractions, not
        # 0-100 -- the d3-format "%" type (not plain "f") multiplies by
        # 100 and appends "%" itself, so it must be used here rather
        # than a hand-rolled "...:.1f}%" suffix.
        texttemplate="%{x:.1%}",
        hovertemplate=(
            "%{y}<br>"
            "%{customdata[1]:.0f} of %{customdata[0]:.0f} (%{x:.1%})<br>"
            "95% CI %{customdata[2]:.1%}-%{customdata[3]:.1%}"
            "<extra></extra>"
        ),
    )


def funnel_chart(cascade_df: pd.DataFrame) -> go.Figure:
    """Step 2 screening cascade funnel (Implementation Plan Phase 5 item 3).

    Takes `cascade.step2_screening_cascade(df)`'s long-format output
    directly (`stage`, `n`, `count`, `pct`, `ci_low`, `ci_high`,
    `suppressed`) called with *no* `group_by` -- exactly one row per
    `cascade._STEP2_STAGES` stage, for the whole cohort. The per-
    `TargetGroup` small-multiples version (Phase 5 item 4) is
    `funnel_chart_by_group`, a separate function, since faceting into a
    subplot grid is a distinct layout problem, not a parameter on this
    figure.

    Plotted by `pct` (not raw `count`), so the funnel reads the same
    regardless of cohort size. Bars are ordered per `cascade._STEP2_
    STAGES` (screened -> suspected_tb -> diaskintest_positive ->
    full_eval) regardless of the input row order, and any
    `suppressed=True` stage is dropped from the funnel geometry (its
    `pct` is already `pd.NA`) with a caption noting how many stages
    were suppressed.
    """
    _validate_step2_stages(cascade_df, caller="funnel_chart", group_col=None)

    ordered = cascade_df.set_index("stage").loc[list(_STEP2_STAGES)].reset_index()
    plotted = _drop_suppressed(ordered)

    fig = go.Figure(_step2_funnel_trace(plotted))
    fig.update_layout(
        title="Screening cascade (% of cohort)",
        xaxis_tickformat=".0%",
    )
    return _add_suppression_caption(fig, ordered)


def funnel_chart_by_group(cascade_df: pd.DataFrame, group_col: str = "TargetGroup") -> go.Figure:
    """Per-`group_col` small multiples of the Step 2 screening funnel
    (Implementation Plan Phase 5 item 4) -- a distinct layout problem
    from `funnel_chart` (item 3), not a parameter on the same figure.
    `group_col` defaults to `"TargetGroup"`, the plan's stated use case
    (`cascade.step2_screening_cascade(df, group_by=["TargetGroup"])`),
    but any single `cascade._ALLOWED_GROUP_DIMS` column works the same
    way -- faceting only needs `group_col` to be a label column
    alongside `stage`/`n`/.../`suppressed`.

    Takes `cascade.step2_screening_cascade(df, group_by=[group_col])`'s
    long-format output directly -- one row per (`stage`, `group_col`
    value). Renders one funnel sub-chart per observed `group_col` value
    in a grid, each sharing the same stage order, x-axis scale, and
    hover/text convention as `funnel_chart`, so the panels are directly
    comparable to each other and to the overall funnel.

    Facets are ordered using `cascade._LABEL_MAPS[group_col]`'s own
    value order when `group_col` is one of its coded columns (e.g.
    TargetGroup always reads Contact -> Homeless -> PLHIV -> Other
    left-to-right), rather than whatever order SQL `GROUP BY` happened
    to return; falls back to alphabetical for an uncoded `group_col`
    (e.g. `Source`).
    """
    _validate_step2_stages(cascade_df, caller="funnel_chart_by_group", group_col=group_col)

    observed = set(cascade_df[group_col].dropna())
    if group_col in _LABEL_MAPS:
        canonical = [v for v in _LABEL_MAPS[group_col].values() if v in observed]
        canonical += sorted(observed - set(canonical))
    else:
        canonical = sorted(observed)

    n = len(canonical)
    n_cols = math.ceil(math.sqrt(n)) if n else 1
    n_rows = math.ceil(n / n_cols) if n else 1

    fig = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=[str(g) for g in canonical])
    for idx, group_value in enumerate(canonical):
        row, col = divmod(idx, n_cols)
        facet = cascade_df.loc[cascade_df[group_col] == group_value]
        ordered = facet.set_index("stage").loc[list(_STEP2_STAGES)].reset_index()
        plotted = _drop_suppressed(ordered)
        fig.add_trace(_step2_funnel_trace(plotted), row=row + 1, col=col + 1)

    fig.update_xaxes(tickformat=".0%")
    fig.update_layout(
        title=f"Screening cascade by {group_col} (% of cohort)",
        showlegend=False,
    )
    return _add_suppression_caption(fig, cascade_df)
