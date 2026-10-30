"""Minimal async A2A-style client: POST a JSON payload to an agent's /run
endpoint and return its JSON response.

Timeout is generous (not the spec's original 60s) because each downstream
agent can itself retry OpenAI 429s with backoff (see common/adk_runner.py) —
a 60s client-side timeout would cut off a call that's still legitimately
retrying server-side, surfacing a confusing empty-message httpx.ReadTimeout
instead of the real quota error.
"""

from __future__ import annotations

import httpx

DEFAULT_TIMEOUT_SECONDS = 240.0


async def call_agent(url: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
