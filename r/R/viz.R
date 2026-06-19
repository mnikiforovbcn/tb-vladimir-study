#' Site color palette shared across every chart in this module
#' @export
SITE_COLORS <- c(Vladimir = "#2C7FB8", Kovrov = "#41AB5D", Murom = "#D95F0E")

#' Drop suppressed rows before plotting
#'
#' [suppress_small_cells()] blanks every numeric column on a suppressed row
#' to `NA` but leaves the row itself in place; plotting an `NA`-valued bar
#' or segment would either error or render as a misleading blank, so every
#' chart in this module drops suppressed rows entirely and relies on
#' [.suppression_caption()] to disclose that some categories are omitted.
#' @keywords internal
.drop_suppressed <- function(df) {
  if (!"suppressed" %in% names(df)) return(df)
  df[!df$suppressed, ]
}

#' Standard disclosure-control caption for suppressed-cell charts
#' @keywords internal
.suppression_caption <- function() {
  sprintf(
    "Cells with counts below %d are suppressed and omitted, per the Study Plan's disclosure-control policy.",
    SMALL_CELL_THRESHOLD
  )
}

#' Recode the raw 1-4 `TargetGroup` code to [TARGET_GROUP_LABELS], for display
#' @keywords internal
.label_target_group <- function(target_group) {
  factor(target_group, levels = seq_along(TARGET_GROUP_LABELS), labels = TARGET_GROUP_LABELS)
}

#' Cascade/funnel chart: proportion of the cohort reaching each milestone
#'
#' Designed for the output of any Step 2-8 milestone-proportion function
#' ([screening_cascade()], [diagnostic_outcomes()], [lti_treatment_cascade()],
#' [dose_threshold_uptake()], [followup_outcomes()], or [step_proportion()]
#' directly): one bar per `milestone`, height equal to the Wilson
#' `proportion`, with a 95% CI error bar and a percentage label.
#' Suppressed milestones are dropped rather than drawn as an empty bar
#' (Study Plan SS11); see [.suppression_caption()].
#'
#' @param df A `milestone`-plus-[step_proportion()]-shaped tibble.
#' @param facet_var Optional column name in `df` to facet by (e.g.
#'   `"TargetGroup"` or `"Source"`), producing one small-multiple panel
#'   per group -- the cascade-by-target-group view (Study Plan SS9) and
#'   the Step 10 cross-site comparison view share this one function.
#' @return A `ggplot` object.
#' @export
funnel_chart <- function(df, facet_var = NULL) {
  plot_df <- .drop_suppressed(df)
  if (identical(facet_var, "TargetGroup")) {
    plot_df$TargetGroup <- .label_target_group(plot_df$TargetGroup)
  }

  p <- ggplot2::ggplot(plot_df, ggplot2::aes(x = .data$milestone, y = .data$proportion))

  p <- if (identical(facet_var, "Source") && "Source" %in% names(plot_df)) {
    p + ggplot2::geom_col(ggplot2::aes(fill = .data$Source), show.legend = FALSE) +
      ggplot2::scale_fill_manual(values = SITE_COLORS)
  } else {
    p + ggplot2::geom_col(fill = "#2C7FB8")
  }

  p <- p +
    ggplot2::geom_errorbar(
      ggplot2::aes(ymin = .data$ci_lower, ymax = .data$ci_upper), width = 0.2, linewidth = 0.4
    ) +
    ggplot2::geom_text(
      ggplot2::aes(label = scales::percent(.data$proportion, accuracy = 1)), vjust = -0.6, size = 3
    ) +
    ggplot2::scale_y_continuous(
      labels = scales::percent, limits = c(0, NA), expand = ggplot2::expansion(mult = c(0, 0.15))
    ) +
    ggplot2::labs(x = NULL, y = "Proportion of cohort", caption = .suppression_caption()) +
    ggplot2::theme_minimal() +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 30, hjust = 1))

  if (!is.null(facet_var)) p <- p + ggplot2::facet_wrap(facets = facet_var)
  p
}

#' Outcome-composition stacked bar chart, by site or target group
#'
#' Designed for the output of [outcome_breakdown()] or
#' [final_outcome_distribution()]: one stacked bar per group, segments
#' sized by `proportion` within `category_col`. Suppressed categories are
#' dropped rather than redistributed, so segments may not sum to exactly
#' 100% within a group when a category was suppressed.
#'
#' @param df A [.category_breakdown()]-shaped tibble (`n`, `total`,
#'   `proportion`, `suppressed`, plus a category column and a grouping
#'   column).
#' @param category_col Character: name of the category column in `df`
#'   (e.g. `"outcome_branch"`, `"final_outcome_category"`).
#' @param group_var Character: name of the grouping column to put on the
#'   x-axis (e.g. `"Source"`, `"TargetGroup"`).
#' @return A `ggplot` object.
#' @export
outcome_stacked_bar <- function(df, category_col, group_var) {
  plot_df <- .drop_suppressed(df)
  if (identical(group_var, "TargetGroup")) {
    plot_df$TargetGroup <- .label_target_group(plot_df$TargetGroup)
  }

  ggplot2::ggplot(
    plot_df,
    ggplot2::aes(x = .data[[group_var]], y = .data$proportion, fill = .data[[category_col]])
  ) +
    ggplot2::geom_col(position = "stack") +
    ggplot2::scale_y_continuous(labels = scales::percent) +
    ggplot2::labs(x = NULL, y = "Proportion", fill = NULL, caption = .suppression_caption()) +
    ggplot2::theme_minimal()
}

#' Zero-filled quarterly trend line chart
#'
#' Designed for [quarterly_counts()]/[enrollment_trends()] output: `n`
#' against `quarter` (an ordered factor), one line per `color_var`.
#' Structural zero quarters stay on the line; suppressed nonzero small
#' counts are genuine missing data and create a gap rather than being
#' interpolated or dropped, since a visible gap correctly signals "a
#' small, undisclosed count occurred here," unlike a true zero.
#'
#' @param df A [quarterly_counts()]/[enrollment_trends()]-shaped tibble.
#' @param color_var Character: column name to map to line color; defaults
#'   to `"milestone"` if present in `df`, else `NULL` (a single line).
#' @return A `ggplot` object.
#' @export
trend_line_chart <- function(df, color_var = if ("milestone" %in% names(df)) "milestone" else NULL) {
  mapping <- if (is.null(color_var)) {
    ggplot2::aes(x = .data$quarter, y = .data$n, group = 1)
  } else {
    ggplot2::aes(x = .data$quarter, y = .data$n, color = .data[[color_var]], group = .data[[color_var]])
  }

  ggplot2::ggplot(df, mapping) +
    ggplot2::geom_line(na.rm = TRUE) +
    ggplot2::geom_point(na.rm = TRUE, size = 1) +
    ggplot2::labs(x = "Quarter", y = "Count", color = NULL, caption = .suppression_caption()) +
    ggplot2::theme_minimal() +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1))
}

#' Render [table1()] as a styled `gt` table, with a small-cell caveat footnote
#'
#' [table1()] is a `gtsummary::tbl_summary()` over the full cohort per
#' group, not a cascade-step numerator/denominator pair, so it is never
#' passed through [suppress_small_cells()]. A small stratified cell can
#' still occur (e.g. a `RelationWithSource` level at Murom, n=380), so the
#' Study Plan's disclosure-control policy is surfaced here as an explicit
#' footnote instead of automatic suppression.
#' @param tbl1 A `gtsummary::tbl_summary` object, as returned by [table1()].
#' @return A `gt_tbl` object.
#' @export
render_table1 <- function(tbl1) {
  gtsummary::as_gt(tbl1) |>
    gt::tab_footnote(
      footnote = paste(
        "Counts below", SMALL_CELL_THRESHOLD,
        "in any stratified cell should be treated as indicative only and not reported externally,",
        "per the Study Plan's disclosure-control policy."
      )
    )
}

#' Step 10 site-comparison table: a wide, side-by-side `gt` rendering
#'
#' Pivots [site_comparison()]'s long `step`/`milestone`/`Source` table so
#' each site is a column, grouped by `step` -- the "side-by-side summary
#' table (Vladimir / Kovrov / Murom)" the Study Plan's Step 10 calls for.
#' Suppressed cells display as `"<5"` rather than being blanked outright,
#' so the reader knows a milestone was reached but the count is withheld,
#' as distinct from a cell that is empty because a milestone does not
#' apply at that site.
#' @param result A [site_comparison()]-shaped tibble.
#' @return A `gt_tbl` object.
#' @export
site_comparison_table <- function(result) {
  display <- result |>
    dplyr::mutate(
      cell = dplyr::if_else(
        .data$suppressed,
        sprintf("<%d", SMALL_CELL_THRESHOLD),
        sprintf("%d/%d (%s)", as.integer(.data$x), as.integer(.data$n), scales::percent(.data$proportion, accuracy = 1))
      )
    ) |>
    dplyr::select("step", "milestone", "Source", "cell") |>
    tidyr::pivot_wider(names_from = "Source", values_from = "cell")

  gt::gt(display, groupname_col = "step") |>
    gt::tab_header(title = "Step 10: Cascade proportions by site") |>
    gt::cols_label(milestone = "Milestone") |>
    gt::tab_footnote(footnote = .suppression_caption())
}

#' Point `RSTUDIO_PANDOC` at Quarto's bundled pandoc if no other pandoc is on PATH
#'
#' [htmlwidgets::saveWidget()]'s `selfcontained = TRUE` requires pandoc;
#' this machine has no standalone pandoc install, only the copy bundled
#' inside the Quarto install (Phase 0). Falls back to `FALSE` (a
#' non-self-contained HTML plus a sibling `_files/` directory) if no
#' pandoc can be found at all, rather than erroring.
#' @return `TRUE` if pandoc is available (so `selfcontained = TRUE` is safe).
#' @keywords internal
.ensure_pandoc <- function() {
  if (rmarkdown::pandoc_available()) return(TRUE)
  quarto_bin <- Sys.which("quarto")
  if (nzchar(quarto_bin)) {
    candidate <- file.path(dirname(dirname(quarto_bin)), "tools")
    if (file.exists(file.path(candidate, "pandoc.exe")) || file.exists(file.path(candidate, "pandoc"))) {
      Sys.setenv(RSTUDIO_PANDOC = candidate)
    }
  }
  rmarkdown::pandoc_available()
}

#' Export a chart or table to file
#'
#' A `ggplot` is written as a static PNG via [ggplot2::ggsave()] and, if
#' `interactive = TRUE`, also as an interactive HTML page via
#' `plotly::ggplotly()` + [htmlwidgets::saveWidget()]. A `gt_tbl` is
#' written as an HTML page via [gt::gtsave()] only -- `gt`'s PNG export
#' requires a headless-browser dependency (`webshot2`/Chrome) that this
#' project does not otherwise need, so static table images are out of
#' scope; tables are consumed directly by the Quarto report instead.
#' @param plot A `ggplot` or `gt_tbl` object.
#' @param path Output path, without extension; `.png`/`.html` is appended.
#' @param interactive If `TRUE` (the default), also write an interactive
#'   HTML version (ignored for `gt_tbl`, which is always HTML).
#' @param width,height PNG dimensions, in inches; only used for `ggplot`.
#' @return `path`, invisibly.
#' @export
export <- function(plot, path, interactive = TRUE, width = 8, height = 5) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)

  if (inherits(plot, "gt_tbl")) {
    gt::gtsave(plot, paste0(path, ".html"))
  } else {
    ggplot2::ggsave(paste0(path, ".png"), plot, width = width, height = height)
    if (interactive) {
      htmlwidgets::saveWidget(
        plotly::ggplotly(plot), paste0(path, ".html"), selfcontained = .ensure_pandoc()
      )
    }
  }
  invisible(path)
}
