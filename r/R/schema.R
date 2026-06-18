.BINARY_FLAG_COLUMNS <- c(
  "Contact", "Homeless", "PLHIV", "Others",
  "TreatGroup_01", "TreatGroup_02", "TreatGroup_03",
  "Screening", "SuspectedTB", "DiaskintestPositive",
  "Screening_y", "NoTbAfter_y_xray", "NoTbAfter_y", "Screening_24", "NoTbAfter_24",
  "CompleteExaminationTB", "ConfirmedDiagnosisTB", "LTI", "NoTBNoLTI", "NoTBLTIunknown",
  "PrevTreatmentRec", "PrevTreatmentPresc", "PrevTreatmentStart",
  "RegBq", "RegMfx",
  "TreatmentCompleted", "TreatmentFinished", "TBdeveloped", "TreatmentStopedMed",
  "TreatmetnNotFinished", "TreatmentContinue", "OutcomeNotKnown",
  "Take50pc", "Take100pc",
  "SuppScreening", "Supp50pc", "Supp100pc", "Supp1yearGr23", "Supp1yearGr1"
)

.CODED_VALUE_SETS <- list(
  Source_id = c(1L, 2L, 3L),
  Source = c("Vladimir", "Murom", "Kovrov"),
  Sex = c(1L, 2L),
  TargetGroup = c(1L, 2L, 3L, 4L),
  RelationWithSource = c(45L, 313L, 314L, 348L, 366L),
  TreatGroup = c(1L, 2L, 3L),
  FinalOutcome = c(1L, 2L, 3L, 4L)
)

.NONNEGATIVE_COLUMNS <- c("Nomer", "DosesTaken", "SchemaDoses")

#' Build and interrogate the declarative pointblank schema for the raw registry export
#'
#' Checks every coded/binary column against its data-dictionary value set and
#' confirms count-like columns are non-negative. Missing values (`NA`) are
#' treated as passing every check here -- missingness itself is audited
#' separately by [audit_missingness()] -- so a step only fails when a
#' genuinely out-of-range value is present.
#'
#' @param df A data frame as returned by [load_raw()].
#' @param label Character label attached to the pointblank agent.
#' @return An interrogated pointblank `ptblank_agent` object.
#' @export
build_schema_agent <- function(df, label = "tbcascade raw schema") {
  agent <- pointblank::create_agent(df, label = label)

  for (col in .BINARY_FLAG_COLUMNS) {
    agent <- pointblank::col_vals_in_set(agent, columns = dplyr::all_of(col), set = c(0L, 1L, NA))
  }

  for (col in names(.CODED_VALUE_SETS)) {
    agent <- pointblank::col_vals_in_set(
      agent, columns = dplyr::all_of(col), set = c(.CODED_VALUE_SETS[[col]], NA)
    )
  }

  for (col in .NONNEGATIVE_COLUMNS) {
    agent <- pointblank::col_vals_gte(agent, columns = dplyr::all_of(col), value = 0, na_pass = TRUE)
  }

  pointblank::interrogate(agent)
}

#' Tidy per-column pass/fail summary from an interrogated schema agent
#'
#' @param agent An interrogated agent as returned by [build_schema_agent()].
#' @return A tibble with one row per validation step: `column`, `n`,
#'   `n_passed`, `n_failed`, `all_passed`.
#' @export
schema_summary <- function(agent) {
  validation <- agent$validation_set
  tibble::tibble(
    column = vapply(validation$column, function(x) paste(unlist(x), collapse = ", "), character(1)),
    n = validation$n,
    n_passed = validation$n_passed,
    n_failed = validation$n_failed,
    all_passed = validation$all_passed
  )
}
