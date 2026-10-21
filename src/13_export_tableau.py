"""
Step 13: Export Tableau-ready data files.

Output folder: tableau/
  films.csv               one row per main-sample film (box office dashboards)
  release_calendar.csv    one row per film x genre, TMDB universe (release heatmap)
  weekly_share.csv        horror / romance share of releases by week of year
  did_decomposition.csv   the four groups behind the DiD premium
  regression_results.csv  holiday premium by model, with 95% CI (coefficient plot)

Column names are human-readable so they show up nicely in Tableau.
Run: open this file in VS Code and press the Run button.
"""

import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from config import DATA_DIR, ROOT

FINAL_CSV = DATA_DIR / "movies_final.csv"
CLEAN_CSV = DATA_DIR / "movies_clean.csv"
OUT_DIR = ROOT / "tableau"
OUT_DIR.mkdir(exist_ok=True)
WINDOW_DAYS = 28

for f in (FINAL_CSV, CLEAN_CSV):
    if not f.exists():
        sys.exit(f"{f} not found. Run steps 04 and 09 first.")


def days_from_nearest(dates, month, day):
    out = []
    for d in dates:
        cands = [pd.Timestamp(year=d.year + k, month=month, day=day) for k in (-1, 0, 1)]
        out.append(min(((d - c).days for c in cands), key=abs))
    return np.array(out)


def timing_bin(rel):
    if -7 <= rel <= 0:
        return "1. 0-1 wk before"
    if -21 <= rel <= -8:
        return "2. 2-3 wk before"
    if -35 <= rel <= -22:
        return "3. 4-5 wk before"
    if -56 <= rel <= -36:
        return "4. 6-8 wk before"
    if 1 <= rel <= 28:
        return "5. 1-4 wk after"
    return "6. Rest of year"


# ---------- films.csv ----------
fin = pd.read_csv(FINAL_CSV, parse_dates=["us_date"])
fin = fin[fin["main_sample"]].copy()
fin["rel_h"] = days_from_nearest(fin["us_date"], 10, 31)
fin["rel_v"] = days_from_nearest(fin["us_date"], 2, 14)
cert = fin["us_certification"].fillna("").str.upper()

films = pd.DataFrame({
    "Title": fin["title"],
    "IMDb ID": fin["imdb_id"],
    "Release Date": fin["us_date"].dt.date,
    "Year": fin["year"],
    "Month": fin["month"],
    "Week of Year": fin["week"],
    "Genre Group": np.select([fin["horror_strict"], fin["romance_strict"]],
                             ["Horror", "Romance"], "Other"),
    "Is Horror": fin["horror_strict"],
    "Is Romance": fin["romance_strict"],
    "Genres (TMDB)": fin["genres"],
    "Days from Halloween": fin["rel_h"],
    "Days from Valentine's": fin["rel_v"],
    "In Halloween Window": fin["rel_h"].between(-WINDOW_DAYS, 0),
    "In Valentine's Window": fin["rel_v"].between(-WINDOW_DAYS, 0),
    "Halloween Timing": [timing_bin(r) for r in fin["rel_h"]],
    "Valentine's Timing": [timing_bin(r) for r in fin["rel_v"]],
    "Domestic Gross": fin["box_office_domestic"],
    "Domestic Gross ($M)": fin["gross_m"].round(2),
    "Budget": fin["budget"],
    "ROI (Gross / Budget)": fin["roi"].round(2),
    "Franchise": fin["is_franchise"].astype(bool),
    "Collection": fin["collection_name"],
    "MPA Rating": np.where(cert.isin(["G", "PG", "PG-13", "R"]), cert, "Other/NA"),
    "IMDb Rating": fin["imdb_rating"],
    "Pandemic Year": fin["pandemic_year"],
    "Dates Agree": fin["date_agree"],
})
films.to_csv(OUT_DIR / "films.csv", index=False)

# ---------- release_calendar.csv (TMDB universe, for the scheduling story) ----------
clean = pd.read_csv(CLEAN_CSV, parse_dates=["us_date"])
clean = clean[~clean["is_documentary"]]
cal = clean.assign(Genre=clean["genres"].str.split("|")).explode("Genre")
cal = cal[cal["Genre"].notna() & (cal["Genre"] != "")]
calendar = pd.DataFrame({
    "Title": cal["title"],
    "Release Date": cal["us_date"].dt.date,
    "Year": cal["year"],
    "Week of Year": cal["week"],
    "Genre": cal["Genre"],
    "Pandemic Year": cal["pandemic_year"],
})
calendar.to_csv(OUT_DIR / "release_calendar.csv", index=False)

# ---------- weekly_share.csv ----------
normal = clean[~clean["pandemic_year"]]
weekly = normal.groupby("week").agg(
    Releases=("tmdb_id", "count"), Horror=("is_horror", "sum"), Romance=("is_romance", "sum"))
weekly["Horror Share"] = (weekly["Horror"] / weekly["Releases"]).round(4)
weekly["Romance Share"] = (weekly["Romance"] / weekly["Releases"]).round(4)
weekly = weekly.reset_index().rename(columns={"week": "Week of Year"})
weekly.to_csv(OUT_DIR / "weekly_share.csv", index=False)

# ---------- did_decomposition.csv ----------
rows = []
for genre, flag, win, hol in [("Horror", "Is Horror", "In Halloween Window", "Halloween"),
                              ("Romance", "Is Romance", "In Valentine's Window", "Valentine's")]:
    for gl, gv in [(genre, True), ("All other films", False)]:
        for tl, tv in [(f"{hol} window", True), ("Rest of year", False)]:
            s = films[(films[flag] == gv) & (films[win] == tv)]
            rows.append({"Comparison": f"{genre} x {hol}", "Group": gl, "Timing": tl,
                         "Films": len(s),
                         "Median Gross ($M)": round(s["Domestic Gross ($M)"].median(), 2)})
pd.DataFrame(rows).to_csv(OUT_DIR / "did_decomposition.csv", index=False)

# ---------- regression_results.csv ----------
d = fin.copy()
d["hw_win"] = d["rel_h"].between(-WINDOW_DAYS, 0).astype(int)
d["vd_win"] = d["rel_v"].between(-WINDOW_DAYS, 0).astype(int)
d["horror"] = d["horror_strict"].astype(int)
d["romance"] = d["romance_strict"].astype(int)
d["franchise"] = d["is_franchise"].astype(bool).astype(int)
d["log_budget"] = np.log(d["budget"].where(d["budget"] > 0))
d["mpa"] = films["MPA Rating"].values
bq = d.dropna(subset=["log_budget", "imdb_rating"])
models = [
    ("1. Year FE", d, "C(year)"),
    ("2. Year FE (budget subset)", bq, "C(year)"),
    ("3. + Budget, franchise, MPA", bq, "C(year) + log_budget + franchise + C(mpa)"),
    ("4. + IMDb rating", bq, "C(year) + log_budget + franchise + C(mpa) + imdb_rating"),
    ("5. + Month FE", bq, "C(year) + C(month) + log_budget + franchise + C(mpa) + imdb_rating"),
]
res = []
for genre, g, w in [("Horror", "horror", "hw_win"), ("Romance", "romance", "vd_win")]:
    for label, data, ctrl in models:
        fit = smf.ols(f"log_gross ~ {g} * {w} + {ctrl}", data=data).fit(cov_type="HC1")
        b, se = fit.params[f"{g}:{w}"], fit.bse[f"{g}:{w}"]
        res.append({"Genre": genre, "Model": label,
                    "Premium %": round((np.exp(b) - 1) * 100, 1),
                    "CI Low %": round((np.exp(b - 1.96 * se) - 1) * 100, 1),
                    "CI High %": round((np.exp(b + 1.96 * se) - 1) * 100, 1),
                    "p-value": round(fit.pvalues[f"{g}:{w}"], 4),
                    "Films": int(fit.nobs)})
pd.DataFrame(res).to_csv(OUT_DIR / "regression_results.csv", index=False)

for f in sorted(OUT_DIR.glob("*.csv")):
    print(f"Saved {f.name:26s} {len(pd.read_csv(f)):>7,} rows")
print(f"\nFolder: {OUT_DIR}")
