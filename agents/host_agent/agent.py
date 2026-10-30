"""Host Agent's own LlmAgent: decides how to split the traveler's total
budget across flight/hotel/food/activity, as a per-trip judgment call
rather than a fixed percentage rule (e.g. an economy budget_tier paired
with a 5-star hotel_stars choice signals "willing to compromise on
flights, not lodging" — a fixed 30/40/30 split can't see that).

Deliberately outputs qualitative priorities (low/medium/high), not raw
percentages — common/budget_optimizer.py converts these to percentages
with a fixed weight table in Python. Every other numeric-precision bug
this project has hit (flight price formatting, combo counts, image/maps
matching) traced back to trusting an LLM with exact arithmetic; asking for
a category judgment instead of three numbers that must sum to 1.0 sidesteps
that whole class of failure.

No tools, so output_schema works directly (same as itinerary_agent) — no
gatherer/formatter split needed. Runs once per trip, in parallel with the
Flight/Research/Accommodation agent calls (see task_manager.py's
run_trip_stream) since it only needs the trip request, not their results.
"""

from __future__ import annotations

from google.adk.agents import Agent

from common.llm_config import get_model
from common.schemas import BudgetPriorityDecision

MODEL = get_model()

budget_allocation_agent = Agent(
    model=MODEL,
    name="budget_allocation_agent",
    description="Decides how to prioritize a traveler's total budget across flight, hotel, food, and activities.",
    instruction=(
        "You are given a trip's origin, destination, number of nights, "
        "budget tier, flight class, hotel stars, theme, travel pace, and "
        "total budget. Decide a priority — 'low', 'medium', or 'high' — "
        "for each of four categories: flight (round-trip airfare), hotel "
        "(the full stay, all nights combined), food (dining across the "
        "whole trip), and activities (paid attractions/tours across the "
        "whole trip). A higher priority means more of the total budget "
        "should be targeted there.\n"
        "Reason about the specific trip, don't apply a fixed rule:\n"
        "- Look for mismatches between budget_tier and the traveler's "
        "explicit flight_class/hotel_stars choices — these are the "
        "strongest signal of what they actually care about. Example: "
        "budget_tier 'economy' but hotel_stars is 5 means they're willing "
        "to compromise on flights to afford better lodging, so hotel "
        "should be 'high' priority and flight 'low', even though the tier "
        "alone would suggest everything should be economical. The reverse "
        "(a high tier but an economy flight_class override) means the "
        "opposite. When flight_class/hotel_stars are simply what the "
        "budget_tier already implies (no override), there's no mismatch "
        "signal from them specifically.\n"
        "- Nights: hotel and food/activity costs scale with trip length "
        "while flight cost is fixed regardless of nights, so a longer "
        "trip should generally lean flight priority down relative to the "
        "others compared to a short trip with the same total budget.\n"
        "- Travel pace: 'packed' (many paid activities each day) "
        "justifies a higher activity priority than 'relaxed' (more "
        "free/unscheduled time, fewer paid activities).\n"
        "- Theme: e.g. a culinary theme justifies a higher food priority; "
        "a nature/adventure theme might justify a higher activity "
        "priority; a pure relaxation theme might justify a higher hotel "
        "priority.\n"
        "State your reasoning briefly (1-2 sentences, naming the specific "
        "signals you used), then give the four priorities."
    ),
    output_schema=BudgetPriorityDecision,
)
