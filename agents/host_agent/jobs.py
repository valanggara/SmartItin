"""In-memory job store backing /run-async + /status/{job_id} polling, and
/modify-itinerary (which needs the original trip request to reconstruct
context — destination/budget_tier/theme/nights — for the itinerary agent).

Deliberately simple (single-process dict, no TTL/eviction) — this is a dev
server for a single-user trip planner, not a durable multi-worker queue.
"""

from __future__ import annotations

import uuid
from typing import Any

JOB_SECTIONS = ["flights", "research", "accommodation", "itinerary", "cost_summary"]

_jobs: dict[str, dict[str, Any]] = {}


def create_job(request: dict) -> str:
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {
        "status": "running",
        "sections": {key: None for key in JOB_SECTIONS},
        "error": None,
        "request": request,
    }
    return job_id


def set_section(job_id: str, key: str, value: Any) -> None:
    _jobs[job_id]["sections"][key] = value


def mark_done(job_id: str) -> None:
    _jobs[job_id]["status"] = "done"


def mark_failed(job_id: str, error: str) -> None:
    _jobs[job_id]["status"] = "error"
    _jobs[job_id]["error"] = error


def get_job(job_id: str) -> dict[str, Any] | None:
    return _jobs.get(job_id)
