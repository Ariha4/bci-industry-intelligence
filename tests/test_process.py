import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.process import flatten_study, load_processed, _first_year
from src.analyze import (
    trials_per_year,
    sponsor_leaderboard,
    phase_funnel,
    whitespace_conditions,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def sample_studies():
    return json.loads((FIXTURES_DIR / "sample_studies.json").read_text())


@pytest.fixture
def sample_df(sample_studies):
    rows = [flatten_study(s) for s in sample_studies]
    return pd.DataFrame(rows)


def test_first_year_handles_multiple_formats():
    assert _first_year("2024-03-15") == 2024
    assert _first_year("2021-09") == 2021
    assert _first_year(None) is None
    assert _first_year("") is None


def test_flatten_study_extracts_core_fields(sample_studies):
    row = flatten_study(sample_studies[0])
    assert row["nct_id"] == "NCT99990001"
    assert row["overall_status"] == "RECRUITING"
    assert row["lead_sponsor"] == "Example Neurotech Inc."
    assert "Amyotrophic Lateral Sclerosis" in row["conditions"]
    assert row["start_year"] == 2024
    assert row["intervention_types"] == "DEVICE"


def test_flatten_study_handles_missing_fields_gracefully(sample_studies):
    """The third fixture record has no dates, no interventions, no locations --
    real ClinicalTrials.gov data is frequently this incomplete."""
    row = flatten_study(sample_studies[2])
    assert row["nct_id"] == "NCT99990003"
    assert row["start_year"] is None
    assert row["intervention_names"] == ""
    assert row["countries"] == ""


def test_load_processed_dedupes_by_nct_id(tmp_path, sample_studies):
    duplicated = sample_studies + [sample_studies[0]]  # inject a duplicate
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(duplicated))

    df = load_processed(raw_path=raw_path)
    assert len(df) == 3  # duplicate collapsed
    assert df["nct_id"].is_unique


def test_trials_per_year(sample_df):
    out = trials_per_year(sample_df)
    assert set(out["start_year"]) == {2024, 2021}
    assert out.loc[out["start_year"] == 2024, "trial_count"].iloc[0] == 1


def test_sponsor_leaderboard(sample_df):
    out = sponsor_leaderboard(sample_df)
    top = out.iloc[0]
    assert top["lead_sponsor"] == "Example Neurotech Inc."
    assert top["trial_count"] == 2  # appears in fixtures 1 and 3


def test_phase_funnel_includes_na_for_missing_phase(sample_df):
    out = phase_funnel(sample_df)
    assert "NA" in out["phase"].values  # observational study has no phase


def test_whitespace_conditions_flags_thin_sponsor_coverage(sample_df):
    out = whitespace_conditions(sample_df, recent_years=10, max_sponsors=1)
    # ALS has 1 dated trial / 1 sponsor -- should qualify as thin coverage.
    # (Epilepsy's only fixture record has no start date, so it's correctly
    # excluded from a *recent-activity* trend -- undated trials can't be
    # placed in a time window.)
    assert "Amyotrophic Lateral Sclerosis" in out["condition"].values
    assert "Epilepsy" not in out["condition"].values
