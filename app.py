"""
BCI Industry Intelligence Dashboard
------------------------------------
An interactive view of the brain-computer interface clinical trial
landscape, built on public ClinicalTrials.gov data. Run:

    streamlit run app.py

Requires data/raw/trials_processed.csv to exist first -- generate it with:

    python src/fetch_trials.py
    python src/process.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analyze import (
    trials_per_year,
    trials_by_condition_and_year,
    sponsor_leaderboard,
    phase_funnel,
    sponsor_regulatory_cross_reference,
    whitespace_conditions,
)

DATA_PATH = Path(__file__).resolve().parent / "data" / "raw" / "trials_processed.csv"

st.set_page_config(page_title="BCI Industry Intelligence", layout="wide")
st.title("BCI Industry Intelligence Dashboard")
st.caption(
    "Public clinical trial data on brain-computer interfaces, sourced from the "
    "ClinicalTrials.gov API v2. Regulatory designations sourced separately and "
    "cited in data/reference/fda_breakthrough_devices.csv."
)

if not DATA_PATH.exists():
    st.warning(
        "No processed data found yet. Run these two commands from the project "
        "root, then refresh this page:\n\n"
        "```\npython src/fetch_trials.py\npython src/process.py\n```"
    )
    st.stop()

df = pd.read_csv(DATA_PATH)

if df.empty:
    st.info("The processed dataset is empty -- the last fetch may not have matched any trials.")
    st.stop()

# ---------------------------------------------------------------- Overview
col1, col2, col3 = st.columns(3)
col1.metric("Total trials tracked", len(df))
col2.metric("Distinct sponsors", df["lead_sponsor"].nunique())
col3.metric("Countries represented", df["countries"].str.split("; ").explode().nunique())

st.divider()

# ---------------------------------------------------------------- Trend
st.subheader("Trial volume over time")
yearly = trials_per_year(df)
if not yearly.empty:
    fig = px.bar(yearly, x="start_year", y="trial_count", labels={"start_year": "Year", "trial_count": "Trials started"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No dated trials to plot yet.")

st.subheader("Trial volume by condition, over time")
by_condition = trials_by_condition_and_year(df)
if not by_condition.empty:
    fig2 = px.line(
        by_condition, x="start_year", y="trial_count", color="condition", markers=True,
        labels={"start_year": "Year", "trial_count": "Trials started", "condition": "Condition"},
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---------------------------------------------------------------- Competitive landscape
st.subheader("Sponsor / competitive landscape")
leaderboard = sponsor_leaderboard(df)
if not leaderboard.empty:
    fig3 = px.bar(
        leaderboard.sort_values("trial_count"), x="trial_count", y="lead_sponsor",
        color="lead_sponsor_class", orientation="h",
        labels={"trial_count": "Trials", "lead_sponsor": "Lead sponsor", "lead_sponsor_class": "Sponsor type"},
    )
    st.plotly_chart(fig3, use_container_width=True)

st.subheader("Regulatory cross-reference (FDA Breakthrough Device status)")
reg = sponsor_regulatory_cross_reference(df)
st.dataframe(reg.sort_values("trial_count", ascending=False), use_container_width=True)
st.caption(
    "Breakthrough Device status compiled by hand from public reporting (FDA does not "
    "publish a queryable API for this program) -- see data/reference/fda_breakthrough_devices.csv "
    "for sources. Treat as directionally accurate, not a legal/regulatory record of truth."
)

st.divider()

# ---------------------------------------------------------------- Pipeline maturity
st.subheader("Trial phase funnel")
funnel = phase_funnel(df)
if not funnel.empty:
    fig4 = px.bar(funnel, x="phase", y="trial_count", labels={"phase": "Phase", "trial_count": "Trials"})
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ---------------------------------------------------------------- White space
st.subheader("Growth-opportunity signal: conditions with thin sponsor coverage")
st.caption(
    "Conditions with active recent trial volume but very few distinct sponsors -- "
    "a simple heuristic for validated patient need with limited competitive coverage."
)
whitespace = whitespace_conditions(df)
if not whitespace.empty:
    st.dataframe(whitespace, use_container_width=True)
else:
    st.info("No conditions met the white-space threshold with the current dataset.")

with st.expander("Raw trial data"):
    st.dataframe(df, use_container_width=True)
