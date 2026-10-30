"""Minimal A2A-style server: wraps any async task handler in a FastAPI app
with a single POST /run endpoint (plus a GET /health check)."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

RunFn = Callable[[dict], Awaitable[dict]]


def create_app(agent_name: str, run_fn: RunFn) -> FastAPI:
    app = FastAPI(title=agent_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "agent": agent_name}

    @app.post("/run")
    async def run(payload: dict) -> dict:
        try:
            return await run_fn(payload)
        except Exception as exc:  # noqa: BLE001 — surface any failure as a 500
            logger.exception("%s failed to process /run request", agent_name)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app
