"""
models.py
---------
Pydantic response models. They mirror the JSON written by
src/export_json.py, so the API and the React site share one data shape.
"""

from __future__ import annotations

from pydantic import BaseModel


class BreakthroughDesignation(BaseModel):
    company: str
    device: str
    designation_year: int
    source_url: str


class Trial(BaseModel):
    nct_id: str
    brief_title: str
    overall_status: str
    phase: str
    study_type: str | None = None
    conditions: list[str]
    lead_sponsor: str
    lead_sponsor_class: str
    collaborators: list[str]
    interventions: list[str]
    start_date: str | None = None
    start_year: int | None = None
    countries: list[str]
    breakthrough_designations: list[BreakthroughDesignation]


class TrialPage(BaseModel):
    total: int
    limit: int
    offset: int
    trials: list[Trial]


class SponsorCount(BaseModel):
    sponsor: str
    trial_count: int
    has_breakthrough_designation: bool


class Stats(BaseModel):
    generated_at: str
    total_trials: int
    active_trials: int
    distinct_sponsors: int
    breakthrough_companies: int
    trials_by_status: dict[str, int]


class LiveStatus(BaseModel):
    """Current status pulled straight from ClinicalTrials.gov, compared with the
    status in our weekly snapshot so callers can see what changed."""

    nct_id: str
    snapshot_status: str | None
    live_status: str | None
    changed: bool
    error: str | None = None


class LiveStatusResponse(BaseModel):
    checked: int
    changed: int
    failed: int
    results: list[LiveStatus]
