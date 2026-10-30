"""Accommodation & Food Agent: hotels matched to the explicit hotel_stars
choice; restaurants matched to the tier-locked dining_style. Same two-stage
gatherer/formatter split as flight_agent — see that module's docstring for
why (output_schema + tools don't mix on gemini-2.0-flash).

NOTE ON maps_link/image_url: generic web search (search_web, SerpAPI's
"google" engine) surfaces good descriptive text for price/amenities/cuisine
via organic result snippets, but has no structured location data. SerpAPI's
"google_maps" engine has the opposite trade-off: real GPS coordinates and
photo thumbnails per place, but no reliable price/amenity/cuisine fields.
So both are used together: search_web still drives the descriptive
findings, and search_places (google_maps) gets a real candidate list with
actual maps links and photos. task_manager.py does the name-matching in
Python (common.serpapi_tools.attach_place_matches), not the formatter — an
earlier version had the formatter cross-reference names itself, and in a
real run (research_agent, which used the identical pattern) it fabricated
a plausible-looking "https://example.com/image1.jpg" instead of leaving
the field empty as instructed.

search_places is NOT exposed as a tool the gatherer LLM can choose to call
either — task_manager.py calls it directly in Python, with two fully
templated queries. It used to be an LLM-callable tool (still is on the
`main` branch), but on gpt-4o-mini (see common/llm_config.py) a real run
showed research_agent's identical gatherer pattern skip the call entirely
— 0 calls logged — despite an explicit instruction to make it. Since
neither query string needs any LLM judgment, there's no reason to route
either call through the model.
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from common.llm_config import get_model
from common.schemas import StayFoodResponse
from common.serpapi_tools import search_web

MODEL = get_model()

web_search_tool = FunctionTool(func=search_web)

stay_food_gatherer_agent = Agent(
    model=MODEL,
    name="stay_food_gatherer",
    description="Finds hotels by star rating and restaurants by dining style.",
    instruction=(
        "You are given a JSON request with destination, hotel_stars (a list "
        "of acceptable star ratings, e.g. [4] or [3,4]), dining_style (a "
        "locked description such as 'fine dining' or 'street food and "
        "casual local eateries'), theme, and nights. Use search_web (call "
        "it several times) to find: 3 real hotels/guesthouses/resorts in "
        "the destination matching ONLY the given hotel_stars ratings, with "
        "approximate nightly price in IDR, guest rating, and key "
        "facilities; and 4 real restaurants matching ONLY the given "
        "dining_style, with cuisine type, approximate price range in IDR, "
        "and location/area.\n"
        "If halal_food is true, every restaurant MUST be halal-certified "
        "or clearly Muslim-friendly (serves no pork, no alcohol-focused "
        "venues such as bars or izakaya) — include 'halal' in your "
        "search_web queries, and for each restaurant note what makes it "
        "halal (certification body, Muslim-owned, halal menu). Never "
        "include a restaurant whose halal status you couldn't find.\n"
        "Write a detailed plain-text summary of the descriptive findings "
        "from search_web."
    ),
    tools=[web_search_tool],
)

stay_food_formatter_agent = Agent(
    model=MODEL,
    name="stay_food_formatter",
    description="Formats hotel/restaurant findings into the strict StayFoodResponse JSON schema.",
    instruction=(
        "Convert the hotel and restaurant findings you are given into the "
        "required JSON schema: exactly 3 stays — the single best ones only "
        "(each with name, location, price_per_night_idr, rating, stars, "
        "facilities, maps_link, image_url) — and exactly 4 restaurants — "
        "the single best ones only (each with name, cuisine, "
        "price_range_min_idr, price_range_max_idr, location, maps_link, "
        "image_url). price_range_min_idr/price_range_max_idr are plain "
        "integers (e.g. 150000 and 300000, NOT \"150000-300000\" or "
        "\"Rp150,000\") — the frontend formats them for display itself, so "
        "do not add currency symbols, thousands separators, or units. Only "
        "include stays whose stars value is one of the requested "
        "hotel_stars, and restaurants consistent with the requested "
        "dining_style. Base every field only on the findings provided — do "
        "not invent options that weren't found.\n"
        "If halal food is required, only include restaurants the findings "
        "identify as halal or Muslim-friendly, and start their cuisine "
        "field with 'Halal · ' (e.g. 'Halal · Japanese ramen').\n"
        "For EVERY stay and restaurant, always set maps_link and image_url "
        "to empty strings '' — a separate step fills those in from verified "
        "real data afterward, so do not try to guess, construct, or recall "
        "a URL for them yourself."
    ),
    output_schema=StayFoodResponse,
)
