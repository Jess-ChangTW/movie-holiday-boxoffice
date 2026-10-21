"""
Step 12 (Layer 4, analysis direction 3): Does the holiday premium survive controls?

1. DiD decomposition: the four groups behind the DiD premium (genre / other x window / rest of year)
2. Regression: log gross ~ genre x window + controls, adding controls step by step
   M1  year fixed effects (all main-sample films)
   M2  same as M1, only films with a known budget (so later models compare like with like)
   M3  + log budget + franchise + MPA rating
   M4  + IMDb rating (quality proxy; measured after release, so read with care)
   M5  + month fixed effects (compares to other films released in the same month)
3. Horror timing: is the "2-3 weeks before Halloween" sweet spot still there with controls?

Robust (HC1) standard errors. Coefficients on log gross are shown as % differences: exp(b) - 1.

Input : data/movies_final.csv
Output: outputs/10_premium_by_model.png, outputs/regression.md
Run: open this file in VS Code and press the Run button.
"""

import sys
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from config import DATA_DIR, OUTPUT_DIR

IN_CSV = DATA_DIR / "movies_final.csv"
REPORT_MD = OUTPUT_DIR / "regression.md"
WINDOW_DAYS = 28

INK, MUTED, GRID = "#1f2328", "#6e7781", "#e6e8eb"
BLUE, ORANGE = "#2f6fdb", "#d9730d"

if not IN_CSV.exists():
    sys.exit(f"{IN_CSV} not found. Run 09_merge_boxoffice.py first.")

df = pd.read_csv(IN_CSV, parse_dates=["us_date"])
df = df[df["main_sample"]].copy()
print(f"Main sample: {len(df):,} films")

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
})


def days_from_nearest(dates, month, day):
    out = []
    for d in dates:
        cands = [pd.Timestamp(year=d.year + k, month=month, day=day) for k in (-1, 0, 1)]
        out.append(min(((d - c).days for c in cands), key=abs))
    return np.array(out)


df["rel_halloween"] = days_from_nearest(df["us_date"], 10, 31)
df["rel_valentine"] = days_from_nearest(df["us_date"], 2, 14)
df["hw_win"] = df["rel_halloween"].between(-WINDOW_DAYS, 0).astype(int)
df["vd_win"] = df["rel_valentine"].between(-WINDOW_DAYS, 0).astype(int)
df["horror"] = df["horror_strict"].astype(int)
df["romance"] = df["romance_strict"].astype(int)
df["franchise"] = df["is_franchise"].astype(bool).astype(int)
df["log_budget"] = np.log(df["budget"].where(df["budget"] > 0))
cert = df["us_certification"].fillna("").str.upper()
df["mpa"] = np.where(cert.isin(["G", "PG", "PG-13", "R"]), cert, "Other/NA")

CASES = [("Horror", "horror", "hw_win", "Halloween"),
         ("Romance", "romance", "vd_win", "Valentine's")]


def pct(b):
    return (np.exp(b) - 1) * 100


def md(frame):
    cols = [str(c) for c in frame.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in frame.itertuples(index=False):
        out.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(out)


# ---------- 1. DiD decomposition ----------
dec_rows = []
for name, g, w, hol in CASES:
    for gl, gv in [(name, 1), ("All other films", 0)]:
        for wl, wv in [(f"{hol} window", 1), ("Rest of year", 0)]:
            s = df[(df[g] == gv) & (df[w] == wv)]
            dec_rows.append({
                "Comparison": f"{name} vs others",
                "Group": gl, "Timing": wl, "Films": len(s),
                "Median gross": f"${s['gross_m'].median():.1f}M",
                "Mean log gross": round(s["log_gross"].mean(), 2),
            })
decomp = pd.DataFrame(dec_rows)

dec_summary = []
for name, g, w, hol in CASES:
    m = lambda gv, wv: df[(df[g] == gv) & (df[w] == wv)]["log_gross"].mean()
    genre_diff, other_diff = m(1, 1) - m(1, 0), m(0, 1) - m(0, 0)
    dec_summary.append({
        "Genre": name,
        f"Genre: window vs rest": f"{pct(genre_diff):+.0f}%",
        f"Others: window vs rest": f"{pct(other_diff):+.0f}%",
        "DiD (genre minus others)": f"{pct(genre_diff - other_diff):+.0f}%",
    })
dec_summary = pd.DataFrame(dec_summary)

# ---------- 2. regressions ----------
budget_df = df.dropna(subset=["log_budget"])
budget_q = budget_df.dropna(subset=["imdb_rating"])
models = [
    ("M1 Year FE", df, "C(year)"),
    ("M2 Year FE, budget subset", budget_q, "C(year)"),
    ("M3 + budget, franchise, MPA", budget_q, "C(year) + log_budget + franchise + C(mpa)"),
    ("M4 + IMDb rating", budget_q, "C(year) + log_budget + franchise + C(mpa) + imdb_rating"),
    ("M5 + month FE", budget_q,
     "C(year) + C(month) + log_budget + franchise + C(mpa) + imdb_rating"),
]

reg_rows, plot_data, control_rows = [], [], []
for name, g, w, hol in CASES:
    for label, data, controls in models:
        fit = smf.ols(f"log_gross ~ {g} * {w} + {controls}", data=data).fit(cov_type="HC1")
        term = f"{g}:{w}"
        b, se, p = fit.params[term], fit.bse[term], fit.pvalues[term]
        lo, hi = b - 1.96 * se, b + 1.96 * se
        n_cell = int(((data[g] == 1) & (data[w] == 1)).sum())
        reg_rows.append({
            "Genre": name, "Model": label, "Films": int(fit.nobs),
            "Genre films in window": n_cell,
            "Premium (genre x window)": f"{pct(b):+.0f}%",
            "95% CI": f"{pct(lo):+.0f}% to {pct(hi):+.0f}%",
            "p-value": f"{p:.3f}" if p >= 0.001 else "<0.001",
            "R2": f"{fit.rsquared:.2f}",
        })
        plot_data.append((name, label, pct(b), pct(lo), pct(hi)))
        if label.startswith("M4"):
            for t, lab in [("log_budget", "log budget (1% more budget)"),
                           ("franchise", "Franchise film"), ("imdb_rating", "IMDb rating (+1 point)")]:
                cb = fit.params[t]
                eff = f"{cb:.2f}% gross per 1% budget" if t == "log_budget" else f"{pct(cb):+.0f}%"
                control_rows.append({"Genre model": name, "Control": lab, "Effect": eff,
                                     "p-value": f"{fit.pvalues[t]:.3f}" if fit.pvalues[t] >= 0.001 else "<0.001"})
regs = pd.DataFrame(reg_rows)
controls_tbl = pd.DataFrame(control_rows)

# chart: premium across models
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharex=True)
for ax, (name, _, _, hol), color in zip(axes, CASES, [BLUE, ORANGE]):
    rows = [r for r in plot_data if r[0] == name]
    y = np.arange(len(rows))
    for yi, (_, label, est, lo, hi) in zip(y, rows):
        ax.plot([lo, hi], [yi, yi], color=color, lw=2, alpha=0.6)
        ax.plot(est, yi, "o", color=color, ms=8)
        ax.text(est, yi + 0.3, f"{est:+.0f}%", ha="center", fontsize=8, color=INK)
    ax.axvline(0, color=INK, lw=1, ls="--", alpha=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([r[1] for r in rows])
    ax.invert_yaxis()
    ax.set_title(f"{name} x {hol} window", loc="left", fontsize=11)
    ax.set_xlabel("Premium in log gross, % (line = 95% CI)")
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("Does the holiday premium survive controls?", x=0.01, ha="left", fontsize=12)
fig.tight_layout()
chart = OUTPUT_DIR / "10_premium_by_model.png"
fig.savefig(chart, dpi=150)
plt.close(fig)

# ---------- 3. horror timing with controls ----------
h = budget_q[budget_q["horror"] == 1].copy()
bins = [(-7, 0, "0-1 wk before"), (-21, -8, "2-3 wk before"), (-35, -22, "4-5 wk before"),
        (-56, -36, "6-8 wk before"), (1, 28, "1-4 wk after")]
h["timing"] = "Rest of year"
for lo_d, hi_d, lab in bins:
    h.loc[h["rel_halloween"].between(lo_d, hi_d), "timing"] = lab
tfit = smf.ols("log_gross ~ C(timing, Treatment('Rest of year')) + C(year) + log_budget"
               " + franchise + C(mpa) + imdb_rating", data=h).fit(cov_type="HC1")
t_rows = []
for _, _, lab in bins:
    term = f"C(timing, Treatment('Rest of year'))[T.{lab}]"
    if term in tfit.params:
        b, se, p = tfit.params[term], tfit.bse[term], tfit.pvalues[term]
        t_rows.append({"Horror released": lab, "Films": int((h["timing"] == lab).sum()),
                       "vs rest of year": f"{pct(b):+.0f}%",
                       "95% CI": f"{pct(b - 1.96 * se):+.0f}% to {pct(b + 1.96 * se):+.0f}%",
                       "p-value": f"{p:.3f}" if p >= 0.001 else "<0.001"})
timing = pd.DataFrame(t_rows)

# ---------- report ----------
report = f"""# Regression and Controls

Generated {date.today():%B %d, %Y} by `src/12_regression.py`.

Main sample: {len(df):,} films (gross >= $1M, no re-releases). Models M2 to M5 use the {len(budget_q):,} films with known budget and IMDb rating. Strict genres; window = 0 to {WINDOW_DAYS} days before the holiday. Robust (HC1) standard errors.

## 1. What drives the DiD premium?

{md(dec_summary)}

{md(decomp)}

## 2. Holiday premium with controls

The premium is the coefficient on genre x window: how much more (in %) a matched-genre film in the window earns, beyond the genre's usual level and beyond the window's effect on other films.

![Premium by model](10_premium_by_model.png)

{md(regs)}

### Control variables (model M4)

{md(controls_tbl)}

## 3. Horror release timing with controls (horror films only)

Compared with horror released at other times of year, controlling for year, budget, franchise, MPA rating and IMDb rating.

{md(timing)}

## Caveats

- Observational data: controls reduce but do not remove the bias from studios choosing release dates.
- IMDb rating is measured after release and may partly reflect box office success, so M4 and M5 may over-control.
- Small cells (about 30-40 films per genre in the window) give wide intervals.
"""
REPORT_MD.write_text(report, encoding="utf-8")

print(f"Saved {chart}\nSaved {REPORT_MD}\n")
print("1. DiD decomposition")
print(dec_summary.to_string(index=False))
print()
print(decomp.drop(columns=["Comparison"]).to_string(index=False))
print("\n2. Premium by model")
print(regs.to_string(index=False))
print("\nControls (M4)")
print(controls_tbl.to_string(index=False))
print("\n3. Horror timing with controls")
print(timing.to_string(index=False))
