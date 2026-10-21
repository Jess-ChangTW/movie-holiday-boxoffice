"""
Step 9: Merge OMDb box office into the clean dataset, define the final film universe,
and add the data-quality flags decided in step 10.

Final universe = films with a recorded US domestic box office.

Rules (see outputs/quality_check.md for the evidence):
1. is_rerelease : OMDb original date is more than 1 year before the TMDB US date
                  (old films re-released in theaters, e.g. Studio Ghibli re-runs)
2. main_sample  : gross >= $1M and not a re-release (main Layer 3 analysis)
3. horror_strict / romance_strict : genre tagged by BOTH TMDB and IMDb
4. date_agree   : TMDB and OMDb dates within 7 days (used for robustness checks)
5. Release date : TMDB US date is used everywhere; box office analyzed in logs / medians

Input : data/movies_clean.csv, data/omdb_boxoffice.csv
Output: data/movies_final.csv
Run: open this file in VS Code and press the Run button.
"""

import sys

import numpy as np
import pandas as pd

from config import DATA_DIR

CLEAN_CSV = DATA_DIR / "movies_clean.csv"
OMDB_CSV = DATA_DIR / "omdb_boxoffice.csv"
OUT_CSV = DATA_DIR / "movies_final.csv"
MIN_GROSS = 1                 # final universe: any positive gross
MAIN_MIN_GROSS = 1_000_000    # main analysis sample
RERELEASE_DAYS = 365
DATE_AGREE_DAYS = 7
DATE_GAP_FLAG_DAYS = 60

for f in (CLEAN_CSV, OMDB_CSV):
    if not f.exists():
        sys.exit(f"{f} not found. Run steps 04 and 08 first.")

clean = pd.read_csv(CLEAN_CSV, parse_dates=["us_date"])
omdb = pd.read_csv(OMDB_CSV).drop_duplicates(subset="imdb_id")

keep = ["imdb_id", "box_office_domestic", "omdb_released", "omdb_rated", "omdb_genre",
        "imdb_rating", "imdb_votes", "metascore"]
df = clean.merge(omdb[keep], on="imdb_id", how="left")
n_clean = len(df)
n_matched = df["box_office_domestic"].notna().sum()

# final universe: films with US box office
df = df[df["box_office_domestic"] >= MIN_GROSS].copy()

# box office columns
df["log_gross"] = np.log(df["box_office_domestic"])
df["gross_m"] = df["box_office_domestic"] / 1e6
df["roi"] = np.where(df["budget"] > 0, df["box_office_domestic"] / df["budget"], np.nan)
df["gross_tier"] = pd.cut(
    df["box_office_domestic"],
    bins=[0, 1e6, 10e6, 50e6, 100e6, np.inf],
    labels=["<$1M", "$1-10M", "$10-50M", "$50-100M", "$100M+"],
)

# release date agreement
df["omdb_date"] = pd.to_datetime(df["omdb_released"], format="%d %b %Y", errors="coerce")
df["date_gap_days"] = (df["omdb_date"] - df["us_date"]).dt.days
df["date_mismatch"] = df["date_gap_days"].abs() > DATE_GAP_FLAG_DAYS
df["date_agree"] = df["date_gap_days"].abs() <= DATE_AGREE_DAYS
df["is_rerelease"] = df["date_gap_days"] < -RERELEASE_DAYS

# strict genres: both TMDB and IMDb agree
imdb_genre = df["omdb_genre"].fillna("")
df["horror_strict"] = df["is_horror"] & imdb_genre.str.contains("Horror")
df["romance_strict"] = df["is_romance"] & imdb_genre.str.contains("Romance")

# main analysis sample
df["main_sample"] = (df["box_office_domestic"] >= MAIN_MIN_GROSS) & ~df["is_rerelease"]

df = df.sort_values("us_date")
df.to_csv(OUT_CSV, index=False)

# ---------- summary ----------
m = df[df["main_sample"]]
print(f"Clean dataset            : {n_clean:,}")
print(f"Matched with box office  : {n_matched:,} ({n_matched / n_clean:.0%})")
print(f"Final universe (gross>0) : {len(df):,}")
print(f"Re-releases flagged      : {int(df['is_rerelease'].sum()):,}")
print(f"Main sample (>= $1M, no re-releases): {len(m):,}")
print(f"\nSaved {OUT_CSV}\n")

rows = []
for label, s in [("Final universe", df), ("Main sample", m)]:
    rows.append({
        "Sample": label,
        "Films": len(s),
        "Horror (strict)": int(s["horror_strict"].sum()),
        "Horror strict in Halloween window": int((s["horror_strict"] & s["halloween_window"]).sum()),
        "Romance (strict)": int(s["romance_strict"].sum()),
        "Romance strict in Valentine window": int((s["romance_strict"] & s["valentine_window"]).sum()),
        "With budget": int(s["budget"].notna().sum()),
        "Dates agree (<=7d)": f"{s['date_agree'].mean():.0%}",
    })
print(pd.DataFrame(rows).set_index("Sample").T.to_string())

print("\nMain sample films per year:")
print(m["year"].value_counts().sort_index().to_string())

print("\nRe-release examples (excluded from main sample):")
ex = df[df["is_rerelease"]].nlargest(8, "box_office_domestic")
print(ex[["title", "us_date", "omdb_date", "gross_m"]]
      .assign(us_date=ex["us_date"].dt.date, omdb_date=ex["omdb_date"].dt.date)
      .round(2).to_string(index=False))

print("\nSanity check: top 10 strict-horror films in the Halloween window (main sample)")
top = m[m["horror_strict"] & m["halloween_window"]].nlargest(10, "box_office_domestic")
print(top[["title", "us_date", "gross_m"]].assign(us_date=top["us_date"].dt.date)
      .round(1).to_string(index=False))
