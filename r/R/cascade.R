#' Wilson 95% confidence interval for a binomial proportion
#'
#' Vectorized: `x`/`n` may be vectors, returning one row per element. Groups
#' with `n == 0` get `NA` for all three columns rather than erroring.
#' @param x Number of successes (vectorized).
#' @param n Number of trials (vectorized).
#' @param conf_level Confidence level; defaults to 0.95.
#' @return A tibble with `proportion`, `ci_lower`, `ci_upper`.
#' @export
wilson_ci <- function(x, n, conf_level = 0.95) {
  result <- tibble::tibble(
    proportion = rep(NA_real_, length(n)), ci_lower = NA_real_, ci_upper = NA_real_
  )
  valid <- !is.na(n) & n > 0
  if (any(valid)) {
    ci <- binom::binom.confint(x = x[valid], n = n[valid], conf.level = conf_level, methods = "wilson")
    result$proportion[valid] <- ci$mean
    result$ci_lower[valid] <- ci$lower
    result$ci_upper[valid] <- ci$upper
  }
  result
}

#' Suppress small cells per the Study Plan's disclosure-control policy
#'
#' Per Descriptive Study Plan SS11, no stratified cell with a count below
#' `threshold` may be presented, since it could indirectly identify an
#' individual (particularly at the smaller sites). Any row where a column
#' in `count_cols` is below `threshold` has every numeric column (counts,
#' proportions, confidence intervals) replaced with `NA` and is marked
#' `suppressed = TRUE`, so a caller can render e.g. `"<5"` without ever
#' holding the real value past this point in the pipeline.
#'
#' @param df A data frame, one row per stratified cell.
#' @param count_cols Character vector of column names in `df` holding raw
#'   counts to check against `threshold` (typically the denominator `n`
#'   and, where present, the numerator `x`).
#' @param threshold Minimum count required to display a cell; defaults to
#'   [SMALL_CELL_THRESHOLD].
#' @return `df` with a new `suppressed` logical column, and all numeric
#'   columns blanked to `NA` on suppressed rows.
#' @export
suppress_small_cells <- function(df, count_cols, threshold = SMALL_CELL_THRESHOLD) {
  small <- Reduce(`|`, lapply(count_cols, function(col) !is.na(df[[col]]) & df[[col]] < threshold))
  df$suppressed <- small
  numeric_cols <- names(df)[vapply(df, is.numeric, logical(1))]
  for (col in numeric_cols) {
    df[[col]][small] <- NA
  }
  df
}

#' Proportion-with-Wilson-CI summary of a logical flag, optionally grouped
#'
#' `NA` in `flag` means "unknown" and is excluded from both the numerator
#' and the denominator -- consistent with how [cascade_flags()] propagates
#' missingness through the pipeline.
#' @param df A data frame, used for `group_vars`.
#' @param flag Either the name of a logical/0-1 column in `df`, or a
#'   logical vector of length `nrow(df)`.
#' @param group_vars Character vector of column names in `df` to group by;
#'   `character(0)` (the default) summarises the whole table as one row.
#' @return A tibble with the `group_vars` columns, `n`, `x`.
#' @keywords internal
.proportion_ci <- function(df, flag, group_vars = character(0)) {
  flag_vec <- if (is.character(flag) && length(flag) == 1L) df[[flag]] else flag
  work <- dplyr::mutate(df, .flag = flag_vec)

  summarised <- if (length(group_vars) == 0L) {
    tibble::tibble(n = sum(!is.na(work$.flag)), x = sum(work$.flag, na.rm = TRUE))
  } else {
    work |>
      dplyr::group_by(dplyr::across(dplyr::all_of(group_vars))) |>
      dplyr::summarise(n = sum(!is.na(.data$.flag)), x = sum(.data$.flag, na.rm = TRUE), .groups = "drop")
  }
  dplyr::bind_cols(summarised, wilson_ci(summarised$x, summarised$n))
}

#' Proportion-with-Wilson-CI summary, suppressed per the disclosure-control policy
#'
#' Thin wrapper around [.proportion_ci()] that applies [suppress_small_cells()]
#' to its result; the building block used by every Step 2-8 milestone-proportion
#' function in this file.
#' @inheritParams .proportion_ci
#' @return A tibble with the `group_vars` columns, `n`, `x`, `proportion`,
#'   `ci_lower`, `ci_upper`, `suppressed`.
#' @export
step_proportion <- function(df, flag, group_vars = character(0)) {
  suppress_small_cells(.proportion_ci(df, flag, group_vars), count_cols = c("n", "x"))
}

#' Category-breakdown summary (counts and proportions summing to 1 within group)
#' @param df A data frame.
#' @param category_col Character: name of a factor/character column in `df`.
#' @param group_vars Character vector of column names to group by.
#' @return A tibble with `group_vars`, `category_col`, `n`, `total`,
#'   `proportion`, `suppressed`.
#' @keywords internal
.category_breakdown <- function(df, category_col, group_vars = character(0)) {
  df |>
    dplyr::filter(!is.na(.data[[category_col]])) |>
    dplyr::count(dplyr::across(dplyr::all_of(c(group_vars, category_col))), name = "n") |>
    dplyr::group_by(dplyr::across(dplyr::all_of(group_vars))) |>
    dplyr::mutate(total = sum(.data$n), proportion = .data$n / .data$total) |>
    dplyr::ungroup() |>
    suppress_small_cells(count_cols = c("n", "total"))
}

#' Step 1 population-profile summary table (Table 1)
#'
#' `TargetGroup`, `Sex`, and `RelationWithSource` are recoded to labelled
#' factors for display only -- the underlying analysis table keeps the raw
#' coded values. Missing `RelationWithSource` for non-contact target groups
#' is structural (Study Plan SS10), not a data-quality defect; `missing =
#' "ifany"` surfaces it as a normal category rather than silently dropping it.
#' @param df Analysis-ready table, as returned by [build_analysis_table()].
#' @param by Stratifying column name, or `NULL` for an unstratified summary;
#'   defaults to `"Source"`.
#' @return A `gtsummary::tbl_summary` object.
#' @export
table1 <- function(df, by = "Source") {
  vars <- c("Source", "TargetGroup", "Sex", "age", "age_band", "RelationWithSource")
  if (!is.null(by)) vars <- setdiff(vars, by)

  labelled <- df |>
    dplyr::mutate(
      TargetGroup = factor(
        .data$TargetGroup, levels = seq_along(TARGET_GROUP_LABELS), labels = TARGET_GROUP_LABELS
      ),
      Sex = factor(.data$Sex, levels = 1:2, labels = c("Male", "Female")),
      RelationWithSource = factor(
        .data$RelationWithSource, levels = c(45L, 313L, 314L, 348L, 366L),
        labels = c("Colleague", "Neighbor", "Other", "Relative/cohabitant", "Healthcare worker")
      )
    ) |>
    dplyr::select(dplyr::all_of(unique(c(vars, by))))

  gtsummary::tbl_summary(
    labelled, by = by,
    statistic = list(gtsummary::all_continuous() ~ "{median} ({p25}, {p75})"),
    missing = "ifany"
  )
}

#' Step 1 median/IQR of number of contacts screened per index case
#' @param df Analysis-ready table.
#' @return A one-row tibble: `n_index_cases`, `median_contacts`, `iqr_low`, `iqr_high`.
#' @export
contacts_per_index_case <- function(df) {
  counts <- df |>
    dplyr::filter(.data$TargetGroup == 1L, !is.na(.data$IndexCase), .data$Screening == 1L) |>
    dplyr::count(.data$IndexCase, name = "n_contacts_screened")

  tibble::tibble(
    n_index_cases = nrow(counts),
    median_contacts = stats::median(counts$n_contacts_screened),
    iqr_low = stats::quantile(counts$n_contacts_screened, 0.25),
    iqr_high = stats::quantile(counts$n_contacts_screened, 0.75)
  )
}

#' Step 2 screening cascade: proportion reaching each milestone, of the full cohort
#' @param df Analysis-ready table.
#' @param group_vars Character vector of column names to group by.
#' @return A tibble: `milestone` (ordered factor) plus the [step_proportion()] columns.
#' @export
screening_cascade <- function(df, group_vars = character(0)) {
  milestones <- c(
    reached_screening = "Screened", reached_suspected = "Suspected TB",
    diaskintest_positive = "Diaskintest positive", reached_full_eval = "Fully evaluated"
  )
  purrr::imap(milestones, function(label, col) {
    step_proportion(df, col, group_vars) |> dplyr::mutate(milestone = label, .before = 1)
  }) |>
    dplyr::bind_rows() |>
    dplyr::mutate(milestone = factor(.data$milestone, levels = unname(milestones), ordered = TRUE))
}

#' Step 3 diagnostic outcomes among those fully evaluated
#' @inheritParams screening_cascade
#' @return A tibble: `milestone` (ordered factor) plus the [step_proportion()] columns.
#' @export
diagnostic_outcomes <- function(df, group_vars = character(0)) {
  evaluated <- df[df$reached_full_eval %in% TRUE, ]
  milestones <- c(
    confirmed_active_tb = "Confirmed active TB", has_lti = "LTI",
    no_tb_no_lti = "No TB, no LTI", no_tb_lti_unknown = "No TB, LTI unknown"
  )
  purrr::imap(milestones, function(label, col) {
    step_proportion(evaluated, col, group_vars) |> dplyr::mutate(milestone = label, .before = 1)
  }) |>
    dplyr::bind_rows() |>
    dplyr::mutate(milestone = factor(.data$milestone, levels = unname(milestones), ordered = TRUE))
}

#' Step 4 LTI preventive treatment cascade among those eligible
#' @inheritParams screening_cascade
#' @return A tibble: `milestone` (ordered factor) plus the [step_proportion()] columns.
#' @export
lti_treatment_cascade <- function(df, group_vars = character(0)) {
  eligible <- df[df$eligible_for_lti_tx %in% TRUE, ]
  milestones <- c(
    lti_recommended = "Recommended", lti_prescribed = "Prescribed", lti_started = "Started"
  )
  purrr::imap(milestones, function(label, col) {
    step_proportion(eligible, col, group_vars) |> dplyr::mutate(milestone = label, .before = 1)
  }) |>
    dplyr::bind_rows() |>
    dplyr::mutate(milestone = factor(.data$milestone, levels = unname(milestones), ordered = TRUE))
}

#' Step 4 treatment-initiation delay and within-target proportions, among those started
#'
#' Delay is `days_eval_to_tx_start` (`DateCompleteExaminationTB` to
#' `DatePrevTreatmentStart`), as defined in [time_intervals()].
#' @inheritParams screening_cascade
#' @return A list with `delay` (one row per group: `n`, `median_days`,
#'   `iqr_low`, `iqr_high`, `suppressed`) and `within_target` (one row per
#'   group per entry in [INITIATION_TARGET_DAYS]: `target`, plus the
#'   [step_proportion()] columns).
#' @export
initiation_delay_summary <- function(df, group_vars = character(0)) {
  started <- df[df$lti_started %in% TRUE, ]

  delay_summary <- if (length(group_vars) == 0L) {
    tibble::tibble(
      n = sum(!is.na(started$days_eval_to_tx_start)),
      median_days = stats::median(started$days_eval_to_tx_start, na.rm = TRUE),
      iqr_low = stats::quantile(started$days_eval_to_tx_start, 0.25, na.rm = TRUE),
      iqr_high = stats::quantile(started$days_eval_to_tx_start, 0.75, na.rm = TRUE)
    )
  } else {
    started |>
      dplyr::group_by(dplyr::across(dplyr::all_of(group_vars))) |>
      dplyr::summarise(
        n = sum(!is.na(.data$days_eval_to_tx_start)),
        median_days = stats::median(.data$days_eval_to_tx_start, na.rm = TRUE),
        iqr_low = stats::quantile(.data$days_eval_to_tx_start, 0.25, na.rm = TRUE),
        iqr_high = stats::quantile(.data$days_eval_to_tx_start, 0.75, na.rm = TRUE),
        .groups = "drop"
      )
  }
  delay_summary <- suppress_small_cells(delay_summary, count_cols = "n")

  within_target <- purrr::map(c("initiated_within_30d", "initiated_within_60d"), function(col) {
    step_proportion(started, col, group_vars) |> dplyr::mutate(target = col, .before = 1)
  }) |> dplyr::bind_rows()

  list(delay = delay_summary, within_target = within_target)
}

#' Step 5 regimen composition among those started, with a bedaquiline/moxifloxacin overlap check
#'
#' `RegBq` and `RegMfx` are not mutually exclusive (Study Plan SS5); the
#' `overlap` row is the proportion of started records with both set.
#' @inheritParams screening_cascade
#' @return A tibble: `milestone` (ordered factor: `"Bedaquiline-containing"`,
#'   `"Moxifloxacin-containing"`, `"Both"`) plus the [step_proportion()] columns.
#' @export
regimen_composition <- function(df, group_vars = character(0)) {
  started <- df[df$lti_started %in% TRUE, ]
  milestones <- c(RegBq = "Bedaquiline-containing", RegMfx = "Moxifloxacin-containing")

  by_regimen <- purrr::imap(milestones, function(label, col) {
    step_proportion(started, started[[col]] == 1L, group_vars) |>
      dplyr::mutate(milestone = label, .before = 1)
  }) |> dplyr::bind_rows()

  overlap <- step_proportion(started, (started$RegBq == 1L) & (started$RegMfx == 1L), group_vars) |>
    dplyr::mutate(milestone = "Both", .before = 1)

  dplyr::bind_rows(by_regimen, overlap) |>
    dplyr::mutate(milestone = factor(.data$milestone, levels = c(unname(milestones), "Both"), ordered = TRUE))
}

#' Step 5 regimen composition by calendar year of treatment start
#' @param df Analysis-ready table.
#' @return The `milestone`/`year` tibble from [regimen_composition()]'s
#'   `by_regimen`/`overlap` rows, grouped by `year(DatePrevTreatmentStart)`.
#' @export
regimen_by_year <- function(df) {
  started <- df[df$lti_started %in% TRUE & !is.na(df$DatePrevTreatmentStart), ]
  started <- dplyr::mutate(started, year = lubridate::year(.data$DatePrevTreatmentStart))
  regimen_composition(started, group_vars = "year")
}

#' Step 6 proportion reaching the 50%/100% dose thresholds, among those started
#' @inheritParams screening_cascade
#' @return A tibble: `milestone` (ordered factor) plus the [step_proportion()] columns.
#' @export
dose_threshold_uptake <- function(df, group_vars = character(0)) {
  started <- df[df$lti_started %in% TRUE, ]
  milestones <- c(Take50pc = "Took >=50% of doses", Take100pc = "Took 100% of doses")
  purrr::imap(milestones, function(label, col) {
    step_proportion(started, started[[col]] == 1L, group_vars) |>
      dplyr::mutate(milestone = label, .before = 1)
  }) |>
    dplyr::bind_rows() |>
    dplyr::mutate(milestone = factor(.data$milestone, levels = unname(milestones), ordered = TRUE))
}

#' Step 6 adherence ratio distribution (median/IQR), among those started
#' @inheritParams screening_cascade
#' @return A tibble: `n`, `median_ratio`, `iqr_low`, `iqr_high`, `suppressed`.
#' @export
adherence_summary <- function(df, group_vars = character(0)) {
  started <- df[df$lti_started %in% TRUE, ]

  summarised <- if (length(group_vars) == 0L) {
    tibble::tibble(
      n = sum(!is.na(started$adherence_ratio)),
      median_ratio = stats::median(started$adherence_ratio, na.rm = TRUE),
      iqr_low = stats::quantile(started$adherence_ratio, 0.25, na.rm = TRUE),
      iqr_high = stats::quantile(started$adherence_ratio, 0.75, na.rm = TRUE)
    )
  } else {
    started |>
      dplyr::group_by(dplyr::across(dplyr::all_of(group_vars))) |>
      dplyr::summarise(
        n = sum(!is.na(.data$adherence_ratio)),
        median_ratio = stats::median(.data$adherence_ratio, na.rm = TRUE),
        iqr_low = stats::quantile(.data$adherence_ratio, 0.25, na.rm = TRUE),
        iqr_high = stats::quantile(.data$adherence_ratio, 0.75, na.rm = TRUE),
        .groups = "drop"
      )
  }
  suppress_small_cells(summarised, count_cols = "n")
}

#' Step 6 treatment-outcome breakdown among those started, summing to 100% within group
#' @inheritParams screening_cascade
#' @return A tibble from [.category_breakdown()] on `outcome_branch`.
#' @export
outcome_breakdown <- function(df, group_vars = character(0)) {
  started <- df[df$lti_started %in% TRUE, ]
  .category_breakdown(started, "outcome_branch", group_vars)
}

#' Uptake proportion and median payment delay for a single incentive
#'
#' @param df A data frame already restricted to those eligible for this incentive.
#' @param flag_col Character: name of the 0/1 "received" column, or `NULL`
#'   if `flag_vec` is supplied directly (for the TreatGroup-dispatched 1-year incentive).
#' @param flag_vec Optional logical vector, used instead of `flag_col`.
#' @param date_col Character: name of the payment-date column (or a
#'   computed column already present in `df`).
#' @param milestone_col Character: name of the reference-date column the
#'   delay is measured from.
#' @param label Character: value for the `milestone` column in the result.
#' @param group_vars Character vector of column names to group by.
#' @return A tibble: `milestone`, `group_vars`, `n`, `x`, `proportion`,
#'   `ci_lower`, `ci_upper`, `median_delay_days`, `delay_iqr_low`,
#'   `delay_iqr_high`, `suppressed`.
#' @keywords internal
.incentive_step <- function(df, flag_col = NULL, flag_vec = NULL, date_col, milestone_col, label,
                             group_vars = character(0)) {
  flag <- if (is.null(flag_vec)) df[[flag_col]] == 1L else flag_vec
  uptake <- .proportion_ci(df, flag, group_vars)

  received <- dplyr::mutate(df, .flag = flag)
  received <- received[received$.flag %in% TRUE, ]
  delay_days <- as.numeric(received[[date_col]] - received[[milestone_col]])

  delay_summary <- if (length(group_vars) == 0L) {
    tibble::tibble(
      median_delay_days = stats::median(delay_days, na.rm = TRUE),
      delay_iqr_low = stats::quantile(delay_days, 0.25, na.rm = TRUE),
      delay_iqr_high = stats::quantile(delay_days, 0.75, na.rm = TRUE)
    )
  } else {
    received <- dplyr::mutate(received, .delay = delay_days)
    received |>
      dplyr::group_by(dplyr::across(dplyr::all_of(group_vars))) |>
      dplyr::summarise(
        median_delay_days = stats::median(.data$.delay, na.rm = TRUE),
        delay_iqr_low = stats::quantile(.data$.delay, 0.25, na.rm = TRUE),
        delay_iqr_high = stats::quantile(.data$.delay, 0.75, na.rm = TRUE),
        .groups = "drop"
      )
  }

  combined <- if (length(group_vars) == 0L) {
    dplyr::bind_cols(uptake, delay_summary)
  } else {
    dplyr::left_join(uptake, delay_summary, by = group_vars)
  }
  dplyr::mutate(combined, milestone = label, .before = 1)
}

#' Step 7 incentive payment uptake among those eligible, with median payment delay
#'
#' Delay is measured from the incentive's associated programmatic milestone
#' to the payment date: `DateScreening` for the screening incentive, and
#' `DatePrevTreatmentStart` for the dose-threshold and 1-year incentives --
#' the dataset records only the payment date for those, not the exact date
#' the threshold was crossed, so treatment start is the nearest available
#' reference point. The 1-year incentive's flag/date columns are dispatched
#' by `TreatGroup`, matching [cascade_flags()]'s `supp_1yr_received`.
#' @inheritParams screening_cascade
#' @return A tibble: `milestone` (one row per incentive) plus the
#'   [.incentive_step()] columns, suppressed per [suppress_small_cells()].
#' @export
incentive_uptake <- function(df, group_vars = character(0)) {
  screening_part <- .incentive_step(
    df[df$reached_screening %in% TRUE, ],
    flag_col = "SuppScreening", date_col = "DateSuppScreening", milestone_col = "DateScreening",
    label = "Screening incentive", group_vars = group_vars
  )

  started <- df[df$lti_started %in% TRUE, ]
  dose50_part <- .incentive_step(
    started, flag_col = "Supp50pc", date_col = "DateSupp50pc",
    milestone_col = "DatePrevTreatmentStart", label = "50% dose incentive", group_vars = group_vars
  )
  dose100_part <- .incentive_step(
    started, flag_col = "Supp100pc", date_col = "DateSupp100pc",
    milestone_col = "DatePrevTreatmentStart", label = "100% dose incentive", group_vars = group_vars
  )

  started_1yr <- dplyr::mutate(
    started,
    .supp_1yr_date = dplyr::case_when(
      .data$TreatGroup == 1L ~ .data$DateSupp1yearGr1,
      .data$TreatGroup %in% c(2L, 3L) ~ .data$DateSupp1yearGr23,
      .default = as.Date(NA)
    )
  )
  oneyr_part <- .incentive_step(
    started_1yr, flag_vec = started_1yr$supp_1yr_received, date_col = ".supp_1yr_date",
    milestone_col = "DatePrevTreatmentStart", label = "1-year incentive", group_vars = group_vars
  )

  dplyr::bind_rows(screening_part, dose50_part, dose100_part, oneyr_part) |>
    suppress_small_cells(count_cols = c("n", "x"))
}

#' Step 8 follow-up re-screening and no-TB-after proportions, among those not censored
#' @inheritParams screening_cascade
#' @return A tibble: `milestone` (ordered factor) plus the [step_proportion()] columns.
#' @export
followup_outcomes <- function(df, group_vars = character(0)) {
  matured <- df[df$censored %in% FALSE, ]
  milestones <- c(
    rescreened_1yr = "Re-screened at 1 year", no_tb_after_1yr = "No TB after 1 year",
    rescreened_24mo = "Re-screened at 24 months", no_tb_after_24mo = "No TB after 24 months"
  )
  purrr::imap(milestones, function(label, col) {
    step_proportion(matured, col, group_vars) |> dplyr::mutate(milestone = label, .before = 1)
  }) |>
    dplyr::bind_rows() |>
    dplyr::mutate(milestone = factor(.data$milestone, levels = unname(milestones), ordered = TRUE))
}

#' Step 8 distribution of FinalOutcome, among those not censored
#' @param df Analysis-ready table.
#' @param group_vars Character vector of column names to group by.
#' @param by_completion If `TRUE`, additionally stratify by `completed_or_finished`.
#' @return A tibble from [.category_breakdown()] on `final_outcome_category`.
#' @export
final_outcome_distribution <- function(df, group_vars = character(0), by_completion = FALSE) {
  matured <- df[df$censored %in% FALSE, ]
  vars <- if (isTRUE(by_completion)) c(group_vars, "completed_or_finished") else group_vars
  .category_breakdown(matured, "final_outcome_category", vars)
}

#' Step 8 incidence rate of TB development, per 100 person-years
#'
#' Person-time runs from `DateScreening` to `DateOutcome` where available,
#' or to `analysis_date` for records still under follow-up with no
#' recorded outcome -- per the Study Plan's "DateScreening to DateOutcome
#' or to censoring" definition. Cases are counted from the raw `TBdeveloped`
#' flag (`NA` treated as not-a-confirmed-case, since only confirmed events
#' are counted as numerator events; person-time still accrues for everyone).
#' The confidence interval is the exact Poisson interval via the standard
#' chi-squared relationship (`qchisq()`).
#' @param df Analysis-ready table.
#' @param group_vars Character vector of column names to group by.
#' @param analysis_date The date the analysis is being run as of; defaults to today.
#' @return A tibble: `group_vars`, `cases`, `person_years`, `rate_per_100py`,
#'   `ci_lower`, `ci_upper`, `suppressed`.
#' @export
incidence_rate <- function(df, group_vars = character(0), analysis_date = Sys.Date()) {
  end_date <- dplyr::if_else(!is.na(df$DateOutcome), df$DateOutcome, analysis_date)
  work <- dplyr::mutate(
    df,
    .person_years = as.numeric(end_date - .data$DateScreening) / 365.25,
    .case = .data$TBdeveloped %in% 1L
  )

  summarised <- if (length(group_vars) == 0L) {
    tibble::tibble(cases = sum(work$.case), person_years = sum(work$.person_years, na.rm = TRUE))
  } else {
    work |>
      dplyr::group_by(dplyr::across(dplyr::all_of(group_vars))) |>
      dplyr::summarise(
        cases = sum(.data$.case), person_years = sum(.data$.person_years, na.rm = TRUE), .groups = "drop"
      )
  }

  summarised |>
    dplyr::mutate(
      rate_per_100py = .data$cases / .data$person_years * 100,
      ci_lower = stats::qchisq(0.025, 2 * .data$cases) / 2 / .data$person_years * 100,
      ci_upper = stats::qchisq(0.975, 2 * (.data$cases + 1)) / 2 / .data$person_years * 100
    ) |>
    suppress_small_cells(count_cols = "cases")
}

#' Step 10 site-comparison table: cascade proportions from Steps 2-8, by site
#'
#' Binds every milestone-proportion step function (Steps 2-4, 6-8) grouped
#' by `Source`, plus the year-5 regimen and incentive uptake tables, into
#' one long table for descriptive flagging of sites with higher attrition --
#' not formal between-site hypothesis testing (Study Plan Step 10).
#' @param df Analysis-ready table.
#' @return A tibble: `step`, `milestone`, `Source`, `n`, `x`, `proportion`,
#'   `ci_lower`, `ci_upper`, `suppressed`.
#' @export
site_comparison <- function(df) {
  to_step <- function(tbl, step_label) {
    tbl <- dplyr::mutate(tbl, milestone = as.character(.data$milestone))
    dplyr::mutate(tbl, step = step_label, .before = 1)
  }
  dplyr::bind_rows(
    to_step(screening_cascade(df, "Source"), "Step 2: Screening cascade"),
    to_step(diagnostic_outcomes(df, "Source"), "Step 3: Diagnostic outcomes"),
    to_step(lti_treatment_cascade(df, "Source"), "Step 4: LTI treatment cascade"),
    to_step(regimen_composition(df, "Source"), "Step 5: Regimen composition"),
    to_step(dose_threshold_uptake(df, "Source"), "Step 6: Dose threshold uptake"),
    to_step(incentive_uptake(df, "Source"), "Step 7: Incentive uptake"),
    to_step(followup_outcomes(df, "Source"), "Step 8: Follow-up outcomes")
  )
}
