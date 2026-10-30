"""Budget tier configuration.

The Budget Tier always drives dining_style and activity_style. Flight Class
and Hotel Stars are only *pre-filled* from the tier's defaults by the
frontend — the request payload carries the user's actual (possibly
overridden) choice for those two fields, so agents must read flight_class /
hotel_stars directly from the request rather than re-deriving them here.
"""

from __future__ import annotations

from typing import TypedDict


class TierDefaults(TypedDict):
    flight_class: str
    hotel_stars: list[int]
    dining_style: str
    activity_style: str


TIER_DEFAULTS: dict[str, TierDefaults] = {
    "economy": {
        "flight_class": "economy",
        "hotel_stars": [2, 3],
        "dining_style": "street food and casual local eateries",
        "activity_style": "free or low-cost attractions",
    },
    "standard": {
        "flight_class": "premium_economy",
        "hotel_stars": [3, 4],
        "dining_style": "mid-range restaurants",
        "activity_style": "paid attractions and guided tours",
    },
    "luxury": {
        "flight_class": "business",
        "hotel_stars": [4, 5],
        "dining_style": "fine dining",
        "activity_style": "premium and private experiences",
    },
}

FLIGHT_CLASS_OPTIONS = ["economy", "premium_economy", "business", "first"]
HOTEL_STAR_OPTIONS = [2, 3, 4, 5]


def get_tier_defaults(budget_tier: str) -> TierDefaults:
    try:
        return TIER_DEFAULTS[budget_tier.strip().lower()]
    except KeyError as exc:
        raise ValueError(
            f"Unknown budget_tier: {budget_tier!r}. Expected one of {list(TIER_DEFAULTS)}"
        ) from exc
