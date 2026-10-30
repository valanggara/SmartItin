from __future__ import annotations

import json
from datetime import date, timedelta

from common.adk_runner import run_agent_once
from common.schemas import ItineraryModifyRequest, ItineraryModifyResponse, ItineraryRequest, ItineraryResponse
from common.tiers import get_tier_defaults

from .agent import itinerary_create_agent, itinerary_modify_agent

APP_NAME = "itinerary_agent"


async def _handle_create(payload: dict) -> dict:
    request = ItineraryRequest.model_validate(payload)
    tier_defaults = get_tier_defaults(request.budget_tier)

    start = date.fromisoformat(request.start_date)
    trip_dates = [(start + timedelta(days=i)).isoformat() for i in range(request.nights + 1)]

    prompt = (
        f"Dates to cover, one DayPlan per date, in order: {json.dumps(trip_dates)}\n"
        f"Theme: {request.theme}\n"
        f"Budget tier: {request.budget_tier}\n"
        f"Travel pace (locked): {request.travel_pace}\n"
        f"Activity style (locked): {tier_defaults['activity_style']}\n"
        f"Dining style (locked): {tier_defaults['dining_style']}\n"
        f"Budget for dining across the WHOLE trip (soft planning target, "
        f"not a hard per-day cap): Rp{request.food_budget_idr:,}\n"
        f"Budget for paid activities/attractions across the WHOLE trip "
        f"(soft planning target, not a hard per-day cap): "
        f"Rp{request.activity_budget_idr:,}\n\n"
        f"Destination research:\n{request.research_context.model_dump_json()}\n\n"
        f"Accommodation & dining context:\n{request.accommodation_context.model_dump_json()}"
    )

    result_text = await run_agent_once(itinerary_create_agent, APP_NAME, prompt)
    response = ItineraryResponse.model_validate(json.loads(result_text))
    return response.model_dump()


async def _handle_modify(payload: dict) -> dict:
    request = ItineraryModifyRequest.model_validate(payload)
    tier_defaults = get_tier_defaults(request.budget_tier)

    prompt = (
        f"Action: {request.action}\n"
        f"Action params: {json.dumps(request.action_params)}\n"
        f"Destination: {request.destination}\n"
        f"Budget tier: {request.budget_tier}\n"
        f"Activity style (locked): {tier_defaults['activity_style']}\n"
        f"Dining style (locked): {tier_defaults['dining_style']}\n\n"
        f"Current itinerary:\n{json.dumps([day.model_dump() for day in request.current_itinerary])}\n\n"
        f"Destination research:\n{request.research_context.model_dump_json()}\n\n"
        f"Accommodation & dining context:\n{request.accommodation_context.model_dump_json()}"
    )

    result_text = await run_agent_once(itinerary_modify_agent, APP_NAME, prompt)
    response = ItineraryModifyResponse.model_validate(json.loads(result_text))
    return response.model_dump()


async def handle_task(payload: dict) -> dict:
    if payload.get("mode") == "modify":
        return await _handle_modify(payload)
    return await _handle_create(payload)
