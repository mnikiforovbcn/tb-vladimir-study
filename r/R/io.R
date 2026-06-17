# Column layout of Data/raw/VladKovMur_dataset.csv, verified against the
# real file header and Documentation/DataSet Description (English).md.
# Order matters: it is also the expected-column-order regression guard.
.EXPECTED_COLUMNS <- c(
  "Source_id", "Source", "Nomer", "IndexCase", "BirthDate", "Sex",
  "TargetGroup", "Contact", "Homeless", "PLHIV", "Others", "TreatGroup",
  "TreatGroup_01", "TreatGroup_02", "TreatGroup_03", "RelationWithSource",
  "Screening", "DateScreening", "SuspectedTB", "DiaskintestPositive",
  "Screening_y", "DateScreening_y", "NoTbAfter_y_xray", "NoTbAfter_y",
  "Screening_24", "NoTbAfter_24", "CompleteExaminationTB",
  "DateCompleteExaminationTB", "ConfirmedDiagnosisTB", "LTI", "NoTBNoLTI",
  "NoTBLTIunknown", "PrevTreatmentRec", "PrevTreatmentPresc",
  "PrevTreatmentStart", "DatePrevTreatmentStart", "DateTreatmentScheme",
  "RegBq", "RegMfx", "TreatmentCompleted", "TreatmentFinished",
  "DateOutcome", "TBdeveloped", "TreatmentStopedMed",
  "TreatmetnNotFinished", "TreatmentContinue", "OutcomeNotKnown",
  "DosesTaken", "SchemaDoses", "Take50pc", "Take100pc",
  "DateSuppScreening", "SuppScreening", "DateSupp50pc", "Supp50pc",
  "DateSupp100pc", "Supp100pc", "DateSupp1yearGr23", "Supp1yearGr23",
  "DateSupp1yearGr1", "Supp1yearGr1", "FinalOutcome"
)

.CHARACTER_COLS <- c("Source", "IndexCase")

.DATE_COLS <- c(
  "BirthDate", "DateScreening", "DateScreening_y",
  "DateCompleteExaminationTB", "DatePrevTreatmentStart",
  "DateTreatmentScheme", "DateOutcome", "DateSuppScreening",
  "DateSupp50pc", "DateSupp100pc", "DateSupp1yearGr23", "DateSupp1yearGr1"
)

#' Column type specification for the raw dataset
#'
#' Every `0/1` flag and numeric code is read as `double` (the source export
#' writes some of them with a trailing `.0`, inconsistently across columns)
#' and then cast to integer in [load_raw()] -- not declared as integer here,
#' since `readr::col_integer()` rejects `"12.0"`-style literals outright.
#' Values are kept as raw coded integers (e.g. `TargetGroup` stays `1`-`4`);
#' recoding into labelled factors happens downstream in `derive.R`/`cascade.R`.
#' Date columns are read as character, not `col_date()`: a handful of rows
#' carry a `" 00:00:00"` timestamp suffix on an otherwise-plain date, which a
#' fixed-format date parser rejects outright; [load_raw()] parses them itself
#' with a more tolerant routine.
#'
#' @return A `readr::cols()` specification.
#' @keywords internal
raw_col_types <- function() {
  char_spec <- stats::setNames(
    rep(list(readr::col_character()), length(.CHARACTER_COLS)),
    .CHARACTER_COLS
  )
  date_spec <- stats::setNames(
    rep(list(readr::col_character()), length(.DATE_COLS)),
    .DATE_COLS
  )
  do.call(readr::cols, c(list(.default = readr::col_double()), char_spec, date_spec))
}

#' Parse a date column tolerant of a trailing time-of-day component
#'
#' Truncates to the first 10 characters (`YYYY-MM-DD`) before parsing, so
#' `"2020-05-14 00:00:00"` parses the same as `"2020-05-14"`. A string that is
#' still unparseable after truncation (e.g. a truncated year like
#' `"201-08-01"`) becomes `NA`, same as readr's own coercion behaviour, and is
#' reported by [load_raw()] rather than silently swallowed.
#'
#' Strings are required to match `YYYY-MM-DD` exactly (4-digit year) before
#' being handed to [as.Date()]: R's date parser otherwise accepts a
#' short/truncated year (e.g. `"201-08-01"` parses as year 201 rather than
#' failing), which would silently mask a real data-entry error as a valid
#' date far in the past.
#'
#' @param x Character vector.
#' @return A `Date` vector.
#' @keywords internal
.parse_date_col <- function(x) {
  cleaned <- substr(trimws(x), 1, 10)
  cleaned[!grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", cleaned)] <- NA
  as.Date(cleaned, format = "%Y-%m-%d")
}

#' Load the raw VladKovMur_dataset.csv export
#'
#' Reads with an explicit column-type map (see [raw_col_types()]), verifies
#' the column layout exactly matches the documented data dictionary, and
#' casts every flag/code/count column to integer. Row count is deliberately
#' *not* asserted here -- the dataset grows with each new export; pin row
#' count in a test against a specific snapshot instead, not in this
#' function.
#'
#' @param path Path to the CSV file. Defaults to [raw_data_path()].
#' @return A tibble with [N_COLS_EXPECTED] columns.
#' @export
load_raw <- function(path = raw_data_path()) {
  df <- readr::read_csv(
    path,
    col_types = raw_col_types(),
    na = c("", "NA"),
    progress = FALSE
  )

  actual_cols <- names(df)
  if (!identical(actual_cols, .EXPECTED_COLUMNS)) {
    missing <- setdiff(.EXPECTED_COLUMNS, actual_cols)
    extra <- setdiff(actual_cols, .EXPECTED_COLUMNS)
    stop(glue::glue(
      "Raw CSV column layout does not match the expected data dictionary.\n",
      "Missing: {paste(missing, collapse = ', ')}\n",
      "Unexpected: {paste(extra, collapse = ', ')}"
    ), call. = FALSE)
  }

  parsed_dates <- lapply(.DATE_COLS, function(col) .parse_date_col(df[[col]]))
  names(parsed_dates) <- .DATE_COLS
  malformed <- vapply(.DATE_COLS, function(col) {
    sum(!is.na(df[[col]]) & is.na(parsed_dates[[col]]))
  }, integer(1))
  malformed <- malformed[malformed > 0]
  if (length(malformed) > 0) {
    detail <- paste(sprintf("%s (%d)", names(malformed), malformed), collapse = ", ")
    warning(glue::glue(
      "load_raw(): {sum(malformed)} date value(s) were not parseable and ",
      "were coerced to NA: {detail}"
    ), call. = FALSE)
  }
  for (col in .DATE_COLS) {
    df[[col]] <- parsed_dates[[col]]
  }

  integer_cols <- setdiff(actual_cols, c(.CHARACTER_COLS, .DATE_COLS))
  df <- dplyr::mutate(df, dplyr::across(dplyr::all_of(integer_cols), as.integer))

  df
}

#' Write an immutable Parquet snapshot of a loaded raw dataset
#'
#' One snapshot per `run_date` so any later report can cite the exact input
#' it was built from.
#'
#' @param df Data frame to snapshot (typically the output of [load_raw()]).
#' @param run_date Date identifying this run; defaults to today.
#' @param dir Output directory; defaults to [processed_data_dir()].
#' @return The path the snapshot was written to, invisibly.
#' @export
snapshot <- function(df, run_date = Sys.Date(), dir = processed_data_dir()) {
  if (!dir.exists(dir)) {
    dir.create(dir, recursive = TRUE)
  }
  path <- file.path(dir, sprintf("raw_snapshot_%s.parquet", format(run_date, "%Y-%m-%d")))
  arrow::write_parquet(df, path)
  invisible(path)
}
