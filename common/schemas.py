"""All Pydantic models shared across agents: request payloads and the
schema-enforced response shapes each LLM agent's output_schema targets."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

PriorityLevel = Literal["low", "medium", "high"]


# ─── Flight Agent ────────────────────────────────────────────────────────────
class FlightLeg(BaseModel):
    date: str
    departure_time: str
    arrival_time: str
    duration_hours: float
    flight_number: str
    airplane: str
    airline_logo: str
    stops: int


class FlightOption(BaseModel):
    airline: str
    flight_class: str
    price_total_idr: int
    outbound: FlightLeg
    return_leg: FlightLeg
    booking_link: str
    selected: bool = False


class FlightResponse(BaseModel):
    flights: list[FlightOption]


class FlightRequest(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str
    flight_class: str


# ─── Research Agent ──────────────────────────────────────────────────────────
class Attraction(BaseModel):
    name: str
    description: str
    maps_link: str
    image_url: str


class TripExtension(BaseModel):
    name: str
    travel_time: str
    reason: str
    best_suited_for: list[str]
    suggested_duration: str


class ResearchResponse(BaseModel):
    why_visit: str
    climate: str
    culture_notes: list[str]
    safety_tips: list[str]
    top_attractions: list[Attraction]
    hidden_gems: list[Attraction]
    trip_extensions: list[TripExtension]


class ResearchRequest(BaseModel):
    destination: str
    start_date: str
    end_date: str
    theme: str


# ─── Accommodation & Food Agent ──────────────────────────────────────────────
class StayOption(BaseModel):
    name: str
    location: str
    price_per_night_idr: int
    rating: float
    stars: int
    facilities: list[str]
    maps_link: str
    image_url: str
    selected: bool = False


class RestaurantOption(BaseModel):
    name: str
    cuisine: str
    price_range_min_idr: int
    price_range_max_idr: int
    location: str
    maps_link: str
    image_url: str


class StayFoodResponse(BaseModel):
    stays: list[StayOption]
    restaurants: list[RestaurantOption]


class AccommodationRequest(BaseModel):
    destination: str
    hotel_stars: list[int]
    budget_tier: str
    theme: str
    nights: int


# ─── Itinerary Agent ─────────────────────────────────────────────────────────
class DayPlan(BaseModel):
    day: int
    date: str
    morning: str
    afternoon: str
    evening: str
    estimated_cost_idr: int
    transportation_notes: str


class ItineraryResponse(BaseModel):
    itinerary: list[DayPlan]


class ItineraryRequest(BaseModel):
    destination: str
    start_date: str
    end_date: str
    theme: str
    budget_tier: str
    travel_pace: str
    nights: int
    food_budget_idr: int
    activity_budget_idr: int
    research_context: ResearchResponse
    accommodation_context: StayFoodResponse


# Modular modification pipeline: `action` names the kind of change
# ("add_extension" today; "remove_activity"/"replace_activity"/"make_relaxed"/
# "add_restaurants"/"reduce_walking"/"extend_trip"/"shorten_trip" are meant to
# reuse this exact request/response pair later — see itinerary_agent/agent.py).
class ItineraryModifyRequest(BaseModel):
    action: str
    action_params: dict
    current_itinerary: list[DayPlan]
    destination: str
    budget_tier: str
    theme: str
    nights: int
    research_context: ResearchResponse
    accommodation_context: StayFoodResponse


class ItineraryAlternative(BaseModel):
    option: str
    label: str
    description: str


class ItineraryModifyResponse(BaseModel):
    applied: bool
    summary_of_changes: str
    modified_itinerary: list[DayPlan]
    removed_activities: list[str]
    added_activities: list[str]
    reasoning: str
    alternatives: list[ItineraryAlternative]


# ─── Host Agent ──────────────────────────────────────────────────────────────
class TripRequest(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str
    theme: str
    budget_tier: str
    flight_class: str
    hotel_stars: int
    total_budget_idr: int
    travel_pace: str


# Raw output of agents/host_agent/agent.py's budget_allocation_agent — a
# per-trip judgment call (e.g. an economy tier paired with a 5-star hotel
# choice signals "willing to compromise on flights, not lodging"), not a
# fixed rule. Deliberately qualitative (low/medium/high), not raw
# percentages — task_manager.py converts these to percentages with a fixed
# weight table in Python, never trusting an LLM to produce numbers that
# already sum to 1.0 (same "don't trust an LLM's arithmetic" discipline as
# everywhere else in this codebase).
class BudgetPriorityDecision(BaseModel):
    flight_priority: PriorityLevel
    hotel_priority: PriorityLevel
    food_priority: PriorityLevel
    activity_priority: PriorityLevel
    reasoning: str


# Target amounts only (see common/budget_optimizer.py) — Flight Agent and
# Hotel Agent are never filtered by these, they're purely a planning
# reference used to score flight×hotel combinations and to show the user
# what was targeted vs. what was actually selected.
class BudgetAllocation(BaseModel):
    total_budget_idr: int
    target_flight_budget_idr: int
    target_hotel_budget_idr: int
    target_food_budget_idr: int
    target_activity_budget_idr: int
    over_budget: bool


class CostSummary(BaseModel):
    budget_tier: str
    estimated_flight_cost_idr: int
    estimated_stay_cost_idr: int
    estimated_itinerary_cost_idr: int
    estimated_total_cost_idr: int
    budget_allocation: BudgetAllocation
