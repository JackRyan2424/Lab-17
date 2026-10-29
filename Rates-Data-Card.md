# Rates as known on a date

## Run the app

From this folder:

```powershell
python -m streamlit run asof_app.py
```

Dependencies: Streamlit 1.66.0, pandas, and requests. If needed, install with `python -m pip install streamlit==1.66.0 pandas requests`.

The app defaults to all four rate series, January 1, 2020, and today's vintage. Enter PAYEMS or another FRED ID in the sidebar. The start date controls both the chart and comparison counts. Expand a series to inspect or download the dated comparisons. Failed IDs do not stop other series.

## Reproduced historical checks

Public source downloads on October 29, 2026 reproduced the October 5, 2026 vintage:

| Series | Last observation known | Value |
|---|---|---:|
| BAA | September 2026 | 6.47 |
| FEDFUNDS | September 2026 | 3.75 |
| DGS10 | October 2, 2026 | 5.28 |
| MORTGAGE30US | October 1, 2026 | 7.28 |

The PAYEMS January 15, 2025 vintage reports December 2024 at **159,536 thousand jobs**. The current download reports that same month at **158,316**, a decrease of **1,220 thousand**. From January 2020, 59 common observations changed and 21 observations occur after the last observation known then. These are comparisons of two actual downloads, not values substituted into the app.

To repeat these checks, select the stated vintage dates in the app and inspect the comparison table. Current values and counts may change after new releases.

## Data card — DGS10

**Selection:** DGS10 is the working choice for this submission; no prework series selection was found in the workspace.

**Source and links:** Board of Governors of the Federal Reserve System, H.15 Selected Interest Rates, distributed by the Federal Reserve Bank of St. Louis through [FRED](https://fred.stlouisfed.org/series/DGS10) and [ALFRED](https://alfred.stlouisfed.org/series?seid=DGS10). [Current CSV](https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10); [September 30 vintage CSV](https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=DGS10&vintage_date=2026-09-30).

**Measure:** Market yield on U.S. Treasury securities at 10-year constant maturity, quoted on an investment basis. This is a yield series, not a bond price or investment total return.

**Units and frequency:** Percent per year, daily, not seasonally adjusted. A value of 5.05 means 5.05%, or 0.0505 as a decimal. Missing days remain missing; they are not zero yields.

**Publication lag:** Short but not zero. The September 30, 2026 vintage ends at September 29 (5.26%); the October 29 download ends at October 28 (5.05%). These observations demonstrate a one-calendar-day gap at the two inspected cutoffs, not a universal publication-time guarantee. Weekends, holidays, and source updates can change the gap. Check the actual vintage rather than assume an observation was available on its measurement date.

**Revisions:** Zero changed common observations in the January 2020 onward comparison of September 30 versus October 29. This establishes no revisions in that inspected comparison, not an assurance that historical corrections can never occur. FRED explicitly notes that data are subject to revision.

**Download date:** October 29, 2026. The running app shows the actual UTC retrieval timestamp for each download. Downloads are cached for an hour; Refresh downloads clears the cache.

### Month-end versus today

| As known on | Last measurement | Value (%) | Later observations in today's file | Revised common observations |
|---|---|---:|---:|---:|
| September 30, 2026 | September 29, 2026 | 5.26 | 20 | 0 |
| October 29, 2026 | October 28, 2026 | 5.05 | 0 | 0 |

The 20 later nonmissing observations were unavailable in the September 30 vintage. A current chart would expose them to a historical decision unless availability is explicitly enforced.

### Three source-page checks

Compared the downloaded observations against the displayed observations on the [FRED DGS10 page](https://fred.stlouisfed.org/series/DGS10), retrieved October 29, 2026:

| Observation | Download (%) | FRED page (%) | Result |
|---|---:|---:|---|
| October 26, 2026 | 5.00 | 5.00 | Match |
| October 27, 2026 | 4.99 | 4.99 | Match |
| October 28, 2026 | 5.05 | 5.05 | Match |

These source-page checks were performed with AI assistance. The student should independently read these three observations on FRED before describing them as personal manual checks.

## Project 2 decision

**Admit DGS10 conditionally:** use only the value in the ALFRED vintage available before each decision. For a trade during day D, use a vintage no later than the previous calendar day and confirm a nonmissing observation exists; do not use day D's end-of-day vintage as proof of intraday availability. Keep the observation date, vintage date, decision timestamp/time zone, source URL, and retrieval timestamp with each input. Never backfill a missing historical value using today's download.

The reason for admission is that the inspected daily yield has a short observed lag and no revisions in this comparison, while ALFRED provides a way to enforce historical availability. This is permission to use a properly timed input, not evidence that it predicts returns.

**Condition that changes the decision:** quarantine any decision-date input if its historical vintage cannot be retrieved, its availability before the trade cannot be established, or the returned series/units are inconsistent. Re-admit only after obtaining verifiable historical availability and rerunning the affected calculations. A download error must not trigger a fallback to today's values.

## What the data card does

A data card records what a series measures, where it came from, its units, and when each version could be known. Observation date and vintage/publication date are separate: the first identifies the period measured, the second controls which version is eligible. The decision timestamp establishes the cutoff; the retrieval timestamp and source link make the result auditable. These fields prevent later releases and revisions from entering an earlier decision.

“Cleaned the data” does not document those facts. Removing blanks and duplicates cannot establish that a number existed before a trade, and can leave look-ahead bias intact.
