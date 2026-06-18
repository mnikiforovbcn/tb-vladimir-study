"""One-off smoke test for Phase 5 item 3 (funnel_chart) -- NOT a project
deliverable, delete this file after running it. Run from the project
root with:

    uv run python _smoke_test_funnel_chart.py

Builds a tiny synthetic analysis-ready table, runs it through the real
cascade.step2_screening_cascade, and checks funnel_chart(...) against
that real output -- including the all-suppressed-stage edge case and a
deliberately malformed input (wrong row count) to confirm the guard
rails raise instead of silently misplotting.
"""

from __future__ import annotations

import sys

import pandas as pd

results: list[str] = []
ok = True


def check(label: str, condition: bool, detail: str = "") -> None:
    global ok
    status = "OK" if condition else "FAILED"
    if not condition:
        ok = False
    suffix = f" -- {detail}" if detail else ""
    results.append(f"  {label}: {status}{suffix}")


from tb_cascade import cascade  # noqa: E402
from tb_cascade.viz import funnel_chart  # noqa: E402

# 8 synthetic rows: enough to exercise every Step 2 flag without
# tripping small-cell suppression (threshold = 5) on any stage.
# connect()/_with_calendar_dims unconditionally needs the three raw
# date columns (even though step2 itself never groups by a calendar
# dimension here), so they're included as plain datetimes.
df = pd.DataFrame(
    {
        "DateScreening": pd.to_datetime(["2022-01-01"] * 8),
        "DatePrevTreatmentStart": pd.to_datetime(["2022-02-01"] * 8),
        "DateOutcome": pd.to_datetime(["2022-06-01"] * 8),
        "reached_screening": [True] * 8,
        "reached_suspected": [True, True, True, True, True, True, False, False],
        "diaskintest_positive": [True, True, True, True, True, False, pd.NA, pd.NA],
        "reached_full_eval": [True, True, True, True, False, pd.NA, pd.NA, pd.NA],
    }
)

cascade_df = cascade.step2_screening_cascade(df)
print("Real step2_screening_cascade output:")
print(cascade_df.to_string(index=False))
print()

fig = funnel_chart(cascade_df)
check("funnel_chart returns a Figure", fig.__class__.__name__ == "Figure")
check("funnel has 4 stages plotted", len(fig.data[0].y) == 4, str(list(fig.data[0].y)))
check(
    "stage order matches cascade._STEP2_STAGES",
    list(fig.data[0].y) == ["Screened", "Suspected TB", "Diaskintest positive", "Fully evaluated"],
    str(list(fig.data[0].y)),
)
check("exactly one caption annotation", len(fig.layout.annotations) == 1)
check(
    "pct (0-1 fraction) formatted as percent, not raw fraction",
    fig.data[0].texttemplate == "%{x:.1%}" and fig.layout.xaxis.tickformat == ".0%",
    f"texttemplate={fig.data[0].texttemplate!r} tickformat={fig.layout.xaxis.tickformat!r}",
)
caption = fig.layout.annotations[0].text
check("caption reports zero suppressed", "No cells suppressed" in caption, caption)

# Edge case: force one stage suppressed (n < 5) and re-check the funnel
# drops it from the geometry but still reports it in the caption.
suppressed_df = cascade_df.copy()
suppressed_df.loc[suppressed_df["stage"] == "full_eval", "n"] = 2
suppressed_df = cascade.suppress_small_cells(
    suppressed_df, value_cols=["count", "pct", "ci_low", "ci_high"]
)
fig2 = funnel_chart(suppressed_df)
check(
    "suppressed stage dropped from funnel geometry",
    len(fig2.data[0].y) == 3,
    str(list(fig2.data[0].y)),
)
caption2 = fig2.layout.annotations[0].text
check("caption reports 1 of 4 suppressed", caption2 == "1 of 4 cells suppressed (n < 5) per Descriptive Study Plan Sec 11.", caption2)

# Edge case: deliberately malformed input (wrong row count) must raise,
# not silently render a broken funnel.
try:
    funnel_chart(cascade_df.head(2))
    check("malformed input (wrong row count) raises ValueError", False, "no exception raised")
except ValueError as exc:
    check("malformed input (wrong row count) raises ValueError", True, str(exc))

print("\n".join(results))
print("\n" + ("ALL CHECKS PASSED" if ok else "ONE OR MORE CHECKS FAILED"))
sys.exit(0 if ok else 1)
