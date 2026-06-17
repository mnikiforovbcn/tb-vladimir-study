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

import plotly.graph_objects as go
import pandas as pd

from tb_cascade.cascade import SMALL_CELL_THRESHOLD

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
