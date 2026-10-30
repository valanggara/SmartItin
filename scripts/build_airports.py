"""Builds frontend/public/airports.json — the dataset behind the Origin/
Destination airport dropdowns — from OurAirports' public-domain CSVs
(https://ourairports.com/data/).

Only airports with an IATA code AND scheduled commercial service are kept,
limited to large/medium airports: SerpAPI's google_flights engine needs an
IATA code, and the thousands of small airstrips in the raw data would only
bury real options in the dropdown.

Re-run whenever the list should be refreshed:
    python3 scripts/build_airports.py
"""

from __future__ import annotations

import csv
import io
import json
import urllib.request
from pathlib import Path

BASE_URL = "https://davidmegginson.github.io/ourairports-data"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "frontend" / "public" / "airports.json"
KEPT_TYPES = {"large_airport", "medium_airport"}

# OurAirports' "municipality" is where the airport physically sits, not the
# city it serves (Narita -> "Narita", Bali -> "Kuta, Badung"). The dropdown
# reads "COUNTRY - CITY", and city is also what research/accommodation
# agents get as the destination, so well-known mismatches are pinned here.
CITY_OVERRIDES = {
    "NRT": "Tokyo",
    "DPS": "Bali",
    "KUL": "Kuala Lumpur",
    "KNO": "Medan",
    "LOP": "Lombok",
    "SUB": "Surabaya",
    "EWR": "New York",
    "MXP": "Milan",
    "BGY": "Milan",
    "CTS": "Sapporo",
    "NGO": "Nagoya",
    "SYD": "Sydney",
    "CDG": "Paris",
    "ORY": "Paris",
    "BER": "Berlin",
    "ARN": "Stockholm",
    "OSL": "Oslo",
    "IAD": "Washington",
    "HKT": "Phuket",
    "USM": "Koh Samui",
    "CNX": "Chiang Mai",
    "SGN": "Ho Chi Minh City",
    "MLE": "Malé",
}


def _clean_city(municipality: str) -> str:
    # "Sydney (Mascot)" -> "Sydney", "London, Essex" -> "London"
    return municipality.split("(")[0].split(",")[0].strip()


def _ascii_keywords(keywords: str, iata: str, city: str) -> str:
    # Keep only Latin-script aliases (e.g. "Tokyo", "Bombay", "KLIA") so
    # typing them matches; ICAO codes and non-Latin names only add weight.
    seen = {iata.lower(), city.lower()}
    kept = []
    for word in keywords.split(","):
        word = word.strip()
        if not word or not word.isascii() or word.lower() in seen:
            continue
        seen.add(word.lower())
        kept.append(word)
    return ", ".join(kept)


def _fetch_csv(name: str) -> list[dict]:
    with urllib.request.urlopen(f"{BASE_URL}/{name}", timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def main() -> None:
    countries = {row["code"]: row["name"] for row in _fetch_csv("countries.csv")}

    airports = []
    seen_iata = set()
    for row in _fetch_csv("airports.csv"):
        iata = row["iata_code"].strip().upper()
        if (
            len(iata) != 3
            or iata in seen_iata
            or row["type"] not in KEPT_TYPES
            or row["scheduled_service"] != "yes"
        ):
            continue
        seen_iata.add(iata)
        city = CITY_OVERRIDES.get(iata) or _clean_city(row["municipality"]) or row["name"].strip()
        airports.append(
            {
                "iata": iata,
                "name": row["name"].strip(),
                "city": city,
                "country": countries.get(row["iso_country"], row["iso_country"]),
                "keywords": _ascii_keywords(row["keywords"], iata, city),
                # large airports first within a city, so e.g. Tokyo lists
                # Haneda/Narita before any regional field
                "large": row["type"] == "large_airport",
            }
        )

    airports.sort(key=lambda a: (a["country"], a["city"], not a["large"], a["name"]))
    OUTPUT_PATH.write_text(json.dumps(airports, ensure_ascii=False, separators=(",", ":")))
    print(f"Wrote {len(airports)} airports to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
