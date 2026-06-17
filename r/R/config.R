#' Repository root directory
#'
#' Walks upward from the working directory looking for the outer Git
#' repository root (the directory containing `.git`), so paths to shared
#' inputs (`Data/`, `Documentation/`) resolve correctly whether code runs via
#' `devtools::load_all()`, `testthat`, or `Rscript r/scripts/run.R` -- all of
#' which have a working directory somewhere *inside* this Git repository.
#' Deliberately keyed on `.git` rather than `rprojroot::is_r_package()`:
#' the package itself lives in the `r/` subdirectory (which has its own
#' `DESCRIPTION`), so a package-root criterion would stop one level too
#' shallow.
#'
#' @return Absolute path to the repository root.
#' @export
repo_root <- function() {
  rprojroot::find_root(rprojroot::has_dir(".git"), path = getwd())
}

#' Path to the raw dataset CSV
#' @param repo Repository root; defaults to [repo_root()].
#' @export
raw_data_path <- function(repo = repo_root()) {
  file.path(repo, "Data", "raw", "VladKovMur_dataset.csv")
}

#' Directory for this package's processed/derived data outputs
#'
#' Kept separate from the Python implementation's `Data/processed/` so the
#' two pipelines never overwrite each other's snapshots.
#' @param repo Repository root; defaults to [repo_root()].
#' @export
processed_data_dir <- function(repo = repo_root()) {
  file.path(repo, "Data", "processed", "r")
}

#' Directory for this package's rendered reports
#' @param repo Repository root; defaults to [repo_root()].
#' @export
reports_dir <- function(repo = repo_root()) {
  file.path(repo, "r", "reports")
}

#' Expected shape of the raw dataset (regression guard)
#' @export
N_ROWS_EXPECTED <- 7732L

#' @rdname N_ROWS_EXPECTED
#' @export
N_COLS_EXPECTED <- 62L

#' Small-cell suppression threshold (Descriptive Study Plan SS11)
#' @export
SMALL_CELL_THRESHOLD <- 5L

#' Treatment-initiation delay targets, in days (Descriptive Study Plan Step 4)
#' @export
INITIATION_TARGET_DAYS <- c(30, 60)

#' Right-censoring window, in months (Descriptive Study Plan SS6.6)
#' @export
CENSORING_WINDOW_MONTHS <- 12

#' Expected chronological order of cascade milestone dates (Descriptive
#' Study Plan SS6, point 3)
#' @export
DATE_ORDER_SEQUENCE <- c(
  "DateScreening",
  "DateCompleteExaminationTB",
  "DatePrevTreatmentStart",
  "DateTreatmentScheme",
  "DateOutcome"
)
