"""Run: python -m streamlit run rates_app.py"""
from datetime import date, datetime, timezone
from io import StringIO
import re

import altair as alt
import pandas as pd
import requests
import streamlit as st

SERIES = {
    "BAA": "Moody's Baa corporate bond yield",
    "FEDFUNDS": "Effective federal funds rate",
    "DGS10": "10-year Treasury yield",
    "MORTGAGE30US": "30-year fixed mortgage rate",
}


def parse_csv(text):
    frame = pd.read_csv(StringIO(text), na_values=["."])
    if len(frame.columns) != 2:
        raise ValueError("Expected a date column and one series column from the source.")
    frame.columns = ["Date", "Value"]
    frame["Date"] = pd.to_datetime(frame["Date"], errors="raise")
    frame["Value"] = pd.to_numeric(frame["Value"], errors="raise")
    if frame["Date"].duplicated().any():
        raise ValueError("Source returned duplicate observation dates.")
    return frame.set_index("Date").sort_index()["Value"]


def download(url, params):
    response = requests.get(url, params=params, timeout=45)
    response.raise_for_status()
    values = parse_csv(response.text)
    return values, datetime.now(timezone.utc).isoformat(), response.url


@st.cache_data(ttl=3600, max_entries=128, show_spinner=False)
def get_today(series_id, download_day):
    return download("https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": series_id})


@st.cache_data(ttl=3600, max_entries=256, show_spinner=False)
def get_vintage(series_id, vintage_date, download_day):
    values, retrieved, url = download(
        "https://alfred.stlouisfed.org/graph/alfredgraph.csv",
        {"id": series_id, "vintage_date": vintage_date.isoformat()},
    )
    if (values.dropna().index > pd.Timestamp(vintage_date)).any():
        raise ValueError("Vintage contains future observations; refusing this response.")
    return values, retrieved, url


def compare(current, historical, start):
    current = current.loc[pd.Timestamp(start):].dropna()
    historical = historical.loc[pd.Timestamp(start):].dropna()
    common = current.index.intersection(historical.index)
    revised = int(((current.loc[common] - historical.loc[common]).abs() > 1e-9).sum())
    return {
        "Last date as known": historical.index.max() if len(historical) else None,
        "Value as known": float(historical.iloc[-1]) if len(historical) else None,
        "Last date today": current.index.max() if len(current) else None,
        "Value today": float(current.iloc[-1]) if len(current) else None,
        "Later observations": int((current.index > historical.index.max()).sum()) if len(historical) else len(current),
        "Revised observations": revised,
    }


def main():
    st.set_page_config(page_title="Rates | As known on", layout="wide")
    today = date.today()
    st.html("""<style>
    .stApp { background: #f5f7fb; color: #142d4e; }
    [data-testid="stSidebar"] { background: #eaf0f7; }
    [data-testid="stMetric"] { background: white; border-radius: 12px; padding: 12px; }
    h1, h2, h3 { letter-spacing: -0.025em; }
    </style>""")
    st.caption("RATES OBSERVATORY / POINT-IN-TIME EXPLORER")
    st.title("Rates, as known on a date")
    st.write("Explore today's history alongside the information available on your decision date.")
    st.caption(f"Data from [FRED](https://fred.stlouisfed.org/) and [ALFRED](https://alfred.stlouisfed.org/), Federal Reserve Bank of St. Louis; downloaded today ({today}). Built with AI help; a learning demonstration, not investment advice.")
    with st.sidebar:
        st.header("Explore the data")
        selected = st.multiselect("Series", list(SERIES), default=list(SERIES), format_func=lambda x: f"{x} — {SERIES[x]}")
        extra = st.text_input("Add another FRED series ID", help="For example PAYEMS. Separate multiple IDs with commas.").upper().strip()
        start = st.date_input("Start date", date(2020, 1, 1), min_value=date(1776, 1, 1), max_value=today)
        asof = st.date_input("As known on", today, min_value=date(1776, 1, 1), max_value=today)
        if st.button("Refresh downloads"):
            get_today.clear()
            get_vintage.clear()
        st.caption("Cached for one hour. Dates are observation dates; availability is determined by the ALFRED vintage.")
    ids = list(dict.fromkeys(selected + [x.strip() for x in extra.split(",") if x.strip()]))
    st.info("Today's chart can include revisions and observations unavailable then. Use the historical vintage for decisions. A date-only vintage does not prove availability before an intraday trade.")
    if start > asof:
        st.warning("The start date is after the vintage date; the historical window may be empty.")
    rows = []
    st.subheader("Rate histories")
    st.caption(f"From {start:%b %d, %Y} | Historical vintage: {asof:%b %d, %Y}")
    grid = st.columns(2, gap="large")
    for position, sid in enumerate(ids):
        with grid[position % 2].container(border=True):
            st.subheader(f"{sid} — {SERIES.get(sid, 'Additional series')}")
            if not re.fullmatch(r"[A-Z0-9_]+", sid):
                st.error(f"{sid}: invalid ID. Use letters, digits, or underscores.")
                continue
            try:
                with st.spinner(f"Loading {sid}…"):
                    current, now_time, now_url = get_today(sid, today)
                    historical, then_time, then_url = get_vintage(sid, asof, today)
                row = compare(current, historical, start)
                rows.append({"Series": f"https://fred.stlouisfed.org/series/{sid}", **row})
                suffix = "%" if sid in SERIES else ""
                with st.container(horizontal=True):
                    for label, key in [("Latest today", "Value today"), ("Latest as known", "Value as known")]:
                        value = row[key]
                        st.metric(label, "N/A" if value is None else f"{value:,.2f}{suffix}")
                chart = current.loc[pd.Timestamp(start):].rename("Today's values")
                if chart.dropna().empty:
                    st.warning("No current observations in this window.")
                else:
                    plotted = pd.concat([chart.rename("Today"), historical.loc[pd.Timestamp(start):].rename("As known")], axis=1)
                    data = plotted.rename_axis("Date").reset_index().melt("Date", var_name="Vintage", value_name="Value")
                    lines = alt.Chart(data).mark_line(strokeWidth=2.5).encode(
                        x=alt.X("Date:T", title=None),
                        y=alt.Y("Value:Q", title="Percent" if sid in SERIES else "Source units", scale=alt.Scale(zero=False)),
                        color=alt.Color("Vintage:N", scale=alt.Scale(domain=["Today", "As known"], range=["#2563eb", "#d97706"]), legend=alt.Legend(orient="top", title=None)),
                        strokeDash=alt.StrokeDash("Vintage:N", scale=alt.Scale(domain=["Today", "As known"], range=[[1, 0], [6, 3]]), legend=None),
                        tooltip=[alt.Tooltip("Date:T", format="%b %d, %Y"), "Vintage:N", alt.Tooltip("Value:Q", format=",.3f")],
                    )
                    cutoff = alt.Chart(pd.DataFrame({"Date": [pd.Timestamp(asof)]})).mark_rule(color="#64748b", strokeDash=[3, 4]).encode(x="Date:T")
                    st.altair_chart((lines + cutoff).properties(height=280).interactive(), width="stretch", alt=f"{sid}: current and historical values with a vintage-date marker")
                    st.caption("Blue: today | Orange dashed: as known | Vertical line: vintage date. Scroll to zoom.")
                known = row["Last date as known"]
                st.write(f"As known on {asof}: last observation **{known.date() if known is not None else 'none in window'}**; value **{row['Value as known'] if known is not None else 'N/A'}**.")
                st.caption(f"[FRED series page](https://fred.stlouisfed.org/series/{sid}) · [Current CSV]({now_url}) · [Vintage CSV]({then_url}) · Retrieved UTC: current {now_time}; vintage {then_time}")
                with st.expander("Inspect values and revisions"):
                    detail = pd.concat([current.rename("Today"), historical.rename("As known")], axis=1).loc[pd.Timestamp(start):]
                    detail["Revision"] = detail["Today"] - detail["As known"]
                    changes = detail["Revision"].dropna()
                    changes = changes[changes.abs() > 1e-9]
                    if not changes.empty:
                        st.caption("Revisions: today minus as known; percentage points for rate series")
                        st.bar_chart(changes, color="#d97706", height=180, alt=f"{sid}: revisions on common observation dates")
                    else:
                        st.caption("No changed values on common nonmissing dates in this window.")
                    st.dataframe(detail.sort_index(ascending=False), alt=f"{sid} observation comparison")
                    st.download_button("Download comparison", detail.to_csv(), file_name=f"{sid}-{asof}.csv", key=sid)
            except (requests.RequestException, ValueError, pd.errors.ParserError) as exc:
                st.error(f"{sid}: could not load this series ({exc}). Check the ID or retry; other series continue.")
    st.subheader("Today's data versus the historical vintage")
    st.caption("Counts use nonmissing values from the selected start date. Later = dates after the last nonmissing date known then (all current values if none known). Revised = changed values on dates present in both downloads. Missing dots are never filled.")
    if rows:
        counts = pd.DataFrame(rows)
        counts["Series ID"] = counts["Series"].str.rsplit("/", n=1).str[-1]
        with st.container(horizontal=True):
            st.metric("Series loaded", len(rows), border=True)
            st.metric("Later observations", int(counts["Later observations"].sum()), border=True)
            st.metric("Revised observations", int(counts["Revised observations"].sum()), border=True)
        st.bar_chart(counts.set_index("Series ID")[["Later observations", "Revised observations"]], stack=False, color=["#2563eb", "#d97706"], height=230, alt="Later and revised observation counts for each series")
        st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={"Series": st.column_config.LinkColumn("Series", display_text=r"https://fred\.stlouisfed\.org/series/(.*)")}, alt="Latest observations, later observations, and revisions by series")
    elif not ids:
        st.info("Select a series or enter an ID to begin.")


if __name__ == "__main__":
    main()
