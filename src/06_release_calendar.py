"""
Step 6 (Layer 2, analysis direction 1): How do studios schedule releases?

Chart 1: genre x week-of-year heatmap (each row = that genre's share of releases per week)
Chart 2: horror share of releases by week, and romance share by week, with holiday markers

Input : data/movies_clean.csv
Output: outputs/03_genre_week_heatmap.png, outputs/04_holiday_genre_share.png
Run: open this file in VS Code and press the Run button.
"""

import sys

import matplotlib.pyplot as plt
import pandas as pd

from config import DATA_DIR, OUTPUT_DIR

IN_CSV = DATA_DIR / "movies_clean.csv"
TOP_GENRES = 12
HALLOWEEN_WEEK = 44   # Oct 31 falls in ISO week 43 or 44
VALENTINE_WEEK = 7    # Feb 14 falls in ISO week 6 or 7
EXCLUDE_PANDEMIC = True
EXCLUDE_DOCUMENTARY = True

INK = "#1f2328"
MUTED = "#6e7781"
GRID = "#e6e8eb"
SERIES = "#2f6fdb"

if not IN_CSV.exists():
    sys.exit(f"{IN_CSV} not found. Run 04_clean_data.py first.")

df = pd.read_csv(IN_CSV, parse_dates=["us_date"])
if EXCLUDE_PANDEMIC:
    df = df[~df["pandemic_year"]]
if EXCLUDE_DOCUMENTARY:
    df = df[~df["is_documentary"]]
print(f"Movies used: {len(df)}")

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
})

# ---------- Chart 1: genre x week heatmap ----------
long = df.assign(genre=df["genres"].str.split("|")).explode("genre").reset_index(drop=True)
long = long[long["genre"].notna() & (long["genre"] != "")]
top = long["genre"].value_counts().head(TOP_GENRES).index
long = long[long["genre"].isin(top)]

counts = pd.crosstab(long["genre"], long["week"]).reindex(columns=range(1, 53), fill_value=0)
share = counts.div(counts.sum(axis=1), axis=0) * 100   # % of that genre's releases
share = share.loc[top]                                 # most common genre on top

fig, ax = plt.subplots(figsize=(14, 6))
im = ax.imshow(share.values, aspect="auto", cmap="Blues", interpolation="nearest")
ax.set_yticks(range(len(share.index)))
ax.set_yticklabels([f"{g} (n={counts.loc[g].sum()})" for g in share.index])
ax.set_xticks(range(0, 52, 4))
ax.set_xticklabels(range(1, 53, 4))
ax.set_xlabel("Week of year")
for wk, label in [(VALENTINE_WEEK, "Valentine's"), (HALLOWEEN_WEEK, "Halloween")]:
    ax.axvline(wk - 1, color=INK, lw=1, ls="--", alpha=0.6)
    ax.text(wk - 1, -0.8, label, ha="center", va="bottom", color=INK, fontsize=9)
cbar = fig.colorbar(im, ax=ax, pad=0.01)
cbar.set_label("% of genre's releases in that week")
cbar.outline.set_visible(False)
ax.set_title("When does each genre get released? (US theatrical, 2010-2025)",
             loc="left", pad=22, fontsize=12)
fig.tight_layout()
out1 = OUTPUT_DIR / "03_genre_week_heatmap.png"
fig.savefig(out1, dpi=150)
print(f"Saved {out1}")

# ---------- Chart 2: horror / romance share by week ----------
weekly = df.groupby("week").agg(
    total=("tmdb_id", "count"),
    horror=("is_horror", "sum"),
    romance=("is_romance", "sum"),
).reindex(range(1, 53), fill_value=0)
weekly["horror_pct"] = weekly["horror"] / weekly["total"].replace(0, pd.NA) * 100
weekly["romance_pct"] = weekly["romance"] / weekly["total"].replace(0, pd.NA) * 100

fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
panels = [
    (axes[0], "horror_pct", "Horror", HALLOWEEN_WEEK, "Halloween"),
    (axes[1], "romance_pct", "Romance", VALENTINE_WEEK, "Valentine's"),
]
for ax, col, name, wk, label in panels:
    avg = weekly[col].mean()
    ax.plot(weekly.index, weekly[col], color=SERIES, lw=2, marker="o", ms=3)
    ax.axhline(avg, color=MUTED, lw=1, ls=":")
    ax.text(52.5, avg, f"avg {avg:.1f}%", va="center", color=MUTED, fontsize=9)
    ax.axvline(wk, color=INK, lw=1, ls="--", alpha=0.6)
    ax.text(wk + 0.4, ax.get_ylim()[1] * 0.95, label, va="top", color=INK, fontsize=9)
    ax.set_ylabel(f"{name} % of releases")
    ax.grid(axis="y", color=GRID)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(bottom=0)
axes[1].set_xlabel("Week of year")
axes[1].set_xticks(range(1, 53, 4))
axes[0].set_title("Share of releases by week: horror peaks near Halloween? romance near Valentine's?",
                  loc="left", fontsize=12)
fig.tight_layout()
out2 = OUTPUT_DIR / "04_holiday_genre_share.png"
fig.savefig(out2, dpi=150)
print(f"Saved {out2}")

# ---------- quick numbers for the write-up ----------
print("\nTop 5 weeks by horror share:")
print(weekly.sort_values("horror_pct", ascending=False)[["total", "horror", "horror_pct"]]
      .head(5).round(1).to_string())
print("\nTop 5 weeks by romance share:")
print(weekly.sort_values("romance_pct", ascending=False)[["total", "romance", "romance_pct"]]
      .head(5).round(1).to_string())

plt.show()
