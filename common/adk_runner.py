"""Shared plumbing for invoking a google-adk Agent for a single turn.

Every LLM-powered agent in this project is a stateless, single-shot
microservice (no multi-turn conversation to persist across /run calls), so
each invocation gets its own throwaway InMemorySessionService session — a
fresh one per retry attempt too, since resuming a session that failed
mid-turn could leave a dangling user message with no model response.

Retries with backoff on transient OpenAI errors (429 rate limit, 5xx,
timeouts, dropped connections): the host agent fires the Flight, Research,
and Accommodation agents in parallel, each making 2 sequential LLM calls
(gatherer + formatter) — up to ~6 concurrent calls per trip request. Low
OpenAI usage tiers hit their requests/tokens-per-minute limits under this
pattern (429), and the API also returns occasional transient 5xx errors —
both are worth retrying rather than failing the whole trip request. We use
the API's own `retry-after` header when present, falling back to
exponential backoff otherwise.

run_agent_and_get_tool_result() exists because trusting an LLM to relay or
reformat a tool's output verbatim has proven unreliable in practice (a real
production run had the gatherer's relay silently drop 2 of 3 flight combos
when asked to "report the list back exactly as given"). When a tool's
return value already matches the target schema, read it straight from the
ADK event stream instead of round-tripping it through another LLM turn.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Awaitable, Callable, TypeVar

import litellm
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

USER_ID = "a2a-client"
RETRYABLE_EXCEPTIONS = (
    litellm.RateLimitError,
    litellm.ServiceUnavailableError,
    litellm.InternalServerError,
    litellm.APIConnectionError,
    litellm.Timeout,
)
MAX_RETRIES = 5
DEFAULT_BACKOFF_SECONDS = 8.0
MAX_BACKOFF_SECONDS = 60.0

T = TypeVar("T")


def _extract_retry_delay_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


async def _run_with_retries(
    agent: Agent,
    app_name: str,
    message: str,
    collect: Callable[[Any], Awaitable[T]],
) -> T:
    """Runs the agent, feeding its event stream to `collect`, retrying the
    whole turn (fresh session) on transient OpenAI errors."""
    user_content = types.Content(role="user", parts=[types.Part(text=message)])

    for attempt in range(MAX_RETRIES + 1):
        session_service = InMemorySessionService()
        session_id = uuid.uuid4().hex
        await session_service.create_session(app_name=app_name, user_id=USER_ID, session_id=session_id)
        runner = Runner(agent=agent, app_name=app_name, session_service=session_service)

        try:
            events = runner.run_async(user_id=USER_ID, session_id=session_id, new_message=user_content)
            return await collect(events)
        except RETRYABLE_EXCEPTIONS as exc:
            if attempt >= MAX_RETRIES:
                raise
            delay = _extract_retry_delay_seconds(exc)
            if delay is None:
                delay = min(DEFAULT_BACKOFF_SECONDS * (2**attempt), MAX_BACKOFF_SECONDS)
            else:
                delay += 1.0  # pad past the API's own estimate
            await asyncio.sleep(delay)

    raise RuntimeError("unreachable")  # loop always returns or raises


async def run_agent_once(agent: Agent, app_name: str, message: str) -> str:
    async def collect(events: Any) -> str:
        final_text = ""
        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text or ""
        return final_text

    return await _run_with_retries(agent, app_name, message, collect)


async def run_agent_and_get_tool_result(agent: Agent, app_name: str, message: str, tool_name: str) -> Any:
    """Runs an agent expected to call exactly one tool, and returns that
    tool's raw Python return value read directly from the event stream —
    not the LLM's text description of it. Raises if the tool was never
    called (e.g. the LLM answered without invoking it)."""

    async def collect(events: Any) -> Any:
        tool_result = None
        async for event in events:
            if not (event.content and event.content.parts):
                continue
            for part in event.content.parts:
                function_response = getattr(part, "function_response", None)
                if function_response is not None and function_response.name == tool_name:
                    tool_result = function_response.response
        if tool_result is None:
            raise RuntimeError(f"{tool_name} was never called by the agent")
        return tool_result

    return await _run_with_retries(agent, app_name, message, collect)
