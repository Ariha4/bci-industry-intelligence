import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyze import sponsor_matches_company, sponsor_regulatory_cross_reference
from src.export_json import build_payload, split_list

FDA_SAMPLE = pd.DataFrame([
    {"company": "Neuralink", "device": "N1 Implant", "designation_year": 2020, "source_url": "https://example.com/n1"},
    {"company": "Synchron", "device": "Stentrode", "designation_year": 2020, "source_url": "https://example.com/stentrode"},
])


def make_trial(nct_id, sponsor, phase="NA", conditions="ALS; Stroke", start_year=2024):
    return {
        "nct_id": nct_id, "brief_title": f"Trial {nct_id}", "overall_status": "RECRUITING",
        "phase": phase, "study_type": "INTERVENTIONAL", "conditions": conditions,
        "lead_sponsor": sponsor, "lead_sponsor_class": "INDUSTRY", "collaborators": "",
        "intervention_names": "Device A", "intervention_types": "DEVICE",
        "start_date": f"{start_year}-01", "start_year": start_year, "countries": "United States",
    }


def test_sponsor_matches_legal_entity_names():
    assert sponsor_matches_company("Neuralink Corp", "Neuralink")
    assert sponsor_matches_company("Synchron, Inc.", "Synchron")
    assert sponsor_matches_company("Synchron Australia Pty Ltd.", "Synchron")
    assert sponsor_matches_company("Paradromics", "Paradromics")


def test_sponsor_match_rejects_lookalike_names():
    # "Neuralinkage" is a different organization, not "Neuralink" + suffix
    assert not sponsor_matches_company("Neuralinkage Labs", "Neuralink")
    assert not sponsor_matches_company("University of Michigan", "Neuralink")


def test_cross_reference_flags_legal_entity_sponsors(monkeypatch):
    import src.analyze as analyze
    monkeypatch.setattr(analyze, "load_fda_breakthrough_devices", lambda: FDA_SAMPLE)
    trials_df = pd.DataFrame([make_trial("NCT1", "Neuralink Corp"), make_trial("NCT2", "University of Michigan")])
    result = sponsor_regulatory_cross_reference(trials_df).set_index("lead_sponsor")
    assert bool(result.loc["Neuralink Corp", "breakthrough_designation"]) is True
    assert bool(result.loc["University of Michigan", "breakthrough_designation"]) is False


def test_split_list_drops_blanks():
    assert split_list("ALS; ; Stroke ", ";") == ["ALS", "Stroke"]
    assert split_list(None, ";") == []


def test_build_payload_shapes_trials_for_frontend():
    trials_df = pd.DataFrame([
        make_trial("NCT1", "Synchron Medical, Inc."),
        make_trial("NCT2", "University of Michigan", phase="PHASE1"),
    ])
    payload = build_payload(trials_df, FDA_SAMPLE)

    assert payload["trial_count"] == 2
    first, second = payload["trials"]
    # alias map merges Synchron Medical into Synchron, Inc., which then matches the FDA list
    assert first["lead_sponsor"] == "Synchron, Inc."
    assert [d["device"] for d in first["breakthrough_designations"]] == ["Stentrode"]
    assert first["conditions"] == ["ALS", "Stroke"]
    assert first["phase"] == "NA"
    assert second["breakthrough_designations"] == []
    assert second["start_year"] == 2024
