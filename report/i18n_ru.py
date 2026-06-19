"""Russian presentation-layer translation for the descriptive report.

This module exists for exactly one reason: `report/descriptive_report_ru.qmd`
needs Russian-language section text, column headers, category labels, and
chart text, but `cascade.py`/`trends.py`/`viz.py` (Phase 4/5) must stay
completely untouched -- they are well-tested, audited against the
Descriptive Study Plan, and several of `viz.py`'s chart functions key their
canonical stage ordering and fixed coloring directly off literal English
strings (`_SITE_COLORS`, `_OUTCOME_BRANCH_LABELS`, `_STEP9_METRIC_LABELS`,
`cascade._STEP2_STAGES`, `cascade._LABEL_MAPS`). Translating a DataFrame's
*values* before handing it to `viz.py` would silently break that ordering/
coloring logic (a lookup keyed by the exact English string would simply
miss). So the rule this module follows everywhere:

    Every DataFrame produced by `cascade.py`/`trends.py` and handed to
    `viz.py` stays in English, unmodified, exactly as the English report
    uses it. Translation happens only here, at the last step before
    something is actually displayed -- either as a Russian markdown table
    (`ru_table`/`ru_table1`/`render_step10_ru`, for the steps the English
    report itself renders as a markdown table or that this module
    deliberately renders as one instead of a `go.Table`: Steps 1 and 10),
    or as a dedicated Russian-label sibling of one of `viz.py`'s four real
    Plotly chart functions (`funnel_chart_ru`, `funnel_chart_by_group_ru`,
    `outcome_stacked_bar_ru`, `trend_lines_ru`), which reuse `viz.py`'s
    private validation/suppression helpers and fixed color dictionaries
    (so a site or outcome branch is still always the same color as in the
    English report) but substitute Russian title/axis/legend/hover text.

Disclosed simplifications (consistent with the "separate Russian report,
presentation-layer dictionary" approach the user chose):
- Steps 1 and 10 are rendered as Russian markdown tables here, not as the
  interactive `go.Table` figures `viz.baseline_table`/`viz.site_comparison_
  table` produce for the English report -- those two renderers build their
  table shape directly from a `tableone.TableOne`/generic DataFrame with no
  translation hook, so reproducing their *look* in Russian would mean
  duplicating their layout code for no analytical benefit. The numbers are
  identical; only the rendering technique differs.
- Numeric formatting (raw `pct` fractions, unrounded floats) is left
  identical to the English report's own `show_table` convention -- this is
  deliberate, not an oversight: it lets a reviewer check a Russian table's
  numbers against the same English table cell-for-cell.
- Small-cell suppression itself is never touched here -- every table this
  module renders has already been through `cascade.suppress_small_cells`
  upstream; this module only translates the `suppressed` column's
  True/False display and the chart caption text, never the underlying
  suppression decision.
"""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
from IPython.display import Markdown, display
from plotly.subplots import make_subplots

from i18n_labels import QC_RULE_LABELS_RU, SITE_LABELS_RU
from tb_cascade import viz
from tb_cascade.cascade import SMALL_CELL_THRESHOLD, _LABEL_MAPS, _STEP2_STAGES

# --- Column headers ------------------------------------------------------

#: Russian header for every column name that appears, verbatim, in any
#: `cascade.py`/`trends.py`/`qc.py` table this report renders. Only columns
#: actually present in a given table are ever renamed (`translate_table`
#: looks each column up by name), so this single dict can be reused as-is
#: for every step's table.
COLUMN_LABELS_RU: dict[str, str] = {
    "Source": "Площадка",
    "TargetGroup": "Целевая группа",
    "Sex": "Пол",
    "age_band": "Возрастная группа",
    "RelationWithSource": "Связь с источником",
    "TreatGroup": "Группа лечения",
    "completed_or_finished": "Лечение завершено",
    "stage": "Этап",
    "category": "Категория",
    "regimen": "Режим",
    "threshold": "Порог",
    "incentive": "Стимул",
    "target_days": "Целевой срок (дни)",
    "n": "n",
    "count": "Количество",
    "pct": "Доля",
    "ci_low": "95% ДИ, нижн.",
    "ci_high": "95% ДИ, верхн.",
    "suppressed": "Подавлено (n<5)",
    "median": "Медиана",
    "q1": "Q1",
    "q3": "Q3",
    "events": "События",
    "person_years": "Человеко-лет",
    "rate_per_100py": "Частота на 100 чел.-лет",
    "rule": "Правило",
    "n_checked": "n проверено",
    "n_violations": "n нарушений",
    "violation_rate": "Доля нарушений",
    "year": "Год",
    "quarter": "Квартал",
    "metric": "Показатель",
}

# --- Value labels, one dict per categorical domain ------------------------
#
# Kept as separate dicts (rather than one merged dict keyed by raw value)
# because a few raw codes are reused across domains with a different
# nuance -- e.g. "tb_developed"/"unknown" appear in both `outcome_branch`
# and `final_outcome_category`. Each call site below passes the dict that
# actually matches the column it is translating.

#: `cascade._STEP2_STAGES` (Step 2) and `cascade._STEP4_STAGES` (Step 4)
#: keys combined -- no collisions between the two stage sets, so one dict
#: covers both the Step 2/4 tables and `funnel_chart_ru`/
#: `funnel_chart_by_group_ru`'s y-axis.
STAGE_LABELS_RU: dict[str, str] = {
    "screened": "Скрининг пройден",
    "suspected_tb": "Подозрение на ТБ",
    "diaskintest_positive": "Диаскинтест положительный",
    "full_eval": "Полное обследование завершено",
    "recommended": "Рекомендовано",
    "prescribed": "Назначено",
    "started": "Начато",
}

#: Step 3 `diagnosis_branch` codes (`derive.cascade_flags`).
DIAGNOSIS_BRANCH_RU: dict[str, str] = {
    "confirmed_tb": "Подтверждённый активный ТБ",
    "lti": "Латентная ТБ-инфекция (ЛТИ)",
    "no_tb_no_lti": "Нет ТБ, нет ЛТИ",
    "no_tb_lti_unknown": "Нет ТБ, статус ЛТИ неизвестен",
}

#: Step 6 `outcome_branch` codes (`derive.cascade_flags`) -- same keys as
#: `viz._OUTCOME_BRANCH_LABELS`/`viz._OUTCOME_BRANCH_COLORS`, so
#: `outcome_stacked_bar_ru` looks Russian text up here while still using
#: `viz._OUTCOME_BRANCH_COLORS[code]` for the fixed color.
OUTCOME_BRANCH_RU: dict[str, str] = {
    "completed": "Завершено (100% доз)",
    "finished": "Окончено (85–99% доз)",
    "continuing": "Продолжается",
    "not_finished": "Не завершено",
    "stopped_med": "Остановлено (по мед. показаниям)",
    "tb_developed": "Развился ТБ",
    "unknown": "Исход неизвестен",
}

#: Step 8 `final_outcome_category` codes (`derive._FINAL_OUTCOME_LABELS`).
FINAL_OUTCOME_RU: dict[str, str] = {
    "no_tb": "ТБ не развился",
    "tb_developed": "Развился ТБ",
    "unknown": "Неизвестно",
    "other": "Другое",
}

#: Step 5 `regimen` codes (`cascade._STEP5_REGIMENS`).
REGIMEN_RU: dict[str, str] = {
    "bedaquiline_containing": "Содержит бедаквилин",
    "moxifloxacin_containing": "Содержит моксифлоксацин",
}

#: Step 6 `threshold` codes (`cascade._STEP6_DOSE_THRESHOLDS`).
THRESHOLD_RU: dict[str, str] = {
    "reached_50pc": "Достигнут порог 50%",
    "reached_100pc": "Достигнут порог 100%",
}

#: Step 7 `incentive` codes (`cascade._STEP7_INCENTIVES`).
INCENTIVE_RU: dict[str, str] = {
    "screening": "Скрининг",
    "dose_50pc": "Доза 50%",
    "dose_100pc": "Доза 100%",
    "one_year": "1 год наблюдения",
}

#: `QC_RULE_LABELS_RU` (`qc.CHECKS` rule names) and `SITE_LABELS_RU`
#: (`Source` values -> Russian city names, keys matching `viz._SITE_COLORS`
#: exactly) now live in `i18n_labels.py` -- a dependency-free module also
#: imported by `tb_cascade.cleaning_list` (Phase 8), which cannot afford
#: this module's `IPython`/`plotly`/`viz`/`cascade` imports. Imported
#: above; re-exported here under the same names so every existing
#: reference in this file (and `ru.QC_RULE_LABELS_RU`/`ru.SITE_LABELS_RU`
#: from the `.qmd` templates) keeps working unchanged.

#: `TargetGroup` values, already recoded from numeric codes to English
#: strings by `cascade._apply_label_maps` before this report ever sees them.
TARGETGROUP_RU: dict[str, str] = {
    "Contact": "Контактное лицо",
    "Homeless": "Бездомный",
    "PLHIV": "ЛЖВ (ВИЧ+)",
    "Other": "Другое",
}

#: `Sex` values, same recoding note as `TARGETGROUP_RU`.
SEX_RU: dict[str, str] = {
    "Male": "Мужской",
    "Female": "Женский",
}

#: `TreatGroup` values, same recoding note as `TARGETGROUP_RU`.
TREATGROUP_RU: dict[str, str] = {
    "TB treatment": "Лечение ТБ",
    "LTI treatment": "Лечение ЛТИ",
    "Observation": "Наблюдение",
}

#: `RelationWithSource` values, same recoding note as `TARGETGROUP_RU`.
RELATIONWITHSOURCE_RU: dict[str, str] = {
    "Colleague": "Коллега",
    "Neighbor": "Сосед(ка)",
    "Other": "Другое",
    "Relative (same household)": "Родственник (тот же дом)",
    "Healthcare worker": "Медицинский работник",
}

#: One dict per `cascade._ALLOWED_GROUP_DIMS` column that has a fixed,
#: known value set -- merged into every table's `value_maps` by `vmaps()`
#: below, since any of these may show up as a `group_by` column on any
#: step's table. Deliberately excludes columns with no translation needed
#: (`age_band`'s "0-14"/"15-24"/... bands, `completed_or_finished`'s
#: True/False, `target_days`'s 30/60) -- an *empty* dict here would map
#: every value in that column to `NaN` via `Series.map`, not leave it
#: alone, so such columns must simply not be keys in this dict at all.
GROUP_DIM_VALUE_MAPS: dict[str, dict] = {
    "Source": SITE_LABELS_RU,
    "TargetGroup": TARGETGROUP_RU,
    "Sex": SEX_RU,
    "TreatGroup": TREATGROUP_RU,
    "RelationWithSource": RELATIONWITHSOURCE_RU,
}


def vmaps(*extra: dict[str, dict]) -> dict[str, dict]:
    """`GROUP_DIM_VALUE_MAPS` plus any step-specific value maps, merged
    into one dict for `ru_table`'s `value_maps=` argument. Every call site
    below uses this rather than repeating the same five group-dimension
    maps at every step -- `translate_table` only applies a map to a column
    that is actually present, so passing maps for columns a given table
    doesn't have is always safe.
    """
    merged = dict(GROUP_DIM_VALUE_MAPS)
    for e in extra:
        merged.update(e)
    return merged


# --- Generic table translation/rendering ----------------------------------


def _facet_label_map_for(group_col: str) -> dict:
    """The Russian value-label dict for a `cascade._ALLOWED_GROUP_DIMS`
    column, or `{}` for one with no fixed translation (e.g. `age_band`).
    Used by the chart functions below to translate facet/legend/axis
    labels for whichever `group_col` the caller passed.
    """
    return GROUP_DIM_VALUE_MAPS.get(group_col, {})


def translate_table(
    df: pd.DataFrame,
    *,
    value_maps: dict[str, dict] | None = None,
    column_labels: dict[str, str] | None = None,
    drop_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Return a Russian-translated copy of `df`, ready for
    `to_markdown()`. Never mutates `df`; the caller's original table
    (still in English, still exactly what `cascade.py`/`trends.py`
    returned) is untouched.

    In order: (1) drop `drop_cols` if given (none of this report's call
    sites use this -- every table keeps its `suppressed` column, matching
    the English report's own `show_table`, which also shows it as-is --
    but it is offered for completeness); (2) apply each `value_maps[col]`
    translation to the matching column, for columns present in `df`,
    leaving any value not in that column's dict (including `pd.NA`)
    unchanged; (3) map every boolean-dtype column's True/False to
    "Да"/"Нет"; (4) blank-fill every remaining `pd.NA` with "—" for a
    clean markdown render; (5) rename columns via `COLUMN_LABELS_RU`
    merged with `column_labels`, for columns present in `df`.
    """
    out = df.copy()
    if drop_cols:
        out = out.drop(columns=[c for c in drop_cols if c in out.columns])

    for col, mapping in (value_maps or {}).items():
        if col in out.columns:
            # `Source` (and potentially other group_by columns) round-trips
            # through DuckDB as an ENUM, which `connect()`/`fetchdf()` turns
            # back into a pandas Categorical. `Series.map` on a Categorical
            # maps its *categories*, returning a new Categorical typed with
            # the translated (Russian) categories; the subsequent
            # `.fillna(out[col])` then fails with "Cannot set a Categorical
            # with another, without identical categories" because pandas
            # validates the fill value's dtype against the mapped column's
            # *new* categories even when there is nothing left to fill.
            # Casting to plain `object` first sidesteps this entirely --
            # `.map`/`.fillna` then operate elementwise on ordinary Python
            # values, same as for every non-categorical column, and the
            # rendered values are identical either way (this function only
            # produces a markdown table; nothing downstream needs the
            # column to stay Categorical).
            series = out[col]
            if isinstance(series.dtype, pd.CategoricalDtype):
                series = series.astype(object)
            out[col] = series.map(mapping).fillna(series)

    for col in out.columns:
        if str(out[col].dtype) in ("bool", "boolean"):
            out[col] = out[col].map({True: "Да", False: "Нет"})

    # A blanket `DataFrame.fillna("—")` silently upcasts a plain numpy
    # column (e.g. ordinary float64) to object if it needs to, but a
    # pandas *nullable*/extension dtype -- "Int64", "Float64", "string",
    # any leftover "category" -- validates the fill value against its own
    # dtype instead of upcasting, and raises TypeError ("Invalid value
    # '—' for dtype 'Int64'") for any such column that actually has a
    # `pd.NA` to fill (e.g. `treat_start_year`). Casting every remaining
    # extension-dtype column to `object` first makes the fill behave the
    # same way for all columns, matching this function's "blank-fill
    # every remaining pd.NA with '—'" contract regardless of dtype.
    for col in out.columns:
        if pd.api.types.is_extension_array_dtype(out[col].dtype):
            out[col] = out[col].astype(object)

    out = out.fillna("—")

    labels = {**COLUMN_LABELS_RU, **(column_labels or {})}
    rename_map = {c: labels[c] for c in out.columns if c in labels}
    return out.rename(columns=rename_map)


def ru_table(
    df: pd.DataFrame,
    *,
    value_maps: dict[str, dict] | None = None,
    column_labels: dict[str, str] | None = None,
    drop_cols: list[str] | None = None,
    note: str | None = None,
) -> None:
    """Render `df` as a Russian markdown table -- the Russian-report
    equivalent of `descriptive_report.qmd`'s own `show_table` helper, used
    for every step that has no dedicated chart function (Steps 3, 4, 5, 7,
    8) plus the QC summary. `note`, if given, is shown in italics above
    the table, same convention as `show_table`.
    """
    translated = translate_table(
        df, value_maps=value_maps, column_labels=column_labels, drop_cols=drop_cols
    )
    if note:
        display(Markdown(f"_{note}_"))
    display(Markdown(translated.to_markdown(index=False)))


def ru_summary_row(df: pd.DataFrame, title: str) -> None:
    """Render a single-row `n`/`median`/`q1`/`q3`/`suppressed` summary
    (Step 1's `age_summary`/`contacts_per_index_case`) as a titled Russian
    markdown table -- the markdown-table counterpart of `viz._summary_row_
    to_table`'s `go.Table`, used because Step 1 is rendered as markdown
    tables in this report (see module docstring).
    """
    display(Markdown(f"**{title}**"))
    ru_table(df)


# --- Step 1: baseline table (Table 1) --------------------------------------

#: Russian translation of `viz._TABLE1_SUPPRESSION_CAVEAT` -- Step 1's
#: categorical table is not yet suppression-safe in either language
#: version (tracked as a follow-up, see `cascade.step1_baseline_table`'s
#: docstring); this report must keep surfacing that caveat too, not hide
#: it by translating only the safe parts of the report.
TABLE1_SUPPRESSION_CAVEAT_RU: str = (
    "Внимание: подавление малых ячеек пока не применяется к этой таблице "
    "(отслеживается как доработка) — проверьте любую малочисленную страту "
    "перед тем, как делиться этим разделом за пределами команды."
)

#: `{"Missing": ..., "Overall": ...}` plus every site's Russian name, for
#: translating `table1.tableone`'s stat-column headers (`ru_table1`).
_TABLE1_STAT_HEADER_RU: dict[str, str] = {
    "Missing": "Пропущено",
    "Overall": "Всего",
    **SITE_LABELS_RU,
}


def _base_column_name(variable: str) -> str | None:
    """`table1.tableone`'s row index gives each variable as either the
    bare column name or `"{column}, n (%)"` depending on the installed
    `tableone` version's formatting -- this recovers the bare column name
    either way, so `_facet_label_map_for`/`COLUMN_LABELS_RU` lookups work
    regardless of which format is in play. Returns `None` (rather than
    echoing `variable` back) if it doesn't match any known column, so a
    no-suffix exact match (`base == variable`) is never confused with a
    failed lookup by its caller.
    """
    for col in COLUMN_LABELS_RU:
        if variable == col or variable.startswith(col + ","):
            return col
    return None


def _translate_variable_label(variable: str) -> str:
    """Russian translation of a `table1.tableone` row's variable label,
    preserving any `", n (%)"`-style suffix `tableone` appended (that
    notation is standard in Russian epidemiological tables too, so it is
    left as-is rather than translated).
    """
    base = _base_column_name(variable)
    if base is None:
        return variable
    return COLUMN_LABELS_RU[base] + variable[len(base):]


def ru_table1(table1: object, strata: str = "Source") -> None:
    """Render Step 1's `tableone.TableOne` as a Russian markdown table.

    Mirrors `viz._table1_to_table`'s flattening of `table1.tableone`'s
    two-level row/column `MultiIndex` exactly (same row/column shape,
    same site-column reordering via `viz._SITE_COLORS` when
    `strata == "Source"`), but renders a markdown table instead of a
    `go.Table` -- this report's Step 1/10 convention (see module
    docstring) -- and translates the variable labels, level values, and
    stat-column headers into Russian. Carries forward the same
    suppression caveat `viz.baseline_table` attaches to this table,
    translated (`TABLE1_SUPPRESSION_CAVEAT_RU`).

    `strata` must match whatever `strata` the caller passed to
    `cascade.step1_baseline_table`, same contract as `viz.baseline_table`.
    """
    raw = table1.tableone

    variable_col: list[str] = []
    level_col: list[str] = []
    prev_variable = None
    for variable, level in raw.index:
        variable_col.append(_translate_variable_label(variable) if variable != prev_variable else "")
        level_map = _facet_label_map_for(_base_column_name(variable))
        level_col.append(level_map.get(level, level))
        prev_variable = variable

    stat_cols = list(raw.columns.get_level_values(1))
    fixed = [c for c in stat_cols if c in ("Missing", "Overall")]
    strata_cols = [c for c in stat_cols if c not in ("Missing", "Overall")]
    if strata == "Source" and set(strata_cols) <= set(viz._SITE_COLORS):
        strata_cols = [s for s in viz._SITE_COLORS if s in strata_cols]
    ordered_stat_cols = fixed + strata_cols

    header = ["Переменная", "Уровень", *[_TABLE1_STAT_HEADER_RU.get(c, c) for c in ordered_stat_cols]]
    cells = {"Переменная": variable_col, "Уровень": level_col}
    for c, h in zip(ordered_stat_cols, header[2:]):
        cells[h] = raw.xs(c, axis=1, level=1).iloc[:, 0].fillna("—").astype(str).tolist()

    table_df = pd.DataFrame(cells)
    display(Markdown(f"_{TABLE1_SUPPRESSION_CAVEAT_RU}_"))
    display(Markdown(table_df.to_markdown(index=False)))


# --- Step 10: site comparison tables ----------------------------------------

#: Russian translation of `viz._STEP10_TITLES`, same keys/shape -- shown
#: as `ru_table`'s `note=` (italic line above each table) rather than a
#: `go.Table` title, since Step 10 is rendered as markdown tables here.
STEP10_TITLES_RU: dict[str, str | dict[str, str]] = {
    "screening_cascade": "Каскад скрининга по площадкам",
    "diagnostic_outcomes": "Диагностические исходы по площадкам",
    "lti_cascade": {
        "cascade": "Каскад профилактического лечения ЛТИ по площадкам",
        "initiation_delay": "Задержка начала лечения по площадкам",
        "initiated_within_target": "Начато в целевой срок по площадкам",
    },
    "regimen": "Режим лечения по площадкам",
    "adherence_completion": {
        "adherence_summary": "Приверженность лечению по площадкам",
        "dose_threshold": "Достижение порогов дозы по площадкам",
        "outcome_distribution": "Распределение исходов лечения по площадкам",
    },
    "incentive_uptake": {
        "uptake": "Получение стимулирующих выплат по площадкам",
        "screening_payment_delay": "Задержка выплаты за скрининг по площадкам",
    },
    "followup_outcomes": {
        "rescreened_1yr": "Повторный скрининг через 1 год по площадкам",
        "no_tb_after_1yr": "Нет ТБ через 1 год по площадкам",
        "rescreened_24mo": "Повторный скрининг через 24 мес. по площадкам",
        "no_tb_after_24mo": "Нет ТБ через 24 мес. по площадкам",
        "final_outcome_distribution": "Распределение итоговых исходов по площадкам",
        "final_outcome_by_completion": "Итоговый исход по завершённости лечения, по площадкам",
        "incidence_rate": "Частота заболеваемости ТБ по площадкам",
    },
}

#: Per-leaf-table value maps for `render_step10_ru`, keyed `(top_key,
#: sub_key)` (`sub_key` is `None` for a plain-DataFrame top-level key).
#: Every leaf has `group_by=["Source"]` baked in by `cascade.
#: step10_site_comparison`, so `vmaps()`'s own `Source` translation
#: already covers that column -- only each leaf's *other* category-coded
#: column needs to be listed here.
_STEP10_VALUE_MAPS: dict[tuple[str, str | None], dict[str, dict]] = {
    ("screening_cascade", None): {"stage": STAGE_LABELS_RU},
    ("diagnostic_outcomes", None): {"category": DIAGNOSIS_BRANCH_RU},
    ("lti_cascade", "cascade"): {"stage": STAGE_LABELS_RU},
    ("regimen", None): {"regimen": REGIMEN_RU},
    ("adherence_completion", "dose_threshold"): {"threshold": THRESHOLD_RU},
    ("adherence_completion", "outcome_distribution"): {"category": OUTCOME_BRANCH_RU},
    ("incentive_uptake", "uptake"): {"incentive": INCENTIVE_RU},
    ("followup_outcomes", "final_outcome_distribution"): {"category": FINAL_OUTCOME_RU},
    ("followup_outcomes", "final_outcome_by_completion"): {"category": FINAL_OUTCOME_RU},
}


def render_step10_ru(step10_dict: dict[str, object]) -> None:
    """Step 10 side-by-side site comparison, as Russian markdown tables.

    Takes `cascade.step10_site_comparison(df, as_of)`'s return dict
    directly -- the same input `viz.site_comparison_table` takes -- and
    renders every leaf table (walking `STEP10_TITLES_RU` the same way
    `viz.site_comparison_table` walks `viz._STEP10_TITLES`) as its own
    `ru_table` call, with whatever value map `_STEP10_VALUE_MAPS` lists
    for that leaf (plus the `Source` translation every leaf gets via
    `vmaps()` automatically).
    """
    for key, titles in STEP10_TITLES_RU.items():
        value = step10_dict[key]
        if isinstance(titles, dict):
            for sub_key, sub_title in titles.items():
                extra = _STEP10_VALUE_MAPS.get((key, sub_key), {})
                ru_table(value[sub_key], value_maps=vmaps(extra), note=sub_title)
        else:
            extra = _STEP10_VALUE_MAPS.get((key, None), {})
            ru_table(value, value_maps=vmaps(extra), note=titles)


# --- Suppression captions for charts ----------------------------------------


def _suppression_caption_ru(df: pd.DataFrame, *, suppressed_col: str = "suppressed") -> str:
    """Russian translation of `viz._suppression_caption`'s text, phrased
    to avoid Russian grammatical-number agreement entirely ("Подавлено
    ячеек: K из N" needs no verb/noun agreement regardless of K or N),
    rather than attempting a literal translation of the English singular/
    plural branching.
    """
    if suppressed_col not in df.columns:
        raise KeyError(
            f"_suppression_caption_ru: '{suppressed_col}' column not found -- was "
            "this table run through cascade.suppress_small_cells?"
        )
    n_suppressed = int(df[suppressed_col].astype(bool).sum())
    n_total = len(df)
    if n_suppressed == 0:
        return f"Подавленных ячеек нет (n = {n_total})."
    return (
        f"Подавлено ячеек: {n_suppressed} из {n_total} (n < {SMALL_CELL_THRESHOLD}) "
        "— см. Описательный план исследования, §11."
    )


def _add_suppression_caption_ru(
    fig: go.Figure, df: pd.DataFrame, *, suppressed_col: str = "suppressed"
) -> go.Figure:
    """Russian-caption counterpart to `viz._add_suppression_caption` --
    same annotation position/style (`viz._CAPTION_ANNOTATION_STYLE`),
    Russian caption text.
    """
    caption = _suppression_caption_ru(df, suppressed_col=suppressed_col)
    fig.add_annotation(text=caption, **viz._CAPTION_ANNOTATION_STYLE)
    return fig


# --- Step 2: screening cascade funnel (Russian) -----------------------------


def _step2_funnel_trace_ru(plotted: pd.DataFrame) -> go.Funnel:
    """Russian-label counterpart to `viz._step2_funnel_trace` -- same
    geometry/hover convention, `STAGE_LABELS_RU` instead of `viz._STEP2_
    STAGE_LABELS` for the y-axis text.
    """
    customdata = plotted[["n", "count", "ci_low", "ci_high"]].astype(float)
    return go.Funnel(
        y=[STAGE_LABELS_RU[s] for s in plotted["stage"]],
        x=plotted["pct"],
        customdata=customdata,
        texttemplate="%{x:.1%}",
        hovertemplate=(
            "%{y}<br>"
            "%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{x:.1%})<br>"
            "95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}"
            "<extra></extra>"
        ),
    )


def funnel_chart_ru(cascade_df: pd.DataFrame) -> go.Figure:
    """Russian-label counterpart to `viz.funnel_chart` (Step 2 overall
    screening cascade funnel). Takes `cascade.step2_screening_cascade(df)`'s
    output directly, unmodified -- same validation
    (`viz._validate_step2_stages`), same stage ordering
    (`cascade._STEP2_STAGES`), same suppressed-row handling
    (`viz._drop_suppressed`) as the English `funnel_chart`.
    """
    viz._validate_step2_stages(cascade_df, caller="funnel_chart_ru", group_col=None)
    ordered = cascade_df.set_index("stage").loc[list(_STEP2_STAGES)].reset_index()
    plotted = viz._drop_suppressed(ordered)

    fig = go.Figure(_step2_funnel_trace_ru(plotted))
    fig.update_layout(title="Каскад скрининга (% от когорты)", xaxis_tickformat=".0%")
    return _add_suppression_caption_ru(fig, ordered)


def funnel_chart_by_group_ru(cascade_df: pd.DataFrame, group_col: str = "TargetGroup") -> go.Figure:
    """Russian-label counterpart to `viz.funnel_chart_by_group` -- same
    per-`group_col` small-multiples layout and facet ordering (`cascade.
    _LABEL_MAPS[group_col]`'s canonical order, falling back to
    alphabetical), with facet titles and funnel labels translated via
    `_facet_label_map_for(group_col)`/`STAGE_LABELS_RU`.
    """
    viz._validate_step2_stages(cascade_df, caller="funnel_chart_by_group_ru", group_col=group_col)

    observed = set(cascade_df[group_col].dropna())
    if group_col in _LABEL_MAPS:
        canonical = [v for v in _LABEL_MAPS[group_col].values() if v in observed]
        canonical += sorted(observed - set(canonical))
    else:
        canonical = sorted(observed)

    facet_labels = _facet_label_map_for(group_col)
    titles = [facet_labels.get(g, str(g)) for g in canonical]

    n = len(canonical)
    n_cols = math.ceil(math.sqrt(n)) if n else 1
    n_rows = math.ceil(n / n_cols) if n else 1

    fig = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=titles)
    for idx, group_value in enumerate(canonical):
        row, col = divmod(idx, n_cols)
        facet = cascade_df.loc[cascade_df[group_col] == group_value]
        ordered = facet.set_index("stage").loc[list(_STEP2_STAGES)].reset_index()
        plotted = viz._drop_suppressed(ordered)
        fig.add_trace(_step2_funnel_trace_ru(plotted), row=row + 1, col=col + 1)

    fig.update_xaxes(tickformat=".0%")
    group_label = COLUMN_LABELS_RU.get(group_col, group_col)
    fig.update_layout(
        title=f"Каскад скрининга по группе «{group_label}» (% от когорты)",
        showlegend=False,
    )
    return _add_suppression_caption_ru(fig, cascade_df)


# --- Step 6: outcome composition stacked bar (Russian) ----------------------


def outcome_stacked_bar_ru(outcome_df: pd.DataFrame, group_by: list[str] | None = None) -> go.Figure:
    """Russian-label counterpart to `viz.outcome_stacked_bar` -- same
    validation (`viz._validate_outcome_distribution`), same fixed stack
    order/colors (`viz._OUTCOME_BRANCH_LABELS`'s key order,
    `viz._OUTCOME_BRANCH_COLORS`), with `OUTCOME_BRANCH_RU` for the legend/
    hover text and `_facet_label_map_for` for translating `group_by`
    dimension values on the x-axis.
    """
    viz._validate_outcome_distribution(outcome_df, group_by=group_by)
    plotted = viz._drop_suppressed(outcome_df)

    dims = list(group_by) if group_by else []

    fig = go.Figure()
    for code, label_en in viz._OUTCOME_BRANCH_LABELS.items():
        label = OUTCOME_BRANCH_RU.get(code, label_en)
        rows = plotted.loc[plotted["category"] == code]
        if rows.empty:
            continue
        if len(dims) == 0:
            x_vals = ["Всего"] * len(rows)
        elif len(dims) == 1:
            fmap = _facet_label_map_for(dims[0])
            x_vals = [fmap.get(v, v) for v in rows[dims[0]].tolist()]
        elif len(dims) == 2:
            fmaps = [_facet_label_map_for(d) for d in dims]
            x_vals = [[fm.get(v, v) for v in rows[d].tolist()] for fm, d in zip(fmaps, dims)]
        else:
            x_vals = rows[dims].astype(str).agg(" | ".join, axis=1).tolist()
        customdata = rows[["n", "count", "ci_low", "ci_high"]].astype(float)
        fig.add_trace(
            go.Bar(
                x=x_vals,
                y=rows["pct"],
                name=label,
                marker_color=viz._OUTCOME_BRANCH_COLORS[code],
                customdata=customdata,
                texttemplate="%{y:.1%}",
                hovertemplate=(
                    f"{label}<br>"
                    "%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})<br>"
                    "95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}"
                    "<extra></extra>"
                ),
            )
        )

    dim_labels = ", ".join(COLUMN_LABELS_RU.get(d, d) for d in dims)
    title = "Структура исходов лечения" + (f" по {dim_labels}" if dims else "")
    fig.update_layout(
        title=title,
        barmode="stack",
        yaxis_tickformat=".0%",
        legend_title="Исход",
    )
    return _add_suppression_caption_ru(fig, outcome_df)


# --- Step 9: quarterly trend lines (Russian) --------------------------------

#: Russian translation of `viz._STEP9_METRIC_LABELS` -- same keys, so
#: `trend_lines_ru` can still color/order by `viz._STEP9_METRIC_COLORS`.
STEP9_METRIC_LABELS_RU: dict[str, str] = {
    "enrollment": "Включение в когорту",
    "treatment_initiation": "Начало лечения",
    "outcome": "Исход",
}


def trend_lines_ru(trend_df: pd.DataFrame) -> go.Figure:
    """Russian-label counterpart to `viz.trend_lines` -- same validation
    (`viz._validate_trend_df`), same continuous-quarter reindexing/zero-
    fill logic (`viz._full_quarter_range`), same fixed per-metric colors
    (`viz._STEP9_METRIC_COLORS`), with `STEP9_METRIC_LABELS_RU` for the
    legend/hover text and a Russian quarter label (`"2020 – К2"`
    instead of `"2020-Q2"`).
    """
    viz._validate_trend_df(trend_df)
    full_range = viz._full_quarter_range(trend_df)

    fig = go.Figure()
    for metric, label_en in viz._STEP9_METRIC_LABELS.items():
        label = STEP9_METRIC_LABELS_RU.get(metric, label_en)
        sub = trend_df.loc[trend_df["metric"] == metric, ["year", "quarter", "n", "suppressed"]]
        merged = full_range.merge(sub, on=["year", "quarter"], how="left")
        no_row = merged["suppressed"].isna()
        merged.loc[no_row, "n"] = 0
        merged.loc[no_row, "suppressed"] = False
        plotted = viz._drop_suppressed(merged)

        if plotted.empty:
            continue
        x = [viz._quarter_start(y, q) for y, q in zip(plotted["year"], plotted["quarter"])]
        quarter_label = [f"{y} – К{q}" for y, q in zip(plotted["year"], plotted["quarter"])]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=plotted["n"],
                mode="lines+markers",
                name=label,
                line=dict(color=viz._STEP9_METRIC_COLORS[metric]),
                marker=dict(color=viz._STEP9_METRIC_COLORS[metric]),
                customdata=quarter_label,
                hovertemplate=f"{label}<br>" "%{customdata}: %{y:.0f}<extra></extra>",
            )
        )

    fig.update_layout(
        title="Квартальная динамика",
        xaxis_title="Квартал",
        yaxis_title="Количество",
    )
    return _add_suppression_caption_ru(fig, trend_df)
