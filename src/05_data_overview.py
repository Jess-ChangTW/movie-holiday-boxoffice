"""
Step 5 (Layer 1): Data scope and data overview report.

1. Data scope + sample funnel (how many movies survive each filter)
2. Sample overview: movies per year, top genres
3. Genre distribution: horror / romance share over time
4. Field quality: missing values in key columns

Input : data/movies_raw.csv, data/movies_details.csv, data/movies_clean.csv
Output: outputs/data_overview.md (the write-up, numbers filled in automatically)
        outputs/01_movies_per_year.png
        outputs/02_genre_share_by_year.png
Run: open this file in VS Code and press the Run button.
"""

import sys
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd

from config import DATA_DIR, END_YEAR, OUTPUT_DIR, RAW_MOVIES_CSV, START_YEAR

DETAILS_CSV = DATA_DIR / "movies_details.csv"
CLEAN_CSV = DATA_DIR / "movies_clean.csv"
REPORT_MD = OUTPUT_DIR / "data_overview.md"
MIN_VOTES = 10       # must match 03_fetch_details.py
WINDOW_DAYS = 28     # must match 04_clean_data.py

INK, MUTED, GRID = "#1f2328", "#6e7781", "#e6e8eb"
BLUE, ORANGE = "#2f6fdb", "#d9730d"

for f in (RAW_MOVIES_CSV, DETAILS_CSV, CLEAN_CSV):
    if not f.exists():
        sys.exit(f"{f} not found. Run steps 01 to 04 first.")

raw = pd.read_csv(RAW_MOVIES_CSV)
details = pd.read_csv(DETAILS_CSV)
df = pd.read_csv(CLEAN_CSV, parse_dates=["us_date"])

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
})


def md_table(frame, index=True):
    """Small markdown table writer (no extra package needed)."""
    frame = frame.reset_index() if index else frame
    cols = [str(c) for c in frame.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in frame.itertuples(index=False):
        cells = [str(v) if col == "year"
                 else f"{v:,}" if isinstance(v, int) and not isinstance(v, bool)
                 else f"{v:.1f}" if isinstance(v, float) else str(v)
                 for col, v in zip(cols, row)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def pct(x, total):
    return f"{x / total * 100:.1f}%"


# ---------- 1. sample funnel ----------
n_raw = len(raw)
n_votes = int((raw["vote_count"] >= MIN_VOTES).sum())
det_ok = details[details["fetch_ok"] == True].copy()
det_ok["d"] = pd.to_datetime(det_ok["us_theatrical_date"], errors="coerce")
n_in_range = int(det_ok["d"].between(f"{START_YEAR}-01-01", f"{END_YEAR}-12-31").sum())
n_clean = len(df)
calendar_set = df[~df["pandemic_year"] & ~df["is_documentary"]]
n_calendar = len(calendar_set)

funnel = pd.DataFrame({
    "Step": [
        "1. TMDB US theatrical releases (raw pull)",
        f"2. At least {MIN_VOTES} TMDB votes",
        f"3. US theatrical date within {START_YEAR}-{END_YEAR}",
        "4. Drop Jan 1 placeholder dates (final dataset)",
        "5. Release-calendar subset (no 2020-21, no documentaries)",
    ],
    "Movies": [f"{n:,}" for n in (n_raw, n_votes, n_in_range, n_clean, n_calendar)],
    "% of raw": [pct(n, n_raw) for n in (n_raw, n_votes, n_in_range, n_clean, n_calendar)],
})

# ---------- 2. sample overview ----------
per_year = df.groupby("year").agg(
    movies=("tmdb_id", "count"),
    horror=("is_horror", "sum"),
    romance=("is_romance", "sum"),
)
per_year["horror_%"] = (per_year["horror"] / per_year["movies"] * 100).round(1)
per_year["romance_%"] = (per_year["romance"] / per_year["movies"] * 100).round(1)

genres_long = df["genres"].fillna("").str.split("|").explode()
genres_long = genres_long[genres_long != ""]
top_genres = genres_long.value_counts().head(12).rename("movies").to_frame()
top_genres["% of films"] = (top_genres["movies"] / n_clean * 100).round(1)
top_genres.index.name = "genre"

multi_genre_share = (df["genres"].fillna("").str.count(r"\|") >= 1).mean() * 100

peak_year = per_year["movies"].idxmax()
peak_n = per_year.loc[peak_year, "movies"]
n_2019 = per_year["movies"].get(2019, 0)
drop_to_2019 = (1 - n_2019 / peak_n) * 100 if peak_n else 0

# Chart 1: movies per year
fig, ax = plt.subplots(figsize=(10, 4))
colors = [MUTED if y in (2020, 2021) else BLUE for y in per_year.index]
ax.bar(per_year.index, per_year["movies"], color=colors, width=0.7)
for y, v in per_year["movies"].items():
    ax.text(y, v + peak_n * 0.01, f"{v:,}", ha="center", va="bottom", fontsize=8, color=MUTED)
ax.set_xticks(per_year.index)
ax.set_xticklabels(per_year.index, rotation=45)
ax.set_ylabel("Movies in dataset")
ax.grid(axis="y", color=GRID)
ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False)
ax.set_title("Movies per year in the final dataset (gray = pandemic years)", loc="left", fontsize=12)
fig.tight_layout()
chart1 = OUTPUT_DIR / "01_movies_per_year.png"
fig.savefig(chart1, dpi=150)
plt.close(fig)

# ---------- 3. genre share over time ----------
fig, ax = plt.subplots(figsize=(10, 4))
for col, name, color in [("horror_%", "Horror", BLUE), ("romance_%", "Romance", ORANGE)]:
    ax.plot(per_year.index, per_year[col], color=color, lw=2, marker="o", ms=4, label=name)
    ax.text(per_year.index[-1] + 0.3, per_year[col].iloc[-1], name,
            va="center", color=INK, fontsize=9)
ax.set_xticks(per_year.index)
ax.set_xticklabels(per_year.index, rotation=45)
ax.set_ylabel("% of movies that year")
ax.set_ylim(bottom=0)
ax.grid(axis="y", color=GRID)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, loc="upper left")
ax.set_title("Horror and romance share of releases by year", loc="left", fontsize=12)
fig.tight_layout()
chart2 = OUTPUT_DIR / "02_genre_share_by_year.png"
fig.savefig(chart2, dpi=150)
plt.close(fig)

# ---------- 4. field quality ----------
key_cols = {
    "us_date": "US theatrical release date",
    "genres": "Genres",
    "imdb_id": "IMDb ID (join key for box office)",
    "us_certification": "MPA rating (G/PG/PG-13/R)",
    "runtime": "Runtime",
    "budget": "Budget",
    "revenue": "Revenue (worldwide)",
    "production_company": "Production company",
}
quality = pd.DataFrame({
    "Field": list(key_cols.values()),
    "Available": [f"{df[c].notna().sum():,}" for c in key_cols],
    "Missing %": [f"{df[c].isna().mean() * 100:.1f}%" for c in key_cols],
})
budget_by_genre = pd.DataFrame({
    "Group": ["All films", "Horror", "Romance", "Franchise films"],
    "Has budget %": [
        f"{df['budget'].notna().mean() * 100:.1f}%",
        f"{df.loc[df['is_horror'], 'budget'].notna().mean() * 100:.1f}%",
        f"{df.loc[df['is_romance'], 'budget'].notna().mean() * 100:.1f}%",
        f"{df.loc[df['is_franchise'] == True, 'budget'].notna().mean() * 100:.1f}%",
    ],
})

# ---------- write the report ----------
n_h, n_r = int(df["is_horror"].sum()), int(df["is_romance"].sum())
n_hw = int((df["is_horror"] & df["halloween_window"]).sum())
n_rw = int((df["is_romance"] & df["valentine_window"]).sum())

report = f"""# Data Overview

Generated {date.today():%B %d, %Y} by `src/05_data_overview.py`.

## 1. Data scope

| Item | Choice |
|---|---|
| Source | TMDB API (The Movie Database, a community-maintained movie database) |
| Market | United States theatrical releases (TMDB release type "Theatrical") |
| Period | US theatrical release date from Jan 1, {START_YEAR} to Dec 31, {END_YEAR} |
| Unit | One row per film; release date = earliest US theatrical date |
| Inclusion rule | At least {MIN_VOTES} TMDB user votes, to remove obscure titles with no activity |
| Exclusion rule | Release dates on Jan 1, which are usually placeholders rather than real dates |
| Genre definition | Multi-label: a film counts as horror if "Horror" appears anywhere in its TMDB genre list (same for romance) |
| Holiday windows | Released 0 to {WINDOW_DAYS} days before Halloween (Oct 31) or Valentine's Day (Feb 14) |
| Release-calendar analyses | Exclude 2020-2021 (pandemic disruption) and documentaries (mostly small limited releases) |

### Sample funnel

{md_table(funnel, index=False)}

## 2. Sample overview

The final dataset has **{n_clean:,} films**, including **{n_h:,} horror** ({pct(n_h, n_clean)}) and **{n_r:,} romance** ({pct(n_r, n_clean)}) titles. {n_hw:,} horror films fall in the Halloween window and {n_rw:,} romance films fall in the Valentine's window. {multi_genre_share:.0f}% of films carry more than one genre tag, which is why genres are treated as multi-label.

![Movies per year](01_movies_per_year.png)

### Movies per year

{md_table(per_year)}

### Most common genres (multi-label, so shares add up to more than 100%)

{md_table(top_genres)}

## 3. Genre distribution over time

![Genre share by year](02_genre_share_by_year.png)

Horror makes up {per_year['horror_%'].min():.1f}% to {per_year['horror_%'].max():.1f}% of films each year; romance ranges from {per_year['romance_%'].min():.1f}% to {per_year['romance_%'].max():.1f}%.

## 4. Field quality

{md_table(quality, index=False)}

Budget coverage by group:

{md_table(budget_by_genre, index=False)}

## 5. Known limitations

1. **TMDB is not a complete list of US theatrical releases.** Film counts peak at {peak_n:,} in {peak_year} and fall {drop_to_2019:.0f}% by 2019, a pre-pandemic year with no comparable drop in the actual number of US releases. This likely reflects how TMDB contributors label release types over time (for example, recent small films released in theaters and on streaming at the same time). Year-over-year comparisons of counts should not be read as industry trends. Analyses here rely on within-year shares, and the box office data added later will define the final film universe.
2. **Genres are community-labeled.** Tagging standards vary between contributors, and the order of genres does not indicate the primary genre.
3. **Budget and revenue are incomplete.** Budget is missing for {df['budget'].isna().mean() * 100:.0f}% of films, and revenue is worldwide rather than US. ROI analysis will use a smaller subsample; US box office will come from Box Office Mojo.
4. **"Theatrical" does not mean wide release.** TMDB's theatrical tag includes small releases. Wide release (600+ theaters) will be defined from box office data.
5. **Release dates are chosen by studios.** Any holiday-window differences are correlational, not causal.
"""

REPORT_MD.write_text(report, encoding="utf-8")

print(f"Saved {REPORT_MD}")
print(f"Saved {chart1}")
print(f"Saved {chart2}")
print("\nSample funnel:")
print(funnel.to_string(index=False))
print("\nField quality:")
print(quality.to_string(index=False))
