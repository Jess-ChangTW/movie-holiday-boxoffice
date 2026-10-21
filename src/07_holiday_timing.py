"""
Step 7 (Layer 2, analysis direction 1): Holiday timing in detail.

1. How many days before the holiday do studios release horror / romance films?
2. Has holiday-window concentration changed over the years?
3. How crowded is the holiday window (same-genre competition)?
4. Is the holiday-window share significantly higher than the rest of the year? (two-proportion z-test)

Note: this is about release COUNTS (studio scheduling), not box office.

Input : data/movies_clean.csv
Output: outputs/05_days_to_holiday.png, outputs/06_window_share_trend.png,
        outputs/holiday_timing.md
Run: open this file in VS Code and press the Run button.
"""

import math
import sys
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import DATA_DIR, OUTPUT_DIR

IN_CSV = DATA_DIR / "movies_clean.csv"
REPORT_MD = OUTPUT_DIR / "holiday_timing.md"
WINDOW_DAYS = 28          # must match 04_clean_data.py
RANGE_DAYS = 63           # plot +/- 9 weeks around the holiday
BIN_DAYS = 7

INK, MUTED, GRID = "#1f2328", "#6e7781", "#e6e8eb"
BLUE, GRAY = "#2f6fdb", "#9aa4ae"

if not IN_CSV.exists():
    sys.exit(f"{IN_CSV} not found. Run 04_clean_data.py first.")

df = pd.read_csv(IN_CSV, parse_dates=["us_date"])
df = df[~df["is_documentary"]].copy()          # same rule as the release calendar
normal = df[~df["pandemic_year"]].copy()        # pandemic years excluded except in the trend chart

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
})


def days_from_nearest(dates, month, day):
    """Days from the nearest occurrence of a holiday (negative = before the holiday)."""
    out = []
    for d in dates:
        cands = [pd.Timestamp(year=d.year + k, month=month, day=day) for k in (-1, 0, 1)]
        diffs = [(d - c).days for c in cands]
        out.append(min(diffs, key=abs))
    return np.array(out)


def two_prop_ztest(x1, n1, x2, n2):
    """Two-sided z-test for p1 vs p2. Returns z and p-value."""
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se else float("nan")
    pval = math.erfc(abs(z) / math.sqrt(2))
    return z, pval


df["rel_halloween"] = days_from_nearest(df["us_date"], 10, 31)
df["rel_valentine"] = days_from_nearest(df["us_date"], 2, 14)
normal = df[~df["pandemic_year"]]

cases = [
    # name, genre flag, holiday label, relative-day column, window flag
    ("Horror", "is_horror", "Halloween", "rel_halloween", "halloween_window"),
    ("Romance", "is_romance", "Valentine's Day", "rel_valentine", "valentine_window"),
]

# ---------- 1. days relative to the holiday ----------
bins = np.arange(-RANGE_DAYS, RANGE_DAYS + BIN_DAYS, BIN_DAYS)
centers = bins[:-1] + BIN_DAYS / 2
fig, axes = plt.subplots(2, 1, figsize=(11, 7))
timing_rows = []
for ax, (name, flag, hol, rel, _) in zip(axes, cases):
    near = normal[normal[rel].between(-RANGE_DAYS, RANGE_DAYS - 1)]
    g = near[near[flag]][rel]
    o = near[~near[flag]][rel]
    g_pct = np.histogram(g, bins)[0] / len(normal[normal[flag]]) * 100
    o_pct = np.histogram(o, bins)[0] / len(normal[~normal[flag]]) * 100
    w = BIN_DAYS * 0.4
    ax.bar(centers - w / 2, g_pct, width=w, color=BLUE, label=f"{name} films")
    ax.bar(centers + w / 2, o_pct, width=w, color=GRAY, label="All other films")
    ax.axvline(0, color=INK, lw=1, ls="--", alpha=0.6)
    ax.text(1, 1.01, hol, va="bottom", color=INK, fontsize=9, transform=ax.get_xaxis_transform())
    ax.set_ylabel(f"% of each group's films")
    ax.grid(axis="y", color=GRID)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    before = normal[normal[flag] & normal[rel].between(-RANGE_DAYS, -1)][rel]
    timing_rows.append({
        "Genre": name,
        "Holiday": hol,
        f"Films released 1-{RANGE_DAYS} days before": len(before),
        "Median days before": int(-before.median()) if len(before) else None,
        "Most common week before": (f"{int(((-before - 1) // 7).mode().iloc[0]) + 1}"
                                    if len(before) else None),
    })
axes[-1].set_xlabel("Days from holiday (negative = released before)")
axes[0].set_title("How close to the holiday are films released? (7-day bins, 2010-2025 excl. 2020-21)",
                  loc="left", fontsize=12, pad=18)
fig.tight_layout()
chart1 = OUTPUT_DIR / "05_days_to_holiday.png"
fig.savefig(chart1, dpi=150)
plt.close(fig)
timing = pd.DataFrame(timing_rows)

# ---------- 2. window concentration over the years ----------
uniform_pct = (WINDOW_DAYS + 1) / 365 * 100   # share expected if releases were spread evenly
trend = pd.DataFrame({
    name: df[df[flag]].groupby("year")[win].mean() * 100
    for name, flag, _, _, win in cases
}).round(1)

fig, ax = plt.subplots(figsize=(11, 4))
for (name, *_), color in zip(cases, [BLUE, "#d9730d"]):
    ax.plot(trend.index, trend[name], color=color, lw=2, marker="o", ms=4, label=name)
    ax.text(trend.index[-1] + 0.3, trend[name].iloc[-1], name, va="center", fontsize=9)
ax.axhline(uniform_pct, color=MUTED, lw=1, ls=":")
ax.text(trend.index[0], uniform_pct + 0.5, f"even spread = {uniform_pct:.1f}%", color=MUTED, fontsize=9)
ax.axvspan(2019.5, 2021.5, color=GRID, alpha=0.6, lw=0)
ax.text(2020.5, 0.03, "pandemic", ha="center", va="bottom", color=MUTED, fontsize=9,
        transform=ax.get_xaxis_transform())
ax.set_xticks(trend.index)
ax.set_xticklabels(trend.index, rotation=45)
ax.set_ylabel("% of genre's films in holiday window")
ax.set_ylim(bottom=0)
ax.grid(axis="y", color=GRID)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, loc="upper left")
ax.set_title(f"Share of horror released in the Halloween window, and romance in the Valentine's window "
             f"({WINDOW_DAYS} days before)", loc="left", fontsize=11)
fig.tight_layout()
chart2 = OUTPUT_DIR / "06_window_share_trend.png"
fig.savefig(chart2, dpi=150)
plt.close(fig)

# ---------- 3. competition inside the window ----------
weeks_in_window = (WINDOW_DAYS + 1) / 7
weeks_outside = 52 - weeks_in_window
comp_rows = []
for name, flag, hol, _, win in cases:
    per_year_in = normal[normal[flag] & normal[win]].groupby("year").size()
    per_year_out = normal[normal[flag] & ~normal[win]].groupby("year").size()
    comp_rows.append({
        "Genre": name,
        "Holiday window": hol,
        "Avg films in window per year": round(per_year_in.mean(), 1),
        "Avg per week, in window": round(per_year_in.mean() / weeks_in_window, 1),
        "Avg per week, rest of year": round(per_year_out.mean() / weeks_outside, 1),
        "Busiest year": f"{per_year_in.idxmax()} ({per_year_in.max()})",
    })
competition = pd.DataFrame(comp_rows)

# ---------- 4. significance test ----------
test_rows = []
for name, flag, hol, _, win in cases:
    inside = normal[normal[win]]
    outside = normal[~normal[win]]
    x1, n1 = int(inside[flag].sum()), len(inside)
    x2, n2 = int(outside[flag].sum()), len(outside)
    z, p = two_prop_ztest(x1, n1, x2, n2)
    test_rows.append({
        "Test": f"{name} share: {hol} window vs rest of year",
        "In window": f"{x1}/{n1} = {x1 / n1 * 100:.1f}%",
        "Rest of year": f"{x2}/{n2} = {x2 / n2 * 100:.1f}%",
        "Difference (pts)": f"{(x1 / n1 - x2 / n2) * 100:+.1f}",
        "z": f"{z:.2f}",
        "p-value": f"{p:.4f}" if p >= 0.0001 else "<0.0001",
    })
tests = pd.DataFrame(test_rows)


# ---------- report ----------
def md_table(frame):
    cols = [str(c) for c in frame.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in frame.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


trend_tbl = trend.reset_index().rename(columns={"year": "Year",
                                                 "Horror": "Horror in Halloween window %",
                                                 "Romance": "Romance in Valentine window %"})

report = f"""# Holiday Timing

Generated {date.today():%B %d, %Y} by `src/07_holiday_timing.py`.

Scope: {len(normal):,} films (2010-2025 excluding 2020-2021 and documentaries). The trend table includes all years.
These results describe **release counts (studio scheduling)**, not box office performance.

## 1. How close to the holiday are films released?

![Days to holiday](05_days_to_holiday.png)

{md_table(timing)}

## 2. Has holiday-window concentration changed over time?

If releases were spread evenly across the year, about {uniform_pct:.1f}% of any genre would land in a {WINDOW_DAYS}-day window.

![Window share trend](06_window_share_trend.png)

{md_table(trend_tbl)}

## 3. Competition inside the window

{md_table(competition)}

## 4. Is the holiday-window share significantly higher?

Two-proportion z-test comparing the genre's share of all releases inside the window vs the rest of the year.

{md_table(tests)}

Caveat: the test treats each film as independent. Films cluster by studio strategy and year, so p-values are approximate.
"""
REPORT_MD.write_text(report, encoding="utf-8")

print(f"Saved {chart1}\nSaved {chart2}\nSaved {REPORT_MD}\n")
print("1. Timing\n" + timing.to_string(index=False))
print("\n2. Window share by year (%)\n" + trend.to_string())
print("\n3. Competition\n" + competition.to_string(index=False))
print("\n4. Significance test\n" + tests.to_string(index=False))
