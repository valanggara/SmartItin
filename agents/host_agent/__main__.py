from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import HTTPException

from common.a2a_server import create_app

from . import jobs
from .task_manager import handle_modify_itinerary, handle_task, run_trip_stream

app = create_app("host_agent", handle_task)


async def _run_job(job_id: str, payload: dict) -> None:
    try:
        async for key, value in run_trip_stream(payload):
            jobs.set_section(job_id, key, value)
        jobs.mark_done(job_id)
    except Exception as exc:  # noqa: BLE001 — surface as a failed job, not a crashed task
        jobs.mark_failed(job_id, str(exc))


@app.post("/run-async")
async def run_async(payload: dict) -> dict:
    job_id = jobs.create_job(payload)
    asyncio.create_task(_run_job(job_id, payload))
    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def status(job_id: str) -> dict:
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.post("/debug/inject-job")
async def debug_inject_job(payload: dict) -> dict:
    """Dev-only: builds a job directly from pre-supplied sections instead of
    running the full pipeline — for previewing a change (e.g. a new
    itinerary_agent prompt) in the frontend by reusing already-fetched data,
    without spending new SerpAPI/LLM quota on flights/research/accommodation
    that haven't changed. Not part of the public trip-planning flow."""
    job_id = jobs.create_job(payload.get("request", {}))
    for key, value in payload.get("sections", {}).items():
        jobs.set_section(job_id, key, value)
    jobs.mark_done(job_id)
    return {"job_id": job_id}


@app.post("/modify-itinerary")
async def modify_itinerary(payload: dict) -> dict:
    job_id = payload.get("job_id")
    action = payload.get("action")
    action_params = payload.get("action_params") or {}
    if not job_id or not action:
        raise HTTPException(status_code=400, detail="job_id and action are required")

    result = await handle_modify_itinerary(job_id, action, action_params)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


if __name__ == "__main__":
    port = int(os.getenv("HOST_AGENT_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
