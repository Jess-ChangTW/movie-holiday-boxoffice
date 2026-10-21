"""
Step 1: Fetch all US theatrical releases (2010-2025) from TMDB.
Output: data/movies_raw.csv

Run: open this file in VS Code and press the Run button.
"""

import sys
import time

import pandas as pd
import requests

from config import END_YEAR, RAW_MOVIES_CSV, START_YEAR, TMDB_API_KEY

BASE = "https://api.themoviedb.org/3"


def get(path, params):
    params = {**params, "api_key": TMDB_API_KEY}
    for attempt in range(5):
        r = requests.get(BASE + path, params=params, timeout=30)
        if r.status_code == 429:  # rate limit, wait and retry
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Failed after retries: {path}")


def main():
    if not TMDB_API_KEY:
        sys.exit("TMDB_API_KEY not found. Put it in the .env file in the repo root.")

    genre_map = {
        g["id"]: g["name"]
        for g in get("/genre/movie/list", {"language": "en-US"})["genres"]
    }

    rows = []
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            start = pd.Timestamp(year=year, month=month, day=1)
            end = start + pd.offsets.MonthEnd(0)
            page = 1
            while True:
                data = get("/discover/movie", {
                    "region": "US",
                    "with_release_type": "3",  # 3 = theatrical
                    "release_date.gte": start.strftime("%Y-%m-%d"),
                    "release_date.lte": end.strftime("%Y-%m-%d"),
                    "sort_by": "popularity.desc",
                    "include_adult": "false",
                    "language": "en-US",
                    "page": page,
                })
                for m in data["results"]:
                    names = [genre_map.get(g, str(g)) for g in m.get("genre_ids", [])]
                    rows.append({
                        "tmdb_id": m["id"],
                        "title": m.get("title"),
                        "original_language": m.get("original_language"),
                        "primary_release_date": m.get("release_date"),
                        "us_release_month": start.strftime("%Y-%m"),
                        "genres": "|".join(names),
                        "main_genre": names[0] if names else None,
                        "popularity": m.get("popularity"),
                        "vote_average": m.get("vote_average"),
                        "vote_count": m.get("vote_count"),
                    })
                if page >= min(data.get("total_pages", 1), 500):
                    break
                page += 1
                time.sleep(0.05)
            print(f"{start:%Y-%m} done, total rows: {len(rows)}")

    df = pd.DataFrame(rows).drop_duplicates(subset="tmdb_id")
    df.to_csv(RAW_MOVIES_CSV, index=False)
    print(f"Saved {len(df)} movies to {RAW_MOVIES_CSV}")


if __name__ == "__main__":
    main()
