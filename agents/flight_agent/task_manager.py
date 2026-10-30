from __future__ import annotations

import asyncio
import json

from common.adk_runner import run_agent_and_get_tool_result
from common.schemas import FlightRequest, FlightResponse

from .agent import build_flight_gatherer_agent, search_google_flights

APP_NAME = "flight_agent"
TOOL_NAME = "search_google_flights_for_dates"


async def handle_task(payload: dict) -> dict:
    request = FlightRequest.model_validate(payload)

    # Airports picked from the frontend dropdown arrive as exact IATA codes,
    # so there's nothing left for the LLM to judge — call the search
    # directly, same reasoning as the templated search_places calls in
    # accommodation_food_agent/task_manager.py.
    if request.origin_iata and request.destination_iata:
        tool_result = await asyncio.to_thread(
            search_google_flights,
            request.origin_iata.upper(),
            request.destination_iata.upper(),
            request.start_date,
            request.end_date,
            request.flight_class,
        )
        combos = tool_result.get("combos", []) if isinstance(tool_result, dict) else []
        return FlightResponse.model_validate({"flights": combos}).model_dump()

    # Dates are bound directly into the tool (see build_flight_gatherer_agent's
    # docstring) rather than relayed through the LLM, so the prompt only
    # needs to carry what the LLM actually has to reason about.
    gatherer = build_flight_gatherer_agent(request.start_date, request.end_date)
    gather_request = {
        "origin": request.origin,
        "destination": request.destination,
        "flight_class": request.flight_class,
    }
    gather_prompt = f"Find round-trip flights for this request:\n{json.dumps(gather_request)}"

    # Read the tool's own return value straight off the event stream instead
    # of trusting the LLM to relay it — see common/adk_runner.py's docstring
    # for why (a production run had the relay silently drop 2 of 3 combos).
    tool_result = await run_agent_and_get_tool_result(gatherer, APP_NAME, gather_prompt, TOOL_NAME)

    combos = tool_result.get("combos", []) if isinstance(tool_result, dict) else []
    response = FlightResponse.model_validate({"flights": combos})
    return response.model_dump()
