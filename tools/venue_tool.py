"""
Venue Search Tool.

Filters the SAMPLE venue dataset (data/venues.json) deterministically by
location, capacity, price ceiling, and indoor/outdoor preference. No LLM
involvement - this is plain data filtering so results are reproducible
and auditable.
"""

import json
import os
from typing import Dict, List, Optional

from langchain_core.tools import tool

from utils.logger import get_logger

logger = get_logger("tools.venue")

_VENUES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "venues.json")


class VenueSearchError(Exception):
    """Raised when venue search inputs are invalid."""


def _load_venues() -> List[Dict]:
    try:
        with open(_VENUES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("venues", [])
    except FileNotFoundError:
        logger.error(f"Venue dataset not found at {_VENUES_PATH}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Venue dataset is malformed JSON: {e}")
        return []


def search_venues(
    location: Optional[str],
    attendees: int,
    max_price: Optional[float] = None,
    venue_type: Optional[str] = None,
) -> List[Dict]:
    """
    Core deterministic filtering logic, callable directly (used by tests
    and by the tool wrapper below). This dataset is SAMPLE DATA, not a
    live inventory feed.
    """
    if attendees is None or attendees <= 0:
        raise VenueSearchError("attendees must be a positive integer for venue search.")

    venues = _load_venues()
    results = []

    for venue in venues:
        if location and venue.get("location", "").strip().lower() != location.strip().lower():
            continue
        if venue.get("capacity", 0) < attendees:
            continue
        if max_price is not None and venue.get("price", 0) > max_price:
            continue
        if venue_type and venue.get("type") != venue_type:
            continue
        results.append(venue)

    # Cheapest-first so the Venue Agent sees the most budget-friendly options first.
    results.sort(key=lambda v: v.get("price", 0))

    logger.info(
        f"Venue search: location={location}, attendees={attendees}, "
        f"max_price={max_price}, venue_type={venue_type} -> {len(results)} matches "
        f"(SAMPLE DATA)"
    )
    return results


@tool("venue_search_tool")
def venue_search_tool(
    location: str,
    attendees: int,
    max_price: float = None,
    venue_type: str = None,
) -> List[Dict]:
    """
    Search the SAMPLE venue dataset for venues matching location, minimum
    capacity, an optional maximum price, and an optional indoor/outdoor
    preference. Returns a list of matching venue records sorted by price.
    """
    return search_venues(location, attendees, max_price, venue_type)
