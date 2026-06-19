fixture_path <- testthat::test_path("fixtures", "synthetic_rows.csv")
df <- suppressWarnings(load_raw(fixture_path))
tab <- build_analysis_table(df, analysis_date = as.Date("2026-06-17"))

test_that("funnel_chart() drops suppressed milestones before plotting", {
  result <- diagnostic_outcomes(tab)
  expect_equal(sum(result$suppressed), 3)

  p <- funnel_chart(result)
  expect_s3_class(p, "ggplot")
  expect_equal(nrow(ggplot2::layer_data(p, 1)), 1)
})

test_that("funnel_chart() facets by TargetGroup using display labels, dropping fully-suppressed panels", {
  result <- screening_cascade(tab, "TargetGroup")
  p <- funnel_chart(result, facet_var = "TargetGroup")

  built <- ggplot2::ggplot_build(p)
  expect_equal(as.character(built$layout$layout$TargetGroup), "Contact")
})

test_that("outcome_stacked_bar() returns a ggplot over the un-suppressed breakdown", {
  result <- outcome_breakdown(tab, "Source")
  p <- outcome_stacked_bar(result, "outcome_branch", "Source")

  expect_s3_class(p, "ggplot")
  expect_equal(nrow(ggplot2::layer_data(p, 1)), sum(!result$suppressed))
})

test_that("trend_line_chart() colors by milestone by default, or by an explicit color_var", {
  et <- enrollment_trends(tab)
  p1 <- trend_line_chart(et)
  expect_equal(rlang::as_label(p1$mapping$colour), "milestone")

  qc <- quarterly_counts(tab, "DateScreening", group_vars = "Source")
  p2 <- trend_line_chart(qc, color_var = "Source")
  expect_equal(rlang::as_label(p2$mapping$colour), "Source")
})

test_that("render_table1() returns a gt table with a disclosure-control footnote", {
  g <- render_table1(table1(tab, by = "Source"))

  expect_s3_class(g, "gt_tbl")
  footnotes <- vapply(g[["_footnotes"]]$footnotes, paste, character(1), collapse = " ")
  expect_true(any(grepl("disclosure-control policy", footnotes, fixed = TRUE)))
})

test_that("site_comparison_table() pivots wide by Source and marks suppressed cells '<5'", {
  result <- site_comparison(tab)
  g <- site_comparison_table(result)
  expect_s3_class(g, "gt_tbl")

  cells <- g[["_data"]]
  confirmed_tb <- dplyr::filter(cells, milestone == "Confirmed active TB")
  expect_equal(confirmed_tb$Vladimir, "<5")

  lti_row <- dplyr::filter(cells, milestone == "LTI")
  expect_equal(lti_row$Vladimir, "5/8 (62%)")
})

test_that("export() writes a PNG, and HTML only when interactive = TRUE, for a ggplot", {
  out <- withr::local_tempfile()
  export(funnel_chart(screening_cascade(tab)), out, interactive = FALSE)

  expect_true(file.exists(paste0(out, ".png")))
  expect_false(file.exists(paste0(out, ".html")))
})

test_that("export() writes a self-contained HTML page for a gt_tbl", {
  out <- withr::local_tempfile()
  export(render_table1(table1(tab, by = "Source")), out)

  expect_true(file.exists(paste0(out, ".html")))
})
