"""
Tests for the FastAPI service. ClinicalTrials.gov is never called: the live
endpoint gets an httpx client backed by a mock transport, so these tests run
offline and the same way in CI.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import live  # noqa: E402
from api.main import app, get_http_client  # noqa: E402

DESIGNATION = {"company": "Neuralink", "device": "N1 Implant", "designation_year": 2020, "source_url": "https://example.com"}


def make_trial(nct_id, title, sponsor, sponsor_class="OTHER", status="RECRUITING", designations=None, conditions=None):
    return {
        "nct_id": nct_id, "brief_title": title, "overall_status": status, "phase": "NA",
        "study_type": "INTERVENTIONAL", "conditions": conditions or ["ALS"], "lead_sponsor": sponsor,
        "lead_sponsor_class": sponsor_class, "collaborators": [], "interventions": ["Implant"],
        "start_date": "2024-01", "start_year": 2024, "countries": ["United States"],
        "breakthrough_designations": designations or [],
    }


SAMPLE_DATASET = {
    "generated_at": "2026-10-19T09:05:00+00:00",
    "trial_count": 4,
    "trials": [
        make_trial("NCT00000001", "PRIME Study of the N1 Implant", "Neuralink Corp", "INDUSTRY", designations=[DESIGNATION]),
        make_trial("NCT00000002", "CONVOY Study", "Neuralink Corp", "INDUSTRY", status="ENROLLING_BY_INVITATION", designations=[DESIGNATION]),
        make_trial("NCT00000003", "BCI Mirror Therapy After Stroke", "Beijing Tiantan Hospital", status="COMPLETED", conditions=["Stroke"]),
        make_trial("NCT00000004", "Speech Neuroprosthesis", "NINDS", "NIH", status="NOT_YET_RECRUITING"),
    ],
    "fda_breakthrough_devices": [DESIGNATION],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    data_file = tmp_path / "trials.json"
    data_file.write_text(json.dumps(SAMPLE_DATASET))
    monkeypatch.setenv("BCI_DATA_PATH", str(data_file))
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def use_mock_clinicaltrials(handler):
    """Route the live endpoint's HTTP calls to `handler` instead of the real API."""
    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_http_client] = lambda: mock_client


def study_response(status):
    return httpx.Response(200, json={"protocolSection": {"statusModule": {"overallStatus": status}}})


# ---------- dataset endpoints ----------

def test_health_reports_loaded_trials(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "trials_loaded": 4, "data_generated_at": "2026-10-19T09:05:00+00:00"}


def test_stats_counts_active_trials_and_companies(client):
    body = client.get("/stats").json()
    assert body["total_trials"] == 4
    assert body["active_trials"] == 3  # recruiting, enrolling by invitation, not yet recruiting
    assert body["breakthrough_companies"] == 1
    assert body["trials_by_status"]["COMPLETED"] == 1


def test_trials_filters_combine(client):
    body = client.get("/trials", params={"sponsor_type": "industry", "breakthrough_only": True}).json()
    assert body["total"] == 2
    assert {trial["nct_id"] for trial in body["trials"]} == {"NCT00000001", "NCT00000002"}

    body = client.get("/trials", params={"search": "stroke", "active_only": True}).json()
    assert body["total"] == 0  # the stroke trial is completed


def test_trials_pagination(client):
    body = client.get("/trials", params={"limit": 3, "offset": 2}).json()
    assert body["total"] == 4
    assert [trial["nct_id"] for trial in body["trials"]] == ["NCT00000003", "NCT00000004"]


def test_trials_rejects_bad_query_params(client):
    assert client.get("/trials", params={"limit": 0}).status_code == 422
    assert client.get("/trials", params={"sponsor_type": "startup"}).status_code == 422


def test_single_trial_and_404(client):
    assert client.get("/trials/nct00000003").json()["brief_title"] == "BCI Mirror Therapy After Stroke"
    response = client.get("/trials/NCT99999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Trial NCT99999999 not found"


def test_sponsor_leaderboard(client):
    body = client.get("/sponsors", params={"limit": 1}).json()
    assert body == [{"sponsor": "Neuralink Corp", "trial_count": 2, "has_breakthrough_designation": True}]


# ---------- live-status endpoint (async, mocked network) ----------

def test_live_status_flags_changed_trials(client):
    live_statuses = {"NCT00000001": "ACTIVE_NOT_RECRUITING", "NCT00000004": "NOT_YET_RECRUITING"}

    def handler(request):
        nct_id = request.url.path.rsplit("/", 1)[-1]
        return study_response(live_statuses[nct_id])

    use_mock_clinicaltrials(handler)
    body = client.get("/live-status", params={"ids": "NCT00000001, nct00000004"}).json()
    assert body["checked"] == 2 and body["changed"] == 1 and body["failed"] == 0
    first, second = body["results"]
    assert first == {"nct_id": "NCT00000001", "snapshot_status": "RECRUITING",
                     "live_status": "ACTIVE_NOT_RECRUITING", "changed": True, "error": None}
    assert second["changed"] is False


def test_live_status_defaults_to_active_trials(client):
    requested_ids = []

    def handler(request):
        nct_id = request.url.path.rsplit("/", 1)[-1]
        requested_ids.append(nct_id)
        return study_response("RECRUITING")

    use_mock_clinicaltrials(handler)
    body = client.get("/live-status").json()
    assert sorted(requested_ids) == ["NCT00000001", "NCT00000002", "NCT00000004"]
    assert body["checked"] == 3


def test_live_status_reports_failures_without_failing_the_batch(client):
    def handler(request):
        nct_id = request.url.path.rsplit("/", 1)[-1]
        if nct_id == "NCT00000001":
            raise httpx.ReadTimeout("slow", request=request)
        if nct_id == "NCT00000002":
            return httpx.Response(404)
        if nct_id == "NCT00000003":
            return httpx.Response(503)
        return study_response("NOT_YET_RECRUITING")

    use_mock_clinicaltrials(handler)
    body = client.get("/live-status", params={"ids": "NCT00000001,NCT00000002,NCT00000003,NCT00000004"}).json()
    errors = {result["nct_id"]: result["error"] for result in body["results"]}
    assert errors == {
        "NCT00000001": "Timed out",
        "NCT00000002": "Not found on ClinicalTrials.gov",
        "NCT00000003": "Request failed: HTTPStatusError",
        "NCT00000004": None,
    }
    assert body["failed"] == 3 and body["changed"] == 0


def test_live_status_validates_ids(client):
    response = client.get("/live-status", params={"ids": "NCT1,DROP TABLE"})
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid NCT ID: NCT1"


def test_fetches_run_concurrently_but_capped_by_semaphore():
    """Twelve requests that each take 0.1s should finish in about 3 rounds
    (cap of 5 in flight), not 12 sequential rounds, and never exceed the cap."""
    in_flight = 0
    max_in_flight = 0

    async def slow_handler(request):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.1)
        in_flight -= 1
        return study_response("RECRUITING")

    async def run_batch():
        async with httpx.AsyncClient(transport=httpx.MockTransport(slow_handler)) as mock_client:
            nct_ids = [f"NCT{index:08d}" for index in range(12)]
            started = time.perf_counter()
            results = await live.fetch_many_live_statuses(mock_client, nct_ids)
            return results, time.perf_counter() - started

    results, elapsed_seconds = asyncio.run(run_batch())
    assert [result["nct_id"] for result in results] == [f"NCT{index:08d}" for index in range(12)]
    assert max_in_flight == live.MAX_CONCURRENT_REQUESTS
    assert elapsed_seconds < 0.6  # sequential would take about 1.2s
