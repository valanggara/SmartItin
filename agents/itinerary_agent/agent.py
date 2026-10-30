"""Itinerary Agent: day-by-day itinerary generation from destination research
and accommodation context. No tools needed (it only reasons over context
already gathered by other agents), so it can use output_schema directly in
LlmAgents — no gatherer/formatter split required here.

Two modes, both handled by this ONE agent (task_manager.py branches on the
incoming payload's "mode" field) rather than spinning up a separate agent
for modifications:
  - itinerary_create_agent — the original CREATE mode: builds a fresh
    itinerary from research + accommodation context. Unchanged behavior.
  - itinerary_modify_agent — MODIFY mode: edits an EXISTING itinerary in
    place for a given `action` (currently "add_extension"; the request/
    response schema is intentionally generic — action + action_params —
    so future actions like "remove_activity", "replace_activity",
    "make_relaxed", "add_restaurants", "reduce_walking", "extend_trip", and
    "shorten_trip" can reuse this exact agent and pipeline by adding a new
    paragraph to the instruction below, without touching the schema, the
    host agent's routing, or the frontend's call shape.
"""

from __future__ import annotations

from google.adk.agents import Agent

from common.llm_config import get_model
from common.schemas import ItineraryModifyResponse, ItineraryResponse

MODEL = get_model()

itinerary_create_agent = Agent(
    model=MODEL,
    name="itinerary_create_agent",
    description="Builds a day-by-day travel itinerary from research and accommodation context.",
    instruction=(
        "You are given the exact list of dates the itinerary must cover, "
        "the trip's theme, budget tier, and travel pace, JSON context from "
        "a destination-research agent and an accommodation/dining agent, "
        "and TWO separate budgets across the whole trip: one for dining, "
        "one for paid activities/attractions. Produce one DayPlan per "
        "listed date, in order, with morning, afternoon, and evening plans "
        "that draw on the provided attractions, hidden gems, and "
        "restaurant options. Route each day around the chosen stay's "
        "location where relevant, and note transportation between "
        "activities. Keep every activity and meal consistent with the "
        "given budget tier's activity/dining style. Set each day's "
        "estimated_cost_idr to a realistic total for that day's activities "
        "and meals at that tier — internally track activity spending "
        "against the activity budget and dining spending against the food "
        "budget separately (estimated_cost_idr itself stays one combined "
        "number per day, but let each sub-total guide how much you spend "
        "on sightseeing vs. meals that day), and aim for each budget's "
        "running total across the whole trip to land close to what was "
        "given — they're planning targets, not hard caps, so don't "
        "sacrifice a realistic recommendation just to hit either number "
        "exactly, but don't ignore them either.\n"
        "If the dietary requirement is halal, it is non-negotiable: every "
        "meal you name must be at a halal or Muslim-friendly place "
        "(prefer the provided halal restaurants), never suggest pork "
        "dishes, alcohol, bars, pubs, wine/sake tastings, or nightlife "
        "built around drinking. Where it fits naturally, note a nearby "
        "mosque or prayer room around midday/afternoon on full sightseeing "
        "days.\n"
        "travel_pace controls how much is scheduled per day — it's a firm "
        "stylistic choice, not a soft suggestion. The schema always has "
        "three slots (morning/afternoon/evening) and none can be left "
        "blank, so pace must show up in what you WRITE in each slot, not "
        "just its tone:\n"
        "  - 'relaxed': on MOST days, exactly one of the three slots must "
        "explicitly be unscheduled rest/free time — write it as that "
        "literally (e.g. 'Free morning to rest at the hotel or explore "
        "nearby at your own pace', 'Free afternoon — relax by the pool or "
        "wander the neighborhood') rather than naming another attraction. "
        "The other two slots hold at most one real activity each, "
        "unhurried, with a long meal or slow-paced stop rather than "
        "sightseeing. Never fill all three slots with named attractions on "
        "a relaxed day.\n"
        "  - 'packed': every slot on EVERY day is a substantive named "
        "activity — never 'free', 'relax', or any unscheduled framing, "
        "that phrasing is reserved for 'relaxed' pace only — and "
        "where realistic, note a second stop within a slot (e.g. two "
        "nearby attractions back-to-back, or an activity plus a market "
        "stop on the way) — minimize idle time and sequence activities to "
        "minimize backtracking, but keep it achievable in a real day."
    ),
    output_schema=ItineraryResponse,
)

itinerary_modify_agent = Agent(
    model=MODEL,
    name="itinerary_modify_agent",
    description="Edits an existing itinerary for a requested change, preserving as much as possible.",
    instruction=(
        "You are given an EXISTING day-by-day itinerary (current_itinerary), "
        "an `action` naming the requested change, `action_params` with that "
        "action's specific data, and the same destination/budget_tier/theme/"
        "research/accommodation context the itinerary was originally built "
        "from. Your job is to EDIT the existing itinerary for this one "
        "action — never regenerate it from scratch, never touch days or "
        "activities unrelated to the requested change.\n"
        "\n"
        "General rules for every action:\n"
        "- Preserve as much of current_itinerary as possible: keep existing "
        "morning/afternoon/evening plans, meals, hotel stays, and "
        "transportation notes untouched unless the action requires "
        "changing them.\n"
        "- Reorder or move activities only when necessary to fit the "
        "change — don't reshuffle days that aren't affected.\n"
        "- Keep travel times and schedules realistic; never produce an "
        "impossible schedule (e.g. two far-apart full-day activities on "
        "the same day, or a day that starts before it ends).\n"
        "- estimated_cost_idr on any day you edit should stay a realistic "
        "total for that day's activities and meals at the given budget "
        "tier.\n"
        "- If the dietary requirement is halal, anything you add or change "
        "must stay halal: no pork, alcohol, bars, or drinking-focused "
        "venues.\n"
        "\n"
        "Action: add_extension — action_params has an 'extension' object "
        "(name, travel_time, reason, best_suited_for, suggested_duration) "
        "naming a nearby destination the traveler wants added to the trip. "
        "Try to insert it logically into the existing itinerary (e.g. as a "
        "day's main activity, or replacing a lower-priority block) WITHOUT "
        "extending the trip's date range or displacing hotel stays/meals "
        "that don't need to move. If it genuinely cannot fit realistically "
        "(e.g. its suggested_duration is 'overnight' but every remaining "
        "day is already full, or its travel_time makes the schedule "
        "impossible) — do NOT force it in. Instead set applied=false, leave "
        "modified_itinerary identical to current_itinerary, and populate "
        "alternatives with exactly these three options: "
        "{option: 'A', label: 'Replace the least important activity', "
        "description: <name the specific activity you'd swap and why>}, "
        "{option: 'B', label: 'Extend the trip by one day', description: "
        "<what that extra day would look like>}, {option: 'C', label: "
        "'Keep the current itinerary', description: <why skipping the "
        "extension is reasonable>}.\n"
        "\n"
        "Action: apply_alternative — a follow-up to an add_extension call "
        "that returned applied=false. action_params has 'extension' (same "
        "object as add_extension) and 'chosen_alternative' (one of the "
        "alternatives YOU proposed in that earlier turn — option/label/"
        "description, e.g. option 'A', label 'Replace the least important "
        "activity', description naming the specific activity to swap). "
        "Unlike add_extension, you must NOT return applied=false here — the "
        "traveler has already chosen this specific approach, so make it "
        "fit by following chosen_alternative.description as closely as "
        "possible. Only 'A'-style alternatives (replacing/adjusting "
        "existing activities within the current date range) are handled by "
        "this action — if chosen_alternative describes extending the trip's "
        "date range (a 'B'-style alternative), that requires a fresh flight "
        "search and is handled by a different flow entirely, so treat that "
        "case as an error you cannot fulfill: set applied=false, "
        "modified_itinerary identical to current_itinerary, reasoning "
        "explaining you cannot extend the trip's dates through this action, "
        "and alternatives as an empty list.\n"
        "\n"
        "Output fields: applied (true if you edited modified_itinerary, "
        "false if you're only offering alternatives), summary_of_changes "
        "(1-2 sentences a user would read), modified_itinerary (the full "
        "day list — identical to current_itinerary if applied=false), "
        "removed_activities (short text description of anything you took "
        "out, empty list if nothing was removed), added_activities (same, "
        "for anything new), reasoning (why you made these specific "
        "choices), alternatives (empty list unless applied=false)."
    ),
    output_schema=ItineraryModifyResponse,
)
