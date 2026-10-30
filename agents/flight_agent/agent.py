"""Flight Agent: real-time flight search via SerpAPI's Google Flights engine.

NOTE ON ARCHITECTURE: there is no separate formatter agent here (unlike
research_agent/accommodation_food_agent). search_google_flights()'s "combos"
already match the FlightResponse schema field-for-field, and letting an LLM
relay or reformat that data has proven unreliable in practice — see
task_manager.py, which reads the tool's raw return value directly off the
ADK event stream (common.adk_runner.run_agent_and_get_tool_result) and
builds FlightResponse in Python. The single `build_flight_gatherer_agent`
here exists only for IATA code resolution (a real judgment call an LLM is
good at) and to invoke the tool — its final text response is never used.

NOTE ON SEARCH STRATEGY — round-trip search + departure_token, single
outbound: a round-trip google_flights request only returns OUTBOUND options
plus a `departure_token` per option — actual return-flight data (real
times, a single combined booking link) only comes from a second request
using that token (see SerpAPI's google-flights-api docs: "To obtain the
returning flight information for Round Trip, you need to make another
request using a departure_token"). An earlier version of this file skipped
that second call entirely, so the LLM had no real return-leg data and
hallucinated placeholder text like "Approximately not specified" to
satisfy the required schema fields (it was also computing duration_hours
itself and emitting unrounded values like 1.6666666666666667 — arithmetic
and date parsing shouldn't be left to an LLM either).

We tried resolving outbound and return as two independent one-way searches
instead (same 2-call cost, genuinely different top-3 prices by pairing
across both lists) — but that produces two separate one-way booking links
and can pair different airlines across legs, which is worse for a user who
wants one link to book a single coherent round trip. So this reverted back
to the single-outbound departure_token design: 1 call to list outbound
options, 1 follow-up call on the cheapest outbound's departure_token to get
its real return options — 2 calls total, one combined booking link, one
consistent (real, Google-validated) airline pairing.

Accepted tradeoff: since all 3 shown options share the same outbound, they
only vary by return flight — if that outbound's airline prices returns as
a flat fare (as one route/carrier we tested did), the 3 totals can come out
identical. That reflects the actual market, not a bug (confirmed: the same
route with more competing airlines, e.g. economy vs. premium economy,
showed genuine price spread). Exploring multiple different outbound options
too would fix this but costs 1 more SerpAPI call per outbound explored
(e.g. 4 calls total for 3 outbounds) — not worth it for this app.
"""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from serpapi import GoogleSearch

from common.llm_config import get_model

load_dotenv()

MODEL = get_model()

_TRAVEL_CLASS_MAP = {"economy": "1", "premium_economy": "2", "business": "3", "first": "4"}

_LEADING_CORPORATE_PREFIX = re.compile(r"^(PT|CV)\s+", re.IGNORECASE)
_TRAILING_CORPORATE_SUFFIX = re.compile(
    r"\s*(\(persero\)|tbk\.?|berhad|pte\.?\s*ltd\.?|ltd\.?|limited|inc\.?|co\.?|corporation|corp\.?|"
    r"service(s)?|group)\s*$",
    re.IGNORECASE,
)


def _shorten_airline_name(name: str) -> str:
    """Trims legal/corporate suffixes (", Pt", "Tbk", "Berhad", "Service", ...)
    down to the common brand name a traveler would recognize, e.g. "Pelita
    Air Service, Pt" -> "Pelita Air", "PT Garuda Indonesia (Persero) Tbk" ->
    "Garuda Indonesia". Deliberately does NOT touch "Airlines" — that's part
    of the actual brand for carriers like Singapore Airlines or Malaysia
    Airlines, not a legal suffix. Never invents a name; only trims one."""
    if not name:
        return name
    cleaned = name.split(",")[0].strip()
    cleaned = _LEADING_CORPORATE_PREFIX.sub("", cleaned)
    while True:
        next_cleaned = _TRAILING_CORPORATE_SUFFIX.sub("", cleaned).strip()
        if next_cleaned == cleaned:
            break
        cleaned = next_cleaned
    return cleaned or name


def _extract_leg(flight_option: dict) -> dict:
    """Pulls date/departure_time/arrival_time/duration_hours/airline/price/
    flight_number/airplane/airline_logo out of a SerpAPI flight option
    deterministically — no LLM parsing or arithmetic.

    flight_number/airplane/airline_logo are technically per-SEGMENT fields
    (a connecting itinerary could have a different aircraft/flight number
    per leg of the connection) — we report the first segment's values as
    representative, same simplification already used for `airline`. Fine
    for this app's short-haul, mostly-direct routes; a multi-stop itinerary
    would only show its first segment's flight number.
    """
    segments = flight_option.get("flights") or []
    first_segment = segments[0] if segments else {}
    first_departure = first_segment.get("departure_airport", {}).get("time", "")
    last_arrival = segments[-1].get("arrival_airport", {}).get("time", "") if segments else ""
    date_part, _, departure_time = first_departure.partition(" ")
    _, _, arrival_time = last_arrival.partition(" ")
    airline = flight_option.get("airline") or first_segment.get("airline", "Unknown airline")
    return {
        "airline": _shorten_airline_name(airline),
        "price_idr": flight_option.get("price", 0),
        "date": date_part,
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "duration_hours": round(flight_option.get("total_duration", 0) / 60, 1),
        "flight_number": first_segment.get("flight_number", ""),
        "airplane": first_segment.get("airplane", ""),
        "airline_logo": flight_option.get("airline_logo") or first_segment.get("airline_logo", ""),
        "stops": max(len(segments) - 1, 0),
    }


_LEG_SCHEMA_FIELDS = (
    "date",
    "departure_time",
    "arrival_time",
    "duration_hours",
    "flight_number",
    "airplane",
    "airline_logo",
    "stops",
)


def _leg_fields(leg: dict) -> dict:
    """Narrows an _extract_leg() result down to exactly the FlightLeg schema fields."""
    return {key: leg[key] for key in _LEG_SCHEMA_FIELDS}


def search_google_flights(
    origin_iata: str,
    destination_iata: str,
    outbound_date: str,
    return_date: str,
    flight_class: str,
) -> dict:
    """Searches Google Flights (via SerpAPI) for round-trip options: the
    cheapest outbound flight, paired with its top 3 cheapest real return
    options (fetched via a departure_token follow-up — see module docstring
    for why this needs 2 calls, not 1).

    Args:
        origin_iata: Departure airport's 3-letter uppercase IATA code (e.g.
            "CGK"). SerpAPI's google_flights engine rejects free-text city
            names here — resolve the city to its primary airport's IATA
            code yourself before calling this tool.
        destination_iata: Arrival airport's 3-letter uppercase IATA code
            (e.g. "DPS"), same rule as origin_iata.
        outbound_date: Departure date, formatted YYYY-MM-DD.
        return_date: Return date, formatted YYYY-MM-DD.
        flight_class: One of economy, premium_economy, business, first.

    Returns:
        dict: {"combos": [{airline, flight_class, price_total_idr, outbound:
        {date, departure_time, arrival_time, duration_hours, flight_number,
        airplane, airline_logo}, return_leg: {...same shape...},
        booking_link}, ...]}, already extracted and rounded, all sharing
        one combined round-trip booking_link — pass
        these through as-is. Or {"error": message} if the API key is
        missing or no bookable options were found.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {"error": "SERPAPI_API_KEY is not configured"}

    base_params = {
        "engine": "google_flights",
        "departure_id": origin_iata,
        "arrival_id": destination_iata,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "travel_class": _TRAVEL_CLASS_MAP.get(flight_class, "1"),
        "currency": "IDR",
        "hl": "en",
        "api_key": api_key,
    }

    try:
        outbound_data = GoogleSearch(base_params).get_dict()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    if "error" in outbound_data:
        return {"error": outbound_data["error"]}

    outbound_options = [
        opt
        for opt in (outbound_data.get("best_flights") or []) + (outbound_data.get("other_flights") or [])
        if opt.get("departure_token")
    ]
    if not outbound_options:
        return {"error": "No outbound flights with a bookable return path were found"}

    cheapest_outbound = min(outbound_options, key=lambda o: o.get("price", float("inf")))

    return_params = {**base_params, "departure_token": cheapest_outbound["departure_token"]}
    try:
        return_data = GoogleSearch(return_params).get_dict()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    if "error" in return_data:
        return {"error": return_data["error"]}

    return_options = (return_data.get("best_flights") or []) + (return_data.get("other_flights") or [])
    if not return_options:
        return {"error": "No return flights found for the cheapest outbound option"}
    return_options.sort(key=lambda o: o.get("price", float("inf")))

    # This link already reflects the departure_token selection — a single
    # combined round-trip booking flow, not a separate outbound-only link.
    booking_link = return_data.get("search_metadata", {}).get("google_flights_url", "")
    outbound_leg = _extract_leg(cheapest_outbound)
    flight_class_label = flight_class.replace("_", " ").title()

    combos = []
    for ret in return_options[:3]:
        return_leg = _extract_leg(ret)
        combos.append(
            {
                "airline": outbound_leg["airline"],
                "flight_class": flight_class_label,
                # A departure_token response's price is already the FULL
                # round-trip total for this outbound+return pairing —
                # empirically verified (2026-07, CGK->DPS): the outbound-only
                # price and every departure_token return option's price were
                # identical to the rupiah despite differing durations, and
                # summing them would double-count to an implausible total.
                "price_total_idr": return_leg["price_idr"],
                "outbound": _leg_fields(outbound_leg),
                "return_leg": _leg_fields(return_leg),
                "booking_link": booking_link,
            }
        )

    return {"combos": combos}


def build_flight_gatherer_agent(outbound_date: str, return_date: str) -> Agent:
    """Builds a fresh flight_gatherer_agent for ONE request, with
    outbound_date/return_date bound via closure — NOT exposed as an
    LLM-supplied tool argument.

    Earlier, the LLM was instructed to pass outbound_date=start_date and
    return_date=end_date itself when calling the tool. On at least one real
    1-night trip, it transcribed the SAME date for both legs (a round trip
    that should have searched two different dates ended up searching one
    date twice) — exactly the kind of mechanical value-passing an LLM
    shouldn't be trusted with, matching every other date/arithmetic bug
    we've hit in this file. Binding the dates here, so the LLM only ever
    supplies origin_iata/destination_iata/flight_class, removes this
    failure mode entirely rather than just instructing more carefully.
    """

    def search_google_flights_for_dates(origin_iata: str, destination_iata: str, flight_class: str) -> dict:
        """Searches Google Flights (via SerpAPI) for round-trip options
        between the given airports, for this request's fixed dates.

        Args:
            origin_iata: Departure airport's 3-letter uppercase IATA code
                (e.g. "CGK"). SerpAPI's google_flights engine rejects
                free-text city names here — resolve the city to its primary
                airport's IATA code yourself before calling this tool.
            destination_iata: Arrival airport's 3-letter uppercase IATA
                code (e.g. "DPS"), same rule as origin_iata.
            flight_class: One of economy, premium_economy, business, first.

        Returns:
            dict: {"combos": [...]} or {"error": message} — see
            search_google_flights's docstring for the combo shape.
        """
        return search_google_flights(origin_iata, destination_iata, outbound_date, return_date, flight_class)

    tool = FunctionTool(func=search_google_flights_for_dates)
    return Agent(
        model=MODEL,
        name="flight_gatherer",
        description="Searches live round-trip flight prices via Google Flights.",
        instruction=(
            "You are given a JSON request with origin, destination, and "
            "flight_class, where origin/destination are free-text place "
            "names (e.g. a city). The trip dates are already fixed for "
            "this search — you don't need to read or pass them anywhere. "
            "First determine the 3-letter uppercase IATA code of the "
            "primary international airport serving each place (e.g. "
            "Jakarta -> CGK, Bali/Denpasar -> DPS, London -> LHR) — use "
            "your own knowledge for this, picking the single best-known "
            "airport if a city has several.\n"
            "Two specific, verified exceptions where you must override your "
            "own general knowledge — for every other place, resolve it "
            "yourself as normal:\n"
            "- Yogyakarta: ALWAYS use YIA, never JOG. Yogyakarta "
            "International Airport (YIA) opened in 2020 and is now the "
            "primary commercial airport for the region; the older "
            "Adisutjipto Airport (IATA code JOG), which you may recall as "
            "'the' Yogyakarta airport from training data, now has little "
            "to no scheduled commercial service, and a real search using "
            "JOG found zero flights.\n"
            "- Bandung: ALWAYS use CGK (Jakarta), never BDO or KJT. "
            "Bandung's own airport (Husein Sastranegara, BDO) had most "
            "routes discontinued in 2023 and lost international status in "
            "2024; its intended replacement (Kertajati, KJT) has also been "
            "confirmed to have no available flights. CGK is the nearest "
            "major hub with real service and is what Google Flights itself "
            "surfaces as the practical option for reaching Bandung right "
            "now — it's a real compromise (a different city, ~150km away), "
            "not Bandung's own airport, but it's the only option that "
            "actually returns bookable flights.\n"
            "Then call search_google_flights_for_dates with origin_iata/"
            "destination_iata set to those resolved codes (never pass the "
            "raw place name) and flight_class as given. The tool already "
            "returns fully-formed, correctly-rounded round-trip combos — "
            "your job is ONLY to report its 'combos' list back exactly as "
            "given, as JSON text. Do not summarize, recompute, reformat, "
            "or invent anything. If the tool returns an error, report that "
            "error plainly instead."
        ),
        tools=[tool],
    )
