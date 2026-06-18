# Каскад превентивного лечения туберкулёза — описательный отчёт


- [Метаданные отчёта](#метаданные-отчёта)
- [Шаг 1 — Профиль популяции (Таблица
  1)](#шаг-1--профиль-популяции-таблица-1)
- [Шаг 2 — Каскад скрининга](#шаг-2--каскад-скрининга)
- [Шаг 3 — Диагностические исходы](#шаг-3--диагностические-исходы)
- [Шаг 4 — Каскад превентивного лечения
  ЛТИ](#шаг-4--каскад-превентивного-лечения-лти)
- [Шаг 5 — Описание режима лечения](#шаг-5--описание-режима-лечения)
- [Шаг 6 — Приверженность и завершение
  лечения](#шаг-6--приверженность-и-завершение-лечения)
- [Шаг 7 — Получение стимулирующих
  выплат](#шаг-7--получение-стимулирующих-выплат)
- [Шаг 8 — Катамнез и итоговые
  исходы](#шаг-8--катамнез-и-итоговые-исходы)
- [Шаг 9 — Временные тренды](#шаг-9--временные-тренды)
- [Шаг 10 — Сравнение площадок](#шаг-10--сравнение-площадок)
- [Ограничения](#ограничения)

<!--
Russian-language sibling of `descriptive_report.qmd` (Phase 6 follow-up:
"separate Russian report, presentation-layer dictionary"). Mirrors the
English report section-for-section and calls the exact same
`cascade.py`/`trends.py`/`viz.py` functions on the exact same `df` --
every number in this report is computed by the same Phase 4/5 code the
English report uses, completely unmodified. The only thing specific to
this file is `report/i18n_ru.py`, a presentation-layer module that
translates column headers, category labels, and chart text into Russian
just before display -- see that module's own docstring for why a
translation *dictionary* applied at render time, rather than translating
the DataFrames themselves, is the safe approach (`viz.py`'s chart
functions key fixed coloring/ordering off literal English strings).
&#10;Disclosed simplification: Steps 1 and 10 are rendered here as Russian
markdown tables rather than the interactive `go.Table` figures
`viz.baseline_table`/`viz.site_comparison_table` produce for the English
report (see `i18n_ru.py`'s docstring) -- the numbers are identical, only
the rendering technique differs for those two steps.
&#10;Parameters follow the same Quarto/Jupyter convention as the English
report, e.g.
    quarto render report/descriptive_report_ru.qmd -P as_of:2026-07-01
-->

## Метаданные отчёта

    Дата анализа (as_of): 2026-06-16
    Снимок данных: 2026-06-16 (VladKovMur_dataset.csv)
    Коммит пайплайна: b116378+dirty
    Записей (n): 7732

*Счётчики строк по правилам контроля качества (Описательный план
исследования §6): `n проверено` — знаменатель, к которому применялось
правило (без неприменимых записей), `n нарушений` — сколько из них
правило не прошло. Рассчитано по исходным данным до применения
производных переменных; полное приложение по каждой площадке — в
`reports/qc_report.md`.*

| Правило                              | n проверено | n нарушений | Доля нарушений |
|:-------------------------------------|------------:|------------:|---------------:|
| Дублирующаяся регистрация            |        7732 |          18 |     0.00232799 |
| Согласованность TreatGroup (one-hot) |        7732 |          30 |     0.00387998 |
| Взаимоисключаемость исходов лечения  |        1214 |           0 |              0 |
| Порядок дат                          |        7628 |        2030 |       0.266125 |
| DosesTaken ≤ SchemaDoses             |        1155 |         126 |       0.109091 |
| Согласованность порогов доз          |        7732 |         126 |      0.0162959 |
| Взаимоисключаемость диагнозов        |        7705 |           0 |              0 |
| Диапазон возраста                    |        7676 |           1 |    0.000130276 |

Во всех таблицах и графиках ниже малые ячейки (n \< 5) подавлены
согласно Описательному плану исследования §11. Никакие идентификаторы
записей (`Source_id`, `Nomer`, `IndexCase`) не показаны в этом отчёте —
`Source` (площадка) присутствует только как агрегированная группирующая
переменная.

## Шаг 1 — Профиль популяции (Таблица 1)

Частоты/доли по площадке, целевой группе, полу, возрастной группе и
связи с источником (для контактных лиц), в целом и по площадкам;
медиана/МКИ для возраста и числа контактов, обследованных на одного
индекс-пациента.

*Внимание: подавление малых ячеек пока не применяется к этой таблице
(отслеживается как доработка) — проверьте любую малочисленную страту
перед тем, как делиться этим разделом за пределами команды.*

| Переменная | Уровень | Пропущено | Всего | Владимир | Муром | Ковров |
|:---|:---|:---|:---|:---|:---|:---|
| n |  |  | 7732 | 6318 | 380 | 1034 |
| Целевая группа, n (%) | Контактное лицо |  | 6004 (77.7) | 4660 (73.8) | 368 (96.8) | 976 (94.4) |
|  | Бездомный |  | 1042 (13.5) | 1041 (16.5) | 0 (0.0) | 1 (0.1) |
|  | ЛЖВ (ВИЧ+) |  | 686 (8.9) | 617 (9.8) | 12 (3.2) | 57 (5.5) |
| Пол, n (%) | Женский |  | 3940 (51.0) | 3117 (49.3) | 238 (62.6) | 585 (56.6) |
|  | Мужской |  | 3792 (49.0) | 3201 (50.7) | 142 (37.4) | 449 (43.4) |
| Возрастная группа, n (%) | 0-14 |  | 1 (0.0) | 0 (0.0) | 0 (0.0) | 1 (0.1) |
|  | 15-24 |  | 451 (5.8) | 403 (6.4) | 12 (3.2) | 36 (3.5) |
|  | 25-34 |  | 1373 (17.8) | 1242 (19.7) | 50 (13.2) | 81 (7.8) |
|  | 35-44 |  | 1981 (25.6) | 1662 (26.3) | 106 (27.9) | 213 (20.6) |
|  | 45-54 |  | 1824 (23.6) | 1483 (23.5) | 83 (21.8) | 258 (25.0) |
|  | 55-64 |  | 1365 (17.7) | 1049 (16.6) | 89 (23.4) | 227 (22.0) |
|  | 65+ |  | 680 (8.8) | 450 (7.1) | 36 (9.5) | 194 (18.8) |
|  | None |  | 57 (0.7) | 29 (0.5) | 4 (1.1) | 24 (2.3) |
| Связь с источником, n (%) | Коллега |  | 3247 (42.0) | 2978 (47.1) | 193 (50.8) | 76 (7.4) |
|  | Медицинский работник |  | 626 (8.1) | 597 (9.4) | 28 (7.4) | 1 (0.1) |
|  | Сосед(ка) |  | 359 (4.6) | 319 (5.0) | 12 (3.2) | 28 (2.7) |
|  | None |  | 2466 (31.9) | 1690 (26.7) | 9 (2.4) | 767 (74.2) |
|  | Другое |  | 541 (7.0) | 396 (6.3) | 84 (22.1) | 61 (5.9) |
|  | Родственник (тот же дом) |  | 493 (6.4) | 338 (5.3) | 54 (14.2) | 101 (9.8) |

**Возраст (лет), медиана/МКИ**

|    n | Медиана |      Q1 |      Q3 | Подавлено (n\<5) |
|-----:|--------:|--------:|--------:|:-----------------|
| 7676 | 44.1205 | 34.4962 | 54.7953 | Нет              |

**Контактов, обследованных на одного индекс-пациента, медиана/МКИ**

|   n | Медиана |  Q1 |   Q3 | Подавлено (n\<5) |
|----:|--------:|----:|-----:|:-----------------|
| 636 |       2 |   1 | 4.25 | Нет              |

## Шаг 2 — Каскад скрининга

Доля прошедших скрининг → с подозрением на ТБ → с положительным
Диаскинтестом → полностью обследованных, по всей когорте и по целевой
группе/площадке.

        <script>
        window.PlotlyConfig = {MathJaxConfig: 'local'};
        if (window.MathJax && window.MathJax.Hub && window.MathJax.Hub.Config) {window.MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}
        </script>
        <script type="module">import "https://cdn.plot.ly/plotly-3.6.0.min"</script>
        

<div style="height:525px; width:100%;">            <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-AMS-MML_SVG"></script><script>if (window.MathJax && window.MathJax.Hub && window.MathJax.Hub.Config) {window.MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}</script>                <script>window.PlotlyConfig = {MathJaxConfig: 'local'};</script>
        <script charset="utf-8" src="https://cdn.plot.ly/plotly-3.6.0.min.js" integrity="sha256-QaOVwtVY0T02VaHrr6pnoHLCwayMJp4O5n4YyaE3rJk=" crossorigin="anonymous"></script>                <div id="a63f5979-e694-4d17-807a-543e355112d1" class="plotly-graph-div" style="height:100%; width:100%;"></div>            <script>                window.PLOTLYENV=window.PLOTLYENV || {};                                if (document.getElementById("a63f5979-e694-4d17-807a-543e355112d1")) {                    Plotly.newPlot(                        "a63f5979-e694-4d17-807a-543e355112d1",                        [{"customdata":{"dtype":"f8","bdata":"AAAAAAA0vkAAAAAAAMS9QAfDdBh2ce8\u002fhVnIGkOd7z8AAAAAADS+QAAAAAAAKJVALAQ2kuxZxT8YUzrDE4XHPwAAAAAANL5AAAAAAACQiUBLAoHfyGC5P3tn5JKE47w\u002fAAAAAAA0vkAAAAAAABm+QCqAteBq1u8\u002f+MzEj1Ts7z8=","shape":"4, 4"},"hovertemplate":"%{y}\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{x:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","texttemplate":"%{x:.1%}","x":{"dtype":"f8","bdata":"UcdbN1aJ7z+Y2SnUNmrGPy+CDYJSFbs\u002fDSDGyGTj7z8="},"y":["Скрининг пройден","Подозрение на ТБ","Диаскинтест положительный","Полное обследование завершено"],"type":"funnel"}],                        {"template":{"data":{"histogram2dcontour":[{"type":"histogram2dcontour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"choropleth":[{"type":"choropleth","colorbar":{"outlinewidth":0,"ticks":""}}],"histogram2d":[{"type":"histogram2d","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmap":[{"type":"heatmap","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"contourcarpet":[{"type":"contourcarpet","colorbar":{"outlinewidth":0,"ticks":""}}],"contour":[{"type":"contour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"surface":[{"type":"surface","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"mesh3d":[{"type":"mesh3d","colorbar":{"outlinewidth":0,"ticks":""}}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"parcoords":[{"type":"parcoords","line":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolargl":[{"type":"scatterpolargl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"scattergeo":[{"type":"scattergeo","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolar":[{"type":"scatterpolar","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"scattergl":[{"type":"scattergl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatter3d":[{"type":"scatter3d","line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermap":[{"type":"scattermap","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermapbox":[{"type":"scattermapbox","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterternary":[{"type":"scatterternary","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattercarpet":[{"type":"scattercarpet","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"type":"carpet"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}],"barpolar":[{"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"pie":[{"automargin":true,"type":"pie"}]},"layout":{"autotypenumbers":"strict","colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"hovermode":"closest","hoverlabel":{"align":"left"},"paper_bgcolor":"white","plot_bgcolor":"#E5ECF6","polar":{"bgcolor":"#E5ECF6","angularaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"radialaxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"ternary":{"bgcolor":"#E5ECF6","aaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"baxis":{"gridcolor":"white","linecolor":"white","ticks":""},"caxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]]},"xaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"yaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"scene":{"xaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"yaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"zaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"geo":{"bgcolor":"white","landcolor":"#E5ECF6","subunitcolor":"white","showland":true,"showlakes":true,"lakecolor":"white"},"title":{"x":0.05},"mapbox":{"style":"light"},"margin":{"b":0,"l":0,"r":0,"t":30}}},"xaxis":{"tickformat":".0%"},"title":{"text":"Каскад скрининга (% от когорты)"},"annotations":[{"align":"left","font":{"color":"#666666","size":10},"showarrow":false,"text":"Подавленных ячеек нет (n = 4).","x":0,"xanchor":"left","xref":"paper","y":-0.18,"yanchor":"top","yref":"paper"}]},                        {"responsive": true}                    ).then(function(){
                            &#10;var gd = document.getElementById('a63f5979-e694-4d17-807a-543e355112d1');
var x = new MutationObserver(function (mutations, observer) {{
        var display = window.getComputedStyle(gd).display;
        if (!display || display === 'none') {{
            console.log([gd, 'removed!']);
            Plotly.purge(gd);
            observer.disconnect();
        }}
}});
&#10;// Listen for the removal of the full notebook cells
var notebookContainer = gd.closest('#notebook-container');
if (notebookContainer) {{
    x.observe(notebookContainer, {childList: true});
}}
&#10;// Listen for the clearing of the current output cell
var outputEl = gd.closest('.output');
if (outputEl) {{
    x.observe(outputEl, {childList: true});
}}
&#10;                        })                };            </script>        </div>

<div style="height:525px; width:100%;">            <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-AMS-MML_SVG"></script><script>if (window.MathJax && window.MathJax.Hub && window.MathJax.Hub.Config) {window.MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}</script>                <script>window.PlotlyConfig = {MathJaxConfig: 'local'};</script>
        <script charset="utf-8" src="https://cdn.plot.ly/plotly-3.6.0.min.js" integrity="sha256-QaOVwtVY0T02VaHrr6pnoHLCwayMJp4O5n4YyaE3rJk=" crossorigin="anonymous"></script>                <div id="3d86fad7-3233-4143-84e2-a2911305d9de" class="plotly-graph-div" style="height:100%; width:100%;"></div>            <script>                window.PLOTLYENV=window.PLOTLYENV || {};                                if (document.getElementById("3d86fad7-3233-4143-84e2-a2911305d9de")) {                    Plotly.newPlot(                        "3d86fad7-3233-4143-84e2-a2911305d9de",                        [{"customdata":{"dtype":"f8","bdata":"AAAAAAB0t0AAAAAAABK3QBOl+wNiXe8\u002fp7n+fx+S7z8AAAAAAHS3QAAAAAAAYIhAoHq94SMkvz8KGZ8tcb\u002fBPwAAAAAAdLdAAAAAAAC4g0D0xlmbq\u002fu4P7B+bNKl9Lw\u002fAAAAAAB0t0AAAAAAAFq3QI14lsEUzO8\u002fJT3atsbn7z8=","shape":"4, 4"},"hovertemplate":"%{y}\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{x:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","texttemplate":"%{x:.1%}","x":{"dtype":"f8","bdata":"EGl4Vkl67z\u002fJE\u002fyCAKHAPwVKpmWc57o\u002fTfdOZYbc7z8="},"y":["Скрининг пройден","Подозрение на ТБ","Диаскинтест положительный","Полное обследование завершено"],"type":"funnel","xaxis":"x","yaxis":"y"},{"customdata":{"dtype":"f8","bdata":"AAAAAABIkEAAAAAAACSQQGUZmUUyeu8\u002fJZ33l7ja7z8AAAAAAEiQQAAAAAAA0HNAvrPf+yu70T\u002fO+pDbKE3VPwAAAAAASJBAAAAAAABgZUBUcM43QUnCP4rcWZKMCsg\u002fAAAAAABIkEAAAAAAAESQQF\u002fSxdqh0+8\u002fBSdBrpz+7z8=","shape":"4, 4"},"hovertemplate":"%{y}\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{x:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","texttemplate":"%{x:.1%}","x":{"dtype":"f8","bdata":"hakvZz657z\u002fqBMZFYnjTP3is2V15AcU\u002fK2jMYCP47z8="},"y":["Скрининг пройден","Подозрение на ТБ","Диаскинтест положительный","Полное обследование завершено"],"type":"funnel","xaxis":"x2","yaxis":"y2"},{"customdata":{"dtype":"f8","bdata":"AAAAAABwhUAAAAAAAEiFQCNDqXUqde8\u002ff0D20nbm7z8AAAAAAHCFQAAAAAAAEHBAHM1aGJK11T8A+bT3XFXaPwAAAAAAcIVAAAAAAAAAMECzNQ41PYGNP9tnin2tOaM\u002fAAAAAABwhUAAAAAAAHCFQG72qsZh0u8\u002fAAAAAAAA8D8=","shape":"4, 4"},"hovertemplate":"%{y}\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{x:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","texttemplate":"%{x:.1%}","x":{"dtype":"f8","bdata":"Op60okrE7z9sqat2B\u002frXPx1PWlEl4pc\u002fAAAAAAAA8D8="},"y":["Скрининг пройден","Подозрение на ТБ","Диаскинтест положительный","Полное обследование завершено"],"type":"funnel","xaxis":"x3","yaxis":"y3"}],                        {"template":{"data":{"histogram2dcontour":[{"type":"histogram2dcontour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"choropleth":[{"type":"choropleth","colorbar":{"outlinewidth":0,"ticks":""}}],"histogram2d":[{"type":"histogram2d","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmap":[{"type":"heatmap","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"contourcarpet":[{"type":"contourcarpet","colorbar":{"outlinewidth":0,"ticks":""}}],"contour":[{"type":"contour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"surface":[{"type":"surface","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"mesh3d":[{"type":"mesh3d","colorbar":{"outlinewidth":0,"ticks":""}}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"parcoords":[{"type":"parcoords","line":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolargl":[{"type":"scatterpolargl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"scattergeo":[{"type":"scattergeo","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolar":[{"type":"scatterpolar","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"scattergl":[{"type":"scattergl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatter3d":[{"type":"scatter3d","line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermap":[{"type":"scattermap","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermapbox":[{"type":"scattermapbox","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterternary":[{"type":"scatterternary","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattercarpet":[{"type":"scattercarpet","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"type":"carpet"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}],"barpolar":[{"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"pie":[{"automargin":true,"type":"pie"}]},"layout":{"autotypenumbers":"strict","colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"hovermode":"closest","hoverlabel":{"align":"left"},"paper_bgcolor":"white","plot_bgcolor":"#E5ECF6","polar":{"bgcolor":"#E5ECF6","angularaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"radialaxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"ternary":{"bgcolor":"#E5ECF6","aaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"baxis":{"gridcolor":"white","linecolor":"white","ticks":""},"caxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]]},"xaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"yaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"scene":{"xaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"yaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"zaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"geo":{"bgcolor":"white","landcolor":"#E5ECF6","subunitcolor":"white","showland":true,"showlakes":true,"lakecolor":"white"},"title":{"x":0.05},"mapbox":{"style":"light"},"margin":{"b":0,"l":0,"r":0,"t":30}}},"xaxis":{"anchor":"y","domain":[0.0,0.45],"tickformat":".0%"},"yaxis":{"anchor":"x","domain":[0.625,1.0]},"xaxis2":{"anchor":"y2","domain":[0.55,1.0],"tickformat":".0%"},"yaxis2":{"anchor":"x2","domain":[0.625,1.0]},"xaxis3":{"anchor":"y3","domain":[0.0,0.45],"tickformat":".0%"},"yaxis3":{"anchor":"x3","domain":[0.0,0.375]},"xaxis4":{"anchor":"y4","domain":[0.55,1.0],"tickformat":".0%"},"yaxis4":{"anchor":"x4","domain":[0.0,0.375]},"annotations":[{"font":{"size":16},"showarrow":false,"text":"Контактное лицо","x":0.225,"xanchor":"center","xref":"paper","y":1.0,"yanchor":"bottom","yref":"paper"},{"font":{"size":16},"showarrow":false,"text":"Бездомный","x":0.775,"xanchor":"center","xref":"paper","y":1.0,"yanchor":"bottom","yref":"paper"},{"font":{"size":16},"showarrow":false,"text":"ЛЖВ (ВИЧ+)","x":0.225,"xanchor":"center","xref":"paper","y":0.375,"yanchor":"bottom","yref":"paper"},{"align":"left","font":{"color":"#666666","size":10},"showarrow":false,"text":"Подавленных ячеек нет (n = 12).","x":0,"xanchor":"left","xref":"paper","y":-0.18,"yanchor":"top","yref":"paper"}],"title":{"text":"Каскад скрининга по группе «Целевая группа» (% от когорты)"},"showlegend":false},                        {"responsive": true}                    ).then(function(){
                            &#10;var gd = document.getElementById('3d86fad7-3233-4143-84e2-a2911305d9de');
var x = new MutationObserver(function (mutations, observer) {{
        var display = window.getComputedStyle(gd).display;
        if (!display || display === 'none') {{
            console.log([gd, 'removed!']);
            Plotly.purge(gd);
            observer.disconnect();
        }}
}});
&#10;// Listen for the removal of the full notebook cells
var notebookContainer = gd.closest('#notebook-container');
if (notebookContainer) {{
    x.observe(notebookContainer, {childList: true});
}}
&#10;// Listen for the clearing of the current output cell
var outputEl = gd.closest('.output');
if (outputEl) {{
    x.observe(outputEl, {childList: true});
}}
&#10;                        })                };            </script>        </div>

<div style="height:525px; width:100%;">            <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-AMS-MML_SVG"></script><script>if (window.MathJax && window.MathJax.Hub && window.MathJax.Hub.Config) {window.MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}</script>                <script>window.PlotlyConfig = {MathJaxConfig: 'local'};</script>
        <script charset="utf-8" src="https://cdn.plot.ly/plotly-3.6.0.min.js" integrity="sha256-QaOVwtVY0T02VaHrr6pnoHLCwayMJp4O5n4YyaE3rJk=" crossorigin="anonymous"></script>                <div id="316c19f8-160a-4fb0-a245-a4dbc46a188b" class="plotly-graph-div" style="height:100%; width:100%;"></div>            <script>                window.PLOTLYENV=window.PLOTLYENV || {};                                if (document.getElementById("316c19f8-160a-4fb0-a245-a4dbc46a188b")) {                    Plotly.newPlot(                        "316c19f8-160a-4fb0-a245-a4dbc46a188b",                        [{"customdata":{"dtype":"f8","bdata":"AAAAAAAokEAAAAAAAHiOQAnw3yHAqu0\u002fV83LgIST7j8AAAAAACiQQAAAAAAAIGRAeHcNeudDwT8MlBX99evGPwAAAAAAKJBAAAAAAABAYUAfJn4GqTS9P96dNK0q6cM\u002fAAAAAAAokEAAAAAAACiQQKQb6p2t4e8\u002fAAAAAAAA8D8=","shape":"4, 4"},"hovertemplate":"%{y}\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{x:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","texttemplate":"%{x:.1%}","x":{"dtype":"f8","bdata":"0KyHlpAs7j+th5aQLO7DP7lPE8VKFcE\u002fAAAAAAAA8D8="},"y":["Скрининг пройден","Подозрение на ТБ","Диаскинтест положительный","Полное обследование завершено"],"type":"funnel","xaxis":"x","yaxis":"y"},{"customdata":{"dtype":"f8","bdata":"AAAAAADAd0AAAAAAAJB3QDAmbHj8Q+8\u002frhm91\u002fnp7z8AAAAAAMB3QAAAAAAAwFVAWkXxONxCyD8ht94wm4XRPwAAAAAAwHdAAAAAAACAUkAtxToTRTvEP6tP\u002fEM4Z84\u002fAAAAAADAd0AAAAAAAMB3QC\u002f\u002f+dgDru8\u002f\u002f\u002f\u002f\u002f\u002f\u002f\u002f\u002f7z8=","shape":"4, 4"},"hovertemplate":"%{y}\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{x:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","texttemplate":"%{x:.1%}","x":{"dtype":"f8","bdata":"9XtuiVO\u002f7z\u002fi1O+5JU7NP9KOFQgj7cg\u002fAAAAAAAA8D8="},"y":["Скрининг пройден","Подозрение на ТБ","Диаскинтест положительный","Полное обследование завершено"],"type":"funnel","xaxis":"x2","yaxis":"y2"},{"customdata":{"dtype":"f8","bdata":"AAAAAACuuEAAAAAAAHy4QK4dYOmoqu8\u002fksozo8fO7z8AAAAAAK64QAAAAAAASJFA0YtYOKk7xT+JR4+wtaHHPwAAAAAArrhAAAAAAADwgkDk07WZEsK2PwI4yK8Rero\u002fAAAAAACuuEAAAAAAAJO4QHrgjjEfze8\u002fQg+I\u002fezn7z8=","shape":"4, 4"},"hovertemplate":"%{y}\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{x:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","texttemplate":"%{x:.1%}","x":{"dtype":"f8","bdata":"LIoBWyu\u002f7z9L2CUbN2jGPzXexqb6jbg\u002f0P3cz\u002f3c7z8="},"y":["Скрининг пройден","Подозрение на ТБ","Диаскинтест положительный","Полное обследование завершено"],"type":"funnel","xaxis":"x3","yaxis":"y3"}],                        {"template":{"data":{"histogram2dcontour":[{"type":"histogram2dcontour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"choropleth":[{"type":"choropleth","colorbar":{"outlinewidth":0,"ticks":""}}],"histogram2d":[{"type":"histogram2d","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmap":[{"type":"heatmap","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"contourcarpet":[{"type":"contourcarpet","colorbar":{"outlinewidth":0,"ticks":""}}],"contour":[{"type":"contour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"surface":[{"type":"surface","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"mesh3d":[{"type":"mesh3d","colorbar":{"outlinewidth":0,"ticks":""}}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"parcoords":[{"type":"parcoords","line":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolargl":[{"type":"scatterpolargl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"scattergeo":[{"type":"scattergeo","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolar":[{"type":"scatterpolar","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"scattergl":[{"type":"scattergl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatter3d":[{"type":"scatter3d","line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermap":[{"type":"scattermap","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermapbox":[{"type":"scattermapbox","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterternary":[{"type":"scatterternary","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattercarpet":[{"type":"scattercarpet","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"type":"carpet"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}],"barpolar":[{"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"pie":[{"automargin":true,"type":"pie"}]},"layout":{"autotypenumbers":"strict","colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"hovermode":"closest","hoverlabel":{"align":"left"},"paper_bgcolor":"white","plot_bgcolor":"#E5ECF6","polar":{"bgcolor":"#E5ECF6","angularaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"radialaxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"ternary":{"bgcolor":"#E5ECF6","aaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"baxis":{"gridcolor":"white","linecolor":"white","ticks":""},"caxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]]},"xaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"yaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"scene":{"xaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"yaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"zaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"geo":{"bgcolor":"white","landcolor":"#E5ECF6","subunitcolor":"white","showland":true,"showlakes":true,"lakecolor":"white"},"title":{"x":0.05},"mapbox":{"style":"light"},"margin":{"b":0,"l":0,"r":0,"t":30}}},"xaxis":{"anchor":"y","domain":[0.0,0.45],"tickformat":".0%"},"yaxis":{"anchor":"x","domain":[0.625,1.0]},"xaxis2":{"anchor":"y2","domain":[0.55,1.0],"tickformat":".0%"},"yaxis2":{"anchor":"x2","domain":[0.625,1.0]},"xaxis3":{"anchor":"y3","domain":[0.0,0.45],"tickformat":".0%"},"yaxis3":{"anchor":"x3","domain":[0.0,0.375]},"xaxis4":{"anchor":"y4","domain":[0.55,1.0],"tickformat":".0%"},"yaxis4":{"anchor":"x4","domain":[0.0,0.375]},"annotations":[{"font":{"size":16},"showarrow":false,"text":"Ковров","x":0.225,"xanchor":"center","xref":"paper","y":1.0,"yanchor":"bottom","yref":"paper"},{"font":{"size":16},"showarrow":false,"text":"Муром","x":0.775,"xanchor":"center","xref":"paper","y":1.0,"yanchor":"bottom","yref":"paper"},{"font":{"size":16},"showarrow":false,"text":"Владимир","x":0.225,"xanchor":"center","xref":"paper","y":0.375,"yanchor":"bottom","yref":"paper"},{"align":"left","font":{"color":"#666666","size":10},"showarrow":false,"text":"Подавленных ячеек нет (n = 12).","x":0,"xanchor":"left","xref":"paper","y":-0.18,"yanchor":"top","yref":"paper"}],"title":{"text":"Каскад скрининга по группе «Площадка» (% от когорты)"},"showlegend":false},                        {"responsive": true}                    ).then(function(){
                            &#10;var gd = document.getElementById('316c19f8-160a-4fb0-a245-a4dbc46a188b');
var x = new MutationObserver(function (mutations, observer) {{
        var display = window.getComputedStyle(gd).display;
        if (!display || display === 'none') {{
            console.log([gd, 'removed!']);
            Plotly.purge(gd);
            observer.disconnect();
        }}
}});
&#10;// Listen for the removal of the full notebook cells
var notebookContainer = gd.closest('#notebook-container');
if (notebookContainer) {{
    x.observe(notebookContainer, {childList: true});
}}
&#10;// Listen for the clearing of the current output cell
var outputEl = gd.closest('.output');
if (outputEl) {{
    x.observe(outputEl, {childList: true});
}}
&#10;                        })                };            </script>        </div>

## Шаг 3 — Диагностические исходы

Среди полностью обследованных: доля подтверждённого ТБ, ЛТИ, “нет ТБ,
нет ЛТИ”, “нет ТБ, статус ЛТИ неизвестен”; с разбивкой по целевой группе
и площадке.

| Категория | Количество | n | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|:---|
| Подтверждённый активный ТБ | 101 | 7705 | 0.0131084 | 0.0108004 | 0.0159016 | Нет |
| Нет ТБ, нет ЛТИ | 6165 | 7705 | 0.80013 | 0.791052 | 0.808909 | Нет |
| Нет ТБ, статус ЛТИ неизвестен | 610 | 7705 | 0.0791694 | 0.0733481 | 0.08541 | Нет |
| Латентная ТБ-инфекция (ЛТИ) | 829 | 7705 | 0.107592 | 0.100868 | 0.114708 | Нет |

*По целевой группе*

| Целевая группа | Категория | Количество | n | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| ЛЖВ (ВИЧ+) | Нет ТБ, статус ЛТИ неизвестен | 513 | 686 | 0.747813 | 0.713998 | 0.778869 | Нет |
| ЛЖВ (ВИЧ+) | Латентная ТБ-инфекция (ЛТИ) | 18 | 686 | 0.0262391 | 0.0166608 | 0.0410937 | Нет |
| ЛЖВ (ВИЧ+) | Нет ТБ, нет ЛТИ | 109 | 686 | 0.158892 | 0.133445 | 0.188138 | Нет |
| ЛЖВ (ВИЧ+) | Подтверждённый активный ТБ | 46 | 686 | 0.0670554 | 0.0506466 | 0.0882859 | Нет |
| Бездомный | Нет ТБ, нет ЛТИ | 847 | 1041 | 0.813641 | 0.788848 | 0.836127 | Нет |
| Бездомный | Латентная ТБ-инфекция (ЛТИ) | 154 | 1041 | 0.147935 | 0.127663 | 0.170795 | Нет |
| Бездомный | Подтверждённый активный ТБ | 36 | 1041 | 0.0345821 | 0.0250828 | 0.0475038 | Нет |
| Бездомный | Нет ТБ, статус ЛТИ неизвестен | 4 | 1041 | 0.00384246 | 0.00149524 | 0.00983802 | Нет |
| Контактное лицо | Нет ТБ, нет ЛТИ | 5209 | 5978 | 0.871362 | 0.862636 | 0.879611 | Нет |
| Контактное лицо | Нет ТБ, статус ЛТИ неизвестен | 93 | 5978 | 0.015557 | 0.0127167 | 0.0190196 | Нет |
| Контактное лицо | Подтверждённый активный ТБ | 19 | 5978 | 0.00317832 | 0.00203574 | 0.00495901 | Нет |
| Контактное лицо | Латентная ТБ-инфекция (ЛТИ) | 657 | 5978 | 0.109903 | 0.102224 | 0.118083 | Нет |

*По площадке*

| Площадка | Категория | Количество | n | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Владимир | Подтверждённый активный ТБ | 97 | 6291 | 0.0154189 | 0.0126565 | 0.0187726 | Нет |
| Владимир | Нет ТБ, нет ЛТИ | 5089 | 6291 | 0.808933 | 0.799031 | 0.818459 | Нет |
| Владимир | Нет ТБ, статус ЛТИ неизвестен | 527 | 6291 | 0.0837705 | 0.0771759 | 0.0908731 | Нет |
| Владимир | Латентная ТБ-инфекция (ЛТИ) | 578 | 6291 | 0.0918773 | 0.0849864 | 0.0992663 | Нет |
| Муром | Латентная ТБ-инфекция (ЛТИ) | 77 | 380 | 0.202632 | 0.165286 | 0.24593 | Нет |
| Муром | Нет ТБ, статус ЛТИ неизвестен | 7 | 380 | 0.0184211 | 0.00895118 | 0.0375301 | Нет |
| Муром | Нет ТБ, нет ЛТИ | 296 | 380 | 0.778947 | 0.73455 | 0.817761 | Нет |
| Ковров | Подтверждённый активный ТБ | 4 | 1034 | 0.00386847 | 0.00150537 | 0.00990433 | Нет |
| Ковров | Нет ТБ, нет ЛТИ | 780 | 1034 | 0.754352 | 0.727204 | 0.779617 | Нет |
| Ковров | Нет ТБ, статус ЛТИ неизвестен | 76 | 1034 | 0.073501 | 0.0591249 | 0.0910343 | Нет |
| Ковров | Латентная ТБ-инфекция (ЛТИ) | 174 | 1034 | 0.168279 | 0.146713 | 0.1923 | Нет |

## Шаг 4 — Каскад превентивного лечения ЛТИ

Среди тех, кому показано лечение: рекомендовано → назначено → начато;
задержка начала лечения (дни, медиана/МКИ) и доля начавших лечение в
течение 30/60 дней.

*Этапы каскада (% от показанных к лечению ЛТИ)*

| Этап | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|:---|
| Рекомендовано | 1710 | 1701 | 0.994737 | 0.990027 | 0.997229 | Нет |
| Назначено | 1710 | 1227 | 0.717544 | 0.695737 | 0.738376 | Нет |
| Начато | 1710 | 1213 | 0.709357 | 0.687385 | 0.730389 | Нет |

*Задержка от диагноза до начала лечения (дни), медиана/МКИ*

|    n | Медиана |   Q1 |  Q3 | Подавлено (n\<5) |
|-----:|--------:|-----:|----:|:-----------------|
| 1213 |    -105 | -212 |  -9 | Нет              |

*Начато в течение целевого срока*

| Целевой срок (дни) | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|---:|---:|---:|---:|---:|---:|:---|
| 30 | 289 | 224 | 0.775087 | 0.723521 | 0.819434 | Нет |
| 60 | 289 | 250 | 0.865052 | 0.820839 | 0.899687 | Нет |

## Шаг 5 — Описание режима лечения

Среди начавших лечение: режимы, содержащие бедаквилин (`RegBq`) и
моксифлоксацин (`RegMfx`), по площадке и по году начала лечения.

| Режим | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|:---|
| Содержит бедаквилин | 1214 | 78 | 0.0642504 | 0.0517853 | 0.0794645 | Нет |
| Содержит моксифлоксацин | 1214 | 92 | 0.0757825 | 0.0621969 | 0.0920444 | Нет |

*По площадке и году начала лечения*

| Режим | Площадка | treat_start_year | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| Содержит бедаквилин | Владимир | 2020 | 179.0 | 18.0 | 0.1005586592178771 | 0.06455835613141786 | 0.15334331167230042 | Нет |
| Содержит бедаквилин | Ковров | 2020 | 30.0 | 6.0 | 0.2 | 0.09505107177289873 | 0.3730569641314826 | Нет |
| Содержит бедаквилин | Муром | 2020 | 11.0 | 5.0 | 0.45454545454545453 | 0.2127127162245977 | 0.719908462590678 | Нет |
| Содержит бедаквилин | Ковров | — | — | — | — | — | — | Да |
| Содержит бедаквилин | Муром | 2022 | 18.0 | 2.0 | 0.1111111111111111 | 0.031019522645612363 | 0.3279976513017881 | Нет |
| Содержит бедаквилин | Владимир | 2026 | 64.0 | 1.0 | 0.015625 | 0.002763541923337505 | 0.08334101600094268 | Нет |
| Содержит бедаквилин | Муром | 2024 | 8.0 | 0.0 | 0.0 | 0.0 | 0.32440756488388034 | Нет |
| Содержит бедаквилин | Ковров | 2026 | 28.0 | 0.0 | 0.0 | 1.3877787807814457e-17 | 0.12064330476584569 | Нет |
| Содержит бедаквилин | Владимир | 2021 | 74.0 | 1.0 | 0.013513513513513514 | 0.002389463403456818 | 0.07265356519843236 | Нет |
| Содержит бедаквилин | Ковров | 2021 | 32.0 | 4.0 | 0.125 | 0.0497013438748007 | 0.2806830548165023 | Нет |
| Содержит бедаквилин | Владимир | 2023 | 86.0 | 2.0 | 0.023255813953488372 | 0.0064009262042708515 | 0.08088014562632058 | Нет |
| Содержит бедаквилин | Владимир | 2025 | 133.0 | 9.0 | 0.06766917293233082 | 0.03600638717710822 | 0.12360502744039734 | Нет |
| Содержит бедаквилин | Ковров | 2023 | 36.0 | 6.0 | 0.16666666666666666 | 0.07870447595018111 | 0.3189079431127947 | Нет |
| Содержит бедаквилин | Ковров | 2025 | 49.0 | 7.0 | 0.14285714285714285 | 0.07096423720406757 | 0.26667706223914406 | Нет |
| Содержит бедаквилин | Муром | 2023 | 14.0 | 0.0 | 0.0 | 2.7755575615628914e-17 | 0.21531080273763586 | Нет |
| Содержит бедаквилин | Муром | 2025 | — | — | — | — | — | Да |
| Содержит бедаквилин | Владимир | 2019 | 226.0 | 3.0 | 0.01327433628318584 | 0.004524556168813011 | 0.038293910400230696 | Нет |
| Содержит бедаквилин | Муром | 2021 | 10.0 | 1.0 | 0.1 | 0.017876213095072924 | 0.40415002679523854 | Нет |
| Содержит бедаквилин | Владимир | 2024 | 86.0 | 1.0 | 0.011627906976744186 | 0.0020555686652495644 | 0.06296406589291728 | Нет |
| Содержит бедаквилин | Муром | 2026 | — | — | — | — | — | Да |
| Содержит бедаквилин | Ковров | 2024 | 26.0 | 5.0 | 0.19230769230769232 | 0.08507061148942405 | 0.37876257119317003 | Нет |
| Содержит бедаквилин | Владимир | 2022 | 67.0 | 5.0 | 0.07462686567164178 | 0.03229604916632266 | 0.16309036792776993 | Нет |
| Содержит бедаквилин | Ковров | 2022 | 31.0 | 2.0 | 0.06451612903225806 | 0.01787478352191456 | 0.2071863673629813 | Нет |
| Содержит моксифлоксацин | Муром | 2020 | 11.0 | 2.0 | 0.18181818181818182 | 0.051367689746085105 | 0.47698056196084426 | Нет |
| Содержит моксифлоксацин | Ковров | — | — | — | — | — | — | Да |
| Содержит моксифлоксацин | Владимир | 2019 | 226.0 | 14.0 | 0.061946902654867256 | 0.03725555040654468 | 0.10128106950559462 | Нет |
| Содержит моксифлоксацин | Муром | 2021 | 10.0 | 2.0 | 0.2 | 0.056682151454375246 | 0.5098375284633583 | Нет |
| Содержит моксифлоксацин | Владимир | 2023 | 86.0 | 1.0 | 0.011627906976744186 | 0.0020555686652495644 | 0.06296406589291728 | Нет |
| Содержит моксифлоксацин | Владимир | 2025 | 133.0 | 9.0 | 0.06766917293233082 | 0.03600638717710822 | 0.12360502744039734 | Нет |
| Содержит моксифлоксацин | Ковров | 2023 | 36.0 | 1.0 | 0.027777777777777776 | 0.00492040713981047 | 0.1416971865327386 | Нет |
| Содержит моксифлоксацин | Ковров | 2025 | 49.0 | 1.0 | 0.02040816326530612 | 0.0036116725898252405 | 0.10693521523391619 | Нет |
| Содержит моксифлоксацин | Владимир | 2022 | 67.0 | 3.0 | 0.04477611940298507 | 0.015343975122038639 | 0.12357833089093762 | Нет |
| Содержит моксифлоксацин | Ковров | 2022 | 31.0 | 4.0 | 0.12903225806451613 | 0.05134284374629143 | 0.2885240625630643 | Нет |
| Содержит моксифлоксацин | Владимир | 2020 | 179.0 | 16.0 | 0.0893854748603352 | 0.05576870080005942 | 0.14025609057858804 | Нет |
| Содержит моксифлоксацин | Ковров | 2020 | 30.0 | 16.0 | 0.5333333333333333 | 0.36142299619873297 | 0.6976761109230025 | Нет |
| Содержит моксифлоксацин | Владимир | 2024 | 86.0 | 6.0 | 0.06976744186046512 | 0.032365414509921336 | 0.1439614064103685 | Нет |
| Содержит моксифлоксацин | Муром | 2026 | — | — | — | — | — | Да |
| Содержит моксифлоксацин | Ковров | 2024 | 26.0 | 3.0 | 0.11538461538461539 | 0.040032446236106134 | 0.28975903211713644 | Нет |
| Содержит моксифлоксацин | Муром | 2022 | 18.0 | 0.0 | 0.0 | 1.3877787807814457e-17 | 0.1758792236466577 | Нет |
| Содержит моксифлоксацин | Муром | 2023 | 14.0 | 1.0 | 0.07142857142857142 | 0.012722215247890939 | 0.3146870442415113 | Нет |
| Содержит моксифлоксацин | Муром | 2025 | — | — | — | — | — | Да |
| Содержит моксифлоксацин | Владимир | 2026 | 64.0 | 3.0 | 0.046875 | 0.016069016786292974 | 0.1289965374009369 | Нет |
| Содержит моксифлоксацин | Муром | 2024 | 8.0 | 0.0 | 0.0 | 0.0 | 0.32440756488388034 | Нет |
| Содержит моксифлоксацин | Ковров | 2026 | 28.0 | 1.0 | 0.03571428571428571 | 0.0063325198490377654 | 0.17712197743353322 | Нет |
| Содержит моксифлоксацин | Владимир | 2021 | 74.0 | 1.0 | 0.013513513513513514 | 0.002389463403456818 | 0.07265356519843236 | Нет |
| Содержит моксифлоксацин | Ковров | 2021 | 32.0 | 8.0 | 0.25 | 0.1325240091850904 | 0.4210655899424449 | Нет |

## Шаг 6 — Приверженность и завершение лечения

Распределение доли принятых доз; доля достигших порогов 50%/100%; состав
исходов лечения (завершено/окончено/категории незавершения) в виде
столбчатой диаграммы с накоплением, в сумме 100% от начавших лечение.

*Доля принятых доз (от назначенных), медиана/МКИ*

|    n | Медиана |       Q1 |  Q3 | Подавлено (n\<5) |
|-----:|--------:|---------:|----:|:-----------------|
| 1155 |       1 | 0.964286 |   1 | Нет              |

*Достигнутые пороги доз*

| Порог | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|:---|
| Достигнут порог 50% | 1214 | 962 | 0.792422 | 0.768702 | 0.814296 | Нет |
| Достигнут порог 100% | 1214 | 830 | 0.68369 | 0.656987 | 0.709235 | Нет |

<div style="height:525px; width:100%;">            <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-AMS-MML_SVG"></script><script>if (window.MathJax && window.MathJax.Hub && window.MathJax.Hub.Config) {window.MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}</script>                <script>window.PlotlyConfig = {MathJaxConfig: 'local'};</script>
        <script charset="utf-8" src="https://cdn.plot.ly/plotly-3.6.0.min.js" integrity="sha256-QaOVwtVY0T02VaHrr6pnoHLCwayMJp4O5n4YyaE3rJk=" crossorigin="anonymous"></script>                <div id="6ae32e8d-6595-42a9-b3e6-ae3bd2ae05bb" class="plotly-graph-div" style="height:100%; width:100%;"></div>            <script>                window.PLOTLYENV=window.PLOTLYENV || {};                                if (document.getElementById("6ae32e8d-6595-42a9-b3e6-ae3bd2ae05bb")) {                    Plotly.newPlot(                        "6ae32e8d-6595-42a9-b3e6-ae3bd2ae05bb",                        [{"customdata":{"dtype":"f8","bdata":"AAAAAAD4kkAAAAAAAIiNQKusqNJkIug\u002fjfFhR9Og6T8=","shape":"1, 4"},"hovertemplate":"Завершено (100% доз)\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#2ca02c"},"name":"Завершено (100% доз)","texttemplate":"%{y:.1%}","x":["Всего"],"y":{"dtype":"f8","bdata":"lcHrz83o6D8="},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAAD4kkAAAAAAAAAsQBtPLjwIMHw\u002fft9A9fW5kz8=","shape":"1, 4"},"hovertemplate":"Окончено (85–99% доз)\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#98df8a"},"name":"Окончено (85–99% доз)","texttemplate":"%{y:.1%}","x":["Всего"],"y":{"dtype":"f8","bdata":"8h3npCeehz8="},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAAD4kkAAAAAAAABHQOil5jEkNp0\u002fEO08TQKwqT8=","shape":"1, 4"},"hovertemplate":"Продолжается\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#1f77b4"},"name":"Продолжается","texttemplate":"%{y:.1%}","x":["Всего"],"y":{"dtype":"f8","bdata":"vSFQ\u002fntmoz8="},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAAD4kkAAAAAAAABfQMVL7ySGGrY\u002fBwwVyOHVvj8=","shape":"1, 4"},"hovertemplate":"Не завершено\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#ff7f0e"},"name":"Не завершено","texttemplate":"%{y:.1%}","x":["Всего"],"y":{"dtype":"f8","bdata":"3k7bCPUluj8="},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAAD4kkAAAAAAAEBVQLRlGVcgLK0\u002fDomB5Oj0tT8=","shape":"1, 4"},"hovertemplate":"Остановлено (по мед. показаниям)\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#d62728"},"name":"Остановлено (по мед. показаниям)","texttemplate":"%{y:.1%}","x":["Всего"],"y":{"dtype":"f8","bdata":"3q8BhJnssT8="},"type":"bar"}],                        {"template":{"data":{"histogram2dcontour":[{"type":"histogram2dcontour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"choropleth":[{"type":"choropleth","colorbar":{"outlinewidth":0,"ticks":""}}],"histogram2d":[{"type":"histogram2d","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmap":[{"type":"heatmap","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"contourcarpet":[{"type":"contourcarpet","colorbar":{"outlinewidth":0,"ticks":""}}],"contour":[{"type":"contour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"surface":[{"type":"surface","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"mesh3d":[{"type":"mesh3d","colorbar":{"outlinewidth":0,"ticks":""}}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"parcoords":[{"type":"parcoords","line":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolargl":[{"type":"scatterpolargl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"scattergeo":[{"type":"scattergeo","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolar":[{"type":"scatterpolar","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"scattergl":[{"type":"scattergl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatter3d":[{"type":"scatter3d","line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermap":[{"type":"scattermap","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermapbox":[{"type":"scattermapbox","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterternary":[{"type":"scatterternary","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattercarpet":[{"type":"scattercarpet","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"type":"carpet"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}],"barpolar":[{"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"pie":[{"automargin":true,"type":"pie"}]},"layout":{"autotypenumbers":"strict","colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"hovermode":"closest","hoverlabel":{"align":"left"},"paper_bgcolor":"white","plot_bgcolor":"#E5ECF6","polar":{"bgcolor":"#E5ECF6","angularaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"radialaxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"ternary":{"bgcolor":"#E5ECF6","aaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"baxis":{"gridcolor":"white","linecolor":"white","ticks":""},"caxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]]},"xaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"yaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"scene":{"xaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"yaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"zaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"geo":{"bgcolor":"white","landcolor":"#E5ECF6","subunitcolor":"white","showland":true,"showlakes":true,"lakecolor":"white"},"title":{"x":0.05},"mapbox":{"style":"light"},"margin":{"b":0,"l":0,"r":0,"t":30}}},"yaxis":{"tickformat":".0%"},"title":{"text":"Структура исходов лечения"},"barmode":"stack","legend":{"title":{"text":"Исход"}},"annotations":[{"align":"left","font":{"color":"#666666","size":10},"showarrow":false,"text":"Подавленных ячеек нет (n = 5).","x":0,"xanchor":"left","xref":"paper","y":-0.18,"yanchor":"top","yref":"paper"}]},                        {"responsive": true}                    ).then(function(){
                            &#10;var gd = document.getElementById('6ae32e8d-6595-42a9-b3e6-ae3bd2ae05bb');
var x = new MutationObserver(function (mutations, observer) {{
        var display = window.getComputedStyle(gd).display;
        if (!display || display === 'none') {{
            console.log([gd, 'removed!']);
            Plotly.purge(gd);
            observer.disconnect();
        }}
}});
&#10;// Listen for the removal of the full notebook cells
var notebookContainer = gd.closest('#notebook-container');
if (notebookContainer) {{
    x.observe(notebookContainer, {childList: true});
}}
&#10;// Listen for the clearing of the current output cell
var outputEl = gd.closest('.output');
if (outputEl) {{
    x.observe(outputEl, {childList: true});
}}
&#10;                        })                };            </script>        </div>

<div style="height:525px; width:100%;">            <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-AMS-MML_SVG"></script><script>if (window.MathJax && window.MathJax.Hub && window.MathJax.Hub.Config) {window.MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}</script>                <script>window.PlotlyConfig = {MathJaxConfig: 'local'};</script>
        <script charset="utf-8" src="https://cdn.plot.ly/plotly-3.6.0.min.js" integrity="sha256-QaOVwtVY0T02VaHrr6pnoHLCwayMJp4O5n4YyaE3rJk=" crossorigin="anonymous"></script>                <div id="f4aabad5-6767-4055-916d-f456aff5acae" class="plotly-graph-div" style="height:100%; width:100%;"></div>            <script>                window.PLOTLYENV=window.PLOTLYENV || {};                                if (document.getElementById("f4aabad5-6767-4055-916d-f456aff5acae")) {                    Plotly.newPlot(                        "f4aabad5-6767-4055-916d-f456aff5acae",                        [{"customdata":{"dtype":"f8","bdata":"AAAAAACAUEAAAAAAAIBMQEmd+Q+wV+g\u002fb8SEaW+m7T8AAAAAAJiMQAAAAAAAQIVAktoccifY5j8Y56PdRqfoPwAAAAAAIG1AAAAAAAAAakBd\u002fASwxRXrP0v0Ni7uo+0\u002f","shape":"3, 4"},"hovertemplate":"Завершено (100% доз)\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#2ca02c"},"name":"Завершено (100% доз)","texttemplate":"%{y:.1%}","x":["Муром","Владимир","Ковров"],"y":{"dtype":"f8","bdata":"o4suuuii6z8pNfYwC8jnPz6I5LAHkew\u002f"},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAACAUEAAAAAAAAAAQBBx0vnBGYE\u002fwGpW2deauj8AAAAAAJiMQAAAAAAAAChA2zfM5g7Lfj\u002fgwwfyW1SXPw==","shape":"2, 4"},"hovertemplate":"Окончено (85–99% доз)\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#98df8a"},"name":"Окончено (85–99% доз)","texttemplate":"%{y:.1%}","x":["Муром","Владимир"],"y":{"dtype":"f8","bdata":"CB988MEHnz9ekJR\u002f6NuKPw=="},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAACAUEAAAAAAAAAAQBBx0vnBGYE\u002fwGpW2deauj8AAAAAAJiMQAAAAAAAAERAiOoJCzSFoD9o5hi9tjKuPwAAAAAAIG1AAAAAAAAAEEAUfSJgDW17PxDFOuygK6Y\u002f","shape":"3, 4"},"hovertemplate":"Продолжается\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#1f77b4"},"name":"Продолжается","texttemplate":"%{y:.1%}","x":["Муром","Владимир","Ковров"],"y":{"dtype":"f8","bdata":"CB988MEHnz\u002f5IlFq7GGmP5yijIBTlJE\u002f"},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAACAUEAAAAAAAAAIQBAnW5aA548\u002f9GQil+oKwD8AAAAAAJiMQAAAAAAAgFxApFZXC8jQuj+mLd3nm+PCPwAAAAAAIG1AAAAAAAAAHEA+9x+NBfWNPySAQCOBFK8\u002f","shape":"3, 4"},"hovertemplate":"Не завершено\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#ff7f0e"},"name":"Не завершено","texttemplate":"%{y:.1%}","x":["Муром","Владимир","Ковров"],"y":{"dtype":"f8","bdata":"RhdddNFFpz9wa4AXJOW\u002fP5Ec9iCSw54\u002f"},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAACAUEAAAAAAAAAAQBBx0vnBGYE\u002fwGpW2deauj8AAAAAAJiMQAAAAAAAQFFASgG8fOW6rj+xfeBQVie4PwAAAAAAIG1AAAAAAAAALEBOl92BEn+iP3fDVZhCK7k\u002f","shape":"3, 4"},"hovertemplate":"Остановлено (по мед. показаниям)\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#d62728"},"name":"Остановлено (по мед. показаниям)","texttemplate":"%{y:.1%}","x":["Муром","Владимир","Ковров"],"y":{"dtype":"f8","bdata":"CB988MEHnz\u002fEx7IbD06zP5Ec9iCSw64\u002f"},"type":"bar"}],                        {"template":{"data":{"histogram2dcontour":[{"type":"histogram2dcontour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"choropleth":[{"type":"choropleth","colorbar":{"outlinewidth":0,"ticks":""}}],"histogram2d":[{"type":"histogram2d","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmap":[{"type":"heatmap","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"contourcarpet":[{"type":"contourcarpet","colorbar":{"outlinewidth":0,"ticks":""}}],"contour":[{"type":"contour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"surface":[{"type":"surface","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"mesh3d":[{"type":"mesh3d","colorbar":{"outlinewidth":0,"ticks":""}}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"parcoords":[{"type":"parcoords","line":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolargl":[{"type":"scatterpolargl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"scattergeo":[{"type":"scattergeo","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolar":[{"type":"scatterpolar","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"scattergl":[{"type":"scattergl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatter3d":[{"type":"scatter3d","line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermap":[{"type":"scattermap","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermapbox":[{"type":"scattermapbox","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterternary":[{"type":"scatterternary","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattercarpet":[{"type":"scattercarpet","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"type":"carpet"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}],"barpolar":[{"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"pie":[{"automargin":true,"type":"pie"}]},"layout":{"autotypenumbers":"strict","colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"hovermode":"closest","hoverlabel":{"align":"left"},"paper_bgcolor":"white","plot_bgcolor":"#E5ECF6","polar":{"bgcolor":"#E5ECF6","angularaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"radialaxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"ternary":{"bgcolor":"#E5ECF6","aaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"baxis":{"gridcolor":"white","linecolor":"white","ticks":""},"caxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]]},"xaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"yaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"scene":{"xaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"yaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"zaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"geo":{"bgcolor":"white","landcolor":"#E5ECF6","subunitcolor":"white","showland":true,"showlakes":true,"lakecolor":"white"},"title":{"x":0.05},"mapbox":{"style":"light"},"margin":{"b":0,"l":0,"r":0,"t":30}}},"yaxis":{"tickformat":".0%"},"title":{"text":"Структура исходов лечения по Площадка"},"barmode":"stack","legend":{"title":{"text":"Исход"}},"annotations":[{"align":"left","font":{"color":"#666666","size":10},"showarrow":false,"text":"Подавленных ячеек нет (n = 14).","x":0,"xanchor":"left","xref":"paper","y":-0.18,"yanchor":"top","yref":"paper"}]},                        {"responsive": true}                    ).then(function(){
                            &#10;var gd = document.getElementById('f4aabad5-6767-4055-916d-f456aff5acae');
var x = new MutationObserver(function (mutations, observer) {{
        var display = window.getComputedStyle(gd).display;
        if (!display || display === 'none') {{
            console.log([gd, 'removed!']);
            Plotly.purge(gd);
            observer.disconnect();
        }}
}});
&#10;// Listen for the removal of the full notebook cells
var notebookContainer = gd.closest('#notebook-container');
if (notebookContainer) {{
    x.observe(notebookContainer, {childList: true});
}}
&#10;// Listen for the clearing of the current output cell
var outputEl = gd.closest('.output');
if (outputEl) {{
    x.observe(outputEl, {childList: true});
}}
&#10;                        })                };            </script>        </div>

<div style="height:525px; width:100%;">            <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-AMS-MML_SVG"></script><script>if (window.MathJax && window.MathJax.Hub && window.MathJax.Hub.Config) {window.MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}</script>                <script>window.PlotlyConfig = {MathJaxConfig: 'local'};</script>
        <script charset="utf-8" src="https://cdn.plot.ly/plotly-3.6.0.min.js" integrity="sha256-QaOVwtVY0T02VaHrr6pnoHLCwayMJp4O5n4YyaE3rJk=" crossorigin="anonymous"></script>                <div id="127c89a8-6645-4030-b8ab-3da1b3028bea" class="plotly-graph-div" style="height:100%; width:100%;"></div>            <script>                window.PLOTLYENV=window.PLOTLYENV || {};                                if (document.getElementById("127c89a8-6645-4030-b8ab-3da1b3028bea")) {                    Plotly.newPlot(                        "127c89a8-6645-4030-b8ab-3da1b3028bea",                        [{"customdata":{"dtype":"f8","bdata":"AAAAAABQfUAAAAAAACB1QGRD1DiIteU\u002fUtHknMBM6D8AAAAAAAiEQAAAAAAAqIBANiawGl2e6T\u002fskmL6ynjrPwAAAAAAAFpAAAAAAACAUkDb5TXlAsjjP6EXDnBgRuk\u002f","shape":"3, 4"},"hovertemplate":"Завершено (100% доз)\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#2ca02c"},"name":"Завершено (100% доз)","texttemplate":"%{y:.1%}","x":["ЛЖВ (ВИЧ+)","Контактное лицо","Бездомный"],"y":{"dtype":"f8","bdata":"OsEmVdQP5z8+ZIWywZvqP0\u002fsxE7sxOY\u002f"},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAABQfUAAAAAAAAAQQKBw37bCNWs\u002fkVExvTM+lj8AAAAAAAiEQAAAAAAAACJAkE6MJbVTfj8Q42qPKhqbPwAAAAAAAFpAAAAAAAAA8D+wkwe0r9dbP1SsbrMM3ao\u002f","shape":"3, 4"},"hovertemplate":"Окончено (85–99% доз)\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#98df8a"},"name":"Окончено (85–99% доз)","texttemplate":"%{y:.1%}","x":["ЛЖВ (ВИЧ+)","Контактное лицо","Бездомный"],"y":{"dtype":"f8","bdata":"hNYbGYp3gT+0PuNHTMGMPxQ7sRM7sYM\u002f"},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAABQfUAAAAAAAAA8QBP8vA\u002foT6U\u002fxstAThi+tT8AAAAAAAiEQAAAAAAAADFAZOPE87EFkT93djWY5YilPwAAAAAAAFpAAAAAAAAA8D+wkwe0r9dbP1SsbrMM3ao\u002f","shape":"3, 4"},"hovertemplate":"Продолжается\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#1f77b4"},"name":"Продолжается","texttemplate":"%{y:.1%}","x":["ЛЖВ (ВИЧ+)","Контактное лицо","Бездомный"],"y":{"dtype":"f8","bdata":"Z7fwqzGRrj+q1+RDViibPxQ7sRM7sYM\u002f"},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAABQfUAAAAAAAABOQH7YVAZIx7k\u002fQ9\u002f3XZiixD8AAAAAAAiEQAAAAAAAAENAx+pqmK5Epj+AtU52CpC0PwAAAAAAAFpAAAAAAAAAOkDE0Urd\u002fJ3GP5zLXPbQ1NU\u002f","shape":"3, 4"},"hovertemplate":"Не завершено\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#ff7f0e"},"name":"Не завершено","texttemplate":"%{y:.1%}","x":["ЛЖВ (ВИЧ+)","Контактное лицо","Бездомный"],"y":{"dtype":"f8","bdata":"HBmKdxFgwD++peFLQlquPwAAAAAAANA\u002f"},"type":"bar"},{"customdata":{"dtype":"f8","bdata":"AAAAAABQfUAAAAAAAIBDQFd4Ubgec68\u002fLmAjP7KVvD8AAAAAAAiEQAAAAAAAAEZAxTLwvfRhqj9Qaq5h+kS3PwAAAAAAAFpAAAAAAAAAAECwvzUkqqp1PwjpuWakQrE\u002f","shape":"3, 4"},"hovertemplate":"Остановлено (по мед. показаниям)\u003cbr\u003e%{customdata[1]:.0f} из %{customdata[0]:.0f} (%{y:.1%})\u003cbr\u003e95% ДИ %{customdata[2]:.1%}–%{customdata[3]:.1%}\u003cextra\u003e\u003c\u002fextra\u003e","marker":{"color":"#d62728"},"name":"Остановлено (по мед. показаниям)","texttemplate":"%{y:.1%}","x":["ЛЖВ (ВИЧ+)","Контактное лицо","Бездомный"],"y":{"dtype":"f8","bdata":"ce2ZTrBJtT9ube4rkpKxPxQ7sRM7sZM\u002f"},"type":"bar"}],                        {"template":{"data":{"histogram2dcontour":[{"type":"histogram2dcontour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"choropleth":[{"type":"choropleth","colorbar":{"outlinewidth":0,"ticks":""}}],"histogram2d":[{"type":"histogram2d","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmap":[{"type":"heatmap","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"contourcarpet":[{"type":"contourcarpet","colorbar":{"outlinewidth":0,"ticks":""}}],"contour":[{"type":"contour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"surface":[{"type":"surface","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"mesh3d":[{"type":"mesh3d","colorbar":{"outlinewidth":0,"ticks":""}}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"parcoords":[{"type":"parcoords","line":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolargl":[{"type":"scatterpolargl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"scattergeo":[{"type":"scattergeo","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolar":[{"type":"scatterpolar","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"scattergl":[{"type":"scattergl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatter3d":[{"type":"scatter3d","line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermap":[{"type":"scattermap","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermapbox":[{"type":"scattermapbox","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterternary":[{"type":"scatterternary","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattercarpet":[{"type":"scattercarpet","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"type":"carpet"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}],"barpolar":[{"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"pie":[{"automargin":true,"type":"pie"}]},"layout":{"autotypenumbers":"strict","colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"hovermode":"closest","hoverlabel":{"align":"left"},"paper_bgcolor":"white","plot_bgcolor":"#E5ECF6","polar":{"bgcolor":"#E5ECF6","angularaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"radialaxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"ternary":{"bgcolor":"#E5ECF6","aaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"baxis":{"gridcolor":"white","linecolor":"white","ticks":""},"caxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]]},"xaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"yaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"scene":{"xaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"yaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"zaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"geo":{"bgcolor":"white","landcolor":"#E5ECF6","subunitcolor":"white","showland":true,"showlakes":true,"lakecolor":"white"},"title":{"x":0.05},"mapbox":{"style":"light"},"margin":{"b":0,"l":0,"r":0,"t":30}}},"yaxis":{"tickformat":".0%"},"title":{"text":"Структура исходов лечения по Целевая группа"},"barmode":"stack","legend":{"title":{"text":"Исход"}},"annotations":[{"align":"left","font":{"color":"#666666","size":10},"showarrow":false,"text":"Подавленных ячеек нет (n = 15).","x":0,"xanchor":"left","xref":"paper","y":-0.18,"yanchor":"top","yref":"paper"}]},                        {"responsive": true}                    ).then(function(){
                            &#10;var gd = document.getElementById('127c89a8-6645-4030-b8ab-3da1b3028bea');
var x = new MutationObserver(function (mutations, observer) {{
        var display = window.getComputedStyle(gd).display;
        if (!display || display === 'none') {{
            console.log([gd, 'removed!']);
            Plotly.purge(gd);
            observer.disconnect();
        }}
}});
&#10;// Listen for the removal of the full notebook cells
var notebookContainer = gd.closest('#notebook-container');
if (notebookContainer) {{
    x.observe(notebookContainer, {childList: true});
}}
&#10;// Listen for the clearing of the current output cell
var outputEl = gd.closest('.output');
if (outputEl) {{
    x.observe(outputEl, {childList: true});
}}
&#10;                        })                };            </script>        </div>

## Шаг 7 — Получение стимулирующих выплат

Доля получивших каждую выплату среди имеющих на неё право, и медианная
задержка между достижением показателя и датой выплаты; сравнение по
площадкам.

*Получение выплат (% от собственной когорты каждой выплаты)*

| Стимул | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|:---|
| Скрининг | 4618 | 4150 | 0.898657 | 0.889619 | 0.907033 | Нет |
| Доза 50% | 772 | 557 | 0.721503 | 0.688845 | 0.751967 | Нет |
| Доза 100% | 772 | 571 | 0.739637 | 0.707549 | 0.769352 | Нет |
| 1 год наблюдения | 4631 | 1490 | 0.321745 | 0.308443 | 0.335342 | Нет |

*Задержка выплаты за скрининг (дни), медиана/МКИ*

|    n | Медиана |  Q1 |  Q3 | Подавлено (n\<5) |
|-----:|--------:|----:|----:|:-----------------|
| 4159 |      21 |  12 |  36 | Нет              |

*Получение выплат по площадке*

| Стимул | Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Скрининг | Ковров | 127 | 104 | 0.818898 | 0.742888 | 0.876182 | Нет |
| Скрининг | Муром | 201 | 144 | 0.716418 | 0.650501 | 0.774218 | Нет |
| Скрининг | Владимир | 4290 | 3902 | 0.909557 | 0.900604 | 0.917777 | Нет |
| Доза 50% | Ковров | 54 | 39 | 0.722222 | 0.591096 | 0.823832 | Нет |
| Доза 50% | Муром | 51 | 50 | 0.980392 | 0.896954 | 0.99653 | Нет |
| Доза 50% | Владимир | 667 | 468 | 0.701649 | 0.665852 | 0.735136 | Нет |
| Доза 100% | Ковров | 54 | 40 | 0.740741 | 0.610691 | 0.838813 | Нет |
| Доза 100% | Муром | 51 | 46 | 0.901961 | 0.790218 | 0.957392 | Нет |
| Доза 100% | Владимир | 667 | 485 | 0.727136 | 0.692104 | 0.759568 | Нет |
| 1 год наблюдения | Ковров | 128 | 31 | 0.242188 | 0.176187 | 0.323211 | Нет |
| 1 год наблюдения | Муром | 201 | 84 | 0.41791 | 0.35189 | 0.48701 | Нет |
| 1 год наблюдения | Владимир | 4302 | 1375 | 0.319619 | 0.30585 | 0.333709 | Нет |

## Шаг 8 — Катамнез и итоговые исходы

Повторный скрининг через 1 год/24 месяца; распределение итогового исхода
в целом и по завершённости лечения; частота заболеваемости ТБ (на 100
человеко-лет) среди начавших лечение ЛТИ.

*Повторный скрининг через 1 год (среди зрелой 1-годичной когорты)*

|    n | Количество |     Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|-----:|-----------:|---------:|--------------:|---------------:|:-----------------|
| 6845 |       3256 | 0.475676 |      0.463862 |       0.487517 | Нет              |

*Нет ТБ через 1 год*

|    n | Количество |     Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|-----:|-----------:|---------:|--------------:|---------------:|:-----------------|
| 3492 |       3474 | 0.994845 |      0.991866 |       0.996737 | Нет              |

*Повторный скрининг через 24 месяца (среди зрелой 24-месячной когорты)*

|    n | Количество |      Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|-----:|-----------:|----------:|--------------:|---------------:|:-----------------|
| 6213 |        184 | 0.0296153 |      0.025682 |        0.03413 | Нет              |

*Нет ТБ через 24 месяца*

|   n | Количество |     Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|----:|-----------:|---------:|--------------:|---------------:|:-----------------|
| 184 |        173 | 0.940217 |      0.896136 |       0.966294 | Нет              |

*Распределение итогового исхода*

| Категория | Количество | n | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|:---|
| ТБ не развился | 3296 | 3492 | 0.943872 | 0.935738 | 0.951029 | Нет |
| Другое | 24 | 3492 | 0.00687285 | 0.00462295 | 0.0102065 | Нет |
| Неизвестно | 154 | 3492 | 0.0441008 | 0.0377772 | 0.0514263 | Нет |
| Развился ТБ | 18 | 3492 | 0.00515464 | 0.0032631 | 0.00813372 | Нет |

*Итоговый исход, с разбивкой по завершённости превентивного лечения*

| Лечение завершено | Категория | Количество | n | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Да | Развился ТБ | 2 | 518 | 0.003861 | 0.00105947 | 0.013967 | Нет |
| Да | Другое | 10 | 518 | 0.019305 | 0.0105193 | 0.0351679 | Нет |
| Да | ТБ не развился | 486 | 518 | 0.938224 | 0.914092 | 0.955904 | Нет |
| Да | Неизвестно | 20 | 518 | 0.03861 | 0.0251309 | 0.058882 | Нет |
| Нет | Другое | 14 | 2974 | 0.00470746 | 0.00280625 | 0.00788655 | Нет |
| Нет | ТБ не развился | 2810 | 2974 | 0.944855 | 0.936063 | 0.9525 | Нет |
| Нет | Развился ТБ | 16 | 2974 | 0.00537996 | 0.00331432 | 0.00872173 | Нет |
| Нет | Неизвестно | 134 | 2974 | 0.0450572 | 0.0381708 | 0.0531173 | Нет |

*Частота заболеваемости ТБ (на 100 человеко-лет, среди начавших лечение
ЛТИ)*

| n | События | Человеко-лет | Частота на 100 чел.-лет | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|---:|---:|---:|---:|---:|---:|:---|
| 1203 | 0 | 411.387 | 0 | 0 | 0.896694 | Нет |

## Шаг 9 — Временные тренды

Количество включений в когорту, начал лечения и исходов по календарным
годам/кварталам (2018–2026).

<div style="height:525px; width:100%;">            <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-AMS-MML_SVG"></script><script>if (window.MathJax && window.MathJax.Hub && window.MathJax.Hub.Config) {window.MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}</script>                <script>window.PlotlyConfig = {MathJaxConfig: 'local'};</script>
        <script charset="utf-8" src="https://cdn.plot.ly/plotly-3.6.0.min.js" integrity="sha256-QaOVwtVY0T02VaHrr6pnoHLCwayMJp4O5n4YyaE3rJk=" crossorigin="anonymous"></script>                <div id="f08b9755-0bf8-4b56-a3b7-bd1d706fb810" class="plotly-graph-div" style="height:100%; width:100%;"></div>            <script>                window.PLOTLYENV=window.PLOTLYENV || {};                                if (document.getElementById("f08b9755-0bf8-4b56-a3b7-bd1d706fb810")) {                    Plotly.newPlot(                        "f08b9755-0bf8-4b56-a3b7-bd1d706fb810",                        [{"customdata":["2018 – К4","2019 – К1","2019 – К2","2019 – К3","2019 – К4","2020 – К1","2020 – К2","2020 – К3","2020 – К4","2021 – К1","2021 – К2","2021 – К3","2021 – К4","2022 – К1","2022 – К2","2022 – К3","2022 – К4","2023 – К1","2023 – К2","2023 – К3","2023 – К4","2024 – К1","2024 – К2","2024 – К3","2024 – К4","2025 – К1","2025 – К2","2025 – К3","2025 – К4","2026 – К1","2026 – К2","2026 – К3","2026 – К4"],"hovertemplate":"Включение в когорту\u003cbr\u003e%{customdata}: %{y:.0f}\u003cextra\u003e\u003c\u002fextra\u003e","line":{"color":"#1f77b4"},"marker":{"color":"#1f77b4"},"mode":"lines+markers","name":"Включение в когорту","x":["2018-10-01T00:00:00","2019-01-01T00:00:00","2019-04-01T00:00:00","2019-07-01T00:00:00","2019-10-01T00:00:00","2020-01-01T00:00:00","2020-04-01T00:00:00","2020-07-01T00:00:00","2020-10-01T00:00:00","2021-01-01T00:00:00","2021-04-01T00:00:00","2021-07-01T00:00:00","2021-10-01T00:00:00","2022-01-01T00:00:00","2022-04-01T00:00:00","2022-07-01T00:00:00","2022-10-01T00:00:00","2023-01-01T00:00:00","2023-04-01T00:00:00","2023-07-01T00:00:00","2023-10-01T00:00:00","2024-01-01T00:00:00","2024-04-01T00:00:00","2024-07-01T00:00:00","2024-10-01T00:00:00","2025-01-01T00:00:00","2025-04-01T00:00:00","2025-07-01T00:00:00","2025-10-01T00:00:00","2026-01-01T00:00:00","2026-04-01T00:00:00","2026-07-01T00:00:00","2026-10-01T00:00:00"],"y":{"dtype":"f8","bdata":"AAAAAABAU0AAAAAAAFB6QAAAAAAAYHhAAAAAAADQckAAAAAAAFCBQAAAAAAA0JFAAAAAAABAd0AAAAAAADB9QAAAAAAAUHxAAAAAAACgdUAAAAAAAEBnQAAAAAAAQF5AAAAAAABAUEAAAAAAAABHQAAAAAAAAD9AAAAAAACASkAAAAAAAMBYQAAAAAAAgE9AAAAAAAAAU0AAAAAAAKBkQAAAAAAAQGVAAAAAAADAbkAAAAAAAABuQAAAAAAAgGZAAAAAAADAWUAAAAAAAKBqQAAAAAAAoHFAAAAAAAAgcEAAAAAAAEB3QAAAAAAAwGNAAAAAAAAAOkAAAAAAAAAAAAAAAAAAAAAA"},"type":"scatter"},{"customdata":["2018 – К2","2018 – К3","2018 – К4","2019 – К1","2019 – К2","2019 – К4","2020 – К1","2020 – К2","2020 – К3","2020 – К4","2021 – К1","2021 – К2","2021 – К3","2021 – К4","2022 – К1","2022 – К2","2022 – К4","2023 – К1","2023 – К2","2023 – К4","2024 – К1","2024 – К2","2025 – К1","2025 – К2","2025 – К3","2025 – К4","2026 – К1","2026 – К2"],"hovertemplate":"Начало лечения\u003cbr\u003e%{customdata}: %{y:.0f}\u003cextra\u003e\u003c\u002fextra\u003e","line":{"color":"#ff7f0e"},"marker":{"color":"#ff7f0e"},"mode":"lines+markers","name":"Начало лечения","x":["2018-04-01T00:00:00","2018-07-01T00:00:00","2018-10-01T00:00:00","2019-01-01T00:00:00","2019-04-01T00:00:00","2019-10-01T00:00:00","2020-01-01T00:00:00","2020-04-01T00:00:00","2020-07-01T00:00:00","2020-10-01T00:00:00","2021-01-01T00:00:00","2021-04-01T00:00:00","2021-07-01T00:00:00","2021-10-01T00:00:00","2022-01-01T00:00:00","2022-04-01T00:00:00","2022-10-01T00:00:00","2023-01-01T00:00:00","2023-04-01T00:00:00","2023-10-01T00:00:00","2024-01-01T00:00:00","2024-04-01T00:00:00","2025-01-01T00:00:00","2025-04-01T00:00:00","2025-07-01T00:00:00","2025-10-01T00:00:00","2026-01-01T00:00:00","2026-04-01T00:00:00"],"y":{"dtype":"f8","bdata":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAZ0AAAAAAAAA6QAAAAAAAACJAAAAAAACAZkAAAAAAAAAzQAAAAAAAABRAAAAAAAAAMEAAAAAAAIBWQAAAAAAAABhAAAAAAAAAHEAAAAAAAAAqQAAAAAAAAFhAAAAAAAAAFEAAAAAAAAAqQAAAAAAAwFxAAAAAAAAAHEAAAAAAAAAkQAAAAAAAAFtAAAAAAAAAGEAAAAAAAOBhQAAAAAAAACpAAAAAAAAAFEAAAAAAAAA5QAAAAAAAQFJAAAAAAAAALkA="},"type":"scatter"},{"customdata":["2018 – К2","2018 – К3","2018 – К4","2019 – К2","2019 – К3","2019 – К4","2020 – К1","2020 – К2","2020 – К3","2020 – К4","2021 – К1","2021 – К2","2021 – К3","2021 – К4","2022 – К1","2022 – К2","2022 – К3","2022 – К4","2023 – К1","2023 – К2","2023 – К3","2023 – К4","2024 – К1","2024 – К2","2024 – К3","2024 – К4","2025 – К1","2025 – К2","2025 – К3","2025 – К4","2026 – К1","2026 – К2","2026 – К3","2026 – К4"],"hovertemplate":"Исход\u003cbr\u003e%{customdata}: %{y:.0f}\u003cextra\u003e\u003c\u002fextra\u003e","line":{"color":"#2ca02c"},"marker":{"color":"#2ca02c"},"mode":"lines+markers","name":"Исход","x":["2018-04-01T00:00:00","2018-07-01T00:00:00","2018-10-01T00:00:00","2019-04-01T00:00:00","2019-07-01T00:00:00","2019-10-01T00:00:00","2020-01-01T00:00:00","2020-04-01T00:00:00","2020-07-01T00:00:00","2020-10-01T00:00:00","2021-01-01T00:00:00","2021-04-01T00:00:00","2021-07-01T00:00:00","2021-10-01T00:00:00","2022-01-01T00:00:00","2022-04-01T00:00:00","2022-07-01T00:00:00","2022-10-01T00:00:00","2023-01-01T00:00:00","2023-04-01T00:00:00","2023-07-01T00:00:00","2023-10-01T00:00:00","2024-01-01T00:00:00","2024-04-01T00:00:00","2024-07-01T00:00:00","2024-10-01T00:00:00","2025-01-01T00:00:00","2025-04-01T00:00:00","2025-07-01T00:00:00","2025-10-01T00:00:00","2026-01-01T00:00:00","2026-04-01T00:00:00","2026-07-01T00:00:00","2026-10-01T00:00:00"],"y":{"dtype":"f8","bdata":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACARkAAAAAAAABQQAAAAAAAAFRAAAAAAACAQkAAAAAAAMBQQAAAAAAAgEJAAAAAAACAS0AAAAAAAIBJQAAAAAAAAEZAAAAAAAAAOUAAAAAAAAA1QAAAAAAAAEVAAAAAAAAANUAAAAAAAAA8QAAAAAAAAEBAAAAAAAAAREAAAAAAAIBBQAAAAAAAADtAAAAAAAAAOkAAAAAAAIBCQAAAAAAAADlAAAAAAACAQUAAAAAAAABAQAAAAAAAAEFAAAAAAAAAPUAAAAAAAAA9QAAAAAAAQFJAAAAAAACAUEAAAAAAAAA+QAAAAAAAAAAAAAAAAAAAAAA="},"type":"scatter"}],                        {"template":{"data":{"histogram2dcontour":[{"type":"histogram2dcontour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"choropleth":[{"type":"choropleth","colorbar":{"outlinewidth":0,"ticks":""}}],"histogram2d":[{"type":"histogram2d","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmap":[{"type":"heatmap","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"contourcarpet":[{"type":"contourcarpet","colorbar":{"outlinewidth":0,"ticks":""}}],"contour":[{"type":"contour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"surface":[{"type":"surface","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"mesh3d":[{"type":"mesh3d","colorbar":{"outlinewidth":0,"ticks":""}}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"parcoords":[{"type":"parcoords","line":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolargl":[{"type":"scatterpolargl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"scattergeo":[{"type":"scattergeo","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolar":[{"type":"scatterpolar","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"scattergl":[{"type":"scattergl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatter3d":[{"type":"scatter3d","line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermap":[{"type":"scattermap","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermapbox":[{"type":"scattermapbox","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterternary":[{"type":"scatterternary","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattercarpet":[{"type":"scattercarpet","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"type":"carpet"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}],"barpolar":[{"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"pie":[{"automargin":true,"type":"pie"}]},"layout":{"autotypenumbers":"strict","colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"hovermode":"closest","hoverlabel":{"align":"left"},"paper_bgcolor":"white","plot_bgcolor":"#E5ECF6","polar":{"bgcolor":"#E5ECF6","angularaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"radialaxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"ternary":{"bgcolor":"#E5ECF6","aaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"baxis":{"gridcolor":"white","linecolor":"white","ticks":""},"caxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]]},"xaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"yaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"scene":{"xaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"yaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"zaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"geo":{"bgcolor":"white","landcolor":"#E5ECF6","subunitcolor":"white","showland":true,"showlakes":true,"lakecolor":"white"},"title":{"x":0.05},"mapbox":{"style":"light"},"margin":{"b":0,"l":0,"r":0,"t":30}}},"title":{"text":"Квартальная динамика"},"xaxis":{"title":{"text":"Квартал"}},"yaxis":{"title":{"text":"Количество"}},"annotations":[{"align":"left","font":{"color":"#666666","size":10},"showarrow":false,"text":"Подавлено ячеек: 10 из 95 (n \u003c 5) — см. Описательный план исследования, §11.","x":0,"xanchor":"left","xref":"paper","y":-0.18,"yanchor":"top","yref":"paper"}]},                        {"responsive": true}                    ).then(function(){
                            &#10;var gd = document.getElementById('f08b9755-0bf8-4b56-a3b7-bd1d706fb810');
var x = new MutationObserver(function (mutations, observer) {{
        var display = window.getComputedStyle(gd).display;
        if (!display || display === 'none') {{
            console.log([gd, 'removed!']);
            Plotly.purge(gd);
            observer.disconnect();
        }}
}});
&#10;// Listen for the removal of the full notebook cells
var notebookContainer = gd.closest('#notebook-container');
if (notebookContainer) {{
    x.observe(notebookContainer, {childList: true});
}}
&#10;// Listen for the clearing of the current output cell
var outputEl = gd.closest('.output');
if (outputEl) {{
    x.observe(outputEl, {childList: true});
}}
&#10;                        })                };            </script>        </div>

## Шаг 10 — Сравнение площадок

Сопоставление (Владимир / Ковров / Муром) всех доль каскада из Шагов 2–8
— только описательное выявление различий, не формальное статистическое
сравнение между площадками.

*Каскад скрининга по площадкам*

| Этап | Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Скрининг пройден | Ковров | 1034 | 975 | 0.94294 | 0.927094 | 0.955508 | Нет |
| Скрининг пройден | Муром | 380 | 377 | 0.992105 | 0.977049 | 0.997312 | Нет |
| Скрининг пройден | Владимир | 6318 | 6268 | 0.992086 | 0.989582 | 0.993992 | Нет |
| Подозрение на ТБ | Ковров | 1034 | 161 | 0.155706 | 0.134885 | 0.179076 | Нет |
| Подозрение на ТБ | Муром | 380 | 87 | 0.228947 | 0.18954 | 0.27378 | Нет |
| Подозрение на ТБ | Владимир | 6318 | 1106 | 0.175055 | 0.165883 | 0.184622 | Нет |
| Диаскинтест положительный | Ковров | 1034 | 138 | 0.133462 | 0.114085 | 0.155553 | Нет |
| Диаскинтест положительный | Муром | 380 | 74 | 0.194737 | 0.158059 | 0.237525 | Нет |
| Диаскинтест положительный | Владимир | 6318 | 606 | 0.0959164 | 0.0888988 | 0.103425 | Нет |
| Полное обследование завершено | Ковров | 1034 | 1034 | 1 | 0.996299 | 1 | Нет |
| Полное обследование завершено | Муром | 380 | 380 | 1 | 0.989992 | 1 | Нет |
| Полное обследование завершено | Владимир | 6318 | 6291 | 0.995726 | 0.993789 | 0.997061 | Нет |

*Диагностические исходы по площадкам*

| Площадка | Категория | Количество | n | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Муром | Нет ТБ, нет ЛТИ | 296 | 380 | 0.778947 | 0.73455 | 0.817761 | Нет |
| Муром | Латентная ТБ-инфекция (ЛТИ) | 77 | 380 | 0.202632 | 0.165286 | 0.24593 | Нет |
| Муром | Нет ТБ, статус ЛТИ неизвестен | 7 | 380 | 0.0184211 | 0.00895118 | 0.0375301 | Нет |
| Ковров | Нет ТБ, статус ЛТИ неизвестен | 76 | 1034 | 0.073501 | 0.0591249 | 0.0910343 | Нет |
| Ковров | Подтверждённый активный ТБ | 4 | 1034 | 0.00386847 | 0.00150537 | 0.00990433 | Нет |
| Ковров | Нет ТБ, нет ЛТИ | 780 | 1034 | 0.754352 | 0.727204 | 0.779617 | Нет |
| Ковров | Латентная ТБ-инфекция (ЛТИ) | 174 | 1034 | 0.168279 | 0.146713 | 0.1923 | Нет |
| Владимир | Нет ТБ, статус ЛТИ неизвестен | 527 | 6291 | 0.0837705 | 0.0771759 | 0.0908731 | Нет |
| Владимир | Подтверждённый активный ТБ | 97 | 6291 | 0.0154189 | 0.0126565 | 0.0187726 | Нет |
| Владимир | Нет ТБ, нет ЛТИ | 5089 | 6291 | 0.808933 | 0.799031 | 0.818459 | Нет |
| Владимир | Латентная ТБ-инфекция (ЛТИ) | 578 | 6291 | 0.0918773 | 0.0849864 | 0.0992663 | Нет |

*Каскад профилактического лечения ЛТИ по площадкам*

| Этап | Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Рекомендовано | Ковров | 321 | 317 | 0.987539 | 0.968403 | 0.995144 | Нет |
| Рекомендовано | Муром | 172 | 172 | 1 | 0.978154 | 1 | Нет |
| Рекомендовано | Владимир | 1217 | 1212 | 0.995892 | 0.990418 | 0.998244 | Нет |
| Назначено | Ковров | 321 | 233 | 0.725857 | 0.674603 | 0.771769 | Нет |
| Назначено | Муром | 172 | 66 | 0.383721 | 0.31434 | 0.458182 | Нет |
| Назначено | Владимир | 1217 | 928 | 0.762531 | 0.737821 | 0.785589 | Нет |
| Начато | Ковров | 321 | 232 | 0.722741 | 0.671357 | 0.768858 | Нет |
| Начато | Муром | 172 | 66 | 0.383721 | 0.31434 | 0.458182 | Нет |
| Начато | Владимир | 1217 | 915 | 0.751849 | 0.726814 | 0.775299 | Нет |

*Задержка начала лечения по площадкам*

| Площадка |   n | Медиана |     Q1 |  Q3 | Подавлено (n\<5) |
|:---------|----:|--------:|-------:|----:|:-----------------|
| Ковров   | 232 |    -104 | -198.5 | -23 | Нет              |
| Муром    |  66 |  -143.5 |   -238 |   0 | Нет              |
| Владимир | 915 |    -104 |   -217 |  -5 | Нет              |

*Начато в целевой срок по площадкам*

| Целевой срок (дни) | Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|---:|:---|---:|---:|---:|---:|---:|:---|
| 30 | Ковров | 50 | 34 | 0.68 | 0.541897 | 0.792418 | Нет |
| 30 | Муром | 18 | 16 | 0.888889 | 0.672002 | 0.96898 | Нет |
| 30 | Владимир | 221 | 174 | 0.78733 | 0.72871 | 0.836132 | Нет |
| 60 | Ковров | 50 | 38 | 0.76 | 0.625873 | 0.857026 | Нет |
| 60 | Муром | 18 | 18 | 1 | 0.824121 | 1 | Нет |
| 60 | Владимир | 221 | 194 | 0.877828 | 0.828083 | 0.914662 | Нет |

*Режим лечения по площадкам*

| Режим | Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Содержит бедаквилин | Ковров | 233 | 30 | 0.128755 | 0.0916987 | 0.177855 | Нет |
| Содержит бедаквилин | Муром | 66 | 8 | 0.121212 | 0.0627185 | 0.221374 | Нет |
| Содержит бедаквилин | Владимир | 915 | 40 | 0.0437158 | 0.0322663 | 0.0589807 | Нет |
| Содержит моксифлоксацин | Ковров | 233 | 34 | 0.145923 | 0.10634 | 0.196991 | Нет |
| Содержит моксифлоксацин | Муром | 66 | 5 | 0.0757576 | 0.032792 | 0.165392 | Нет |
| Содержит моксифлоксацин | Владимир | 915 | 53 | 0.0579235 | 0.0445548 | 0.0749886 | Нет |

*Приверженность лечению по площадкам*

| Площадка |   n | Медиана |       Q1 |  Q3 | Подавлено (n\<5) |
|:---------|----:|--------:|---------:|----:|:-----------------|
| Ковров   | 228 |       1 |        1 |   1 | Нет              |
| Муром    |  64 |       1 |        1 |   1 | Нет              |
| Владимир | 863 |       1 | 0.853571 |   1 | Нет              |

*Достижение порогов дозы по площадкам*

| Порог | Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Достигнут порог 50% | Ковров | 233 | 203 | 0.871245 | 0.822145 | 0.908301 | Нет |
| Достигнут порог 50% | Муром | 66 | 58 | 0.878788 | 0.778626 | 0.937282 | Нет |
| Достигнут порог 50% | Владимир | 915 | 701 | 0.76612 | 0.737615 | 0.7924 | Нет |
| Достигнут порог 100% | Ковров | 233 | 184 | 0.7897 | 0.732888 | 0.837113 | Нет |
| Достигнут порог 100% | Муром | 66 | 54 | 0.818182 | 0.708548 | 0.892814 | Нет |
| Достигнут порог 100% | Владимир | 915 | 592 | 0.646995 | 0.615473 | 0.677287 | Нет |

*Распределение исходов лечения по площадкам*

| Площадка | Категория | Количество | n | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Ковров | Продолжается | 4 | 233 | 0.0171674 | 0.0066958 | 0.0433016 | Нет |
| Ковров | Завершено (100% доз) | 208 | 233 | 0.892704 | 0.846408 | 0.926261 | Нет |
| Ковров | Не завершено | 7 | 233 | 0.0300429 | 0.0146275 | 0.0607033 | Нет |
| Ковров | Остановлено (по мед. показаниям) | 14 | 233 | 0.0600858 | 0.0361257 | 0.0983163 | Нет |
| Владимир | Продолжается | 40 | 915 | 0.0437158 | 0.0322663 | 0.0589807 | Нет |
| Владимир | Завершено (100% доз) | 680 | 915 | 0.743169 | 0.713886 | 0.77042 | Нет |
| Владимир | Не завершено | 114 | 915 | 0.12459 | 0.104748 | 0.147571 | Нет |
| Владимир | Окончено (85–99% доз) | 12 | 915 | 0.0131148 | 0.00751787 | 0.0227827 | Нет |
| Владимир | Остановлено (по мед. показаниям) | 69 | 915 | 0.0754098 | 0.0600197 | 0.0943502 | Нет |
| Муром | Не завершено | 3 | 66 | 0.0454545 | 0.0155783 | 0.125333 | Нет |
| Муром | Окончено (85–99% доз) | 2 | 66 | 0.030303 | 0.00834991 | 0.103925 | Нет |
| Муром | Продолжается | 2 | 66 | 0.030303 | 0.00834991 | 0.103925 | Нет |
| Муром | Завершено (100% доз) | 57 | 66 | 0.863636 | 0.760704 | 0.926567 | Нет |
| Муром | Остановлено (по мед. показаниям) | 2 | 66 | 0.030303 | 0.00834991 | 0.103925 | Нет |

*Получение стимулирующих выплат по площадкам*

| Стимул | Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Скрининг | Ковров | 127 | 104 | 0.818898 | 0.742888 | 0.876182 | Нет |
| Скрининг | Муром | 201 | 144 | 0.716418 | 0.650501 | 0.774218 | Нет |
| Скрининг | Владимир | 4290 | 3902 | 0.909557 | 0.900604 | 0.917777 | Нет |
| Доза 50% | Ковров | 54 | 39 | 0.722222 | 0.591096 | 0.823832 | Нет |
| Доза 50% | Муром | 51 | 50 | 0.980392 | 0.896954 | 0.99653 | Нет |
| Доза 50% | Владимир | 667 | 468 | 0.701649 | 0.665852 | 0.735136 | Нет |
| Доза 100% | Ковров | 54 | 40 | 0.740741 | 0.610691 | 0.838813 | Нет |
| Доза 100% | Муром | 51 | 46 | 0.901961 | 0.790218 | 0.957392 | Нет |
| Доза 100% | Владимир | 667 | 485 | 0.727136 | 0.692104 | 0.759568 | Нет |
| 1 год наблюдения | Ковров | 128 | 31 | 0.242188 | 0.176187 | 0.323211 | Нет |
| 1 год наблюдения | Муром | 201 | 84 | 0.41791 | 0.35189 | 0.48701 | Нет |
| 1 год наблюдения | Владимир | 4302 | 1375 | 0.319619 | 0.30585 | 0.333709 | Нет |

*Задержка выплаты за скрининг по площадкам*

| Площадка |    n | Медиана |  Q1 |    Q3 | Подавлено (n\<5) |
|:---------|-----:|--------:|----:|------:|:-----------------|
| Ковров   |  104 |      14 |   4 |    19 | Нет              |
| Муром    |  144 |      24 |  14 | 38.25 | Нет              |
| Владимир | 3911 |      21 |  12 |    36 | Нет              |

*Повторный скрининг через 1 год по площадкам*

| Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|:---|
| Ковров | 675 | 319 | 0.472593 | 0.435191 | 0.510304 | Нет |
| Муром | 368 | 219 | 0.595109 | 0.544224 | 0.644028 | Нет |
| Владимир | 5802 | 2718 | 0.468459 | 0.455644 | 0.481316 | Нет |

*Нет ТБ через 1 год по площадкам*

| Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|:---|
| Ковров | 453 | 450 | 0.993377 | 0.980712 | 0.997745 | Нет |
| Муром | 276 | 275 | 0.996377 | 0.979766 | 0.99936 | Нет |
| Владимир | 2763 | 2749 | 0.994933 | 0.991512 | 0.996979 | Нет |

*Повторный скрининг через 24 мес. по площадкам*

| Площадка | n | Количество | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|:---|
| Ковров | 547 | 105 | 0.191956 | 0.161145 | 0.227064 | Нет |
| Муром | 319 | 72 | 0.225705 | 0.183251 | 0.274687 | Нет |
| Владимир | 5347 | 7 | 0.00130915 | 0.000634302 | 0.00270003 | Нет |

*Нет ТБ через 24 мес. по площадкам*

| Площадка |   n | Количество |     Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---------|----:|-----------:|---------:|--------------:|---------------:|:-----------------|
| Ковров   | 105 |        104 | 0.990476 |      0.948014 |       0.998317 | Нет              |
| Муром    |  72 |         69 | 0.958333 |      0.884507 |       0.985729 | Нет              |
| Владимир |   7 |          0 |        0 |   2.77556e-17 |        0.35433 | Нет              |

*Распределение итоговых исходов по площадкам*

| Площадка | Категория | Количество | n | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|---:|---:|---:|---:|---:|:---|
| Муром | Неизвестно | 1 | 276 | 0.00362319 | 0.000639868 | 0.0202343 | Нет |
| Муром | Развился ТБ | 1 | 276 | 0.00362319 | 0.000639868 | 0.0202343 | Нет |
| Муром | Другое | 5 | 276 | 0.0181159 | 0.00776225 | 0.0416995 | Нет |
| Муром | ТБ не развился | 269 | 276 | 0.974638 | 0.948583 | 0.987661 | Нет |
| Владимир | Развился ТБ | 14 | 2763 | 0.00506696 | 0.00302072 | 0.00848751 | Нет |
| Владимир | ТБ не развился | 2709 | 2763 | 0.980456 | 0.974588 | 0.98499 | Нет |
| Владимир | Неизвестно | 26 | 2763 | 0.00941006 | 0.00642979 | 0.0137526 | Нет |
| Владимир | Другое | 14 | 2763 | 0.00506696 | 0.00302072 | 0.00848751 | Нет |
| Ковров | Развился ТБ | 3 | 453 | 0.00662252 | 0.00225476 | 0.0192876 | Нет |
| Ковров | ТБ не развился | 318 | 453 | 0.701987 | 0.658312 | 0.742265 | Нет |
| Ковров | Неизвестно | 127 | 453 | 0.280353 | 0.24097 | 0.32343 | Нет |
| Ковров | Другое | 5 | 453 | 0.0110375 | 0.00472353 | 0.0255746 | Нет |

*Итоговый исход по завершённости лечения, по площадкам*

| Площадка | Лечение завершено | Категория | Количество | n | Доля | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|:---|:---|---:|---:|---:|---:|---:|:---|
| Ковров | Да | Неизвестно | 17 | 128 | 0.132812 | 0.0846023 | 0.20242 | Нет |
| Ковров | Да | Другое | 4 | 128 | 0.03125 | 0.0122183 | 0.0775976 | Нет |
| Ковров | Да | ТБ не развился | 107 | 128 | 0.835938 | 0.762182 | 0.890117 | Нет |
| Владимир | Да | Неизвестно | 3 | 345 | 0.00869565 | 0.00296163 | 0.0252502 | Нет |
| Владимир | Да | Развился ТБ | 2 | 345 | 0.0057971 | 0.00159122 | 0.0208874 | Нет |
| Владимир | Да | Другое | 5 | 345 | 0.0144928 | 0.00620591 | 0.0334725 | Нет |
| Владимир | Да | ТБ не развился | 335 | 345 | 0.971014 | 0.947474 | 0.984181 | Нет |
| Муром | Нет | Неизвестно | 1 | 231 | 0.004329 | 0.000764585 | 0.0241095 | Нет |
| Муром | Нет | ТБ не развился | 225 | 231 | 0.974026 | 0.944501 | 0.988043 | Нет |
| Муром | Нет | Развился ТБ | 1 | 231 | 0.004329 | 0.000764585 | 0.0241095 | Нет |
| Муром | Нет | Другое | 4 | 231 | 0.017316 | 0.00675394 | 0.0436693 | Нет |
| Муром | Да | Другое | 1 | 45 | 0.0222222 | 0.0039336 | 0.115667 | Нет |
| Муром | Да | ТБ не развился | 44 | 45 | 0.977778 | 0.884333 | 0.996066 | Нет |
| Ковров | Нет | ТБ не развился | 211 | 325 | 0.649231 | 0.59588 | 0.699095 | Нет |
| Ковров | Нет | Другое | 1 | 325 | 0.00307692 | 0.000543359 | 0.0172204 | Нет |
| Ковров | Нет | Неизвестно | 110 | 325 | 0.338462 | 0.289171 | 0.391526 | Нет |
| Ковров | Нет | Развился ТБ | 3 | 325 | 0.00923077 | 0.00314416 | 0.0267835 | Нет |
| Владимир | Нет | Другое | 9 | 2418 | 0.00372208 | 0.00195945 | 0.00705908 | Нет |
| Владимир | Нет | Развился ТБ | 12 | 2418 | 0.00496278 | 0.00284122 | 0.00865477 | Нет |
| Владимир | Нет | ТБ не развился | 2374 | 2418 | 0.981803 | 0.975661 | 0.986417 | Нет |
| Владимир | Нет | Неизвестно | 23 | 2418 | 0.00951199 | 0.00634672 | 0.0142333 | Нет |

*Частота заболеваемости ТБ по площадкам*

| Площадка | n | События | Человеко-лет | Частота на 100 чел.-лет | 95% ДИ, нижн. | 95% ДИ, верхн. | Подавлено (n\<5) |
|:---|---:|---:|---:|---:|---:|---:|:---|
| Ковров | 229 | 0 | 54.3491 | 0 | 0 | 6.78738 | Нет |
| Муром | 64 | 0 | 25.7084 | 0 | 0 | 14.3489 | Нет |
| Владимир | 910 | 0 | 331.329 | 0 | 0 | 1.11336 | Нет |

## Ограничения

Согласно Описательному плану исследования §10: правоцензурирование
(записи, включённые незадолго до даты анализа, ещё не могут показать
зрелый исход); программные, нерандомизированные данные (различия между
площадками/целевыми группами могут отражать особенности реализации
программы, а не эффект лечения — причинно-следственные выводы не
подразумеваются); структурные (а не связанные с качеством данных)
пропуски для полей, применимых только к определённым целевым группам;
полнота выявления исходов зависит от полноты катамнестического
наблюдения, которая может различаться по площадкам.
