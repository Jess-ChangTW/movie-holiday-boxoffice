"""
Step 2: Quick sanity check of data/movies_raw.csv.
Prints row counts by year, genre distribution, vote_count stats,
and how many movies sit on January 1 (likely placeholder dates).

Run: open this file in VS Code and press the Run button.
"""

import sys

import pandas as pd

from config import RAW_MOVIES_CSV

if not RAW_MOVIES_CSV.exists():
    sys.exit(f"{RAW_MOVIES_CSV} not found. Run 01_fetch_tmdb.py first.")

df = pd.read_csv(RAW_MOVIES_CSV)

print("Shape:", df.shape)

print("\nMovies per year:")
print(df["us_release_month"].str[:4].value_counts().sort_index().to_string())

print("\nMovies per month (all years combined):")
print(df["us_release_month"].str[5:7].value_counts().sort_index().to_string())

print("\nTop 12 main genres:")
print(df["main_genre"].value_counts().head(12).to_string())

print("\nHorror / Romance anywhere in genres:")
print("Horror :", df["genres"].fillna("").str.contains("Horror").sum())
print("Romance:", df["genres"].fillna("").str.contains("Romance").sum())

print("\nvote_count summary:")
print(df["vote_count"].describe().round(1).to_string())

for threshold in [10, 50, 100]:
    print(f"Movies with vote_count >= {threshold}: {(df['vote_count'] >= threshold).sum()}")

jan1 = df["primary_release_date"].astype(str).str.endswith("-01-01").sum()
print(f"\nMovies with primary_release_date on Jan 1: {jan1}")
