# Findings Log

## 06_release_calendar (release counts, not box office)

Scope: 9,359 films, 2010-2025 excluding 2020-21 and documentaries.

### Horror x Halloween: strong pattern
- Horror share of releases rises to 30-34% in weeks 39-44 (late Sep to Halloween), vs a 20.3% yearly average.
- Peak is weeks 40-42, i.e. 2-4 weeks BEFORE Halloween, not Halloween week itself. Studios seem to release early so films get several weekends before the holiday.
- Right after Halloween, horror share drops to 9-15%, the lowest of the year. Post-holiday avoidance is as clear as the pre-holiday peak.

### Romance x Valentine's: weak pattern
- Romance share peaks around 20% in weeks 5-6 (just before Valentine's), vs a 13.6% average.
- But similar peaks appear in weeks 25 and 36, so the Valentine's signal is hard to separate from noise.
- Small sample (about 25 romance films per week) makes weekly shares noisy.
- Romance share is lowest in weeks 42-43, possibly crowded out by Halloween horror.

### Other seasonal patterns (heatmap)
- Family, Animation, Fantasy concentrate in weeks 45-51 (Thanksgiving and Christmas).
- Adventure peaks in weeks 50-51 (Christmas blockbusters).
- Thriller is also elevated in October, partly because many horror films are also tagged Thriller.

### Takeaway so far
Halloween scheduling effect is strong and clear; Valentine's effect is weak. The contrast between the two holidays is itself a story worth exploring.

### Open questions
- Is the Valentine's pattern statistically significant? (07 z-test)
- Do horror films released 2-4 weeks before Halloween actually earn more? (needs box office, Layer 3)


## 07_holiday_timing (release counts, not box office)

### Timing: two different strategies
- Horror: median release is 27 days before Halloween; the most common week is the 5th week before (29-35 days). Studios treat all of October as "horror season".
- Romance: median 25 days before Valentine's, but the most common week is the 1st week before, i.e. the weekend right before the holiday.
- The horror peak falls just outside the 28-day window. Robustness check: try 35- and 42-day windows.

### Trend: Halloween concentration is weakening
- Share of horror released in the Halloween window fell from about 17-20% (2010-2014) to about 12% (2017 onward), 9.5% in 2025.
- Still above the 7.9% even-spread baseline every year.
- Possible reason: horror became a year-round mainstream genre. Needs confirmation with box office data, since TMDB's yearly coverage changes.
- Romance in the Valentine's window stays roughly flat at 9-13%.

### Competition
- Halloween window: 5.2 horror films per week vs 2.4 the rest of the year (2.2x more crowded).
- Valentine's window: 2.2 romance films per week vs 1.7 (1.3x).

### Significance (two-proportion z-test)
- Horror: 30.5% in window vs 19.5% rest of year, +10.9 pts, z = 8.02, p < 0.0001.
- Romance: 17.5% vs 13.3%, +4.3 pts, z = 3.23, p = 0.0012.
- Revises the 06 takeaway: the Valentine's effect is real but much smaller than Halloween's. Weekly charts looked like noise; pooling the window shows a significant effect.
- Caveat: test assumes films are independent, so p-values are approximate.

### Updated takeaway (Layer 2)
Both holidays shape release schedules. Halloween's effect is large, season-long, and weakening over time; Valentine's is smaller and targets the holiday weekend itself.

### Open questions for Layer 3 (needs box office)
- Does being crowded into the Halloween window hurt or help each horror film's box office?
- Do films released 4-5 weeks before Halloween outperform those released in the final week?
- Do romance films released the weekend before Valentine's earn more than other romance films?

## 08-10: Box office and data quality

### Box office source
- Box Office Mojo robots.txt disallows automated access, so it was not used.
- Used OMDb API (CC BY-NC 4.0) by imdb_id: 4,761 of 11,205 films (42%) have US domestic gross.
- Spot check: most top grosses match known figures within about 1%; Avengers: Endgame is off (OMDb $896M vs about $858M). Analysis uses log gross, so small errors matter little.

### Data quality findings
- Date mismatch between TMDB and OMDb is concentrated in small films (33% for <$1M, about 0% for $10M+).
- Main cause: re-releases of old films (Studio Ghibli, classics, Hamilton). TMDB records the recent US re-release, OMDb the original date.
- Box office is extremely concentrated: 8.8% of films ($100M+) earn 62% of total gross; 44% of films (<$1M) earn 0.2%.
- Genre labels: horror agreement between TMDB and IMDb is good (481 both); romance agreement is weaker (461 both, 350 labeled by only one side).

### Rules adopted
1. Exclude re-releases (OMDb date more than 1 year before TMDB date): 95 films.
2. Main sample: gross >= $1M and not a re-release: 2,636 films.
3. Strict genres: tagged by both TMDB and IMDb.
4. Release date: TMDB US date; robustness check with films whose dates agree within 7 days (89% of main sample).
5. Use medians and log gross, not means.

### Result
- Main sample has a stable 160-200 films per pre-pandemic year, fixing the declining-count bias seen in the TMDB-only data.
- Small holiday-window groups: 40 strict horror (Halloween), 36 strict romance (Valentine's). Report uncertainty with bootstrap confidence intervals.


## 11_boxoffice_comparison (Layer 3)

Sample: 2,636 films (gross >= $1M, no re-releases), strict genres. Bootstrap 95% CIs.

### Window vs rest of year (same genre)
- Horror: median $36.7M in Halloween window vs $22.8M rest of year (1.61x, CI 0.76-2.52).
- Romance: $20.9M vs $16.7M (1.25x, CI 0.82-2.88).
- Point estimates favor the window, but CIs include 1: not conclusive with 40 / 36 films.
- Median ROI also higher in window (horror 2.63 vs 1.93; romance 1.29 vs 1.07).

### Difference-in-differences (log gross)
- Horror +131% (CI +42% to +277%); romance +111% (CI +26% to +255%).
- Likely driven partly by other films doing worse in these weeks (October and late Jan-Feb are weak seasons).
- Interpretation: a RELATIVE advantage. Holiday-matched genres hold up or beat their own average while other films slump. To verify by decomposing the DiD.

### Timing within the season
- Horror sweet spot: 2-3 weeks before Halloween, median $53.9M (CI $35.2M-$71.1M) vs $24.6M rest of year. CIs do not overlap: strongest single finding so far.
- 0-1 week before: $19.8M (too late to build a run). 4-5 weeks before: $13.4M (n = 14, wide CI).
- Romance: 1 week before Valentine's $35.1M vs $14.8M rest of year, but CI is wide ($12.7M-$85.9M). Releasing after Valentine's is weakest ($12.3M).

### Robustness
- Horror DiD positive and significant in 5 of 6 variants; not significant with a 42-day window, consistent with the 2-3 week sweet spot.
- Romance DiD positive in all 6; borderline (lower bound +1%) when dates must agree.
- Romance ratio jumps to 4x with a $100K cutoff, driven by small films: not reliable.

### Takeaway
Holiday windows give matched genres a relative advantage in otherwise weak weeks. For horror, timing matters: opening 2-3 weeks before Halloween performs best.


## 12_regression (Layer 4)

### DiD decomposition
- Halloween window: other films' median gross drops from $24.1M to $11.3M (mean log -43%); horror rises from $22.8M to $36.7M (+32%).
- Valentine's window: other films -21%; romance +66%.
- Horror's premium is mostly relative (others slump); romance's comes more from its own lift.

### Premium with controls (genre x window, log gross, HC1 SEs)
- Horror: +124% (year FE) -> +48% with budget, franchise, MPA (p = 0.054) -> +62-64% with IMDb rating and month FE (p about 0.01).
- Romance: +113% -> +52-62%, significant in every model (p 0.003-0.044).
- About half of the raw premium is explained by bigger-budget and franchise films being placed in holiday windows (selection on observables). A 50-60% premium remains.
- Adding IMDb rating raises the horror premium: window horror films are not better rated, so quality does not explain their performance; seasonal demand does.
- Controls behave as expected: 1% more budget -> about 0.55% more gross; franchise +131-158%; +1 IMDb point -> +26-34%.

### Horror timing with controls
- The raw "2-3 weeks before" sweet spot shrinks to +19% (n.s.): it mostly reflects studios placing their biggest horror films there.
- Releasing 1-4 weeks after Halloween: -39% (p = 0.068), consistent with post-holiday avoidance.

### Overall conclusions
1. Studios cluster horror before Halloween (strong) and romance in the week before Valentine's (weaker but significant).
2. Matched genres earn a clear relative premium in holiday windows, largely because other films slump in those weeks.
3. About half the raw premium comes from bigger films being scheduled there; after controls, a 50-60% premium remains.
4. Exact timing within the window shows no robust effect after controls; releasing after the holiday may hurt.

### Caveats
- Observational: controls reduce but do not remove selection bias.
- IMDb rating is post-release and may over-control.
- Small cells (35-40 films per genre in window).