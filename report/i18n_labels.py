"""Pure-data Russian label dictionaries with zero heavy dependencies.

`report/i18n_ru.py` (the descriptive report's presentation layer)
unconditionally imports `IPython`, `plotly`, `tb_cascade.viz`, and
`tb_cascade.cascade` at module load time, since its job is rendering
charts and markdown tables. `src/tb_cascade/cleaning_list.py` (Phase 8)
only needs two of `i18n_ru.py`'s label dictionaries (`QC_RULE_LABELS_RU`,
`SITE_LABELS_RU`) and must stay importable on a machine with no
Quarto/Jupyter kernel installed at all -- that is the entire point of
`cli.py run --skip-report`. Rather than duplicate those two dictionaries
(risking silent drift between the report and the cleaning list) or pull
`cleaning_list.py` into the report's heavy import graph, the dictionaries
live here, with no imports beyond the standard library, and `i18n_ru.py`
imports them from this module instead of defining them inline. Both
modules therefore share the exact same dict objects -- there is still
only one glossary, just relocated to a dependency-free home.

`FIELD_LABELS_RU` is new for Phase 8: Russian labels for the raw CSV
column names `cleaning_list.RULE_FIELDS` references that are not already
covered by `i18n_ru.COLUMN_LABELS_RU` (which only covers derived/
cascade-table columns, not raw fields like `DosesTaken`, `BirthDate`, or
the outcome/diagnosis flags). Field meanings are taken from
`Documentation/DataSet Description (English).md`.
"""

from __future__ import annotations

#: `qc.CHECKS` rule names (the `rule` column of `qc.run_qc(...).summary`
#: and `qc_result.flagged`). Identical to the dict formerly defined inline
#: in `report/i18n_ru.py`.
QC_RULE_LABELS_RU: dict[str, str] = {
    "duplicate_registration": "Дублирующаяся регистрация",
    "treatgroup_onehot": "Согласованность TreatGroup (one-hot)",
    "outcome_mutual_exclusivity": "Взаимоисключаемость исходов лечения",
    "date_order": "Порядок дат",
    "doses_taken_le_schema": "DosesTaken ≤ SchemaDoses",
    "dose_threshold_consistency": "Согласованность порогов доз",
    "diagnosis_mutual_exclusivity": "Взаимоисключаемость диагнозов",
    "age_range": "Диапазон возраста",
}

#: `Source` values -> Russian city names. Identical to the dict formerly
#: defined inline in `report/i18n_ru.py`; keys match `viz._SITE_COLORS`.
SITE_LABELS_RU: dict[str, str] = {
    "Vladimir": "Владимир",
    "Murom": "Муром",
    "Kovrov": "Ковров",
}

#: Raw `tb_cascade.io.load_raw` column names implicated by one or more
#: `qc.CHECKS` rules (see `cleaning_list.RULE_FIELDS`), translated for a
#: local data manager who knows the dataset by these original field
#: names, not by any report's derived/recoded vocabulary.
FIELD_LABELS_RU: dict[str, str] = {
    "Source": "Площадка",
    "Nomer": "Регистрационный номер",
    "TreatGroup": "Группа лечения",
    "TreatGroup_01": "Группа 1 (лечение ТБ)",
    "TreatGroup_02": "Группа 2 (лечение ЛТИ)",
    "TreatGroup_03": "Группа 3 (наблюдение)",
    "BirthDate": "Дата рождения",
    "DateScreening": "Дата скрининга",
    "DateCompleteExaminationTB": "Дата завершения обследования на ТБ",
    "ConfirmedDiagnosisTB": "Подтверждённый диагноз ТБ",
    "LTI": "Нет ТБ, есть ЛТИ (латентная ТБ-инфекция)",
    "NoTBNoLTI": "Нет ТБ, нет ЛТИ",
    "NoTBLTIunknown": "Нет ТБ, статус ЛТИ неизвестен",
    "DatePrevTreatmentStart": "Дата начала лечения",
    "DateTreatmentScheme": "Дата назначения схемы лечения",
    "TreatmentCompleted": "Лечение завершено (100% доз)",
    "TreatmentFinished": "Лечение окончено (85-99% доз)",
    "DateOutcome": "Дата завершения лечения",
    "TBdeveloped": "Развился ТБ",
    "TreatmentStopedMed": "Остановлено по медицинским показаниям",
    "TreatmetnNotFinished": "Не завершено",
    "TreatmentContinue": "Продолжает лечение ЛТИ",
    "OutcomeNotKnown": "Исход неизвестен",
    "DosesTaken": "Принято доз",
    "SchemaDoses": "Доз по схеме лечения",
    "Take50pc": "Принято ≥50% доз",
    "Take100pc": "Принято 100% доз",
}
