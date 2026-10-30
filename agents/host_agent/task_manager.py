"""Orchestration logic: dispatch Flight, Research, and Accommodation & Food
agents in parallel (none depends on another — budget_tier drives each
one's own filtering; total_budget_idr never does, see below), then call
the Itinerary Agent with their results as context, then combine everything
with a cost summary.

Each downstream call is wrapped so a single agent failing (timeout,
connection refused, upstream 500) returns a partial plan with a clear
{"error": ...} flag for that section instead of crashing the whole request.

Budget allocation (agents/host_agent/agent.py's budget_allocation_agent):
runs concurrently with the Flight/Research/Accommodation calls (it only
needs the trip request, not their results) to judge a per-trip priority
(low/medium/high) for flight/hotel/food/activity — not a fixed percentage
rule, see that module's docstring. common/budget_optimizer.py converts
that judgment to percentages deterministically.

Combination optimization (common/budget_optimizer.py): Flight Agent and
Accommodation & Food Agent are never filtered by total_budget_idr — they
keep returning their normal top candidates. Once both are back, this
module scores every flight x stay pairing and marks the winner
`selected=True`, rather than just pairing the cheapest of each
independently. total_budget_idr is a planning target throughout, never a
hard filter on any individual agent's results.

run_trip_stream() yields each section's result as soon as it's ready (used
by the /run-async + /status polling endpoints for progressive UI reveal);
handle_task() is the simple all-at-once version (used by the plain /run
endpoint, e.g. for curl/tests).

handle_modify_itinerary() is the entry point for /modify-itinerary: it
reconstructs the itinerary agent's MODIFY-mode context from a job's stored
state (original request + research/accommodation sections) rather than
requiring the caller to resend all of that, then — if the change was
applied — refreshes the job's stored itinerary and cost_summary so a page
reload or later poll reflects it too.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import date
from typing import AsyncIterator

from common.a2a_client import call_agent
from common.adk_runner import run_agent_once
from common.budget_optimizer import DEFAULT_PRIORITIES, compute_allocation, priorities_to_percentages, select_best_combo
from common.schemas import BudgetPriorityDecision, TripRequest

from . import jobs
from .agent import budget_allocation_agent

APP_NAME = "host_agent"

FLIGHT_AGENT_URL = os.getenv("FLIGHT_AGENT_URL", "http://localhost:8001")
RESEARCH_AGENT_URL = os.getenv("RESEARCH_AGENT_URL", "http://localhost:8002")
ACCOMMODATION_FOOD_AGENT_URL = os.getenv("ACCOMMODATION_FOOD_AGENT_URL", "http://localhost:8003")
ITINERARY_AGENT_URL = os.getenv("ITINERARY_AGENT_URL", "http://localhost:8004")


async def _safe_call(base_url: str, payload: dict, section: str) -> dict:
    try:
        return await call_agent(f"{base_url}/run", payload)
    except Exception as exc:  # noqa: BLE001 — network/upstream failure, not a schema issue
        return {"error": f"{section} agent call failed: {exc}"}


async def _tagged(key: str, coro) -> tuple[str, dict]:
    return key, await coro


def _compute_nights(start_date: str, end_date: str) -> int:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    return max((end - start).days, 1)


def _cheapest(options: list[dict], price_key: str) -> int:
    prices = [opt[price_key] for opt in options if price_key in opt]
    return min(prices) if prices else 0


async def _decide_allocation_percentages(request: TripRequest, nights: int) -> dict[str, float]:
    """Asks budget_allocation_agent to judge a per-trip priority for
    flight/hotel/food/activity (see agents/host_agent/agent.py), then
    converts that judgment to percentages deterministically. Falls back to
    DEFAULT_PRIORITIES if the call fails or the response doesn't
    validate, so a bad LLM response never blocks the rest of the trip —
    same resilience as _safe_call() for the HTTP-based agent calls, just
    for this in-process one."""
    prompt = (
        f"Origin: {request.origin}\n"
        f"Destination: {request.destination}\n"
        f"Nights: {nights}\n"
        f"Budget tier: {request.budget_tier}\n"
        f"Flight class: {request.flight_class}\n"
        f"Hotel stars: {request.hotel_stars}\n"
        f"Theme: {request.theme}\n"
        f"Travel pace: {request.travel_pace}\n"
        f"Total budget: Rp{request.total_budget_idr:,}"
    )
    try:
        result_text = await run_agent_once(budget_allocation_agent, APP_NAME, prompt)
        decision = BudgetPriorityDecision.model_validate(json.loads(result_text))
        priorities = {
            "flight": decision.flight_priority,
            "hotel": decision.hotel_priority,
            "food": decision.food_priority,
            "activity": decision.activity_priority,
        }
    except Exception:  # noqa: BLE001 — a bad/failed LLM call degrades to defaults, never crashes the trip
        priorities = DEFAULT_PRIORITIES
    return priorities_to_percentages(priorities)


def _fallback_allocation(total_budget_idr: int, percentages: dict[str, float]) -> dict:
    """Used whenever select_best_combo() couldn't run (flights or
    accommodation errored/empty) — still gives a sensible BudgetAllocation
    from the target percentages alone, just without a scored selection.
    over_budget is left False here since without a selected combo there's
    no actual cost to compare against the target."""
    targets = compute_allocation(total_budget_idr, percentages)
    return {
        "total_budget_idr": total_budget_idr,
        "target_flight_budget_idr": targets["flight"],
        "target_hotel_budget_idr": targets["hotel"],
        "target_food_budget_idr": targets["food"],
        "target_activity_budget_idr": targets["activity"],
        "over_budget": False,
    }


def _select_costs(flight_result: dict, accommodation_result: dict, nights: int) -> tuple[int, int]:
    """Cost of whichever flight/stay select_best_combo() marked
    selected=True, falling back to cheapest if no selection was made
    (e.g. optimization was skipped because one side errored)."""
    flights = flight_result.get("flights", []) if "error" not in flight_result else []
    stays = accommodation_result.get("stays", []) if "error" not in accommodation_result else []

    selected_flight = next((f for f in flights if f.get("selected")), None)
    flight_cost = selected_flight["price_total_idr"] if selected_flight else _cheapest(flights, "price_total_idr")

    selected_stay = next((s for s in stays if s.get("selected")), None)
    stay_per_night = (
        selected_stay["price_per_night_idr"] if selected_stay else _cheapest(stays, "price_per_night_idr")
    )

    return flight_cost, stay_per_night * nights


def _build_cost_summary(
    budget_tier: str,
    nights: int,
    flight_result: dict,
    accommodation_result: dict,
    itinerary_result: dict,
    budget_allocation: dict,
) -> dict:
    flight_cost, stay_cost = _select_costs(flight_result, accommodation_result, nights)

    itinerary_cost = 0
    if "error" not in itinerary_result:
        itinerary_cost = sum(
            day.get("estimated_cost_idr", 0) for day in itinerary_result.get("itinerary", [])
        )

    return {
        "budget_tier": budget_tier,
        "estimated_flight_cost_idr": flight_cost,
        "estimated_stay_cost_idr": stay_cost,
        "estimated_itinerary_cost_idr": itinerary_cost,
        "estimated_total_cost_idr": flight_cost + stay_cost + itinerary_cost,
        "budget_allocation": budget_allocation,
    }


async def run_trip_stream(payload: dict) -> AsyncIterator[tuple[str, dict]]:
    """Yields (section, result) as each becomes available: flights/research/
    accommodation in whatever order they finish (they run concurrently),
    then itinerary, then cost_summary last."""
    request = TripRequest.model_validate(payload)
    nights = _compute_nights(request.start_date, request.end_date)
    base_payload = request.model_dump()

    pending = [
        asyncio.create_task(_tagged("flights", _safe_call(FLIGHT_AGENT_URL, base_payload, "flight"))),
        asyncio.create_task(_tagged("research", _safe_call(RESEARCH_AGENT_URL, base_payload, "research"))),
        asyncio.create_task(
            _tagged(
                "accommodation",
                _safe_call(
                    ACCOMMODATION_FOOD_AGENT_URL,
                    {**base_payload, "hotel_stars": [request.hotel_stars], "nights": nights},
                    "accommodation",
                ),
            )
        ),
    ]
    # Started alongside the three HTTP calls above, not awaited until
    # after — it only needs the trip request, not their results, so there's
    # no reason to make it block the critical path.
    allocation_task = asyncio.create_task(_decide_allocation_percentages(request, nights))

    results: dict[str, dict] = {}
    for task in asyncio.as_completed(pending):
        key, result = await task
        results[key] = result
        yield key, result

    percentages = await allocation_task

    # Combination optimization: now that both flights and accommodation are
    # in, pick the best flight+stay pairing (see common/budget_optimizer.py)
    # instead of the cheapest of each independently. Mutates the flight/stay
    # dicts already sitting in `results` in place (marks the winner
    # selected=True) and re-yields both sections so a later /status poll
    # picks up which one was recommended — same mechanism
    # handle_modify_itinerary() below already uses to refresh a job's
    # stored state after the fact.
    optimization = None
    flights_list = results["flights"].get("flights", []) if "error" not in results["flights"] else []
    stays_list = results["accommodation"].get("stays", []) if "error" not in results["accommodation"] else []
    if flights_list and stays_list:
        optimization = select_best_combo(flights_list, stays_list, nights, request.total_budget_idr, percentages)
        flights_list[optimization["flight_index"]]["selected"] = True
        stays_list[optimization["stay_index"]]["selected"] = True
        yield "flights", results["flights"]
        yield "accommodation", results["accommodation"]

    if optimization:
        food_budget_idr = optimization["food_budget_idr"]
        activity_budget_idr = optimization["activity_budget_idr"]
    else:
        fallback_targets = compute_allocation(request.total_budget_idr, percentages)
        food_budget_idr = fallback_targets["food"]
        activity_budget_idr = fallback_targets["activity"]

    if "error" in results["research"] or "error" in results["accommodation"]:
        itinerary_result = {
            "error": "itinerary skipped: research or accommodation context unavailable"
        }
    else:
        itinerary_result = await _safe_call(
            ITINERARY_AGENT_URL,
            {
                **base_payload,
                "nights": nights,
                "food_budget_idr": food_budget_idr,
                "activity_budget_idr": activity_budget_idr,
                "research_context": results["research"],
                "accommodation_context": results["accommodation"],
            },
            "itinerary",
        )
    yield "itinerary", itinerary_result

    budget_allocation = (
        optimization["allocation"] if optimization else _fallback_allocation(request.total_budget_idr, percentages)
    )
    cost_summary = _build_cost_summary(
        request.budget_tier,
        nights,
        results["flights"],
        results["accommodation"],
        itinerary_result,
        budget_allocation,
    )
    yield "cost_summary", cost_summary


async def handle_task(payload: dict) -> dict:
    sections: dict[str, dict] = {}
    async for key, value in run_trip_stream(payload):
        sections[key] = value
    return sections


async def handle_modify_itinerary(job_id: str, action: str, action_params: dict) -> dict:
    job = jobs.get_job(job_id)
    if job is None:
        return {"error": "job not found"}

    sections = job.get("sections") or {}
    current_itinerary = sections.get("itinerary")
    research_result = sections.get("research")
    accommodation_result = sections.get("accommodation")

    if not current_itinerary or "error" in current_itinerary:
        return {"error": "no existing itinerary to modify"}
    if not research_result or "error" in research_result:
        return {"error": "destination research is unavailable, cannot modify itinerary"}
    if not accommodation_result or "error" in accommodation_result:
        return {"error": "accommodation context is unavailable, cannot modify itinerary"}

    request = TripRequest.model_validate(job.get("request") or {})
    nights = _compute_nights(request.start_date, request.end_date)

    modify_payload = {
        "mode": "modify",
        "action": action,
        "action_params": action_params,
        "current_itinerary": current_itinerary.get("itinerary", []),
        "destination": request.destination,
        "budget_tier": request.budget_tier,
        "theme": request.theme,
        "nights": nights,
        "research_context": research_result,
        "accommodation_context": accommodation_result,
    }

    result = await _safe_call(ITINERARY_AGENT_URL, modify_payload, "itinerary_modify")
    if "error" in result:
        return result

    if result.get("applied"):
        new_itinerary_section = {"itinerary": result["modified_itinerary"]}
        jobs.set_section(job_id, "itinerary", new_itinerary_section)
        # Reuse the allocation from the original run — modifying the
        # itinerary doesn't change which flight/stay was selected, so
        # there's nothing new to (re-)optimize here.
        existing_allocation = sections.get("cost_summary", {}).get("budget_allocation")
        budget_allocation = existing_allocation or _fallback_allocation(
            request.total_budget_idr, priorities_to_percentages(DEFAULT_PRIORITIES)
        )
        new_cost_summary = _build_cost_summary(
            request.budget_tier,
            nights,
            sections.get("flights", {}),
            accommodation_result,
            new_itinerary_section,
            budget_allocation,
        )
        jobs.set_section(job_id, "cost_summary", new_cost_summary)

    return result
