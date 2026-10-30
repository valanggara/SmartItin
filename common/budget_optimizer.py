"""Combination optimizer for the Host Agent: given the flight candidates
from Flight Agent and stay candidates from Accommodation & Food Agent
(both already fetched, unfiltered, exactly as returned), scores every
flight x stay pairing and picks the best one.

Pure functions, no I/O, no SerpAPI/LLM calls — Flight Agent and Hotel
Agent stay completely unaware this exists; they keep returning their
normal top candidates regardless of budget. This module only reads
prices/ratings off objects they already produced.

Percentages are never hardcoded here — they come from
agents/host_agent/agent.py's budget_allocation_agent, which judges a
priority (low/medium/high) per category for the specific trip (e.g. an
economy budget_tier paired with 5-star hotel_stars signals "compromise on
flights, not lodging"). priorities_to_percentages() converts that
qualitative judgment to actual percentages with the fixed weight table
below — deterministic Python math, not LLM arithmetic. Percentages (from
whichever source) are planning TARGETS only, never hard filters — flight/
stay candidates are never discarded for being over/under a target; targets
only feed into scoring which combination to recommend.
"""

from __future__ import annotations

PRIORITY_WEIGHTS = {"low": 1, "medium": 2, "high": 3}

# Used only if budget_allocation_agent's call fails/errors — a neutral
# fallback, not a "correct" default (every real trip should get an actual
# per-trip judgment, not this).
DEFAULT_PRIORITIES = {"flight": "medium", "hotel": "medium", "food": "medium", "activity": "medium"}

# How much more heavily "don't blow the combined flight+hotel target"
# counts vs. the other signals below — soft (a combo exceeding it is
# never excluded outright), but this weight makes it dominate the score
# once violated, per the "soft but heavily weighted" requirement: a combo
# that blows the target will almost always lose to one that doesn't,
# unless every combo does.
TOTAL_BUDGET_WEIGHT = 4.0
FLIGHT_FIT_WEIGHT = 1.0
HOTEL_FIT_WEIGHT = 1.0
QUALITY_WEIGHT = 1.0


def priorities_to_percentages(priorities: dict[str, str]) -> dict[str, float]:
    """Converts {"flight": "low", "hotel": "high", "food": "medium",
    "activity": "medium"} to normalized percentages summing to 1.0, via a
    fixed weight table — never trusts an LLM to produce numbers that
    already sum to 1.0 on its own. Unknown/invalid priority strings fall
    back to "medium"'s weight rather than raising, so a slightly malformed
    LLM response still degrades to a reasonable default instead of
    crashing the whole trip request."""
    weights = {
        category: PRIORITY_WEIGHTS.get(level, PRIORITY_WEIGHTS["medium"]) for category, level in priorities.items()
    }
    total = sum(weights.values())
    if total <= 0:
        equal_share = 1.0 / len(priorities)
        return {category: equal_share for category in priorities}
    return {category: weight / total for category, weight in weights.items()}


def compute_allocation(total_budget_idr: int, percentages: dict[str, float]) -> dict[str, int]:
    """{"flight": int, "hotel": int, "food": int, "activity": int} —
    target amounts, not caps."""
    return {key: int(total_budget_idr * pct) for key, pct in percentages.items()}


def _budget_fit(price: int, target: int) -> float:
    """1.0 = exactly on target, decaying toward 0.0 the further away
    (either direction) price is."""
    if target <= 0:
        return 0.0
    return max(1.0 - abs(price - target) / target, 0.0)


def _total_budget_fit(combo_cost: int, target_total: int) -> float:
    """No penalty at or under target_total; a steep, uncapped-below
    penalty scaling with how far over it a combo goes."""
    if target_total <= 0 or combo_cost <= target_total:
        return 1.0
    overage_ratio = (combo_cost - target_total) / target_total
    return 1.0 - overage_ratio * 2


def _flight_quality(flight: dict) -> float:
    """Fewer total stops (outbound + return) scores higher."""
    outbound_stops = (flight.get("outbound") or {}).get("stops", 0)
    return_stops = (flight.get("return_leg") or {}).get("stops", 0)
    total_stops = outbound_stops + return_stops
    return max(1.0 - total_stops / 4, 0.0)


def _hotel_quality(stay: dict) -> float:
    """Guest rating (typically 0-5) normalized to [0, 1]."""
    return max(min(stay.get("rating", 0) / 5, 1.0), 0.0)


def select_best_combo(
    flights: list[dict], stays: list[dict], nights: int, total_budget_idr: int, percentages: dict[str, float]
) -> dict:
    """Scores every (flight, stay) pair and returns the winner.

    Returns:
        {
            "flight_index": int, "stay_index": int, "combo_cost_idr": int,
            "remaining_budget_idr": int, "food_budget_idr": int,
            "activity_budget_idr": int, "over_budget": bool,
            "allocation": {target amounts + total_budget_idr + over_budget,
                ready to build a BudgetAllocation with},
        }

    remaining_budget_idr (total_budget_idr minus the selected combo's
    cost, floored at 0) is split into food_budget_idr/activity_budget_idr
    using the food:activity ratio from `percentages` — not their original
    target amounts, since the selected flight/hotel may have over- or
    under-spent relative to their own targets, changing how much is
    actually left. These two feed itinerary_agent's two separate soft
    spending targets.

    Raises ValueError if `flights` or `stays` is empty — callers must
    only invoke this once both upstream results are confirmed non-empty.
    """
    if not flights or not stays:
        raise ValueError("select_best_combo requires at least one flight and one stay")

    allocation = compute_allocation(total_budget_idr, percentages)
    target_flight = allocation["flight"]
    target_hotel = allocation["hotel"]
    target_total = target_flight + target_hotel

    best: dict | None = None
    for f_idx, flight in enumerate(flights):
        flight_price = flight.get("price_total_idr", 0)
        for s_idx, stay in enumerate(stays):
            stay_total = stay.get("price_per_night_idr", 0) * nights
            combo_cost = flight_price + stay_total

            score = (
                FLIGHT_FIT_WEIGHT * _budget_fit(flight_price, target_flight)
                + HOTEL_FIT_WEIGHT * _budget_fit(stay_total, target_hotel)
                + TOTAL_BUDGET_WEIGHT * _total_budget_fit(combo_cost, target_total)
                + QUALITY_WEIGHT * (_flight_quality(flight) + _hotel_quality(stay)) / 2
            )

            if best is None or score > best["score"]:
                best = {
                    "score": score,
                    "flight_index": f_idx,
                    "stay_index": s_idx,
                    "combo_cost_idr": combo_cost,
                }

    assert best is not None  # flights/stays both non-empty, guaranteed by the guard above
    remaining = max(total_budget_idr - best["combo_cost_idr"], 0)
    over_budget = total_budget_idr - best["combo_cost_idr"] < 0

    food_pct = percentages.get("food", 0.0)
    activity_pct = percentages.get("activity", 0.0)
    food_activity_total = food_pct + activity_pct
    food_share = food_pct / food_activity_total if food_activity_total > 0 else 0.5
    food_budget_idr = int(remaining * food_share)
    activity_budget_idr = remaining - food_budget_idr

    return {
        "flight_index": best["flight_index"],
        "stay_index": best["stay_index"],
        "combo_cost_idr": best["combo_cost_idr"],
        "remaining_budget_idr": remaining,
        "food_budget_idr": food_budget_idr,
        "activity_budget_idr": activity_budget_idr,
        "over_budget": over_budget,
        "allocation": {
            "total_budget_idr": total_budget_idr,
            "target_flight_budget_idr": target_flight,
            "target_hotel_budget_idr": target_hotel,
            "target_food_budget_idr": allocation["food"],
            "target_activity_budget_idr": allocation["activity"],
            "over_budget": over_budget,
        },
    }
