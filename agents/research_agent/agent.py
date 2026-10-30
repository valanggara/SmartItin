"""Research Agent: destination research and attraction discovery via SerpAPI
web search. Same two-stage gatherer/formatter split as flight_agent — see
that module's docstring for why (output_schema + tools don't mix on
gemini-2.0-flash).

NOTE ON maps_link/image_url (top_attractions/hidden_gems): search_web gives
good descriptive text but no structured location data, so search_places
(SerpAPI's google_maps engine) is used to get a real candidate list of
place names with actual maps links (built from real gps_coordinates) and
real photos. An earlier version had the FORMATTER cross-reference
attraction names against that places list itself — in a real run it
fabricated a plausible-looking "https://example.com/image1.jpg" instead of
leaving the field empty as instructed, despite an explicit "never invent a
URL" instruction. task_manager.py does that matching in Python instead
(common.serpapi_tools.attach_place_matches) — the formatter is told to
just leave maps_link/image_url as empty strings; task_manager.py overwrites
them afterward with a real match or empty, guaranteeing correctness
regardless of what the formatter says.

search_places is NOT exposed as a tool the gatherer LLM can choose to call
— task_manager.py calls it directly in Python instead, with two fully
templated queries ("top attractions in <destination>", "hidden gems in
<destination> city"). It used to be an LLM-callable tool (still is on the
`main` branch), but on gpt-4o-mini (see common/llm_config.py) a real run
showed the gatherer skipping it entirely — 0 calls logged — despite an
explicit two-call instruction, same class of failure as the flight-combo-
dropping and URL-fabrication bugs: an LLM given a long multi-step
instruction with multiple tools is not reliable at executing every step.
Since the query strings need no LLM judgment at all, there's no reason to
route the call through the model.
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from common.llm_config import get_model
from common.schemas import ResearchResponse
from common.serpapi_tools import search_web

MODEL = get_model()

web_search_tool = FunctionTool(func=search_web)

research_gatherer_agent = Agent(
    model=MODEL,
    name="research_gatherer",
    description="Researches a destination's climate, culture, safety, and attractions.",
    instruction=(
        "You are given a JSON request with destination, start_date, "
        "end_date, and theme (e.g. family holiday, solo traveler, culinary). "
        "Use search_web (call it several times with different queries) to "
        "research: what makes this destination distinctive — its history, "
        "cultural character, or the specific reason travelers go there (e.g. "
        "royal heritage, a famous natural feature, a food scene) — as well "
        "as typical weather/climate for the given dates (season, rain, "
        "humidity, sunshine — not just a temperature number), local culture "
        "and etiquette notes, safety tips for travelers, top tourist "
        "attractions, and lesser-known hidden-gem spots — favor findings "
        "that fit the given theme. Hidden gems must be genuinely IN or a "
        "short trip from <destination> itself (walkable or a short local "
        "ride) — a multi-hour-away regional attraction is NOT a hidden gem "
        "of <destination>, it belongs in the day-trip research below "
        "instead.\n"
        "Also use search_web to find 3-5 candidate day-trip / nearby "
        "destinations reachable from <destination> (e.g. 'day trips from "
        "<destination>', 'nearby destinations from <destination>') — note "
        "each candidate's approximate travel time and what it's known for, "
        "so a later step can pick genuinely complementary ones (not places "
        "whose main draw duplicates what's already covered above).\n"
        "Write a detailed plain-text summary covering all of the above, "
        "organized by category (including the day-trip candidates)."
    ),
    tools=[web_search_tool],
)

research_formatter_agent = Agent(
    model=MODEL,
    name="research_formatter",
    description="Formats destination research findings into the strict ResearchResponse JSON schema.",
    instruction=(
        "Convert the destination research findings you are given into the "
        "required JSON schema: why_visit, a climate summary, a list of "
        "culture_notes, a list of safety_tips, top_attractions (exactly 3 — "
        "the single best/most iconic ones only), hidden_gems (exactly 3 — "
        "the single best ones only; each attraction has a name, "
        "description, maps_link, and image_url), and trip_extensions. Base "
        "every field only on the findings provided — do not invent facts "
        "not present there.\n"
        "For EVERY attraction (top_attractions and hidden_gems), always set "
        "maps_link and image_url to empty strings '' — a separate step "
        "fills those in from verified real data afterward, so do not try to "
        "guess, construct, or recall a URL for them yourself.\n"
        "trip_extensions: up to 3 optional day-trip/nearby destinations a "
        "traveler could add to this trip, each with name, travel_time (from "
        "<destination>), reason (why it's worth the extra time), "
        "best_suited_for (a list of tags like 'history', 'food', 'nature', "
        "'culture', 'shopping', 'nightlife', 'adventure'), and "
        "suggested_duration ('half-day', 'full-day', or 'overnight'). "
        "Before including one, check ALL of:\n"
        "  - it is NOT simply a nearby city or attraction for its own sake — "
        "it must offer a genuinely different experience from what's already "
        "in top_attractions/hidden_gems above, not a rehash;\n"
        "  - its primary draw is not already covered by an attraction "
        "already listed in top_attractions or hidden_gems;\n"
        "  - you can articulate a concrete reason a traveler would spend "
        "additional time there (the 'reason' field must say this, not just "
        "restate the name);\n"
        "  - it complements the main destination rather than repeating it.\n"
        "If fewer than 3 candidates meet all of these, include only the "
        "ones that do — if NONE do, return an empty list. Never pad "
        "trip_extensions with a weak or duplicate recommendation just to "
        "reach 3.\n"
        "why_visit is a short 2-4 sentence narrative introduction to the "
        "destination — its history, cultural character, or what makes it "
        "distinctive — written BEFORE any weather/attraction specifics, so "
        "a traveler gets context on why this place is worth visiting before "
        "seeing the practical details. For example: 'Yogyakarta is "
        "considered the cultural heart of Java, known for its royal "
        "heritage, traditional arts, and proximity to UNESCO World Heritage "
        "sites like Borobudur and Prambanan. It offers a slower pace than "
        "Jakarta and is ideal for travelers interested in history, local "
        "cuisine, and Javanese culture.' Base it only on the findings "
        "provided, do not invent history/facts not present there.\n"
        "climate: a full descriptive paragraph (2-3 sentences), NOT just a "
        "bare number range — cover the season/conditions during the travel "
        "dates (e.g. dry/rainy season, sunshine, humidity, what it means "
        "for packing or activities), same as you would for why_visit. "
        "Within that paragraph, state temperatures in Celsius FIRST as the "
        "primary unit, with Fahrenheit second in parentheses as a secondary "
        "reference, e.g.: 'August is one of the driest months, with plenty "
        "of sunshine and high humidity. Daily highs reach 27-34°C "
        "(81-93°F), dropping to a more comfortable 22-25°C (72-77°F) "
        "overnight — expect a light rain jacket only occasionally.' Never "
        "state Fahrenheit before Celsius, and never output just the "
        "temperature figures with no surrounding sentence. If the findings "
        "only give one unit, convert precisely using °C = (°F - 32) x 5/9 "
        "(or the inverse) rather than guessing an approximate figure.\n"
        "Every attraction and hidden gem named in the findings MUST appear "
        "in your output — never omit one."
    ),
    output_schema=ResearchResponse,
)
