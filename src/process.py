"""
process.py
----------
Flattens raw ClinicalTrials.gov API v2 study records (deeply nested JSON)
into a tidy pandas DataFrame suitable for analysis and the dashboard.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "trials_raw.json"
PROCESSED_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "trials_processed.csv"


def _first_year(date_str: str | None) -> int | None:
    """ClinicalTrials.gov dates arrive in inconsistent formats
    ('2024-01', '2024-01-15', 'January 2024'). We only need the year."""
    if not date_str:
        return None
    for token in date_str.replace("-", " ").split():
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


def flatten_study(study: dict) -> dict:
    """Extract the fields we care about from one nested study record."""
    protocol = study.get("protocolSection", {})

    ident = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {})
    design = protocol.get("designModule", {})
    conditions_mod = protocol.get("conditionsModule", {})
    arms = protocol.get("armsInterventionsModule", {})
    locations = protocol.get("contactsLocationsModule", {}).get("locations", [])

    interventions = arms.get("interventions", [])
    intervention_names = [i.get("name", "") for i in interventions]
    intervention_types = sorted({i.get("type", "") for i in interventions if i.get("type")})

    lead_sponsor = sponsor.get("leadSponsor", {})
    collaborators = [c.get("name", "") for c in sponsor.get("collaborators", [])]

    start_date = status.get("startDateStruct", {}).get("date")
    countries = sorted({loc.get("country", "") for loc in locations if loc.get("country")})

    return {
        "nct_id": ident.get("nctId"),
        "brief_title": ident.get("briefTitle"),
        "overall_status": status.get("overallStatus"),
        "phase": ",".join(design.get("phases", [])) or "NA",
        "study_type": design.get("studyType"),
        "conditions": "; ".join(conditions_mod.get("conditions", [])),
        "lead_sponsor": lead_sponsor.get("name"),
        "lead_sponsor_class": lead_sponsor.get("class"),
        "collaborators": "; ".join(collaborators),
        "intervention_names": "; ".join(intervention_names),
        "intervention_types": ",".join(intervention_types),
        "start_date": start_date,
        "start_year": _first_year(start_date),
        "countries": "; ".join(countries),
    }


def load_processed(raw_path: Path = RAW_PATH) -> pd.DataFrame:
    """Load raw JSON, flatten every study, and return a tidy DataFrame."""
    studies = json.loads(raw_path.read_text())
    rows = [flatten_study(s) for s in studies]
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset="nct_id").reset_index(drop=True)
    return df


def main() -> None:
    df = load_processed()
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)
    print(f"Wrote {len(df)} rows to {PROCESSED_PATH}")


if __name__ == "__main__":
    main()
