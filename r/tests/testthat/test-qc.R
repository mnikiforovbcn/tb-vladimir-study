fixture_path <- testthat::test_path("fixtures", "synthetic_rows.csv")
df <- suppressWarnings(load_raw(fixture_path))

test_that("check_duplicate_registrations() finds the duplicated registration", {
  flagged <- check_duplicate_registrations(df)
  expect_equal(nrow(flagged), 2L)
  expect_true(all(flagged$Source == "Vladimir" & flagged$Nomer == 1005))
})

test_that("check_treat_group_onehot() flags an index mismatch but not a consistent all-zero/NA group", {
  flagged <- check_treat_group_onehot(df)
  expect_equal(nrow(flagged), 1L)
  expect_equal(flagged$Source, "Vladimir")
  expect_equal(flagged$Nomer, 1003L)
  expect_equal(flagged$issue, "index_mismatch")
})

test_that("check_treat_group_onehot() does not flag TreatGroup==NA with all flags unset", {
  na_consistent <- data.frame(
    Source = "Test", Nomer = 9999L, TreatGroup = NA_integer_,
    TreatGroup_01 = 0L, TreatGroup_02 = 0L, TreatGroup_03 = 0L
  )
  expect_equal(nrow(check_treat_group_onehot(na_consistent)), 0L)
})

test_that("check_treat_group_onehot() still flags a one-hot sum violation when TreatGroup is NA", {
  na_inconsistent <- data.frame(
    Source = "Test", Nomer = 9998L, TreatGroup = NA_integer_,
    TreatGroup_01 = 1L, TreatGroup_02 = 1L, TreatGroup_03 = 0L
  )
  flagged <- check_treat_group_onehot(na_inconsistent)
  expect_equal(nrow(flagged), 1L)
  expect_equal(flagged$issue, "sum_not_one")
})

test_that("check_outcome_mutual_exclusivity() flags the completed+TB-developed record", {
  flagged <- check_outcome_mutual_exclusivity(df)
  expect_equal(nrow(flagged), 1L)
  expect_equal(flagged$Source, "Vladimir")
  expect_equal(flagged$Nomer, 1004L)
  expect_equal(flagged$n_flags_set, 2L)
})

test_that("check_diagnosis_mutual_exclusivity() flags the confirmed-TB+LTI record", {
  flagged <- check_diagnosis_mutual_exclusivity(df)
  expect_equal(nrow(flagged), 1L)
  expect_equal(flagged$Source, "Murom")
  expect_equal(flagged$Nomer, 2001L)
  expect_equal(flagged$n_flags_set, 2L)
})

test_that("check_date_order() flags the reversed screening/evaluation dates", {
  flagged <- check_date_order(df)
  expect_equal(nrow(flagged), 1L)
  expect_equal(flagged$Source, "Vladimir")
  expect_equal(flagged$Nomer, 1002L)
  expect_equal(flagged$date_a, "DateScreening")
  expect_equal(flagged$date_b, "DateCompleteExaminationTB")
})

test_that("date_order_pair_summary() reports completeness and reversal rate per pair", {
  pairs <- date_order_pair_summary(df)
  expect_equal(nrow(pairs), length(DATE_ORDER_SEQUENCE) - 1L)
  first <- pairs[pairs$date_a == "DateScreening", ]
  expect_equal(first$n_both_present, 11L)
  expect_equal(first$n_reversed, 1L)
})

test_that("check_dose_consistency() flags both the over-dose and threshold-inconsistent records", {
  flagged <- check_dose_consistency(df)
  expect_setequal(flagged$issue, c("doses_exceed_schema", "take50pc_inconsistent"))

  over_dose <- flagged[flagged$issue == "doses_exceed_schema", ]
  expect_equal(over_dose$Source, "Kovrov")
  expect_equal(over_dose$Nomer, 3001L)

  inconsistent <- flagged[flagged$issue == "take50pc_inconsistent", ]
  expect_equal(inconsistent$Source, "Vladimir")
  expect_equal(inconsistent$Nomer, 1012L)
})

test_that("check_age_range() flags the negative-age and over-100 records", {
  flagged <- check_age_range(df)
  expect_setequal(flagged$Nomer, c(1007L, 1008L))
  negative <- flagged[flagged$Nomer == 1007L, ]
  expect_true(negative$age_years < 0)
  elderly <- flagged[flagged$Nomer == 1008L, ]
  expect_true(elderly$age_years > 100)
})

test_that("audit_missingness() marks always-required columns as unexplained when missing", {
  audit <- audit_missingness(df)
  date_screening_row <- audit$by_column[audit$by_column$column == "DateScreening", ]
  expect_equal(date_screening_row$category, "unexplained")

  outcome_row <- audit$by_column[audit$by_column$column == "FinalOutcome", ]
  expect_equal(outcome_row$category, "structural")
  expect_gt(outcome_row$n_missing, 0)
})

test_that("audit_missingness() breaks missingness down by site", {
  audit <- audit_missingness(df)
  expect_true(all(c("column", "Source", "n_missing", "n", "pct_missing") %in% names(audit$by_site)))
  expect_true(all(df$Source %in% audit$by_site$Source))
})

test_that("run_qc() aggregates schema and cross-field checks with per-site breakdowns", {
  qc <- run_qc(df)
  expect_setequal(
    qc$check_summary$check,
    c(
      "duplicate_registrations", "treat_group_onehot", "outcome_mutual_exclusivity",
      "diagnosis_mutual_exclusivity", "date_order", "dose_consistency", "age_range"
    )
  )
  dup_row <- qc$check_summary[qc$check_summary$check == "duplicate_registrations", ]
  expect_equal(dup_row$n_flagged, 2L)
  expect_match(dup_row$by_site, "Vladimir=2")
  expect_true(all(qc$schema_summary$all_passed))
})

test_that("render_qc_report() writes a readable Markdown file with the expected sections", {
  qc <- run_qc(df)
  out_path <- file.path(withr::local_tempdir(), "qc_report.md")
  render_qc_report(qc, out_path)

  expect_true(file.exists(out_path))
  contents <- readLines(out_path)
  expect_true(any(grepl("^# QC Report", contents)))
  expect_true(any(grepl("^## Schema validation", contents)))
  expect_true(any(grepl("^## Cross-field check summary", contents)))
  expect_true(any(grepl("^## Date-order pair breakdown", contents)))
  expect_true(any(grepl("^## Missingness audit", contents)))
})
