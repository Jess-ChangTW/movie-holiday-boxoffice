"""
Step 11 (Layer 3, analysis direction 2): Do holiday-window releases earn more?

1. Window vs rest of year: median domestic gross and ROI, horror (Halloween) and romance (Valentine's)
2. Difference-in-differences on log gross: genre premium in the window minus the
   window effect for all other films (removes the general seasonal effect)
3. Timing bins: does it matter how many weeks before the holiday a film opens?
4. Robustness: dates-agree subset, wider windows, lower gross cutoff

Sample: main_sample (gross >= $1M, no re-releases), strict genres.
Uncertainty: bootstrap 95% confidence intervals (films resampled with replacement).

Input : data/movies_final.csv
Output: outputs/08_window_boxoffice.png, outputs/09_timing_bins.png,
        outputs/boxoffice_comparison.md
Run: open this file in VS Code and press the Run button.
"""

import sys
from datetime import date

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
import numpy as np
import pandas as pd

from config import DATA_DIR, OUTPUT_DIR

IN_CSV = DATA_DIR / "movies_final.csv"
REPORT_MD = OUTPUT_DIR / "boxoffice_comparison.md"
WINDOW_DAYS = 28
N_BOOT = 2000
SEED = 42

INK, MUTED, GRID = "#1f2328", "#6e7781", "#e6e8eb"
BLUE, GRAY = "#2f6fdb", "#9aa4ae"

if not IN_CSV.exists():
    sys.exit(f"{IN_CSV} not found. Run 09_merge_boxoffice.py first.")

full = pd.read_csv(IN_CSV, parse_dates=["us_date"])
rng = np.random.default_rng(SEED)
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
})


def days_from_nearest(dates, month, day):
    """Days from the nearest occurrence of the holiday (negative = before)."""
    out = []
    for d in dates:
        cands = [pd.Timestamp(year=d.year + k, month=month, day=day) for k in (-1, 0, 1)]
        out.append(min(((d - c).days for c in cands), key=abs))
    return np.array(out)


full["rel_halloween"] = days_from_nearest(full["us_date"], 10, 31)
full["rel_valentine"] = days_from_nearest(full["us_date"], 2, 14)

CASES = [
    # name, strict genre flag, holiday, relative-day column
    ("Horror", "horror_strict", "Halloween", "rel_halloween"),
    ("Romance", "romance_strict", "Valentine's", "rel_valentine"),
]


def in_window(s, rel, window=WINDOW_DAYS):
    return s[rel].between(-window, 0)


def boot_ci(values, stat=np.median, n=N_BOOT):
    values = np.asarray(values)
    if len(values) < 3:
        return np.nan, np.nan
    sims = [stat(rng.choice(values, len(values))) for _ in range(n)]
    return np.percentile(sims, [2.5, 97.5])


def boot_ratio(a, b, n=N_BOOT):
    """Median(a) / median(b) with bootstrap CI."""
    a, b = np.asarray(a), np.asarray(b)
    point = np.median(a) / np.median(b)
    sims = [np.median(rng.choice(a, len(a))) / np.median(rng.choice(b, len(b))) for _ in range(n)]
    lo, hi = np.percentile(sims, [2.5, 97.5])
    return point, lo, hi


def boot_did(g_in, g_out, o_in, o_out, n=N_BOOT):
    """(mean log gross genre in - out) - (others in - out), with bootstrap CI."""
    arrs = [np.asarray(x) for x in (g_in, g_out, o_in, o_out)]
    f = lambda a, b, c, d: (a.mean() - b.mean()) - (c.mean() - d.mean())
    point = f(*arrs)
    sims = [f(*(rng.choice(x, len(x)) for x in arrs)) for _ in range(n)]
    lo, hi = np.percentile(sims, [2.5, 97.5])
    return point, lo, hi


def fmt_m(x):
    return f"${x:,.1f}M"


def dollar_log_axis(axis):
    """Readable $ labels on a log axis: $1M, $3M, $10M, $30M ..."""
    axis.set_major_locator(LogLocator(base=10, subs=(1, 3)))
    axis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}M" if v >= 1 else f"${v:.1f}M"))
    axis.set_minor_formatter(NullFormatter())


def compare(sample, name, flag, rel, window=WINDOW_DAYS):
    g = sample[sample[flag]]
    o = sample[~sample[flag]]
    gw, go = g[in_window(g, rel, window)], g[~in_window(g, rel, window)]
    ow, oo = o[in_window(o, rel, window)], o[~in_window(o, rel, window)]
    ratio, rlo, rhi = boot_ratio(gw["gross_m"], go["gross_m"])
    did, dlo, dhi = boot_did(gw["log_gross"], go["log_gross"], ow["log_gross"], oo["log_gross"])
    return {
        "n_in": len(gw), "n_out": len(go),
        "median_in": gw["gross_m"].median(), "median_out": go["gross_m"].median(),
        "ratio": ratio, "ratio_lo": rlo, "ratio_hi": rhi,
        "roi_in": gw["roi"].median(), "roi_out": go["roi"].median(),
        "roi_n_in": int(gw["roi"].notna().sum()),
        "did_pct": (np.exp(did) - 1) * 100,
        "did_lo": (np.exp(dlo) - 1) * 100, "did_hi": (np.exp(dhi) - 1) * 100,
        "groups": (gw, go),
    }


main = full[full["main_sample"]].copy()
print(f"Main sample: {len(main):,} films")

# ---------- 1 & 2. window vs rest of year ----------
results = {name: compare(main, name, flag, rel) for name, flag, _, rel in CASES}

summary_rows = []
for name, flag, hol, rel in CASES:
    r = results[name]
    summary_rows.append({
        "Genre": name,
        "Window": f"{WINDOW_DAYS} days before {hol}",
        "Films in / out": f"{r['n_in']} / {r['n_out']}",
        "Median gross in": fmt_m(r["median_in"]),
        "Median gross out": fmt_m(r["median_out"]),
        "Median ratio (95% CI)": f"{r['ratio']:.2f}x ({r['ratio_lo']:.2f}-{r['ratio_hi']:.2f})",
        "Median ROI in / out": f"{r['roi_in']:.2f} / {r['roi_out']:.2f} (n in = {r['roi_n_in']})",
        "DiD premium (95% CI)": f"{r['did_pct']:+.0f}% ({r['did_lo']:+.0f}% to {r['did_hi']:+.0f}%)",
    })
summary = pd.DataFrame(summary_rows)

# chart 1: box plots of gross, in vs out, log scale
fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
for ax, (name, flag, hol, rel) in zip(axes, CASES):
    gw, go = results[name]["groups"]
    data = [go["gross_m"], gw["gross_m"]]
    bp = ax.boxplot(data, widths=0.5, patch_artist=True, showfliers=False,
                    medianprops=dict(color=INK, lw=2))
    for patch, c in zip(bp["boxes"], [GRAY, BLUE]):
        patch.set_facecolor(c)
        patch.set_alpha(0.5)
        patch.set_edgecolor(c)
    for i, s in enumerate(data, 1):
        x = rng.normal(i, 0.06, len(s))
        ax.scatter(x, s, s=8, color=[GRAY, BLUE][i - 1], alpha=0.5, lw=0)
        ax.text(i + 0.3, s.median(), fmt_m(s.median()), va="center", fontsize=9, color=INK)
    ax.set_xticks([1, 2])
    ax.set_xticklabels([f"Rest of year\n(n={len(go)})", f"{hol} window\n(n={len(gw)})"])
    ax.set_yscale("log")
    dollar_log_axis(ax.yaxis)
    ax.set_title(f"{name}", loc="left", fontsize=11)
    ax.grid(axis="y", color=GRID)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("US domestic gross ($M, log scale)")
fig.suptitle("Do holiday-window releases earn more? (main sample, strict genres)",
             x=0.01, ha="left", fontsize=12)
fig.tight_layout()
chart1 = OUTPUT_DIR / "08_window_boxoffice.png"
fig.savefig(chart1, dpi=150)
plt.close(fig)

# ---------- 3. timing bins ----------
BINS = [(-7, 0, "0-1 wk before"), (-21, -8, "2-3 wk before"), (-35, -22, "4-5 wk before"),
        (-56, -36, "6-8 wk before"), (1, 28, "1-4 wk after")]
timing_rows = []
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=False)
for ax, (name, flag, hol, rel) in zip(axes, CASES):
    g = main[main[flag]]
    labels, meds, los, his, ns = [], [], [], [], []
    near_mask = pd.Series(False, index=g.index)
    for lo_d, hi_d, label in BINS:
        mask = g[rel].between(lo_d, hi_d)
        near_mask |= mask
        s = g.loc[mask, "gross_m"]
        lo, hi = boot_ci(s)
        labels.append(label); meds.append(s.median() if len(s) else np.nan)
        los.append(lo); his.append(hi); ns.append(len(s))
    rest = g.loc[~near_mask & ~g[rel].between(-56, 28), "gross_m"]
    lo, hi = boot_ci(rest)
    labels.append("Rest of year"); meds.append(rest.median()); los.append(lo); his.append(hi); ns.append(len(rest))

    for label, med, lo, hi, n in zip(labels, meds, los, his, ns):
        timing_rows.append({"Genre": name, "Release timing": label, "Films": n,
                            "Median gross": fmt_m(med) if pd.notna(med) else "-",
                            "95% CI": f"{fmt_m(lo)} to {fmt_m(hi)}" if pd.notna(lo) else "too few films"})

    y = np.arange(len(labels))
    colors = [BLUE] * len(BINS) + [GRAY]
    for yi, med, lo, hi, c, n in zip(y, meds, los, his, colors, ns):
        if pd.notna(lo):
            ax.plot([lo, hi], [yi, yi], color=c, lw=2, alpha=0.6)
        if pd.notna(med):
            ax.plot(med, yi, "o", color=c, ms=8)
            ax.text(med, yi + 0.28, f"{fmt_m(med)}  (n={n})", ha="center", fontsize=8, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xscale("log")
    dollar_log_axis(ax.xaxis)
    ax.set_xlabel("Median US gross ($M, log scale), line = 95% CI")
    ax.set_title(f"{name}: timing relative to {hol}", loc="left", fontsize=11)
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
chart2 = OUTPUT_DIR / "09_timing_bins.png"
fig.savefig(chart2, dpi=150)
plt.close(fig)
timing = pd.DataFrame(timing_rows)

# ---------- 4. robustness ----------
variants = [
    ("Main (28-day window)", main, WINDOW_DAYS),
    ("Dates agree within 7 days", main[main["date_agree"]], WINDOW_DAYS),
    ("35-day window", main, 35),
    ("42-day window", main, 42),
    ("Gross >= $100K", full[(full["box_office_domestic"] >= 100_000) & ~full["is_rerelease"]], WINDOW_DAYS),
    ("Exclude pandemic years", main[~main["pandemic_year"]], WINDOW_DAYS),
]
rob_rows = []
for label, s, w in variants:
    for name, flag, _, rel in CASES:
        r = compare(s, name, flag, rel, w)
        rob_rows.append({
            "Variant": label, "Genre": name, "Films in window": r["n_in"],
            "Median ratio": f"{r['ratio']:.2f}x ({r['ratio_lo']:.2f}-{r['ratio_hi']:.2f})",
            "DiD premium": f"{r['did_pct']:+.0f}% ({r['did_lo']:+.0f}% to {r['did_hi']:+.0f}%)",
        })
robust = pd.DataFrame(rob_rows)


# ---------- report ----------
def md(frame):
    cols = [str(c) for c in frame.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in frame.itertuples(index=False):
        out.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(out)


report = f"""# Box Office Comparison

Generated {date.today():%B %d, %Y} by `src/11_boxoffice_comparison.py`.

Sample: {len(main):,} films with US gross of at least $1M, excluding re-releases. Horror and romance use the strict definition (tagged by both TMDB and IMDb). Window = released 0 to {WINDOW_DAYS} days before the holiday. Confidence intervals come from {N_BOOT:,} bootstrap resamples.

## 1. Window vs rest of year

![Window box office](08_window_boxoffice.png)

{md(summary)}

How to read:
- **Median ratio**: median gross of genre films in the window divided by the median for the same genre released at other times. A CI that includes 1.00 means no clear difference.
- **DiD premium**: difference in average log gross (window minus rest of year) for the genre, minus the same difference for all other films. This removes the general effect of that time of year. Expressed as a % change; a CI that includes 0% means no clear premium.

## 2. Does timing within the season matter?

![Timing bins](09_timing_bins.png)

{md(timing)}

## 3. Robustness checks

{md(robust)}

## Caveats

- Correlation, not causation: studios choose release dates, and stronger films may be placed in the holiday window.
- Small groups: only about {results['Horror']['n_in']} horror and {results['Romance']['n_in']} romance films fall in the main window, so intervals are wide.
- Gross is total domestic gross from OMDb, not inflation-adjusted. Medians and log gross limit the influence of outliers and small data errors.
"""
REPORT_MD.write_text(report, encoding="utf-8")

print(f"Saved {chart1}\nSaved {chart2}\nSaved {REPORT_MD}\n")
print("1-2. Window vs rest of year")
print(summary.drop(columns=["Window"]).to_string(index=False))
print("\n3. Timing bins")
print(timing.to_string(index=False))
print("\n4. Robustness")
print(robust.to_string(index=False))
