"""TTL cache, persisted to disk under .cache/ so a process restart doesn't
lose previously-fetched results. research_agent and accommodation_food_agent
results cost real SerpAPI quota to produce; during development, restarting
agents to pick up a code change used to silently wipe an in-memory-only
cache, so the same destination got re-fetched (and re-billed) on every
restart even though its TTL hadn't expired.

Flight Agent results are intentionally NOT cached anywhere — fares are too
volatile; a cached "budget-tier-consistent" price could still be stale and
misleading. Research results cache for ~7 days (destination + theme rarely
change meaning day to day). Accommodation & Food results cache for ~6 hours.

The accommodation cache key includes hotel_stars (not just budget_tier): a
user can override hotel_stars independently of budget_tier, and keying on
budget_tier alone would serve stale results for the overridden star rating.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock
from typing import Any

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"


class TTLCache:
    def __init__(self, persist_file: str) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()
        self._persist_path = CACHE_DIR / persist_file
        self._load()

    def _load(self) -> None:
        if not self._persist_path.exists():
            return
        try:
            raw = json.loads(self._persist_path.read_text())
        except (OSError, json.JSONDecodeError):
            return
        now = time.time()
        self._store = {
            key: (expires_at, value) for key, (expires_at, value) in raw.items() if expires_at > now
        }

    def _save(self) -> None:
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(json.dumps(self._store))

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.time() >= expires_at:
                del self._store[key]
                self._save()
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            self._store[key] = (time.time() + ttl_seconds, value)
            self._save()


research_cache = TTLCache(persist_file="research_cache.json")
accommodation_cache = TTLCache(persist_file="accommodation_cache.json")

RESEARCH_TTL_SECONDS = 7 * 24 * 60 * 60
ACCOMMODATION_TTL_SECONDS = 6 * 60 * 60


def research_cache_key(destination: str, theme: str) -> str:
    return f"{destination.strip().lower()}::{theme.strip().lower()}"


def accommodation_cache_key(destination: str, budget_tier: str, hotel_stars: list[int]) -> str:
    stars_key = ",".join(str(s) for s in sorted(hotel_stars))
    return f"{destination.strip().lower()}::{budget_tier.strip().lower()}::{stars_key}"
