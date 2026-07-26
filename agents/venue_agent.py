
from typing import Any, Dict, Optional

from tools.venue_tool import search_venues, VenueSearchError
from utils.logger import get_logger

logger = get_logger("agents.venue")


class VenueAgent:
    """Agent responsible for finding and recommending a venue."""

    name = "Venue Agent"

    def run(
        self,
        requirements: Dict[str, Any],
        max_venue_budget: Optional[float] = None
    ) -> Dict[str, Any]:

        logger.info("Analyzing venue requirements...")

        location = requirements.get("location")
        attendees = requirements.get("attendees")
        venue_type = requirements.get("venue_type")

        logger.info("Invoking VenueSearchTool...")

        try:
            candidates = search_venues(
                location=location,
                attendees=attendees,
                max_price=max_venue_budget,
                venue_type=venue_type,
            )

        except VenueSearchError as e:
            logger.error(f"Venue search failed: {e}")

            return {
                "status": "error",
                "error": str(e),
                "selected_venue": None,
                "candidates": [],
            }

        if not candidates:
            logger.warning("No suitable venue found.")

            return {
                "status": "no_match",
                "selected_venue": None,
                "candidates": [],
                "reason": (
                    "No venues matched the location/capacity/"
                    "budget/type constraints (SAMPLE DATA)."
                ),
            }

        # Select cheapest suitable venue
        selected = candidates[0]

        reason = (
            "Selected as the lowest-cost venue meeting "
            "location, capacity, budget and venue-type constraints."
        )

        logger.info(
            f"✓ Suitable venues found "
            f"(selected: {selected['name']})"
        )

        return {
            "status": "ok",
            "selected_venue": selected,
            "candidates": candidates,
            "reason": reason,
        }