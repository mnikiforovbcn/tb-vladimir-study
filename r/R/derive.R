.DIAGNOSIS_BRANCH_COLUMNS <- c(
  ConfirmedDiagnosisTB = "active_tb",
  LTI = "lti",
  NoTBNoLTI = "no_tb_no_lti",
  NoTBLTIunknown = "lti_unknown"
)

.OUTCOME_BRANCH_COLUMNS <- c(
  TreatmentCompleted = "completed",
  TreatmentFinished = "finished",
  TBdeveloped = "tb_developed",
  TreatmentStopedMed = "stopped_medical",
  TreatmetnNotFinished = "not_finished",
  TreatmentContinue = "continuing",
  OutcomeNotKnown = "unknown"
)

.FINAL_OUTCOME_LABELS <- c(
  "1" = "no_tb", "2" = "tb_developed", "3" = "unknown", "4" = "other"
)

#' Age in completed years at screening, and standard 10-year age bands
#'
#' Age is computed from `DateScreening` minus `BirthDate` (not from the
#' analysis/run date), truncated to completed years. Implausible ages
#' (negative, or unparseable because either date is missing) are not
#' corrected here -- see [check_age_range()] for the QC-stage flag -- they
#' simply come out as `NA`/negative and are excluded from `age_band`.
#'
#' @param birth_date,screening_date Date vectors of equal length.
#' @return A list with `age` (numeric, years) and `age_band` (ordered
#'   factor in 10-year bands, `"100+"` for the open-ended top band).
#' @export
compute_age <- function(birth_date, screening_date) {
  age <- floor(as.numeric(screening_date - birth_date) / 365.25)

  band_breaks <- c(seq(0, 100, by = 10), Inf)
  band_labels <- c(paste0(seq(0, 90, by = 10), "-", seq(9, 99, by = 10)), "100+")
  age_band <- cut(age, breaks = band_breaks, labels = band_labels, right = FALSE, ordered_result = TRUE)

  list(age = age, age_band = age_band)
}

#' Adherence ratio (doses taken / doses scheduled)
#'
#' `NA` whenever `schema_doses` is missing or zero, since the ratio is
#' undefined (avoids a div-by-zero `Inf`/`NaN`).
#' @param doses_taken,schema_doses Numeric vectors of equal length.
#' @return A numeric vector.
#' @export
adherence_ratio <- function(doses_taken, schema_doses) {
  dplyr::if_else(
    !is.na(schema_doses) & schema_doses > 0 & !is.na(doses_taken),
    doses_taken / schema_doses,
    NA_real_
  )
}

#' Cascade milestone time intervals, in days
#'
#' Computes the four adjacent gaps in [DATE_ORDER_SEQUENCE] plus the total
#' screening-to-outcome span (used as person-time in Step 8's incidence
#' rate). Intervals are signed: a negative value reflects a date-order
#' reversal already surfaced by [check_date_order()] -- it is not corrected
#' or clipped here.
#' @param df A data frame with the columns in [DATE_ORDER_SEQUENCE].
#' @return A tibble with one row per record in `df`: `days_screening_to_eval`,
#'   `days_eval_to_tx_start`, `days_tx_start_to_scheme`,
#'   `days_scheme_to_outcome`, `days_screening_to_outcome`.
#' @export
time_intervals <- function(df) {
  tibble::tibble(
    days_screening_to_eval = as.numeric(df$DateCompleteExaminationTB - df$DateScreening),
    days_eval_to_tx_start = as.numeric(df$DatePrevTreatmentStart - df$DateCompleteExaminationTB),
    days_tx_start_to_scheme = as.numeric(df$DateTreatmentScheme - df$DatePrevTreatmentStart),
    days_scheme_to_outcome = as.numeric(df$DateOutcome - df$DateTreatmentScheme),
    days_screening_to_outcome = as.numeric(df$DateOutcome - df$DateScreening)
  )
}

#' Treatment-initiation-within-target flags
#'
#' For each target in [INITIATION_TARGET_DAYS], whether
#' `days_eval_to_tx_start` (the `DateCompleteExaminationTB` to
#' `DatePrevTreatmentStart` delay) falls within that many days. A negative
#' delay (date-order reversal) is treated as `NA` -- not `TRUE` -- since the
#' true delay cannot be determined from inconsistent dates.
#' @param days_eval_to_tx_start Numeric vector, as returned by
#'   [time_intervals()].
#' @return A tibble with one logical column per entry in
#'   [INITIATION_TARGET_DAYS], named `initiated_within_<n>d`.
#' @export
initiation_target_flags <- function(days_eval_to_tx_start) {
  flags <- purrr::map(INITIATION_TARGET_DAYS, function(target) {
    dplyr::if_else(
      is.na(days_eval_to_tx_start) | days_eval_to_tx_start < 0,
      NA,
      days_eval_to_tx_start <= target
    )
  })
  names(flags) <- paste0("initiated_within_", INITIATION_TARGET_DAYS, "d")
  tibble::as_tibble(flags)
}

#' Map a set of mutually-exclusive 0/1 columns to a single labelled factor
#'
#' @param df A data frame.
#' @param column_labels A named character vector: names are columns of
#'   `df`, values are the factor label to use when that column is `1`.
#' @return A factor, `NA` where none of the columns is `1`.
#' @keywords internal
.branch_factor <- function(df, column_labels) {
  cols <- names(column_labels)
  label <- rep(NA_character_, nrow(df))
  for (col in cols) {
    is_set <- !is.na(df[[col]]) & df[[col]] == 1L
    label[is_set] <- column_labels[[col]]
  }
  factor(label, levels = unname(column_labels))
}

#' Screening-to-outcome cascade boolean/categorical flags (Study Plan Steps 2-8)
#'
#' @param df A data frame as returned by [load_raw()].
#' @return A tibble with one row per record in `df` and the following
#'   columns: `reached_screening`, `reached_suspected`,
#'   `diaskintest_positive`, `reached_full_eval` (Step 2);
#'   `confirmed_active_tb`, `has_lti`, `no_tb_no_lti`, `no_tb_lti_unknown`,
#'   `diagnosis_branch` (Step 3); `eligible_for_lti_tx`, `lti_recommended`,
#'   `lti_prescribed`, `lti_started` (Step 4); `completed_or_finished`,
#'   `outcome_branch` (Step 6); `supp_screening_received`,
#'   `supp_50pc_received`, `supp_100pc_received`, `supp_1yr_received`
#'   (Step 7); `rescreened_1yr`, `no_tb_after_1yr`, `rescreened_24mo`,
#'   `no_tb_after_24mo`, `final_outcome_category` (Step 8).
#' @export
cascade_flags <- function(df) {
  tibble::tibble(
    reached_screening = df$Screening == 1L,
    reached_suspected = df$SuspectedTB == 1L,
    diaskintest_positive = df$DiaskintestPositive == 1L,
    reached_full_eval = df$CompleteExaminationTB == 1L,
    confirmed_active_tb = df$ConfirmedDiagnosisTB == 1L,
    has_lti = df$LTI == 1L,
    no_tb_no_lti = df$NoTBNoLTI == 1L,
    no_tb_lti_unknown = df$NoTBLTIunknown == 1L,
    diagnosis_branch = .branch_factor(df, .DIAGNOSIS_BRANCH_COLUMNS),
    eligible_for_lti_tx = (df$LTI == 1L) | (df$PrevTreatmentRec == 1L),
    lti_recommended = df$PrevTreatmentRec == 1L,
    lti_prescribed = df$PrevTreatmentPresc == 1L,
    lti_started = df$PrevTreatmentStart == 1L,
    completed_or_finished = (df$TreatmentCompleted == 1L) | (df$TreatmentFinished == 1L),
    outcome_branch = .branch_factor(df, .OUTCOME_BRANCH_COLUMNS),
    supp_screening_received = df$SuppScreening == 1L,
    supp_50pc_received = df$Supp50pc == 1L,
    supp_100pc_received = df$Supp100pc == 1L,
    supp_1yr_received = dplyr::case_when(
      df$TreatGroup == 1L ~ df$Supp1yearGr1 == 1L,
      df$TreatGroup %in% c(2L, 3L) ~ df$Supp1yearGr23 == 1L,
      .default = NA
    ),
    rescreened_1yr = df$Screening_y == 1L,
    no_tb_after_1yr = df$NoTbAfter_y == 1L,
    rescreened_24mo = df$Screening_24 == 1L,
    no_tb_after_24mo = df$NoTbAfter_24 == 1L,
    final_outcome_category = factor(
      unname(.FINAL_OUTCOME_LABELS[as.character(df$FinalOutcome)]),
      levels = unname(.FINAL_OUTCOME_LABELS)
    )
  )
}

#' Right-censoring flag for individuals with insufficient follow-up
#'
#' Flags records whose `DateScreening` falls within `window_months` months
#' of `analysis_date` -- not enough time may have elapsed to reach a mature
#' outcome (Descriptive Study Plan SS6, point 6).
#' @param df A data frame with a `DateScreening` column.
#' @param analysis_date The date the analysis is being run as of; defaults
#'   to today.
#' @param window_months Censoring window, in months; defaults to
#'   [CENSORING_WINDOW_MONTHS].
#' @return A logical vector.
#' @export
censoring_flag <- function(df, analysis_date = Sys.Date(), window_months = CENSORING_WINDOW_MONTHS) {
  cutoff <- lubridate::`%m-%`(analysis_date, months(window_months))
  !is.na(df$DateScreening) & df$DateScreening > cutoff
}

#' Build the full analysis-ready table
#'
#' Binds every Phase 3 derived variable onto the raw loaded table: age/age
#' band, adherence ratio, the five cascade time intervals, the
#' initiation-within-target flags, the Step 2-8 cascade flags, and the
#' censoring flag.
#' @param df A data frame as returned by [load_raw()].
#' @param analysis_date The date the analysis is being run as of; defaults
#'   to today. Passed through to [censoring_flag()].
#' @return A tibble: `df` plus all derived columns.
#' @export
build_analysis_table <- function(df, analysis_date = Sys.Date()) {
  age <- compute_age(df$BirthDate, df$DateScreening)
  intervals <- time_intervals(df)

  dplyr::bind_cols(
    df,
    age = age$age,
    age_band = age$age_band,
    adherence_ratio = adherence_ratio(df$DosesTaken, df$SchemaDoses),
    intervals,
    initiation_target_flags(intervals$days_eval_to_tx_start),
    cascade_flags(df),
    censored = censoring_flag(df, analysis_date = analysis_date)
  )
}

#' Write an immutable Parquet snapshot of the analysis-ready table
#'
#' @param table A data frame as returned by [build_analysis_table()].
#' @param run_date Date identifying this run; defaults to today.
#' @param dir Output directory; defaults to [processed_data_dir()].
#' @return The path the snapshot was written to, invisibly.
#' @export
persist_analysis_table <- function(table, run_date = Sys.Date(), dir = processed_data_dir()) {
  if (!dir.exists(dir)) {
    dir.create(dir, recursive = TRUE)
  }
  path <- file.path(dir, sprintf("analysis_ready_%s.parquet", format(run_date, "%Y-%m-%d")))
  arrow::write_parquet(table, path)
  invisible(path)
}
