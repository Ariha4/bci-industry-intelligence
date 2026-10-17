"""
export_json.py
--------------
Writes the processed trial dataset as one JSON file for the React front end
(web/). Runs after process.py in the weekly GitHub Actions refresh, so the
website always shows the same data as the Streamlit dashboard.

Output: web/public/data/trials.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyze import (  # noqa: E402
    FDA_BREAKTHROUGH_PATH,
    _normalize_sponsor,
    sponsor_matches_company,
)

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PATH = ROOT / "data" / "raw" / "trials_processed.csv"
OUTPUT_PATH = ROOT / "web" / "public" / "data" / "trials.json"


def split_list(value: object, separator: str) -> list[str]:
    """The CSV stores lists as joined strings ('ALS; Stroke'). Split them back."""
    if not isinstance(value, str) or value.strip() == "":
        return []
    parts = []
    for part in value.split(separator):
        cleaned = part.strip()
        if cleaned:
            parts.append(cleaned)
    return parts


def clean_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    return None


def build_payload(trials_df: pd.DataFrame, fda_df: pd.DataFrame) -> dict:
    """Turn the tidy DataFrame and the FDA reference list into the JSON
    structure the front end expects (see web/src/types.ts)."""
    fda_records = []
    for _, fda_row in fda_df.iterrows():
        fda_records.append({
            "company": fda_row["company"],
            "device": fda_row["device"],
            "designation_year": int(fda_row["designation_year"]),
            "source_url": fda_row["source_url"],
        })

    trials = []
    for _, row in trials_df.iterrows():
        sponsor_name = _normalize_sponsor(clean_text(row["lead_sponsor"]) or "Unknown")

        matching_designations = []
        for fda_record in fda_records:
            if sponsor_matches_company(sponsor_name, fda_record["company"]):
                matching_designations.append(fda_record)

        start_year = row["start_year"]
        trials.append({
            "nct_id": row["nct_id"],
            "brief_title": clean_text(row["brief_title"]) or "",
            "overall_status": clean_text(row["overall_status"]) or "UNKNOWN",
            "phase": clean_text(row["phase"]) or "NA",
            "study_type": clean_text(row["study_type"]),
            "conditions": split_list(row["conditions"], ";"),
            "lead_sponsor": sponsor_name,
            "lead_sponsor_class": clean_text(row["lead_sponsor_class"]) or "OTHER",
            "collaborators": split_list(row["collaborators"], ";"),
            "interventions": split_list(row["intervention_names"], ";"),
            "start_date": clean_text(row["start_date"]),
            "start_year": int(start_year) if pd.notna(start_year) else None,
            "countries": split_list(row["countries"], ";"),
            "breakthrough_designations": matching_designations,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trial_count": len(trials),
        "trials": trials,
        "fda_breakthrough_devices": fda_records,
    }


def main() -> None:
    # keep_default_na=False: the phase "NA" (not applicable, e.g. device
    # trials) must stay the string "NA" instead of becoming a missing value.
    trials_df = pd.read_csv(PROCESSED_PATH, keep_default_na=False, na_values=[""])
    fda_df = pd.read_csv(FDA_BREAKTHROUGH_PATH)
    payload = build_payload(trials_df, fda_df)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    print(f"Wrote {payload['trial_count']} trials to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
