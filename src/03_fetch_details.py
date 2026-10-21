"""
Step 3: For every movie with enough votes, fetch its detail page from TMDB.
Gets the exact US theatrical release date, budget, revenue, runtime,
franchise (collection), production company, and imdb_id (for joining box office later).

Input : data/movies_raw.csv
Output: data/movies_details.csv

Safe to stop and re-run: finished movies are saved every 500 and skipped next time.
Run: open this file in VS Code and press the Run button.
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

from config import DATA_DIR, RAW_MOVIES_CSV, TMDB_API_KEY

MIN_VOTES = 10          # drop obscure titles with almost no TMDB activity
WORKERS = 8             # parallel requests (TMDB allows ~40/sec)
SAVE_EVERY = 500
OUT_CSV = DATA_DIR / "movies_details.csv"

BASE = "https://api.themoviedb.org/3"
session = requests.Session()


def get(path, params=None):
    params = {**(params or {}), "api_key": TMDB_API_KEY}
    for attempt in range(6):
        try:
            r = session.get(BASE + path, params=params, timeout=30)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    return None


def pick_us_release(release_dates):
    """Earliest US wide theatrical date (type 3); fall back to limited (type 2)."""
    us = [c for c in release_dates.get("results", []) if c.get("iso_3166_1") == "US"]
    if not us:
        return None, None, None
    entries = us[0].get("release_dates", [])
    for rtype in (3, 2):
        hits = [e for e in entries if e.get("type") == rtype and e.get("release_date")]
        if hits:
            first = min(hits, key=lambda e: e["release_date"])
            return first["release_date"][:10], rtype, first.get("certification") or None
    return None, None, None


def fetch_one(tmdb_id):
    d = get(f"/movie/{tmdb_id}", {"append_to_response": "release_dates", "language": "en-US"})
    if d is None:
        return {"tmdb_id": tmdb_id, "fetch_ok": False}
    us_date, us_type, cert = pick_us_release(d.get("release_dates", {}))
    collection = d.get("belongs_to_collection") or {}
    companies = d.get("production_companies") or []
    return {
        "tmdb_id": tmdb_id,
        "fetch_ok": True,
        "imdb_id": d.get("imdb_id"),
        "title": d.get("title"),
        "us_theatrical_date": us_date,
        "us_release_type": us_type,           # 3 = wide/theatrical, 2 = limited
        "us_certification": cert,             # G / PG / PG-13 / R
        "genres": "|".join(g["name"] for g in d.get("genres", [])),
        "runtime": d.get("runtime"),
        "budget": d.get("budget") or None,    # 0 in TMDB means unknown
        "revenue": d.get("revenue") or None,  # worldwide, often missing
        "collection_name": collection.get("name"),
        "is_franchise": bool(collection),
        "production_company": companies[0]["name"] if companies else None,
        "original_language": d.get("original_language"),
        "vote_average": d.get("vote_average"),
        "vote_count": d.get("vote_count"),
        "popularity": d.get("popularity"),
    }


def main():
    if not TMDB_API_KEY:
        sys.exit("TMDB_API_KEY not found. Put it in the .env file in the repo root.")
    if not RAW_MOVIES_CSV.exists():
        sys.exit(f"{RAW_MOVIES_CSV} not found. Run 01_fetch_tmdb.py first.")

    raw = pd.read_csv(RAW_MOVIES_CSV)
    ids = raw.loc[raw["vote_count"] >= MIN_VOTES, "tmdb_id"].astype(int).tolist()

    done = pd.read_csv(OUT_CSV) if OUT_CSV.exists() else pd.DataFrame()
    done_ids = set(done["tmdb_id"]) if not done.empty else set()
    todo = [i for i in ids if i not in done_ids]
    print(f"{len(ids)} movies with vote_count >= {MIN_VOTES}; "
          f"{len(done_ids)} already done; {len(todo)} to fetch")

    results = done.to_dict("records") if not done.empty else []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch_one, i) for i in todo]
        for n, fut in enumerate(as_completed(futures), 1):
            results.append(fut.result())
            if n % SAVE_EVERY == 0 or n == len(todo):
                pd.DataFrame(results).to_csv(OUT_CSV, index=False)
                print(f"{n}/{len(todo)} fetched, saved")

    df = pd.DataFrame(results)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(df)} movies to {OUT_CSV}")
    print("With US theatrical date:", df["us_theatrical_date"].notna().sum())
    print("With budget            :", df["budget"].notna().sum())
    print("With revenue           :", df["revenue"].notna().sum())
    print("With imdb_id           :", df["imdb_id"].notna().sum())
    print("Franchise films        :", df["is_franchise"].sum())


if __name__ == "__main__":
    main()
