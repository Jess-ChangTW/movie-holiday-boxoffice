# Tableau Dashboard Guide

Holiday Box Office: 3 dashboards + 1 story, driven by one parameter that switches between Horror x Halloween and Romance x Valentine's.

Data files are in `tableau/` (created by `src/13_export_tableau.py`).

---

## 0. Connect the data

1. Open Tableau > Connect > Text file > `tableau/films.csv`
2. Add the other files as **separate data sources** (Data > New Data Source), not joins:
   - `release_calendar.csv`, `weekly_share.csv`, `did_decomposition.csv`, `regression_results.csv`
3. Check data types: `Release Date` = Date; `Is Horror`, `In Halloween Window`, etc. = Boolean (T|F)

---

## 1. The parameter (the "wow" part)

Create Parameter (right-click in Data pane > Create Parameter):
- Name: `Focus`
- Data type: String, Allowable values: List
- Values: `Horror x Halloween`, `Romance x Valentine's`

Right-click it > Show Parameter. Every sheet below reacts to it.

### Calculated fields in films.csv

```
// Focus Film
IF [Focus] = "Horror x Halloween" THEN [Is Horror] ELSE [Is Romance] END

// Days from Holiday
IF [Focus] = "Horror x Halloween" THEN [Days from Halloween] ELSE [Days from Valentine's] END

// In Window
IF [Focus] = "Horror x Halloween" THEN [In Halloween Window] ELSE [In Valentine's Window] END

// Window Label
IF [In Window] THEN "Holiday window" ELSE "Rest of year" END

// Timing
IF [Focus] = "Horror x Halloween" THEN [Halloween Timing] ELSE [Valentine's Timing] END

// Jitter (spreads dots horizontally, same position every time)
(INT(RIGHT([IMDb ID], 3)) % 100) / 100 - 0.5
```

### Calculated fields in the other sources

```
// did_decomposition.csv > Show Comparison
[Comparison] = [Focus]

// regression_results.csv > Show Genre
LEFT([Focus], 6) = LEFT([Genre], 6)

// regression_results.csv > CI Width
[CI High %] - [CI Low %]
```

---

## 2. Dashboard 1: When do studios release? (scheduling)

### Sheet "Release Heatmap" (release_calendar.csv)
- Columns: `Week of Year` (discrete)
- Rows: `Genre`
- Color: `CNT(Title)` > Quick Table Calculation > Percent of Total > Compute Using: Week of Year
- Filters: `Pandemic Year` = False; `Genre` > Top 12 by CNT(Title)
- Color palette: single-hue sequential (Blue)
- Annotate weeks 7 (Valentine's) and 44 (Halloween): right-click cell > Annotate > Area

### Sheet "Genre Share by Week" (weekly_share.csv)
- Columns: `Week of Year` (continuous)
- Rows: `Horror Share`, then drag `Romance Share` onto the same axis (Measure Values)
- Format as percentage
- Analytics > Reference Line > Constant 44 ("Halloween") and 7 ("Valentine's")

Headline text box: "Horror share jumps to 30-34% in the 5 weeks before Halloween, vs a 20% yearly average."

---

## 3. Dashboard 2: Does it pay? (box office)

### Sheet "Gross by Window" (films.csv)
- Filter: `Focus Film` = True
- Columns: `Window Label`, then `Jitter` (continuous, hide its header)
- Rows: `Domestic Gross ($M)` > right-click axis > Edit Axis > Logarithmic
- Marks: Circle, size small, opacity 60%
- Analytics > Box Plot (drag onto the cell)
- Tooltip: `Title`, `Release Date`, `Domestic Gross ($M)`, `Budget`, `IMDb Rating`

### Sheet "Release Timing" (films.csv)
- Filter: `Focus Film` = True
- Rows: `Timing` (sorted by name; the numbers keep the order)
- Columns: `MEDIAN(Domestic Gross ($M))`
- Marks: Circle; Label: `CNT(Title)` as "n = ..."
- Color: highlight "6. Rest of year" in gray

### Sheet "Who gains, who slumps" (did_decomposition.csv)
- Filter: `Show Comparison` = True
- Columns: `Timing` (order: Rest of year, then window)
- Rows: `Median Gross ($M)`
- Marks: Line; Color: `Group`; Label: `Median Gross ($M)` at line ends
- This slope chart shows the key story: other films fall in the window while the matched genre rises.

Headline: "In the Halloween window, other films' median gross halves while horror rises 61%."

---

## 4. Dashboard 3: Does the premium survive controls? (regression)

### Sheet "Premium by Model" (regression_results.csv)
- Filter: `Show Genre` = True
- Rows: `Model`
- Columns: `CI Low %` > Marks: Gantt Bar, Size: `CI Width` (the confidence interval)
- Dual axis: add `Premium %` as Circle, synchronize axes
- Reference line: constant 0, dashed
- Label circle with `Premium %`; tooltip with `p-value`, `Films`

Headline: "About half the raw premium is explained by bigger films being scheduled there; a 50-60% premium remains after controls."

---

## 5. Story (Story > New Story)

1. "Studios cluster horror before Halloween" > Dashboard 1
2. "Matched genres earn more in the window" > Dashboard 2 (Gross by Window)
3. "Because everything else slumps" > Dashboard 2 (slope chart)
4. "The premium survives controls, at about half the size" > Dashboard 3
5. "Caveats": text only: observational data, small groups (35-40 films), OMDb gross, studio-chosen dates

---

## 6. Design checklist

- One font, 2-3 colors: blue = matched genre, gray = everything else, orange only for romance
- Every dashboard: title + one-sentence headline with the key number
- Show the `Focus` parameter at the top right of every dashboard
- Dashboard size: Fixed 1200 x 800 (looks consistent on Tableau Public)
- Footer: "Data: TMDB API, OMDb API (CC BY-NC 4.0). This product uses the TMDB API but is not endorsed or certified by TMDB."

## 7. Publish

1. Data > each source > Extract Data (Tableau Public requires extracts)
2. Server > Tableau Public > Save to Tableau Public As (sign in or create a free account)
3. Copy the public link into README.md, LinkedIn, and your resume
