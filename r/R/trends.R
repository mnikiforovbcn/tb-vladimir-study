#' Step 9 quarterly counts of a date-stamped milestone, zero-filled for empty quarters
#'
#' Quarters with zero events are kept (not dropped) so a trend line shows
#' true programmatic gaps (e.g., COVID-19-era disruption) rather than
#' missing data points. Suppression differs from [suppress_small_cells()]:
#' a structural zero is not a disclosure risk and must stay visible as
#' `0`, so only *nonzero* counts below [SMALL_CELL_THRESHOLD] are blanked.
#'
#' @param df Analysis-ready table.
#' @param date_col Character: name of a Date column in `df` (e.g.
#'   `"DateScreening"`, `"DatePrevTreatmentStart"`, `"DateOutcome"`).
#' @param group_vars Character vector of additional grouping columns
#'   (e.g. `"Source"`); the quarter range is zero-filled within every
#'   combination of `group_vars` present in the data.
#' @param quarter_levels Optional character vector of `"YYYY Q#"` quarters
#'   to use as the zero-filled range and factor levels, overriding the
#'   range derived from `date_col`. Used by [enrollment_trends()] so every
#'   milestone shares one consistent, combinable ordered factor.
#' @return A tibble: `group_vars` columns, `quarter` (an ordered factor,
#'   `"YYYY Q#"`), `n`, `suppressed`.
#' @export
quarterly_counts <- function(df, date_col, group_vars = character(0), quarter_levels = NULL) {
  dated <- df[!is.na(df[[date_col]]), ]
  dated <- dplyr::mutate(
    dated,
    quarter = paste0(lubridate::year(.data[[date_col]]), " Q", lubridate::quarter(.data[[date_col]]))
  )

  counted <- dated |>
    dplyr::count(dplyr::across(dplyr::all_of(c(group_vars, "quarter"))), name = "n")

  all_quarters <- quarter_levels
  if (is.null(all_quarters)) {
    full_range <- seq(
      min(dated[[date_col]], na.rm = TRUE), max(dated[[date_col]], na.rm = TRUE),
      by = "quarter"
    )
    all_quarters <- unique(paste0(lubridate::year(full_range), " Q", lubridate::quarter(full_range)))
  }

  scaffold <- if (length(group_vars) == 0L) {
    tibble::tibble(quarter = all_quarters)
  } else {
    group_values <- dplyr::distinct(dated, dplyr::across(dplyr::all_of(group_vars)))
    tidyr::crossing(group_values, quarter = all_quarters)
  }

  result <- scaffold |>
    dplyr::left_join(counted, by = c(group_vars, "quarter")) |>
    dplyr::mutate(
      n = dplyr::if_else(is.na(.data$n), 0L, .data$n),
      quarter = factor(.data$quarter, levels = all_quarters, ordered = TRUE)
    ) |>
    dplyr::arrange(dplyr::across(dplyr::all_of(c(group_vars, "quarter"))))

  result$suppressed <- result$n > 0L & result$n < SMALL_CELL_THRESHOLD
  result$n[result$suppressed] <- NA_integer_
  result
}

#' Step 9 enrollment, treatment-initiation, and outcome trends in one tidy table
#'
#' All three milestones share one zero-filled quarter range -- the union
#' across `DateScreening`, `DatePrevTreatmentStart`, and `DateOutcome` --
#' rather than each deriving its own from [quarterly_counts()]'s default,
#' since combining per-milestone ordered factors with different level sets
#' would otherwise error in the final `bind_rows()`.
#' @param df Analysis-ready table.
#' @param group_vars Character vector of additional grouping columns.
#' @return A tibble: `milestone` (`"Enrollment"`, `"Treatment initiation"`,
#'   `"Outcome recorded"`) plus the [quarterly_counts()] columns.
#' @export
enrollment_trends <- function(df, group_vars = character(0)) {
  milestones <- c(
    DateScreening = "Enrollment",
    DatePrevTreatmentStart = "Treatment initiation",
    DateOutcome = "Outcome recorded"
  )
  all_dates <- do.call(c, lapply(names(milestones), function(col) df[[col]][!is.na(df[[col]])]))
  full_range <- seq(min(all_dates), max(all_dates), by = "quarter")
  quarter_levels <- unique(paste0(lubridate::year(full_range), " Q", lubridate::quarter(full_range)))

  purrr::imap(milestones, function(label, col) {
    quarterly_counts(df, col, group_vars, quarter_levels = quarter_levels) |>
      dplyr::mutate(milestone = label, .before = 1)
  }) |>
    dplyr::bind_rows() |>
    dplyr::mutate(milestone = factor(.data$milestone, levels = unname(milestones), ordered = TRUE))
}
