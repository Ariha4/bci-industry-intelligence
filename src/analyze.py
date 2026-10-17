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

# ClinicalTrials.gov sponsor names aren't fully standardized -- the same
# company can appear under slightly different legal-entity names across
# trials (e.g. a company renaming, or a trial registered under a subsidiary
# name). This map merges known variants we've observed in this dataset so
# sponsor-level counts aren't artificially split. Extend as new variants
# turn up in future data refreshes.
SPONSOR_NAME_ALIASES = {
    "Synchron Medical, Inc.": "Synchron, Inc.",
}


def _normalize_sponsor(name: str) -> str:
    return SPONSOR_NAME_ALIASES.get(name, name)


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
    df = df.copy()
    df["lead_sponsor"] = df["lead_sponsor"].apply(_normalize_sponsor)
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

    fda_companies = list(fda["company"])
    trial_counts["breakthrough_designation"] = trial_counts["lead_sponsor"].apply(
        lambda sponsor_name: sponsor_has_designation(sponsor_name, fda_companies)
    )
    return trial_counts


def sponsor_matches_company(sponsor_name: str, company_name: str) -> bool:
    """True when a trial sponsor is the same organization as an FDA-list company.

    Sponsors are registered under legal-entity names ("Neuralink Corp",
    "Synchron, Inc.", "Synchron Australia Pty Ltd.") while the FDA list uses
    the short company name ("Neuralink", "Synchron"). An exact string match
    misses these, so we accept the company name followed by a space or comma.
    """
    sponsor_lower = str(sponsor_name).lower().strip()
    company_lower = str(company_name).lower().strip()
    if sponsor_lower == company_lower:
        return True
    for separator in (" ", ","):
        if sponsor_lower.startswith(company_lower + separator):
            return True
    return False


def sponsor_has_designation(sponsor_name: str, fda_companies: list[str]) -> bool:
    for company_name in fda_companies:
        if sponsor_matches_company(sponsor_name, company_name):
            return True
    return False


def whitespace_conditions(df: pd.DataFrame, recent_years: int = 3, max_sponsors: int = 2) -> pd.DataFrame:
    """Heuristic 'growth opportunity' flag: conditions with rising trial
    activity in the recent window but very few distinct sponsors -- i.e.
    validated patient need, thin competitive coverage."""
    exploded = df.assign(condition=df["conditions"].str.split("; ")).explode("condition")
    exploded = exploded.dropna(subset=["condition", "start_year"])
    exploded = exploded[exploded["condition"].str.strip() != ""]
    exploded["lead_sponsor"] = exploded["lead_sponsor"].apply(_normalize_sponsor)

    cutoff_year = int(df["start_year"].max()) - recent_years if df["start_year"].notna().any() else None
    recent = exploded[exploded["start_year"] >= cutoff_year] if cutoff_year else exploded

    summary = (
        recent.groupby("condition")
        .agg(trial_count=("nct_id", "nunique"), sponsor_count=("lead_sponsor", "nunique"))
        .reset_index()
        .sort_values("trial_count", ascending=False)
    )
    return summary[summary["sponsor_count"] <= max_sponsors]
