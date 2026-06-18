fixture_path <- testthat::test_path("fixtures", "synthetic_rows.csv")

test_that("real raw CSV has the expected shape (regression guard)", {
  skip_if_not(file.exists(raw_data_path()), "raw dataset not present in this environment")
  raw_lines <- readLines(raw_data_path())
  header <- strsplit(raw_lines[1], ",", fixed = TRUE)[[1]]

  expect_equal(length(raw_lines) - 1L, N_ROWS_EXPECTED)
  expect_equal(length(header), N_COLS_EXPECTED)
  expect_identical(header, tbcascade:::.EXPECTED_COLUMNS)
})

test_that("load_raw() reads the real CSV with correct dtypes", {
  skip_if_not(file.exists(raw_data_path()), "raw dataset not present in this environment")
  df <- suppressWarnings(load_raw())

  expect_equal(nrow(df), N_ROWS_EXPECTED)
  expect_equal(ncol(df), N_COLS_EXPECTED)
  expect_s3_class(df$BirthDate, "Date")
  expect_s3_class(df$DateOutcome, "Date")
  expect_type(df$Sex, "integer")
  expect_type(df$Source, "character")
})

test_that("load_raw() reads the synthetic fixture with the right row/column count", {
  df <- suppressWarnings(load_raw(fixture_path))
  expect_equal(nrow(df), 17L)
  expect_equal(ncol(df), N_COLS_EXPECTED)
  expect_identical(names(df), tbcascade:::.EXPECTED_COLUMNS)
})

test_that("load_raw() casts flags/codes to integer and dates to Date", {
  df <- suppressWarnings(load_raw(fixture_path))
  expect_type(df$TargetGroup, "integer")
  expect_type(df$DosesTaken, "integer")
  expect_s3_class(df$DateScreening, "Date")
  expect_s3_class(df$DatePrevTreatmentStart, "Date")
  expect_type(df$Source, "character")
  expect_type(df$IndexCase, "character")
})

test_that("load_raw() tolerates a timestamp-suffixed date", {
  df <- suppressWarnings(load_raw(fixture_path))
  row <- df[df$Nomer == 1009 & df$Source == "Vladimir", ]
  expect_equal(row$DateSupp1yearGr1, as.Date("2020-05-14"))
})

test_that("load_raw() coerces a malformed (truncated-year) date to NA and warns", {
  expect_warning(
    df <- load_raw(fixture_path),
    "DatePrevTreatmentStart"
  )
  row <- df[df$Nomer == 3002 & df$Source == "Kovrov", ]
  expect_true(is.na(row$DatePrevTreatmentStart))
})

test_that("load_raw() preserves blank IndexCase and blank FinalOutcome as NA, not 0", {
  df <- suppressWarnings(load_raw(fixture_path))
  homeless_row <- df[df$Nomer == 1010, ]
  expect_true(is.na(homeless_row$IndexCase))

  recent_row <- df[df$Nomer == 2002 & df$Source == "Murom", ]
  expect_true(is.na(recent_row$FinalOutcome))
})

test_that("load_raw() errors clearly on an unexpected column layout", {
  bad_csv <- withr::local_tempfile(fileext = ".csv")
  writeLines(c("Source_id,Source,Nomer", "1,Vladimir,1"), bad_csv)
  expect_error(load_raw(bad_csv), "does not match")
})

test_that("snapshot() writes a readable Parquet file and returns its path", {
  df <- suppressWarnings(load_raw(fixture_path))
  out_dir <- withr::local_tempdir()
  path <- snapshot(df, run_date = as.Date("2026-06-17"), dir = out_dir)

  expect_true(file.exists(path))
  expect_match(basename(path), "raw_snapshot_2026-06-17\\.parquet")

  roundtrip <- arrow::read_parquet(path)
  expect_equal(nrow(roundtrip), nrow(df))
  expect_equal(ncol(roundtrip), ncol(df))
  expect_equal(roundtrip$BirthDate, df$BirthDate)
})
