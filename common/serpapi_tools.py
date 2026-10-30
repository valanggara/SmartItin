"""Shared SerpAPI tool functions used by more than one agent
(research_agent and accommodation_food_agent both need general web search
and real Google Maps places data)."""

from __future__ import annotations

import logging
import os
import re
import time
from urllib.parse import quote

from serpapi import GoogleSearch

logger = logging.getLogger("serpapi_tools")

MAPS_SEARCH_RETRIES = 3
MAPS_SEARCH_BACKOFF_SECONDS = 2.0


def search_web(query: str) -> dict:
    """Runs a Google web search (via SerpAPI) and returns organic results.

    Args:
        query: The search query string.

    Returns:
        dict: {"results": [{"title", "link", "snippet"}, ...]}, or
        {"error": message} if the API key is missing or the request failed.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {"error": "SERPAPI_API_KEY is not configured"}

    params = {"engine": "google", "q": query, "num": 8, "hl": "en", "api_key": api_key}
    try:
        data = GoogleSearch(params).get_dict()
        organic = data.get("organic_results", [])
        return {
            "results": [
                {"title": r.get("title"), "link": r.get("link"), "snippet": r.get("snippet")}
                for r in organic
            ]
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _google_maps_search_with_retries(params: dict, query: str) -> dict:
    """Runs the google_maps SerpAPI call, retrying transient failures
    (network hiccups, rate limiting) with backoff. The fallback per-place
    lookups in task_manager.py fire several of these concurrently — bursts
    like that can trip SerpAPI's rate limiting even well under the account's
    overall quota — and unlike the Gemini/OpenAI calls (see
    common/adk_runner.py), search_places previously had no retry at all, so
    a transient throttle permanently lost that place's match instead of
    succeeding on a second attempt."""
    last_error = "unknown error"
    for attempt in range(MAPS_SEARCH_RETRIES + 1):
        try:
            data = GoogleSearch(params).get_dict()
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        else:
            if "error" not in data:
                return data
            last_error = data["error"]
        if attempt < MAPS_SEARCH_RETRIES:
            logger.warning(
                "search_places(%r) attempt %d/%d failed: %s — retrying",
                query,
                attempt + 1,
                MAPS_SEARCH_RETRIES + 1,
                last_error,
            )
            time.sleep(MAPS_SEARCH_BACKOFF_SECONDS * (attempt + 1))
    return {"error": last_error}


def search_places(query: str) -> dict:
    """Searches Google Maps (via SerpAPI) for real places matching a query,
    returning each place's actual Google Maps link and photo — no invented
    URLs. The maps_link points at the exact place (name + place_id, per
    Google's documented Maps Search URL format: "if you specify both
    query and query_place_id, query is only used as a fallback if Google
    Maps can't find the place ID" — so this is precise, not just a bare
    pin at some coordinates) rather than a lat/lng-only link. Falls back
    to a coordinates link only if SerpAPI didn't return a place_id.

    Args:
        query: e.g. "4 star hotels in Bali" or "top attractions in Ubud".

    Returns:
        dict: {"places": [{"name", "address", "rating", "image_url",
        "maps_link"}, ...]}, or {"error": message}.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {"error": "SERPAPI_API_KEY is not configured"}

    # gl/google_domain bias results toward Indonesia — every price field in
    # this app is IDR-only (see common/schemas.py), so it's exclusively an
    # Indonesian-destination trip planner, not a general worldwide one. A
    # real run without this bias returned clean (no-error) but empty or
    # noisy results for a province-level destination ("Bali") much more
    # often than for a specific city ("Yogyakarta") — Google's local pack
    # needs a stronger regional hint to resolve broader destinations.
    params = {
        "engine": "google_maps",
        "type": "search",
        "q": query,
        "hl": "en",
        "gl": "id",
        "google_domain": "google.co.id",
        "api_key": api_key,
    }
    data = _google_maps_search_with_retries(params, query)
    if "error" in data:
        return {"error": data["error"]}

    # A query naming one specific place ("Hotel Gracery Shinjuku") gets a
    # single `place_results` object back instead of a `local_results` list
    # — reading only local_results is what made narrow lookups look like
    # zero-result responses (see find_place's docstring) even though
    # SerpAPI had found the exact place, thumbnail included.
    results = data.get("local_results") or []
    if not results and isinstance(data.get("place_results"), dict):
        results = [data["place_results"]]
    if not results:
        return {"error": f"No places found for query: {query!r}"}

    places = []
    for r in results:
        name = r.get("title", "")
        place_id = r.get("place_id", "")
        if place_id:
            maps_link = f"https://www.google.com/maps/search/?api=1&query={quote(name)}&query_place_id={place_id}"
        else:
            gps = r.get("gps_coordinates") or {}
            lat, lng = gps.get("latitude"), gps.get("longitude")
            maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}" if lat and lng else ""
        places.append(
            {
                "name": name,
                "address": r.get("address", ""),
                "rating": _to_float(r.get("rating")),
                "image_url": r.get("thumbnail", ""),
                "maps_link": maps_link,
            }
        )
    return {"places": places}


def _to_float(value: object) -> float:
    # local_results ratings are numbers, place_results ratings are strings
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_place(name: str, places: list[dict]) -> dict | None:
    """Deterministically matches `name` (e.g. an attraction/hotel/restaurant
    an LLM identified from descriptive research) against a list of real
    places (from search_places), so maps_link/image_url can always be
    either genuinely real or empty — never something an LLM invented to
    fill in the blank. Exact normalized match first, then substring
    containment either direction as a looser fallback."""
    target = _normalize_name(name)
    if not target:
        return None
    for place in places:
        if _normalize_name(place.get("name", "")) == target:
            return place
    for place in places:
        candidate = _normalize_name(place.get("name", ""))
        if candidate and (candidate in target or target in candidate):
            return place
    return None


def attach_place_matches(items: list[dict], places: list[dict]) -> None:
    """Mutates each item in `items` (each must have a "name" key) in place,
    overwriting maps_link/image_url with a real match from `places` or
    empty strings if none — regardless of whatever an LLM may have already
    put there."""
    for item in items:
        match = match_place(item.get("name", ""), places)
        item["maps_link"] = match.get("maps_link", "") if match else ""
        item["image_url"] = match.get("image_url", "") if match else ""
        # Google's real 5-point rating beats an LLM's 0 ("not found in
        # snippets") or a 10-point Booking.com-style score copied verbatim
        if match and "rating" in item and not 0 < item["rating"] <= 5 and match.get("rating"):
            item["rating"] = match["rating"]


def find_place(name: str, destination: str) -> dict | None:
    """Targeted single-place lookup, used as a fallback for whatever
    attach_place_matches() couldn't match against a bulk search_places()
    result set. The bulk queries in task_manager.py ("top attractions in
    <destination>", "<stars>-star hotels in <destination>", etc.) only
    return SerpAPI's top ~20 results for that generic query — a real but
    less-prominent place (or one Google Maps lists under a slightly
    different name) can legitimately not be among them.

    Uses SerpAPI's regular "google" web-search engine, NOT the dedicated
    "google_maps" engine that search_places() above uses. Real runs showed
    the google_maps engine coming back with a clean zero-result response
    (not an error, just no local-pack match) for a single specific name —
    across every test run so far, regardless of query phrasing (comma vs.
    no comma) or geo-bias (gl/google_domain), it resolved close to 0% of
    fallback lookups. A regular web search for "<name> <destination>"
    instead surfaces the same underlying place data (Google shows a local
    business card / knowledge panel directly in normal search results for
    well-known specific businesses), which is a genuinely different
    mechanism than the dedicated Maps search — not just a rephrasing of
    the same one that's already proven unreliable for this narrow-query
    use case."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return None

    params = {
        "engine": "google",
        "q": f"{name} {destination}",
        "hl": "en",
        "gl": "id",
        "google_domain": "google.co.id",
        "api_key": api_key,
    }
    try:
        data = GoogleSearch(params).get_dict()
    except Exception:  # noqa: BLE001
        return None

    def _best_image(*sources: object) -> str:
        """Tries several plausible image locations in SerpAPI's "google"
        engine response, in priority order, and returns the first hit.
        Deliberately does NOT fall back to inline_images (generic photos
        SerpAPI surfaces for the query text) — a real run showed it
        returning a photo with no connection to the actual place (an
        unrelated stock-looking image shown as if it were a specific
        hotel's photo). An empty image_url the frontend shows as a plain
        placeholder is honest; a wrong photo confidently presented as the
        real one is worse than that, so this only returns fields that are
        actually attached to the place/business result itself."""
        for source in sources:
            if isinstance(source, dict):
                for key in ("thumbnail", "image", "serpapi_thumbnail"):
                    if source.get(key):
                        return source[key]
                header_images = source.get("header_images")
                if isinstance(header_images, list) and header_images:
                    img = header_images[0].get("image") or header_images[0].get("thumbnail")
                    if img:
                        return img
        return ""

    def _resolve_via_maps_engine(title: str) -> dict | None:
        """Second-pass lookup: re-queries the dedicated google_maps engine
        (search_places, which reliably returns real "thumbnail" images when
        it finds a match) using Google's own canonical title for this place
        — not the LLM's original guessed name. The maps_maps_engine returning
        zero results for narrow queries was traced earlier to the LLM's
        guessed name not matching Google's actual listing title closely
        enough; querying with the name Google itself just gave us removes
        that guesswork, so it's a meaningfully different, better-odds query
        rather than a retry of the same one."""
        result = search_places(title)
        places = result.get("places", [])
        return places[0] if places else None

    local_results = data.get("local_results")
    candidates = local_results.get("places", []) if isinstance(local_results, dict) else (local_results or [])
    if isinstance(candidates, list) and candidates:
        r = candidates[0]
        title = r.get("title", name)
        place_id = r.get("place_id", "")
        maps_link = (
            f"https://www.google.com/maps/search/?api=1&query={quote(title)}&query_place_id={place_id}"
            if place_id
            else f"https://www.google.com/maps/search/?api=1&query={quote(title)}"
        )
        image_url = _best_image(r)
        rating = _to_float(r.get("rating"))
        if not image_url:
            maps_hit = _resolve_via_maps_engine(title)
            if maps_hit:
                image_url = maps_hit.get("image_url", "")
                rating = rating or maps_hit.get("rating", 0.0)
                if not place_id and maps_hit.get("maps_link"):
                    maps_link = maps_hit["maps_link"]
        return {"name": title, "maps_link": maps_link, "image_url": image_url, "rating": rating}

    kg = data.get("knowledge_graph")
    if isinstance(kg, dict) and kg.get("title"):
        title = kg["title"]
        maps_link = f"https://www.google.com/maps/search/?api=1&query={quote(title)}"
        image_url = _best_image(kg)
        rating = _to_float(kg.get("rating"))
        if not image_url:
            maps_hit = _resolve_via_maps_engine(title)
            if maps_hit:
                image_url = maps_hit.get("image_url", "")
                rating = rating or maps_hit.get("rating", 0.0)
                if maps_hit.get("maps_link"):
                    maps_link = maps_hit["maps_link"]
        return {"name": title, "maps_link": maps_link, "image_url": image_url, "rating": rating}

    return None
