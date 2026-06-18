.OUTCOME_FLAG_COLUMNS <- c(
  "TreatmentCompleted", "TreatmentFinished", "TBdeveloped",
  "TreatmentStopedMed", "TreatmetnNotFinished", "TreatmentContinue", "OutcomeNotKnown"
)

.DIAGNOSIS_FLAG_COLUMNS <- c("ConfirmedDiagnosisTB", "LTI", "NoTBNoLTI", "NoTBLTIunknown")

.TREAT_GROUP_ONEHOT_COLUMNS <- c("TreatGroup_01", "TreatGroup_02", "TreatGroup_03")

#' Columns expected to be populated for every enrolled record
#'
#' Used by [audit_missingness()] to distinguish unexplained data-entry gaps
#' from the structural missingness produced by the cascade's skip pattern
#' (e.g. outcome fields are blank for anyone who has not yet finished
#' treatment).
#' @keywords internal
.ALWAYS_REQUIRED_COLUMNS <- c(
  "Source_id", "Source", "Nomer", "BirthDate", "Sex", "TargetGroup",
  "Screening", "DateScreening"
)

#' Flag duplicate Source + Nomer registrations
#' @param df A data frame as returned by [load_raw()].
#' @return A tibble of all rows sharing a duplicated `Source` + `Nomer` key,
#'   with an added `n_duplicates` column.
#' @export
check_duplicate_registrations <- function(df) {
  df |>
    dplyr::group_by(.data$Source, .data$Nomer) |>
    dplyr::mutate(n_duplicates = dplyr::n()) |>
    dplyr::ungroup() |>
    dplyr::filter(.data$n_duplicates > 1) |>
    dplyr::select("Source", "Nomer", "n_duplicates", dplyr::everything())
}

#' Flag inconsistencies between `TreatGroup` and its one-hot flags
#'
#' Two distinct issues are detected and labelled via `issue`:
#' `"sum_not_one"` (the three flags do not sum to exactly 1, ignoring `NA`s)
#' and `"index_mismatch"` (they sum to 1, but the flagged index does not
#' correspond to `TreatGroup`'s value). Records with `TreatGroup` missing
#' and all three flags unset (0) are not flagged -- that combination is
#' self-consistent ("no group assigned yet") and is surfaced instead by the
#' missingness audit.
#' @param df A data frame as returned by [load_raw()].
#' @return A tibble of flagged rows with an `issue` column.
#' @export
check_treat_group_onehot <- function(df) {
  onehot <- as.matrix(df[.TREAT_GROUP_ONEHOT_COLUMNS])
  onehot_sum <- rowSums(onehot, na.rm = TRUE)

  expected_index <- dplyr::if_else(df$TreatGroup %in% 1:3, df$TreatGroup, NA_integer_)
  safe_index <- dplyr::if_else(is.na(expected_index), 1L, expected_index)
  flagged_value <- onehot[cbind(seq_len(nrow(onehot)), safe_index)]
  index_matches <- !is.na(expected_index) & !is.na(flagged_value) & flagged_value == 1

  issue <- dplyr::case_when(
    is.na(df$TreatGroup) & onehot_sum == 0L ~ NA_character_,
    onehot_sum != 1L ~ "sum_not_one",
    onehot_sum == 1L & !is.na(expected_index) & !index_matches ~ "index_mismatch",
    .default = NA_character_
  )

  df |>
    dplyr::mutate(issue = issue) |>
    dplyr::filter(!is.na(.data$issue)) |>
    dplyr::select(
      "Source", "Nomer", "issue", "TreatGroup",
      dplyr::all_of(.TREAT_GROUP_ONEHOT_COLUMNS)
    )
}

#' Flag violations of outcome-flag mutual exclusivity
#'
#' Among `r .OUTCOME_FLAG_COLUMNS`, at most one should be set per record.
#' @param df A data frame as returned by [load_raw()].
#' @return A tibble of rows where more than one outcome flag is set, with an
#'   added `n_flags_set` column.
#' @export
check_outcome_mutual_exclusivity <- function(df) {
  n_flags_set <- rowSums(df[.OUTCOME_FLAG_COLUMNS], na.rm = TRUE)
  df |>
    dplyr::mutate(n_flags_set = n_flags_set) |>
    dplyr::filter(.data$n_flags_set > 1L) |>
    dplyr::select("Source", "Nomer", "n_flags_set", dplyr::all_of(.OUTCOME_FLAG_COLUMNS))
}

#' Flag violations of diagnosis-flag mutual exclusivity
#'
#' Among `r .DIAGNOSIS_FLAG_COLUMNS`, at most one should be set per record.
#' @param df A data frame as returned by [load_raw()].
#' @return A tibble of rows where more than one diagnosis flag is set, with
#'   an added `n_flags_set` column.
#' @export
check_diagnosis_mutual_exclusivity <- function(df) {
  n_flags_set <- rowSums(df[.DIAGNOSIS_FLAG_COLUMNS], na.rm = TRUE)
  df |>
    dplyr::mutate(n_flags_set = n_flags_set) |>
    dplyr::filter(.data$n_flags_set > 1L) |>
    dplyr::select("Source", "Nomer", "n_flags_set", dplyr::all_of(.DIAGNOSIS_FLAG_COLUMNS))
}

#' Flag reversals in the expected cascade milestone date order
#'
#' Compares every adjacent pair in [DATE_ORDER_SEQUENCE] and flags rows
#' where the earlier milestone date is strictly after the later one. Rows
#' where either date is missing are excluded (handled by the missingness
#' audit, not a date-order violation).
#' @param df A data frame as returned by [load_raw()].
#' @return A tibble with one row per violation: `Source`, `Nomer`, `date_a`,
#'   `date_b` (the column names of the pair), and their values.
#' @export
check_date_order <- function(df) {
  pairs <- utils::head(DATE_ORDER_SEQUENCE, -1)
  next_pairs <- utils::tail(DATE_ORDER_SEQUENCE, -1)

  violations <- purrr::map2(pairs, next_pairs, function(a, b) {
    reversed <- !is.na(df[[a]]) & !is.na(df[[b]]) & df[[a]] > df[[b]]
    if (!any(reversed)) {
      return(NULL)
    }
    tibble::tibble(
      Source = df$Source[reversed],
      Nomer = df$Nomer[reversed],
      date_a = a,
      date_b = b,
      value_a = df[[a]][reversed],
      value_b = df[[b]][reversed]
    )
  })

  violations <- purrr::compact(violations)
  if (length(violations) == 0L) {
    return(tibble::tibble(
      Source = character(), Nomer = integer(), date_a = character(),
      date_b = character(), value_a = as.Date(character()), value_b = as.Date(character())
    ))
  }
  dplyr::bind_rows(violations)
}

#' Per-pair summary of date-order completeness and reversal rate
#'
#' @param df A data frame as returned by [load_raw()].
#' @return A tibble with one row per adjacent pair in [DATE_ORDER_SEQUENCE]:
#'   `date_a`, `date_b`, `n_both_present`, `n_reversed`, `reversal_rate`.
#' @export
date_order_pair_summary <- function(df) {
  pairs <- utils::head(DATE_ORDER_SEQUENCE, -1)
  next_pairs <- utils::tail(DATE_ORDER_SEQUENCE, -1)

  purrr::map2(pairs, next_pairs, function(a, b) {
    both_present <- !is.na(df[[a]]) & !is.na(df[[b]])
    n_both_present <- sum(both_present)
    n_reversed <- sum(both_present & df[[a]] > df[[b]])
    tibble::tibble(
      date_a = a,
      date_b = b,
      n_both_present = n_both_present,
      n_reversed = n_reversed,
      reversal_rate = dplyr::if_else(n_both_present > 0L, n_reversed / n_both_present, NA_real_)
    )
  }) |>
    dplyr::bind_rows()
}

#' Flag dose-count anomalies and threshold-flag inconsistencies
#'
#' Detects three issues, labelled via `issue`: `"doses_exceed_schema"`
#' (`DosesTaken > SchemaDoses`), `"take50pc_inconsistent"` (`Take50pc` does
#' not match whether the dose ratio reached 50%), and
#' `"take100pc_inconsistent"` (likewise for `Take100pc`). Rows with
#' `SchemaDoses` missing or zero are excluded from the threshold checks
#' (the ratio is undefined) but still checked for `doses_exceed_schema`.
#' @param df A data frame as returned by [load_raw()].
#' @return A tibble of flagged rows with an `issue` column (a row may appear
#'   more than once if multiple issues apply).
#' @export
check_dose_consistency <- function(df) {
  ratio <- dplyr::if_else(
    !is.na(df$SchemaDoses) & df$SchemaDoses > 0L & !is.na(df$DosesTaken),
    df$DosesTaken / df$SchemaDoses,
    NA_real_
  )

  exceeds <- !is.na(df$DosesTaken) & !is.na(df$SchemaDoses) & df$DosesTaken > df$SchemaDoses
  take50_bad <- !is.na(ratio) & !is.na(df$Take50pc) & (df$Take50pc == 1L) != (ratio >= 0.5)
  take100_bad <- !is.na(ratio) & !is.na(df$Take100pc) & (df$Take100pc == 1L) != (ratio >= 1.0)

  cols <- c("Source", "Nomer", "DosesTaken", "SchemaDoses", "Take50pc", "Take100pc")
  dplyr::bind_rows(
    dplyr::mutate(df[exceeds, cols], issue = "doses_exceed_schema"),
    dplyr::mutate(df[take50_bad, cols], issue = "take50pc_inconsistent"),
    dplyr::mutate(df[take100_bad, cols], issue = "take100pc_inconsistent")
  )
}

#' Flag implausible ages at screening
#'
#' Age is computed directly from `BirthDate` and `DateScreening` (not via
#' the derived `age` variable built in Phase 3) so this check stands alone
#' against the raw import.
#' @param df A data frame as returned by [load_raw()].
#' @return A tibble of rows with negative age or age over 100 at screening,
#'   with an added `age_years` column.
#' @export
check_age_range <- function(df) {
  age_years <- as.numeric(df$DateScreening - df$BirthDate) / 365.25
  df |>
    dplyr::mutate(age_years = age_years) |>
    dplyr::filter(!is.na(.data$age_years) & (.data$age_years < 0 | .data$age_years > 100)) |>
    dplyr::select("Source", "Nomer", "BirthDate", "DateScreening", "age_years")
}

#' Missingness audit, by column and by site
#'
#' Reports `NA` counts and rates for every column, both overall and broken
#' down by `Source`. Columns in [.ALWAYS_REQUIRED_COLUMNS] are marked
#' `"unexplained"` when missing (these should be populated for every
#' enrolled record); all other missingness is marked `"structural"`, since
#' the cascade's skip pattern (e.g. no outcome date until treatment ends)
#' produces it by design.
#' @param df A data frame as returned by [load_raw()].
#' @return A list with `by_column` (overall missingness per column) and
#'   `by_site` (missingness per column per `Source`).
#' @export
audit_missingness <- function(df) {
  by_column <- tibble::tibble(
    column = names(df),
    n_missing = vapply(df, function(x) sum(is.na(x)), integer(1)),
    n = nrow(df)
  ) |>
    dplyr::mutate(
      pct_missing = .data$n_missing / .data$n,
      category = dplyr::if_else(.data$column %in% .ALWAYS_REQUIRED_COLUMNS, "unexplained", "structural")
    ) |>
    dplyr::select("column", "category", "n_missing", "n", "pct_missing")

  by_site <- purrr::map(names(df), function(col) {
    df |>
      dplyr::group_by(.data$Source) |>
      dplyr::summarise(
        column = col,
        n_missing = sum(is.na(.data[[col]])),
        n = dplyr::n(),
        .groups = "drop"
      )
  }) |>
    dplyr::bind_rows() |>
    dplyr::mutate(pct_missing = .data$n_missing / .data$n) |>
    dplyr::select("column", "Source", "n_missing", "n", "pct_missing")

  list(by_column = by_column, by_site = by_site)
}

#' Run the full Section 6 quality-control suite
#'
#' @param df A data frame as returned by [load_raw()].
#' @return A list: `schema_summary` (per-column value-set/range check
#'   results from [build_schema_agent()]), `flagged` (a named list of
#'   tibbles, one per cross-field check), `check_summary` (a tibble of
#'   check name, n_flagged, and per-site breakdown), `date_order_pairs`
#'   (output of [date_order_pair_summary()]), and `missingness` (output of
#'   [audit_missingness()]).
#' @export
run_qc <- function(df) {
  schema_agent <- build_schema_agent(df)

  flagged <- list(
    duplicate_registrations = check_duplicate_registrations(df),
    treat_group_onehot = check_treat_group_onehot(df),
    outcome_mutual_exclusivity = check_outcome_mutual_exclusivity(df),
    diagnosis_mutual_exclusivity = check_diagnosis_mutual_exclusivity(df),
    date_order = check_date_order(df),
    dose_consistency = check_dose_consistency(df),
    age_range = check_age_range(df)
  )

  check_summary <- purrr::imap(flagged, function(tbl, check_name) {
    site_counts <- if (nrow(tbl) > 0L && "Source" %in% names(tbl)) {
      dplyr::count(tbl, .data$Source) |>
        dplyr::mutate(label = paste0(.data$Source, "=", .data$n)) |>
        dplyr::pull("label") |>
        paste(collapse = "; ")
    } else {
      ""
    }
    tibble::tibble(check = check_name, n_flagged = nrow(tbl), by_site = site_counts)
  }) |>
    dplyr::bind_rows()

  list(
    schema_summary = schema_summary(schema_agent),
    flagged = flagged,
    check_summary = check_summary,
    date_order_pairs = date_order_pair_summary(df),
    missingness = audit_missingness(df)
  )
}

#' Render the QC results to a Markdown report
#'
#' @param qc_result Output of [run_qc()].
#' @param path Output file path for the rendered report.
#' @return The output path, invisibly.
#' @export
render_qc_report <- function(qc_result, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)

  round_doubles <- function(tbl) dplyr::mutate(tbl, dplyr::across(dplyr::where(is.double), ~ round(.x, 4)))

  lines <- c(
    "# QC Report",
    "",
    paste0("Generated: ", format(Sys.time(), "%Y-%m-%d %H:%M:%S")),
    "",
    "## Schema validation (value sets / ranges)",
    "",
    knitr::kable(round_doubles(qc_result$schema_summary), format = "pipe"),
    "",
    "## Cross-field check summary",
    "",
    knitr::kable(round_doubles(qc_result$check_summary), format = "pipe"),
    "",
    "## Date-order pair breakdown",
    "",
    knitr::kable(round_doubles(qc_result$date_order_pairs), format = "pipe"),
    "",
    "## Missingness audit, by column",
    "",
    knitr::kable(round_doubles(qc_result$missingness$by_column), format = "pipe"),
    ""
  )

  writeLines(lines, path)
  invisible(path)
}
