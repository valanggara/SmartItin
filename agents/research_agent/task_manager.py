from __future__ import annotations

import asyncio
import json
import logging

from common.adk_runner import run_agent_once
from common.cache import RESEARCH_TTL_SECONDS, research_cache, research_cache_key
from common.schemas import ResearchRequest, ResearchResponse
from common.serpapi_tools import attach_place_matches, find_place, search_places

from .agent import research_formatter_agent, research_gatherer_agent

APP_NAME = "research_agent"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(APP_NAME)

# Caps how many fallback find_place() lookups run at once — firing them all
# concurrently was tripping SerpAPI's rate limiting (see
# common/serpapi_tools.py's _google_maps_search_with_retries docstring),
# and each retry there is itself an extra billed call, so it's cheaper
# overall to spread the burst out than to lean on retries alone.
FALLBACK_CONCURRENCY = 3


async def handle_task(payload: dict) -> dict:
    request = ResearchRequest.model_validate(payload)

    cache_key = research_cache_key(request.destination, request.theme)
    cached = research_cache.get(cache_key)
    if cached is not None:
        return cached

    gather_prompt = f"Research this destination:\n{request.model_dump_json()}"
    findings = await run_agent_once(research_gatherer_agent, APP_NAME, gather_prompt)

    # search_places queries are fully templated — no LLM judgment needed —
    # so call it directly rather than leaving it to the gatherer's
    # discretion. See agent.py's module docstring for why: on gpt-4o-mini a
    # real run had the gatherer skip this tool call entirely.
    places_results = await asyncio.gather(
        asyncio.to_thread(search_places, f"top attractions in {request.destination}"),
        asyncio.to_thread(search_places, f"hidden gems in {request.destination} city"),
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
        f"Original request:\n{request.model_dump_json()}\n\n"
        f"Destination research findings:\n{findings}"
    )
    formatted = await run_agent_once(research_formatter_agent, APP_NAME, format_prompt)

    response = ResearchResponse.model_validate(json.loads(formatted))
    result = response.model_dump()

    attach_place_matches(result["top_attractions"], real_places)
    attach_place_matches(result["hidden_gems"], real_places)

    # Targeted fallback for anything the cheap bulk search missed — one
    # extra search_places call per miss, for every miss, so coverage isn't
    # capped by whether a place happens to appear in the generic top-20
    # lists above. Checks image_url too, not just maps_link: search_places()
    # sources them from independent SerpAPI fields (place_id/gps_coordinates
    # vs. thumbnail) — a bulk match can have a real place_id and no
    # thumbnail, which used to silently skip the fallback entirely and
    # leave image_url empty forever despite the fallback existing
    # specifically to recover cases like this.
    all_attractions = result["top_attractions"] + result["hidden_gems"]
    unmatched = [item for item in all_attractions if not item["maps_link"] or not item["image_url"]]
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
        "top_attractions matched=%d/%d names=%s",
        sum(1 for a in result["top_attractions"] if a["maps_link"]),
        len(result["top_attractions"]),
        [a["name"] for a in result["top_attractions"]],
    )
    logger.info(
        "hidden_gems matched=%d/%d names=%s",
        sum(1 for a in result["hidden_gems"] if a["maps_link"]),
        len(result["hidden_gems"]),
        [a["name"] for a in result["hidden_gems"]],
    )

    research_cache.set(cache_key, result, RESEARCH_TTL_SECONDS)
    return result
