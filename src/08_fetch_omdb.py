"""
Step 8: Fetch US domestic box office (total gross) from the OMDb API by imdb_id.

- Free OMDb keys have a daily request limit, so this script stops at DAILY_LIMIT
  and remembers progress. Run it once a day until "Remaining: 0".
- Most popular films are fetched first, so early runs already cover most of the box office.
- OMDb content is licensed CC BY-NC 4.0 (non-commercial use, with attribution).

Setup: add a line OMDB_API_KEY=your_key to the .env file in the repo root.
Run TEST_MODE = True first (3 films, prints the full response), then set it to False.

Input : data/movies_clean.csv
Output: data/omdb_boxoffice.csv
"""

import os
import sys
import time

import pandas as pd
import requests

from config import DATA_DIR  # importing config also loads .env

TEST_MODE = False
TEST_IDS = ["tt1285016", "tt1457767", "tt4154796"]  # The Social Network, The Conjuring, Avengers: Endgame
DAILY_LIMIT = 12000          # stay a bit under the free-key limit
DELAY_SECONDS = 0.1
SAVE_EVERY = 100

API_KEY = os.getenv("OMDB_API_KEY")
IN_CSV = DATA_DIR / "movies_clean.csv"
OUT_CSV = DATA_DIR / "omdb_boxoffice.csv"
URL = "https://www.omdbapi.com/"


class LimitReached(Exception):
    pass


def money(x):
    if not x or x == "N/A":
        return None
    return pd.to_numeric(str(x).replace("$", "").replace(",", ""), errors="coerce")


def fetch(imdb_id):
    r = requests.get(URL, params={"apikey": API_KEY, "i": imdb_id, "type": "movie"}, timeout=30)
    if r.status_code == 401:
        msg = r.json().get("Error", "") if r.headers.get("content-type", "").startswith("application/json") else ""
        if "limit" in msg.lower():
            raise LimitReached(msg)
        sys.exit(f"OMDb rejected the key: {msg or r.text[:200]}")
    r.raise_for_status()
    d = r.json()
    if d.get("Response") == "False":
        err = d.get("Error", "")
        if "limit" in err.lower():
            raise LimitReached(err)
        if "invalid api key" in err.lower():
            sys.exit("Invalid OMDb API key. Check OMDB_API_KEY in .env")
        return {"imdb_id": imdb_id, "omdb_ok": False, "omdb_error": err}, d
    return {
        "imdb_id": imdb_id,
        "omdb_ok": True,
        "omdb_error": None,
        "omdb_title": d.get("Title"),
        "omdb_released": d.get("Released"),
        "box_office_raw": d.get("BoxOffice"),
        "box_office_domestic": money(d.get("BoxOffice")),
        "omdb_rated": d.get("Rated"),
        "omdb_genre": d.get("Genre"),
        "imdb_rating": pd.to_numeric(d.get("imdbRating"), errors="coerce"),
        "imdb_votes": money(d.get("imdbVotes")),
        "metascore": pd.to_numeric(d.get("Metascore"), errors="coerce"),
    }, d


def main():
    if not API_KEY:
        sys.exit("OMDB_API_KEY not found. Add a line OMDB_API_KEY=your_key to .env")

    if TEST_MODE:
        for i in TEST_IDS:
            row, raw = fetch(i)
            print(f"\n{i}: {raw.get('Title')} ({raw.get('Year')})")
            print("  BoxOffice field:", raw.get("BoxOffice", "<not in response>"))
            print("  Released:", raw.get("Released"), "| Rated:", raw.get("Rated"))
        print("\nAll fields returned:", list(raw.keys()))
        print("\nIf BoxOffice shows dollar amounts, set TEST_MODE = False and run again.")
        return

    if not IN_CSV.exists():
        sys.exit(f"{IN_CSV} not found. Run 04_clean_data.py first.")
    movies = pd.read_csv(IN_CSV)
    movies = movies[movies["imdb_id"].notna()].sort_values("vote_count", ascending=False)
    all_ids = movies["imdb_id"].drop_duplicates().tolist()

    done = pd.read_csv(OUT_CSV) if OUT_CSV.exists() else pd.DataFrame(columns=["imdb_id"])
    done_ids = set(done["imdb_id"])
    todo = [i for i in all_ids if i not in done_ids][:DAILY_LIMIT]
    print(f"{len(all_ids)} films with imdb_id | already done {len(done_ids)} | fetching {len(todo)} today")

    rows = []
    try:
        for n, imdb_id in enumerate(todo, 1):
            row, _ = fetch(imdb_id)
            rows.append(row)
            if n % SAVE_EVERY == 0:
                done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
                done.to_csv(OUT_CSV, index=False)
                rows = []
                print(f"  {n}/{len(todo)} saved")
            time.sleep(DELAY_SECONDS)
    except LimitReached as e:
        print(f"\nOMDb daily limit reached ({e}). Progress saved; run again tomorrow.")
    finally:
        if rows:
            done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
            done.to_csv(OUT_CSV, index=False)

    ok = done[done.get("omdb_ok", pd.Series(dtype=bool)) == True]
    remaining = len(all_ids) - len(done)
    print(f"\nDone so far : {len(done)} / {len(all_ids)}")
    print(f"With box office : {ok['box_office_domestic'].notna().sum() if len(ok) else 0}")
    print(f"Remaining   : {remaining}  (about {-(-remaining // DAILY_LIMIT)} more daily runs)")


if __name__ == "__main__":
    main()
