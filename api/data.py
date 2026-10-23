"""
data.py
-------
Loads the trial dataset once and answers queries against it. Pure functions
over plain lists, so they are easy to test without starting a server.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = ROOT / "web" / "public" / "data" / "trials.json"

# Statuses that mean a trial is running or about to start (same rule as the React site).
ACTIVE_STATUSES = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING"}


def load_dataset(data_path: Path = DEFAULT_DATA_PATH) -> dict:
    """Read the JSON written by src/export_json.py."""
    return json.loads(Path(data_path).read_text())


def sponsor_type_of(sponsor_class: str) -> str:
    if sponsor_class == "INDUSTRY":
        return "industry"
    if sponsor_class in ("FED", "OTHER_GOV", "NIH"):
        return "government"
    return "academic"


def filter_trials(
    trials: list[dict],
    search: str | None = None,
    status: str | None = None,
    sponsor_type: str | None = None,
    active_only: bool = False,
    breakthrough_only: bool = False,
) -> list[dict]:
    """Every filter is optional; trials must pass all filters that are set."""
    query = (search or "").strip().lower()
    matching_trials = []
    for trial in trials:
        if query:
            searchable_fields = [trial["brief_title"], trial["lead_sponsor"], trial["nct_id"]]
            searchable_fields += trial["conditions"] + trial["interventions"]
            found = False
            for field in searchable_fields:
                if query in field.lower():
                    found = True
                    break
            if not found:
                continue
        if status and trial["overall_status"] != status.upper():
            continue
        if sponsor_type and sponsor_type_of(trial["lead_sponsor_class"]) != sponsor_type.lower():
            continue
        if active_only and trial["overall_status"] not in ACTIVE_STATUSES:
            continue
        if breakthrough_only and not trial["breakthrough_designations"]:
            continue
        matching_trials.append(trial)
    return matching_trials


def find_trial(trials: list[dict], nct_id: str) -> dict | None:
    wanted_id = nct_id.strip().upper()
    for trial in trials:
        if trial["nct_id"].upper() == wanted_id:
            return trial
    return None


def sponsor_leaderboard(trials: list[dict], limit: int) -> list[dict]:
    """Sponsors ranked by trial count, largest first (ties broken by name)."""
    counts_by_sponsor: dict[str, int] = {}
    breakthrough_by_sponsor: dict[str, bool] = {}
    for trial in trials:
        sponsor = trial["lead_sponsor"]
        counts_by_sponsor[sponsor] = counts_by_sponsor.get(sponsor, 0) + 1
        if trial["breakthrough_designations"]:
            breakthrough_by_sponsor[sponsor] = True
    rows = []
    for sponsor, trial_count in counts_by_sponsor.items():
        rows.append({
            "sponsor": sponsor,
            "trial_count": trial_count,
            "has_breakthrough_designation": breakthrough_by_sponsor.get(sponsor, False),
        })
    rows.sort(key=lambda row: (-row["trial_count"], row["sponsor"]))
    return rows[:limit]


def summarize(dataset: dict) -> dict:
    trials = dataset["trials"]
    active_trials = 0
    sponsors = set()
    breakthrough_companies = set()
    trials_by_status: dict[str, int] = {}
    for trial in trials:
        if trial["overall_status"] in ACTIVE_STATUSES:
            active_trials += 1
        sponsors.add(trial["lead_sponsor"])
        for designation in trial["breakthrough_designations"]:
            breakthrough_companies.add(designation["company"])
        status = trial["overall_status"]
        trials_by_status[status] = trials_by_status.get(status, 0) + 1
    return {
        "generated_at": dataset["generated_at"],
        "total_trials": len(trials),
        "active_trials": active_trials,
        "distinct_sponsors": len(sponsors),
        "breakthrough_companies": len(breakthrough_companies),
        "trials_by_status": trials_by_status,
    }
