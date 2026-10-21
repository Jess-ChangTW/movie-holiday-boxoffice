"""
Step 10: Data quality checks before Layer 3 (box office analysis).

A. Release date: TMDB vs OMDb disagreement, and how many films change holiday-window status
B. Sample size: how many horror / romance films survive at different gross cutoffs
C. Gross skew: share of total box office by gross tier
D. Genre labels: TMDB "Horror" vs IMDb (OMDb) genre, and family/comedy titles tagged horror
E. Gross spot check: top films for manual comparison

Input : data/movies_final.csv, data/omdb_boxoffice.csv
Output: outputs/quality_check.md, outputs/07_date_gap.png
Run: open this file in VS Code and press the Run button.
"""

import sys
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import DATA_DIR, OUTPUT_DIR

FINAL_CSV = DATA_DIR / "movies_final.csv"
OMDB_CSV = DATA_DIR / "omdb_boxoffice.csv"
REPORT_MD = OUTPUT_DIR / "quality_check.md"
WINDOW_DAYS = 28
GROSS_CUTOFFS = [1, 100_000, 1_000_000, 10_000_000]
SOFT_TAGS = ["Family", "Animation", "Comedy"]

INK, MUTED, GRID, BLUE = "#1f2328", "#6e7781", "#e6e8eb", "#2f6fdb"

for f in (FINAL_CSV, OMDB_CSV):
    if not f.exists():
        sys.exit(f"{f} not found. Run step 09 first.")

df = pd.read_csv(FINAL_CSV, parse_dates=["us_date"])
omdb = pd.read_csv(OMDB_CSV).drop_duplicates("imdb_id")
df = df.merge(omdb[["imdb_id", "omdb_genre"]], on="imdb_id", how="left")
TIERS = ["<$1M", "$1-10M", "$10-50M", "$50-100M", "$100M+"]
df["gross_tier"] = pd.Categorical(df["gross_tier"], categories=TIERS, ordered=True)
N = len(df)
sections = []


def md(frame, index=False):
    frame = frame.reset_index() if index else frame
    cols = [str(c) for c in frame.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in frame.itertuples(index=False):
        out.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(out)


def show(title, frame, index=False):
    print(f"\n=== {title} ===")
    print(frame.to_string(index=index))
    sections.append(f"### {title}\n\n{md(frame, index)}")


# ---------- A. release date agreement ----------
df["omdb_date"] = pd.to_datetime(df["omdb_released"], format="%d %b %Y", errors="coerce")
gap = df["date_gap_days"]
has_both = gap.notna()

buckets = pd.cut(gap, [-np.inf, -366, -61, -8, 7, 60, 365, np.inf],
                 labels=["OMDb 1y+ earlier", "OMDb 2-12 mo earlier", "OMDb 1-8 wk earlier",
                         "Within 1 week", "OMDb 1-8 wk later", "OMDb 2-12 mo later", "OMDb 1y+ later"])
gap_tbl = buckets.value_counts().reindex(buckets.cat.categories).rename("films").to_frame()
gap_tbl["%"] = (gap_tbl["films"] / has_both.sum() * 100).round(1)
gap_tbl.loc["OMDb date missing"] = [int((~has_both).sum()), round((~has_both).mean() * 100, 1)]
gap_tbl["films"] = gap_tbl["films"].astype(int)
show("A1. OMDb date minus TMDB US date", gap_tbl, index=True)

by_type = df[has_both].groupby("us_release_type").agg(
    films=("tmdb_id", "count"),
    mismatch_pct=("date_mismatch", lambda s: round(s.mean() * 100, 1)),
    median_gap_days=("date_gap_days", "median"),
)
by_type.index = by_type.index.map({2: "2 = limited (fallback)", 3: "3 = theatrical"})
show("A2. Mismatch rate by TMDB release type", by_type, index=True)

by_tier = df[has_both].groupby("gross_tier", observed=True).agg(
    films=("tmdb_id", "count"),
    mismatch_pct=("date_mismatch", lambda s: round(s.mean() * 100, 1)),
)
show("A3. Mismatch rate by gross tier", by_tier, index=True)

# does the holiday-window flag change if we use the OMDb date?
def in_window(dates, month, day):
    hol = pd.to_datetime(dates.dt.year.astype("Int64").astype(str) + f"-{month:02d}-{day:02d}",
                         errors="coerce")
    return ((hol - dates).dt.days.between(0, WINDOW_DAYS))

flip_rows = []
for name, flag, (m, d), win in [("Horror", "is_horror", (10, 31), "halloween_window"),
                                ("Romance", "is_romance", (2, 14), "valentine_window")]:
    g = df[df[flag] & has_both]
    omdb_win = in_window(g["omdb_date"], m, d)
    flip_rows.append({
        "Genre": name,
        "In window (TMDB date)": int(g[win].sum()),
        "In window (OMDb date)": int(omdb_win.sum()),
        "In both": int((g[win] & omdb_win).sum()),
        "Only TMDB": int((g[win] & ~omdb_win).sum()),
        "Only OMDb": int((~g[win] & omdb_win).sum()),
    })
show("A4. Holiday-window status under each date source", pd.DataFrame(flip_rows))

sample = (df[has_both].assign(abs_gap=gap.abs())
          .nlargest(20, "abs_gap")[["title", "us_date", "omdb_date", "date_gap_days",
                                     "us_release_type", "gross_m"]])
sample["us_date"] = sample["us_date"].dt.date
sample["omdb_date"] = sample["omdb_date"].dt.date
sample["gross_m"] = sample["gross_m"].round(2)
show("A5. 20 largest date gaps (check by eye)", sample)

wide_window = df[has_both & (gap.abs() <= 400)]
fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(wide_window["date_gap_days"], bins=np.arange(-400, 401, 14), color=BLUE)
ax.set_yscale("log")
ax.axvline(0, color=INK, lw=1, ls="--", alpha=0.6)
ax.set_xlabel("OMDb date minus TMDB US date (days, 2-week bins)")
ax.set_ylabel("Films (log scale)")
ax.grid(axis="y", color=GRID)
ax.spines[["top", "right"]].set_visible(False)
ax.set_title("How far apart are the two release dates?", loc="left", fontsize=12)
fig.tight_layout()
chart = OUTPUT_DIR / "07_date_gap.png"
fig.savefig(chart, dpi=150)
plt.close(fig)

# ---------- B. sample size at different gross cutoffs ----------
rows = []
for c in GROSS_CUTOFFS:
    s = df[df["box_office_domestic"] >= c]
    rows.append({
        "Min gross": f"${c:,}",
        "Films": len(s),
        "Horror": int(s["is_horror"].sum()),
        "Horror in Halloween window": int((s["is_horror"] & s["halloween_window"]).sum()),
        "Romance": int(s["is_romance"].sum()),
        "Romance in Valentine window": int((s["is_romance"] & s["valentine_window"]).sum()),
        "With budget": int(s["budget"].notna().sum()),
    })
show("B. Sample size by minimum gross", pd.DataFrame(rows))

# ---------- C. gross concentration ----------
tier = df.groupby("gross_tier", observed=True).agg(
    films=("tmdb_id", "count"), total_gross_m=("gross_m", "sum"))
tier["% of films"] = (tier["films"] / N * 100).round(1)
tier["% of total gross"] = (tier["total_gross_m"] / tier["total_gross_m"].sum() * 100).round(1)
tier["total_gross_m"] = tier["total_gross_m"].round(0)
show("C. Share of films vs share of box office by tier", tier, index=True)

# ---------- D. genre labels ----------
tmdb_h = df["is_horror"]
imdb_h = df["omdb_genre"].fillna("").str.contains("Horror")
agree = pd.DataFrame({
    "Check": ["TMDB Horror", "IMDb Horror", "Both", "TMDB only", "IMDb only",
              "TMDB Horror also tagged Family/Animation/Comedy",
              "Horror strict (TMDB and IMDb, no Family/Animation)"],
    "Films": [int(tmdb_h.sum()), int(imdb_h.sum()), int((tmdb_h & imdb_h).sum()),
              int((tmdb_h & ~imdb_h).sum()), int((~tmdb_h & imdb_h).sum()),
              int((tmdb_h & df["genres"].fillna("").str.contains("|".join(SOFT_TAGS))).sum()),
              int((tmdb_h & imdb_h & ~df["genres"].fillna("").str.contains("Family|Animation")).sum())],
})
show("D1. Horror label agreement (TMDB vs IMDb)", agree)

tmdb_r = df["is_romance"]
imdb_r = df["omdb_genre"].fillna("").str.contains("Romance")
show("D2. Romance label agreement (TMDB vs IMDb)", pd.DataFrame({
    "Check": ["TMDB Romance", "IMDb Romance", "Both", "TMDB only", "IMDb only"],
    "Films": [int(tmdb_r.sum()), int(imdb_r.sum()), int((tmdb_r & imdb_r).sum()),
              int((tmdb_r & ~imdb_r).sum()), int((~tmdb_r & imdb_r).sum())],
}))

soft = (df[tmdb_h & df["genres"].fillna("").str.contains("|".join(SOFT_TAGS))]
        .nlargest(10, "box_office_domestic")[["title", "genres", "omdb_genre", "gross_m"]])
soft["gross_m"] = soft["gross_m"].round(1)
show("D3. Top-grossing 'horror' films also tagged Family/Animation/Comedy", soft)

# ---------- E. gross spot check ----------
top = df.nlargest(15, "box_office_domestic")[["title", "year", "gross_m"]]
top["gross_m"] = top["gross_m"].round(1)
show("E. Top 15 domestic grosses (compare with a trusted source by hand)", top)

# ---------- report ----------
report = f"""# Data Quality Check

Generated {date.today():%B %d, %Y} by `src/10_quality_check.py` on {N:,} films with US box office.

![Date gap](07_date_gap.png)

{chr(10).join(s + chr(10) for s in sections)}
"""
REPORT_MD.write_text(report, encoding="utf-8")
print(f"\nSaved {REPORT_MD}\nSaved {chart}")
