fixture_path <- testthat::test_path("fixtures", "synthetic_rows.csv")
df <- suppressWarnings(load_raw(fixture_path))

test_that("compute_age() computes completed years and 10-year bands, including out-of-range ages", {
  age <- compute_age(df$BirthDate, df$DateScreening)
  by_nomer <- stats::setNames(age$age, df$Nomer)
  by_band <- stats::setNames(as.character(age$age_band), df$Nomer)

  expect_equal(by_nomer[["1001"]], 34)
  expect_equal(by_band[["1001"]], "30-39")

  expect_equal(by_nomer[["1007"]], -2)
  expect_true(is.na(by_band[["1007"]]))

  expect_equal(by_nomer[["1008"]], 119)
  expect_equal(by_band[["1008"]], "100+")
})

test_that("adherence_ratio() is NA when SchemaDoses is missing or zero", {
  ratio <- adherence_ratio(df$DosesTaken, df$SchemaDoses)
  by_nomer <- stats::setNames(ratio, df$Nomer)

  expect_equal(by_nomer[["1003"]], 30 / 180)
  expect_equal(by_nomer[["3001"]], 200 / 180)
  expect_true(is.na(by_nomer[["1002"]]))
})

test_that("time_intervals() signs a date-order reversal as negative, not clipped", {
  intervals <- time_intervals(df)
  by_nomer <- stats::setNames(intervals$days_screening_to_eval, df$Nomer)

  expect_equal(by_nomer[["1001"]], 10)
  expect_equal(by_nomer[["1002"]], -30)
})

test_that("initiation_target_flags() is NA when the delay is unknown or negative", {
  intervals <- time_intervals(df)
  flags <- initiation_target_flags(intervals$days_eval_to_tx_start)
  by_nomer_30 <- stats::setNames(flags$initiated_within_30d, df$Nomer)
  by_nomer_60 <- stats::setNames(flags$initiated_within_60d, df$Nomer)

  expect_true(by_nomer_30[["1001"]])
  expect_true(by_nomer_60[["1001"]])
  expect_true(is.na(by_nomer_30[["1002"]]))
  expect_true(is.na(by_nomer_60[["1002"]]))
})

test_that("cascade_flags() assigns diagnosis_branch and outcome_branch from mutually exclusive columns", {
  flags <- cascade_flags(df)
  by_nomer_dx <- stats::setNames(as.character(flags$diagnosis_branch), df$Nomer)
  by_nomer_out <- stats::setNames(as.character(flags$outcome_branch), df$Nomer)

  expect_equal(by_nomer_dx[["1011"]], "active_tb")
  expect_equal(by_nomer_dx[["1001"]], "lti")
  expect_equal(by_nomer_dx[["1002"]], "no_tb_no_lti")

  expect_equal(by_nomer_out[["1011"]], "completed")
  expect_equal(by_nomer_out[["1004"]], "tb_developed")
  expect_true(is.na(by_nomer_out[["1010"]]))
})

test_that("cascade_flags() dispatches supp_1yr_received on TreatGroup (group 1 vs groups 2/3)", {
  flags <- cascade_flags(df)
  by_nomer <- stats::setNames(flags$supp_1yr_received, df$Nomer)

  expect_true(by_nomer[["1011"]])
  expect_true(by_nomer[["1001"]])
  expect_false(by_nomer[["1006"]])
})

test_that("cascade_flags() labels final_outcome_category from the coded FinalOutcome value", {
  flags <- cascade_flags(df)
  by_nomer <- stats::setNames(as.character(flags$final_outcome_category), df$Nomer)

  expect_equal(by_nomer[["1001"]], "no_tb")
  expect_equal(by_nomer[["1004"]], "tb_developed")
  expect_equal(by_nomer[["1003"]], "unknown")
  expect_true(is.na(by_nomer[["2002"]]))
})

test_that("censoring_flag() flags only records screened within the window before analysis_date", {
  flagged <- censoring_flag(df, analysis_date = as.Date("2026-06-17"), window_months = 12)
  by_nomer <- stats::setNames(flagged, df$Nomer)

  expect_true(by_nomer[["2002"]])
  expect_false(by_nomer[["3002"]])
})

test_that("build_analysis_table() binds every derived column onto the raw table without row loss", {
  table <- build_analysis_table(df, analysis_date = as.Date("2026-06-17"))

  expect_equal(nrow(table), nrow(df))
  expect_true(all(c(
    "age", "age_band", "adherence_ratio",
    "days_screening_to_eval", "days_eval_to_tx_start",
    "days_tx_start_to_scheme", "days_scheme_to_outcome", "days_screening_to_outcome",
    "initiated_within_30d", "initiated_within_60d",
    "diagnosis_branch", "outcome_branch", "final_outcome_category", "censored"
  ) %in% names(table)))
})

test_that("persist_analysis_table() round-trips the analysis table through Parquet", {
  table <- build_analysis_table(df, analysis_date = as.Date("2026-06-17"))
  out_dir <- withr::local_tempdir()
  path <- persist_analysis_table(table, run_date = as.Date("2026-06-17"), dir = out_dir)

  expect_true(file.exists(path))
  reloaded <- arrow::read_parquet(path)
  expect_equal(nrow(reloaded), nrow(table))
  expect_equal(ncol(reloaded), ncol(table))
})
