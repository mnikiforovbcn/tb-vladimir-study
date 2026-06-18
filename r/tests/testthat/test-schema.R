fixture_path <- testthat::test_path("fixtures", "synthetic_rows.csv")

test_that("build_schema_agent() passes every check on the synthetic fixture", {
  df <- suppressWarnings(load_raw(fixture_path))
  agent <- build_schema_agent(df)
  summary <- schema_summary(agent)
  expect_true(all(summary$all_passed))
})

test_that("schema treats NA as passing a value-set check", {
  df <- data.frame(TargetGroup = c(1L, 2L, 3L, 4L, NA))
  agent <- pointblank::create_agent(df) |>
    pointblank::col_vals_in_set(columns = "TargetGroup", set = c(.CODED_VALUE_SETS$TargetGroup, NA)) |>
    pointblank::interrogate()
  expect_true(agent$validation_set$all_passed)
})

test_that("schema flags a genuinely out-of-range coded value", {
  df <- data.frame(TargetGroup = c(1L, 2L, 3L, 4L, 5L))
  agent <- pointblank::create_agent(df) |>
    pointblank::col_vals_in_set(columns = "TargetGroup", set = c(.CODED_VALUE_SETS$TargetGroup, NA)) |>
    pointblank::interrogate()
  expect_false(agent$validation_set$all_passed)
  expect_equal(agent$validation_set$n_failed, 1)
})

test_that("build_schema_agent() finds no out-of-range values in the real CSV", {
  skip_if_not(file.exists(raw_data_path()), "raw dataset not present in this environment")
  df <- suppressWarnings(load_raw())
  summary <- schema_summary(build_schema_agent(df))
  expect_true(all(summary$all_passed))
})
