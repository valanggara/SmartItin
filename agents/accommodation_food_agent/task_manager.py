from __future__ import annotations

import asyncio
import json
import logging

from common.adk_runner import run_agent_once
from common.cache import ACCOMMODATION_TTL_SECONDS, accommodation_cache, accommodation_cache_key
from common.schemas import AccommodationRequest, StayFoodResponse
from common.serpapi_tools import attach_place_matches, find_place, search_places
from common.tiers import get_tier_defaults

from .agent import stay_food_formatter_agent, stay_food_gatherer_agent

APP_NAME = "accommodation_food_agent"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(APP_NAME)

# Caps how many fallback find_place() lookups run at once — firing them all
# concurrently was tripping SerpAPI's rate limiting (see
# common/serpapi_tools.py's _google_maps_search_with_retries docstring),
# and each retry there is itself an extra billed call, so it's cheaper
# overall to spread the burst out than to lean on retries alone.
FALLBACK_CONCURRENCY = 3


async def handle_task(payload: dict) -> dict:
    request = AccommodationRequest.model_validate(payload)

    cache_key = accommodation_cache_key(request.destination, request.budget_tier, request.hotel_stars)
    cached = accommodation_cache.get(cache_key)
    if cached is not None:
        return cached

    dining_style = get_tier_defaults(request.budget_tier)["dining_style"]

    gather_request = {
        "destination": request.destination,
        "hotel_stars": request.hotel_stars,
        "dining_style": dining_style,
        "theme": request.theme,
        "nights": request.nights,
    }
    gather_prompt = f"Find stays and restaurants for this request:\n{json.dumps(gather_request)}"
    findings = await run_agent_once(stay_food_gatherer_agent, APP_NAME, gather_prompt)

    # search_places queries are fully templated — no LLM judgment needed —
    # so call it directly rather than leaving it to the gatherer's
    # discretion. See research_agent/agent.py's module docstring for why:
    # on gpt-4o-mini a real run had the gatherer skip this tool call
    # entirely despite an explicit instruction to make it.
    stars = sorted(request.hotel_stars)
    stars_label = f"{stars[0]}-star" if len(stars) == 1 else f"{stars[0]}-{stars[-1]} star"
    places_results = await asyncio.gather(
        asyncio.to_thread(search_places, f"{stars_label} hotels in {request.destination}"),
        asyncio.to_thread(search_places, f"{dining_style} restaurants in {request.destination}"),
    )
    for result in places_results:
        if "error" in result:
            logger.warning("search_places call returned an error: %s", result["error"])
    real_places = [place for result in places_results for place in result.get("places", [])]
    logger.info(
        "search_places calls=%d real_places=%d names=%s",
        len(places_results),
        len(real_places),
        [p.get("name") for p in real_places],
    )

    format_prompt = (
        f"Requested hotel_stars: {request.hotel_stars}\n"
        f"Requested dining_style: {dining_style}\n\n"
        f"Stay & restaurant research findings:\n{findings}"
    )
    formatted = await run_agent_once(stay_food_formatter_agent, APP_NAME, format_prompt)

    response = StayFoodResponse.model_validate(json.loads(formatted))
    result = response.model_dump()

    attach_place_matches(result["stays"], real_places)
    attach_place_matches(result["restaurants"], real_places)

    # Targeted fallback for anything the cheap bulk search missed — one
    # extra search_places call per miss, for every miss, so coverage isn't
    # capped by whether a place happens to appear in the generic top-20
    # lists above. Checks image_url too, not just maps_link: search_places()
    # sources them from independent SerpAPI fields (place_id/gps_coordinates
    # vs. thumbnail) — a bulk match can have a real place_id and no
    # thumbnail, which used to silently skip the fallback entirely and
    # leave image_url empty forever despite the fallback existing
    # specifically to recover cases like this.
    all_places = result["stays"] + result["restaurants"]
    unmatched = [item for item in all_places if not item["maps_link"] or not item["image_url"]]
    if unmatched:
        semaphore = asyncio.Semaphore(FALLBACK_CONCURRENCY)

        async def _lookup(item_name: str) -> dict | None:
            async with semaphore:
                return await asyncio.to_thread(find_place, item_name, request.destination)

        fallback_places = await asyncio.gather(*[_lookup(item["name"]) for item in unmatched])
        for item, place in zip(unmatched, fallback_places):
            if place:
                # Only fill in whichever field was actually missing — an
                # item that already has a good bulk-sourced maps_link but
                # no image shouldn't have that maps_link overwritten by the
                # fallback's independently-resolved (possibly different)
                # place.
                if not item["maps_link"] and place.get("maps_link"):
                    item["maps_link"] = place["maps_link"]
                if not item["image_url"] and place.get("image_url"):
                    item["image_url"] = place["image_url"]
        logger.info(
            "fallback lookups=%d resolved=%d",
            len(unmatched),
            sum(1 for p in fallback_places if p),
        )

    logger.info(
        "stays matched=%d/%d names=%s",
        sum(1 for s in result["stays"] if s["maps_link"]),
        len(result["stays"]),
        [s["name"] for s in result["stays"]],
    )
    logger.info(
        "restaurants matched=%d/%d names=%s",
        sum(1 for r in result["restaurants"] if r["maps_link"]),
        len(result["restaurants"]),
        [r["name"] for r in result["restaurants"]],
    )

    accommodation_cache.set(cache_key, result, ACCOMMODATION_TTL_SECONDS)
    return result
