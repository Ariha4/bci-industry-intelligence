"""
analyze.py
----------
Turns the tidy trial dataset into the market-intelligence views the
dashboard shows: trial volume over time, the sponsor/competitive landscape,
a trial-phase funnel, regulatory designation cross-referencing, and a simple
"white space" heuristic for under-served conditions.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"
FDA_BREAKTHROUGH_PATH = REFERENCE_DIR / "fda_breakthrough_devices.csv"

PHASE_ORDER = ["EARLY_PHASE1", "PHASE1", "PHASE1,PHASE2", "PHASE2", "PHASE2,PHASE3", "PHASE3", "PHASE4", "NA"]


def trials_per_year(df: pd.DataFrame) -> pd.DataFrame:
    """Trial count by start year -- the top-line 'is this field growing' chart."""
    out = (
        df.dropna(subset=["start_year"])
        .groupby("start_year", as_index=False)
        .size()
        .rename(columns={"size": "trial_count"})
        .sort_values("start_year")
    )
    out["start_year"] = out["start_year"].astype(int)
    return out


def trials_by_condition_and_year(df: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """Trial volume over time, broken out by the most common conditions.
    Conditions is a '; '-joined string per trial, so we explode it first."""
    exploded = df.assign(condition=df["conditions"].str.split("; ")).explode("condition")
    exploded = exploded.dropna(subset=["condition", "start_year"])
    exploded = exploded[exploded["condition"].str.strip() != ""]

    top_conditions = exploded["condition"].value_counts().head(top_n).index
    exploded = exploded[exploded["condition"].isin(top_conditions)]

    out = (
        exploded.groupby(["start_year", "condition"], as_index=False)
        .size()
        .rename(columns={"size": "trial_count"})
    )
    out["start_year"] = out["start_year"].astype(int)
    return out


def sponsor_leaderboard(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Trial counts per lead sponsor -- the core competitive-landscape view."""
    out = (
        df.groupby(["lead_sponsor", "lead_sponsor_class"], as_index=False)
        .size()
        .rename(columns={"size": "trial_count"})
        .sort_values("trial_count", ascending=False)
        .head(top_n)
    )
    return out


def phase_funnel(df: pd.DataFrame) -> pd.DataFrame:
    """Count of trials at each phase -- a rough proxy for pipeline maturity."""
    out = df["phase"].value_counts().rename_axis("phase").reset_index(name="trial_count")
    order = {p: i for i, p in enumerate(PHASE_ORDER)}
    out["_sort"] = out["phase"].map(lambda p: order.get(p, len(PHASE_ORDER)))
    out = out.sort_values("_sort").drop(columns="_sort")
    return out


def load_fda_breakthrough_devices() -> pd.DataFrame:
    """Public FDA Breakthrough Device Designation records relevant to BCIs.
    See data/reference/fda_breakthrough_devices.csv for sourcing notes --
    this list is maintained by hand since the FDA does not expose a
    programmatic API for the Breakthrough Devices Program."""
    if not FDA_BREAKTHROUGH_PATH.exists():
        return pd.DataFrame(columns=["company", "device", "designation_year", "source_url"])
    return pd.read_csv(FDA_BREAKTHROUGH_PATH)


def sponsor_regulatory_cross_reference(df: pd.DataFrame) -> pd.DataFrame:
    """Join trial-sponsor activity against known FDA Breakthrough Device
    status, so the dashboard can flag which active sponsors already have
    a regulatory fast-track designation."""
    trial_counts = sponsor_leaderboard(df, top_n=1000)[["lead_sponsor", "trial_count"]]
    fda = load_fda_breakthrough_devices()
    if fda.empty:
        trial_counts["breakthrough_designation"] = False
        return trial_counts

    fda_companies = set(fda["company"].str.lower().str.strip())
    trial_counts["breakthrough_designation"] = (
        trial_counts["lead_sponsor"].str.lower().str.strip().isin(fda_companies)
    )
    return trial_counts


def whitespace_conditions(df: pd.DataFrame, recent_years: int = 3, max_sponsors: int = 2) -> pd.DataFrame:
    """Heuristic 'growth opportunity' flag: conditions with rising trial
    activity in the recent window but very few distinct sponsors -- i.e.
    validated patient need, thin competitive coverage."""
    exploded = df.assign(condition=df["conditions"].str.split("; ")).explode("condition")
    exploded = exploded.dropna(subset=["condition", "start_year"])
    exploded = exploded[exploded["condition"].str.strip() != ""]

    cutoff_year = int(df["start_year"].max()) - recent_years if df["start_year"].notna().any() else None
    recent = exploded[exploded["start_year"] >= cutoff_year] if cutoff_year else exploded

    summary = (
        recent.groupby("condition")
        .agg(trial_count=("nct_id", "nunique"), sponsor_count=("lead_sponsor", "nunique"))
        .reset_index()
        .sort_values("trial_count", ascending=False)
    )
    return summary[summary["sponsor_count"] <= max_sponsors]
