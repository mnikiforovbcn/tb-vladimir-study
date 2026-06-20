#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(optparse))

script_path <- normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)))
pkg_root <- dirname(dirname(script_path))
devtools::load_all(pkg_root, quiet = TRUE)

option_list <- list(
  make_option(c("-d", "--run-date"),
    dest = "run_date", type = "character", default = format(Sys.Date(), "%Y-%m-%d"),
    help = "Analysis/run date, YYYY-MM-DD [default: today]"
  ),
  make_option(c("-c", "--csv-path"),
    dest = "csv_path", type = "character", default = NA_character_,
    help = "Path to the raw registry CSV [default: Data/raw/VladKovMur_dataset.csv]"
  ),
  make_option(c("-o", "--output-dir"),
    dest = "output_dir", type = "character", default = NA_character_,
    help = "Directory to write this run's outputs to [default: r/reports/<run-date>/]"
  ),
  make_option(c("-f", "--formats"),
    dest = "formats", type = "character", default = "html,gfm",
    help = "Comma-separated report formats to render [default: %default]"
  )
)
opt <- parse_args(OptionParser(option_list = option_list))

run_date <- as.Date(opt$run_date)
csv_path <- if (is.na(opt$csv_path)) raw_data_path() else opt$csv_path
output_dir <- if (is.na(opt$output_dir)) file.path(reports_dir(), format(run_date, "%Y-%m-%d")) else opt$output_dir
formats <- trimws(strsplit(opt$formats, ",")[[1]])

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

message("== Phase 1: ingestion ==")
raw <- suppressWarnings(load_raw(csv_path))
message(sprintf("  loaded %d rows from %s", nrow(raw), csv_path))
snapshot_path <- snapshot(raw, run_date = run_date)
message("  raw snapshot -> ", snapshot_path)

message("== Phase 2: quality control ==")
qc_result <- run_qc(raw)
qc_report_path <- file.path(output_dir, "qc_report.md")
render_qc_report(qc_result, qc_report_path)
message("  QC report -> ", qc_report_path)

message("== Phase 3: derived variables ==")
tab <- build_analysis_table(raw, analysis_date = run_date)
analysis_path <- persist_analysis_table(tab, run_date = run_date)
message("  analysis-ready snapshot -> ", analysis_path)

message("== Phase 6: descriptive report (", paste(formats, collapse = ", "), ") ==")
qmd_path <- file.path(pkg_root, "report", "descriptive_report.qmd")
qmd_dir <- dirname(qmd_path)
execute_params <- list(run_date = format(run_date, "%Y-%m-%d"), analysis_ready_path = analysis_path)

# Render each format in its own quarto_render() call: rendering several formats from one
# call lets the HTML target's embed-resources cleanup step delete the shared figure-output
# directory before a later non-self-contained format (e.g. gfm) can consume it.
for (fmt in formats) {
  quarto::quarto_render(input = qmd_path, output_format = fmt, execute_params = execute_params, quiet = TRUE)
}

rendered <- list.files(qmd_dir, pattern = "^descriptive_report[._]", full.names = TRUE)
rendered <- rendered[!grepl("\\.qmd$", rendered)]
invisible(file.copy(rendered, output_dir, recursive = TRUE, overwrite = TRUE))
unlink(rendered, recursive = TRUE)

message("== Done. Outputs in ", normalizePath(output_dir), " ==")
