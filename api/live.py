"""
live.py
-------
Async client for the ClinicalTrials.gov API v2. Checks the current status of
many trials at once: requests run concurrently with asyncio.gather, a
semaphore caps how many are in flight (to be polite to the public API), and
each request has its own timeout so one slow trial can't stall the batch.
"""

from __future__ import annotations

import asyncio

import httpx

API_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
MAX_CONCURRENT_REQUESTS = 5
REQUEST_TIMEOUT_SECONDS = 10.0


async def fetch_live_status(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, nct_id: str) -> dict:
    """Return {"nct_id", "live_status", "error"} for one trial. Never raises:
    a failure becomes an error message so the rest of the batch still returns."""
    async with semaphore:
        try:
            response = await client.get(
                f"{API_BASE_URL}/{nct_id}",
                params={"fields": "protocolSection.statusModule.overallStatus"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 404:
                return {"nct_id": nct_id, "live_status": None, "error": "Not found on ClinicalTrials.gov"}
            response.raise_for_status()
            status_module = response.json().get("protocolSection", {}).get("statusModule", {})
            return {"nct_id": nct_id, "live_status": status_module.get("overallStatus"), "error": None}
        except httpx.TimeoutException:
            return {"nct_id": nct_id, "live_status": None, "error": "Timed out"}
        except httpx.HTTPError as http_error:
            return {"nct_id": nct_id, "live_status": None, "error": f"Request failed: {http_error.__class__.__name__}"}


async def fetch_many_live_statuses(client: httpx.AsyncClient, nct_ids: list[str]) -> list[dict]:
    """Check all trials concurrently and return results in the same order as nct_ids."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    tasks = []
    for nct_id in nct_ids:
        tasks.append(fetch_live_status(client, semaphore, nct_id))
    return await asyncio.gather(*tasks)
