fixture_path <- testthat::test_path("fixtures", "synthetic_rows.csv")
df <- suppressWarnings(load_raw(fixture_path))
tab <- build_analysis_table(df, analysis_date = as.Date("2026-06-17"))

test_that("quarterly_counts() zero-fills empty quarters and only suppresses nonzero small counts", {
  result <- quarterly_counts(tab, "DateScreening")

  expect_equal(nrow(result), 31)
  q3_2018 <- dplyr::filter(result, quarter == "2018 Q3")
  expect_true(q3_2018$suppressed)
  expect_true(is.na(q3_2018$n))

  q4_2018 <- dplyr::filter(result, quarter == "2018 Q4")
  expect_false(q4_2018$suppressed)
  expect_equal(q4_2018$n, 0L)
})

test_that("enrollment_trends() shares one combinable quarter range across all three milestones", {
  result <- enrollment_trends(tab)

  expect_equal(nrow(result), 93)
  expect_true(is.ordered(result$quarter))
  expect_equal(nlevels(result$quarter), 31)
  expect_setequal(as.character(unique(result$milestone)), c(
    "Enrollment", "Treatment initiation", "Outcome recorded"
  ))

  enrollment_q4_2018 <- dplyr::filter(result, milestone == "Enrollment", quarter == "2018 Q4")
  expect_equal(enrollment_q4_2018$n, 0L)
  expect_false(enrollment_q4_2018$suppressed)
})
