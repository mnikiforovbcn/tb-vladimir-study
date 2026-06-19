fixture_path <- testthat::test_path("fixtures", "synthetic_rows.csv")
df <- suppressWarnings(load_raw(fixture_path))
tab <- build_analysis_table(df, analysis_date = as.Date("2026-06-17"))

test_that("wilson_ci() guards n == 0 and matches the raw proportion exactly", {
  ci <- wilson_ci(c(2, 0, 5), c(4, 0, 5))

  expect_equal(ci$proportion, c(0.5, NA, 1))
  expect_true(all(is.na(ci[2, ])))
  expect_equal(ci$ci_upper[3], 1)
  expect_true(ci$ci_lower[1] < ci$proportion[1] && ci$proportion[1] < ci$ci_upper[1])
})

test_that("suppress_small_cells() blanks every numeric column only on rows below threshold", {
  result <- suppress_small_cells(tibble::tibble(n = c(2, 10), x = c(1, 8)), c("n", "x"))

  expect_equal(result$suppressed, c(TRUE, FALSE))
  expect_true(all(is.na(result[1, c("n", "x")])))
  expect_equal(result$n[2], 10)
  expect_equal(result$x[2], 8)
})

test_that("step_proportion() gives identical results for a column-name string and an equivalent logical vector", {
  by_name <- step_proportion(tab, "reached_screening", "Source")
  by_vector <- step_proportion(tab, tab$reached_screening, "Source")

  expect_equal(by_name, by_vector)
  expect_equal(dplyr::filter(by_name, Source == "Vladimir")$n, 13)
})

test_that("table1() builds a Source-stratified gtsummary object without error", {
  t1 <- table1(tab, by = "Source")

  expect_s3_class(t1, "gtsummary")
  expect_equal(t1$inputs$by, "Source")
  expect_gt(nrow(t1$table_body), 0)
})

test_that("contacts_per_index_case() counts repeated screenings of the same index case", {
  result <- contacts_per_index_case(tab)

  expect_equal(result$n_index_cases, 13)
  expect_equal(result$median_contacts, 1)
})

test_that("screening_cascade() computes Step 2 milestone proportions over the full cohort", {
  result <- screening_cascade(tab)

  expect_equal(result$n, rep(17L, 4))
  expect_equal(result$x, c(17L, 10L, 10L, 11L))
  expect_false(any(result$suppressed))
})

test_that("diagnostic_outcomes() restricts the denominator to fully evaluated records", {
  result <- diagnostic_outcomes(tab)
  by_milestone <- dplyr::filter(result, milestone == "LTI")

  expect_equal(by_milestone$n, 11)
  expect_equal(by_milestone$x, 8)
  expect_true(dplyr::filter(result, milestone == "Confirmed active TB")$suppressed)
})

test_that("lti_treatment_cascade() and initiation_delay_summary() restrict to those eligible and started", {
  cascade <- lti_treatment_cascade(tab)
  expect_equal(cascade$n, rep(8L, 3))
  expect_equal(cascade$x, c(8L, 8L, 7L))

  delay <- initiation_delay_summary(tab)
  expect_equal(delay$delay$n, 7)
  expect_equal(delay$delay$median_days, 10)
  expect_equal(delay$within_target$n, rep(7L, 2))
  expect_equal(delay$within_target$x, rep(7L, 2))
})

test_that("regimen_composition() and outcome_breakdown() summarise the started subset", {
  regimen <- regimen_composition(tab)
  expect_equal(nrow(regimen), 3)

  outcomes <- outcome_breakdown(tab)
  expect_setequal(as.character(outcomes$outcome_branch), c("completed", "tb_developed", "continuing"))
})

test_that("incentive_uptake() degrades to NA, not an error, when a stratified subgroup has zero recipients", {
  overall <- incentive_uptake(tab)
  expect_equal(dplyr::filter(overall, milestone == "Screening incentive")$n, 17)
  expect_equal(dplyr::filter(overall, milestone == "Screening incentive")$x, 14)

  by_source <- incentive_uptake(tab, "Source")
  vladimir_dose50 <- dplyr::filter(by_source, milestone == "50% dose incentive", Source == "Vladimir")
  expect_true(vladimir_dose50$suppressed)
  expect_true(is.na(vladimir_dose50$median_delay_days))
})

test_that("final_outcome_distribution() excludes censored records and unmapped FinalOutcome codes", {
  result <- final_outcome_distribution(tab)

  expect_equal(dplyr::filter(result, final_outcome_category == "no_tb")$n, 5)
  expect_equal(dplyr::filter(result, final_outcome_category == "unknown")$n, 9)
  expect_true(dplyr::filter(result, final_outcome_category == "tb_developed")$suppressed)
})

test_that("incidence_rate() suppresses a genuinely small case count rather than reporting it", {
  result <- incidence_rate(tab, analysis_date = as.Date("2026-06-17"))

  expect_true(result$suppressed)
  expect_true(is.na(result$cases))
})

test_that("site_comparison() binds every Step 2-8 table despite differing per-step milestone levels", {
  result <- site_comparison(tab)

  expect_equal(nrow(result), 72)
  expect_true(is.character(result$milestone))
  expect_setequal(unique(result$step), c(
    "Step 2: Screening cascade", "Step 3: Diagnostic outcomes", "Step 4: LTI treatment cascade",
    "Step 5: Regimen composition", "Step 6: Dose threshold uptake", "Step 7: Incentive uptake",
    "Step 8: Follow-up outcomes"
  ))
})
