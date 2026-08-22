"""
fetch_trials.py
----------------
Pulls clinical trial records relevant to brain-computer interfaces (BCIs)
from the public ClinicalTrials.gov API v2 (https://clinicaltrials.gov/data-api/api).

No authentication required. The API is free and rate-limit-friendly, but we
still query narrowly and cache results locally so repeated runs don't hammer
the endpoint.

Strategy
--------
A single free-text search for "brain-computer interface" is too noisy -- it
matches unrelated trials that happen to contain the word "interface" or
"brain" (e.g. mental-health referral interfaces, unrelated CNS oncology
trials). Instead we run a set of *targeted* queries and merge + de-duplicate
the results by NCT ID:

  1. Intervention-name searches for known BCI/neural-interface device terms.
  2. Sponsor searches for named BCI companies (the competitive set relevant
     to this project).
  3. Condition searches for the patient populations BCIs primarily target,
     intersected with device-type interventions.

Run:
    python src/fetch_trials.py

Output:
    data/raw/trials_raw.json   -- deduplicated raw API records
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://clinicaltrials.gov/api/v2/studies"

# NOTE: we deliberately do NOT pass a `fields=` restriction to the API.
# ClinicalTrials.gov's `fields` parameter only accepts a specific set of
# whitelisted names, several of which (e.g. a sponsor-class field, an
# intervention-type field) don't exist under the names you'd guess from the
# JSON schema and cause a 400 Bad Request. Fetching full records is more
# bandwidth but far more robust -- src/process.py's flatten_study() already
# parses the full nested protocolSection regardless.

# Device/technology terms used in trial intervention names.
INTERVENTION_TERMS = [
    "brain-computer interface",
    "brain computer interface",
    "neural interface",
    "intracortical microelectrode",
    "cortical implant",
    "brain implant",
]

# Named companies in the BCI competitive set. Sponsor-name search catches
# trials these companies are running or co-running, even when the trial
# title/intervention text doesn't use one of the generic terms above.
SPONSOR_TERMS = [
    "Blackrock Neurotech",
    "Neuralink",
    "Synchron",
    "Precision Neuroscience",
    "Paradromics",
    "Onward Medical",
    "Ripple Neuro",
    "Motif Neurotech",
    "NeuroPace",
]

# Patient populations BCIs primarily target. Paired with a device-type
# intervention filter so we don't pull in unrelated drug trials for the
# same condition.
CONDITION_TERMS = [
    "Amyotrophic Lateral Sclerosis",
    "Spinal Cord Injury",
    "Tetraplegia",
    "Locked-In Syndrome",
    "Epilepsy",
]

RAW_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "trials_raw.json"
REQUEST_DELAY_SECONDS = 0.34  # be polite to the public API


def _get(params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, "format": "json"}
    resp = requests.get(API_BASE, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _paginate(params: dict[str, Any], page_size: int = 100, max_pages: int = 20) -> list[dict]:
    """Follow nextPageToken until exhausted or max_pages is hit."""
    studies: list[dict] = []
    page_token = None
    for _ in range(max_pages):
        query = {**params, "pageSize": page_size}
        if page_token:
            query["pageToken"] = page_token
        data = _get(query)
        studies.extend(data.get("studies", []))
        page_token = data.get("nextPageToken")
        time.sleep(REQUEST_DELAY_SECONDS)
        if not page_token:
            break
    return studies


def fetch_by_intervention() -> list[dict]:
    results = []
    for term in INTERVENTION_TERMS:
        results.extend(_paginate({"query.intr": term}))
    return results


def fetch_by_sponsor() -> list[dict]:
    results = []
    for name in SPONSOR_TERMS:
        results.extend(_paginate({"query.spons": name}))
    return results


def fetch_by_condition_and_device() -> list[dict]:
    """Condition trials, restricted to device-type interventions, to avoid
    pulling in unrelated drug/biologic trials for the same condition."""
    results = []
    for condition in CONDITION_TERMS:
        results.extend(
            _paginate({"query.cond": condition, "filter.advanced": "AREA[InterventionType]DEVICE"})
        )
    return results


def dedupe(studies: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for s in studies:
        nct_id = s.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
        if nct_id and nct_id not in seen:
            seen[nct_id] = s
    return list(seen.values())


def main() -> None:
    print("Fetching by intervention name...")
    by_intr = fetch_by_intervention()
    print(f"  {len(by_intr)} records")

    print("Fetching by sponsor...")
    by_spons = fetch_by_sponsor()
    print(f"  {len(by_spons)} records")

    print("Fetching by condition + device intervention...")
    by_cond = fetch_by_condition_and_device()
    print(f"  {len(by_cond)} records")

    merged = dedupe(by_intr + by_spons + by_cond)
    print(f"Total unique trials after dedup: {len(merged)}")

    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_OUTPUT_PATH.write_text(json.dumps(merged, indent=2))
    print(f"Wrote {RAW_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
