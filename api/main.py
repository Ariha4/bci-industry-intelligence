"""
main.py
-------
FastAPI service for the BCI trial dataset.

Run locally:
    uvicorn api.main:app --reload
Then open http://127.0.0.1:8000/docs for interactive API docs.

The dataset is loaded once at startup from web/public/data/trials.json (the
same file the weekly refresh writes for the React site). One shared async
HTTP client is opened at startup and reused by the live-status endpoint.
"""

from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from api import data, live
from api.models import LiveStatusResponse, SponsorCount, Stats, Trial, TrialPage

NCT_ID_PATTERN = re.compile(r"^NCT\d{8}$")
MAX_LIVE_CHECKS = 25


@asynccontextmanager
async def lifespan(app: FastAPI):
    data_path = Path(os.environ.get("BCI_DATA_PATH", data.DEFAULT_DATA_PATH))
    app.state.dataset = data.load_dataset(data_path)
    app.state.http_client = httpx.AsyncClient(headers={"User-Agent": "bci-industry-intelligence/1.0"})
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="BCI Trial Tracker API",
    description="Brain-computer interface clinical trials from ClinicalTrials.gov, refreshed weekly.",
    version="1.0.0",
    lifespan=lifespan,
)

# Let the GitHub Pages site (and local dev servers) call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ariha4.github.io", "http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET"],
)


def get_dataset(request: Request) -> dict:
    return request.app.state.dataset


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


@app.get("/health")
async def health(dataset: dict = Depends(get_dataset)) -> dict:
    return {"status": "ok", "trials_loaded": len(dataset["trials"]), "data_generated_at": dataset["generated_at"]}


@app.get("/stats", response_model=Stats)
async def stats(dataset: dict = Depends(get_dataset)) -> dict:
    return data.summarize(dataset)


@app.get("/trials", response_model=TrialPage)
async def list_trials(
    search: str | None = Query(None, description="Matches title, sponsor, NCT ID, conditions, interventions"),
    status: str | None = Query(None, description="e.g. RECRUITING, COMPLETED"),
    sponsor_type: Literal["industry", "academic", "government"] | None = None,
    active_only: bool = False,
    breakthrough_only: bool = Query(False, description="Only sponsors with an FDA Breakthrough Device Designation"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    dataset: dict = Depends(get_dataset),
) -> dict:
    matching_trials = data.filter_trials(
        dataset["trials"], search, status, sponsor_type, active_only, breakthrough_only
    )
    return {
        "total": len(matching_trials),
        "limit": limit,
        "offset": offset,
        "trials": matching_trials[offset : offset + limit],
    }


@app.get("/trials/{nct_id}", response_model=Trial)
async def get_trial(nct_id: str, dataset: dict = Depends(get_dataset)) -> dict:
    trial = data.find_trial(dataset["trials"], nct_id)
    if trial is None:
        raise HTTPException(status_code=404, detail=f"Trial {nct_id} not found")
    return trial


@app.get("/sponsors", response_model=list[SponsorCount])
async def sponsors(limit: int = Query(10, ge=1, le=100), dataset: dict = Depends(get_dataset)) -> list[dict]:
    return data.sponsor_leaderboard(dataset["trials"], limit)


@app.get("/live-status", response_model=LiveStatusResponse)
async def live_status(
    ids: str | None = Query(None, description="Comma-separated NCT IDs; defaults to the snapshot's active trials"),
    dataset: dict = Depends(get_dataset),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> dict:
    """Check the current status of trials on ClinicalTrials.gov, concurrently,
    and flag any whose status changed since the weekly snapshot."""
    if ids:
        nct_ids = []
        for raw_id in ids.split(","):
            cleaned_id = raw_id.strip().upper()
            if cleaned_id:
                nct_ids.append(cleaned_id)
        for nct_id in nct_ids:
            if not NCT_ID_PATTERN.match(nct_id):
                raise HTTPException(status_code=422, detail=f"Invalid NCT ID: {nct_id}")
    else:
        nct_ids = []
        for trial in dataset["trials"]:
            if trial["overall_status"] in data.ACTIVE_STATUSES:
                nct_ids.append(trial["nct_id"])
    if len(nct_ids) > MAX_LIVE_CHECKS:
        nct_ids = nct_ids[:MAX_LIVE_CHECKS]

    live_results = await live.fetch_many_live_statuses(http_client, nct_ids)

    results = []
    changed_count = 0
    failed_count = 0
    for live_result in live_results:
        snapshot_trial = data.find_trial(dataset["trials"], live_result["nct_id"])
        snapshot_status = snapshot_trial["overall_status"] if snapshot_trial else None
        changed = (
            live_result["error"] is None
            and snapshot_status is not None
            and live_result["live_status"] != snapshot_status
        )
        if changed:
            changed_count += 1
        if live_result["error"] is not None:
            failed_count += 1
        results.append({
            "nct_id": live_result["nct_id"],
            "snapshot_status": snapshot_status,
            "live_status": live_result["live_status"],
            "changed": changed,
            "error": live_result["error"],
        })
    return {"checked": len(results), "changed": changed_count, "failed": failed_count, "results": results}
