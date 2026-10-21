"""
Step 4: Clean the detail data and add analysis columns.

Input : data/movies_details.csv
Output: data/movies_clean.csv

Adds: release year/month/week, genre flags (horror, romance, documentary),
days to Halloween / Valentine's Day, and holiday-window flags.
Run: open this file in VS Code and press the Run button.
"""

import sys

import pandas as pd

from config import DATA_DIR, END_YEAR, START_YEAR

IN_CSV = DATA_DIR / "movies_details.csv"
OUT_CSV = DATA_DIR / "movies_clean.csv"
WINDOW_DAYS = 28  # holiday window = released 0 to 28 days before the holiday

if not IN_CSV.exists():
    sys.exit(f"{IN_CSV} not found. Run 03_fetch_details.py first.")

df = pd.read_csv(IN_CSV)
n0 = len(df)

# 1. keep movies we could fetch and that have a US theatrical date in range
df = df[df["fetch_ok"] == True].copy()
df["us_date"] = pd.to_datetime(df["us_theatrical_date"], errors="coerce")
df = df[df["us_date"].between(f"{START_YEAR}-01-01", f"{END_YEAR}-12-31")]
n1 = len(df)

# 2. drop Jan 1 dates (usually placeholders, not real releases)
jan1 = (df["us_date"].dt.month == 1) & (df["us_date"].dt.day == 1)
df = df[~jan1]
n2 = len(df)

# 3. date features
df["year"] = df["us_date"].dt.year
df["month"] = df["us_date"].dt.month
df["week"] = df["us_date"].dt.isocalendar().week.astype(int).clip(upper=52)
df["weekday"] = df["us_date"].dt.day_name()
df["pandemic_year"] = df["year"].isin([2020, 2021])

# 4. genre flags (use "contains", not main genre; see README caveat)
g = df["genres"].fillna("")
df["is_horror"] = g.str.contains("Horror")
df["is_romance"] = g.str.contains("Romance")
df["is_documentary"] = g.str.contains("Documentary")

# 5. holiday distance and windows
halloween = pd.to_datetime(df["year"].astype(str) + "-10-31")
valentine = pd.to_datetime(df["year"].astype(str) + "-02-14")
df["days_to_halloween"] = (halloween - df["us_date"]).dt.days
df["days_to_valentine"] = (valentine - df["us_date"]).dt.days
df["halloween_window"] = df["days_to_halloween"].between(0, WINDOW_DAYS)
df["valentine_window"] = df["days_to_valentine"].between(0, WINDOW_DAYS)

# 6. other helpers
df["wide_release"] = df["us_release_type"] == 3
df["has_budget"] = df["budget"].notna()

df = df.drop(columns=["fetch_ok", "us_theatrical_date"]).sort_values("us_date")
df.to_csv(OUT_CSV, index=False)

print(f"Start                          : {n0}")
print(f"With US date in {START_YEAR}-{END_YEAR}        : {n1}")
print(f"After dropping Jan 1 dates     : {n2}")
print(f"\nSaved {len(df)} movies to {OUT_CSV}\n")
print("Wide releases (type 3) :", df["wide_release"].sum())
print("Horror                 :", df["is_horror"].sum())
print("Romance                :", df["is_romance"].sum())
print("Documentary            :", df["is_documentary"].sum())
print("Horror in Halloween window   :", (df["is_horror"] & df["halloween_window"]).sum())
print("Romance in Valentine window  :", (df["is_romance"] & df["valentine_window"]).sum())
print("\nMovies per year:")
print(df["year"].value_counts().sort_index().to_string())
