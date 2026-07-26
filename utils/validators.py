"""
Deterministic validation helpers.

These are plain Python functions (NOT LLM calls) used to validate
requirements, tool inputs, and agent outputs before they are trusted
by the Decision Agent. Keeping validation deterministic prevents the
system from relying on the LLM for correctness-critical checks.
"""

from typing import Any, Dict, List, Tuple


class ValidationError(Exception):
    """Raised when a critical validation rule fails."""


def validate_attendees(attendees: Any) -> int:
    if attendees is None:
        raise ValidationError("Attendee count is missing.")
    try:
        attendees = int(attendees)
    except (TypeError, ValueError):
        raise ValidationError(f"Attendee count '{attendees}' is not a valid integer.")
    if attendees <= 0:
        raise ValidationError("Attendee count must be greater than zero.")
    return attendees


def validate_budget(budget: Any) -> float:
    if budget is None:
        raise ValidationError("Budget is missing.")
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        raise ValidationError(f"Budget '{budget}' is not a valid number.")
    if budget <= 0:
        raise ValidationError("Budget must be greater than zero.")
    return budget


def validate_requirements(requirements: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that the structured requirements dict produced by the
    Requirement Analysis Agent contains the minimum critical fields.

    Returns (is_valid, list_of_problems).
    """
    problems: List[str] = []
    required_fields = ["event_type", "location", "attendees", "budget", "venue_type"]

    for field in required_fields:
        if field not in requirements or requirements[field] in (None, "", []):
            problems.append(f"Missing required field: '{field}'")

    if "attendees" in requirements and requirements["attendees"] not in (None, ""):
        try:
            validate_attendees(requirements["attendees"])
        except ValidationError as e:
            problems.append(str(e))

    if "budget" in requirements and requirements["budget"] not in (None, ""):
        try:
            validate_budget(requirements["budget"])
        except ValidationError as e:
            problems.append(str(e))

    venue_type = requirements.get("venue_type")
    if venue_type and venue_type not in ("indoor", "outdoor"):
        problems.append(f"Invalid venue_type: '{venue_type}' (expected 'indoor' or 'outdoor')")

    return (len(problems) == 0, problems)


def validate_venue_capacity(venue: Dict[str, Any], attendees: int) -> bool:
    """Venue capacity must be >= attendees."""
    return int(venue.get("capacity", 0)) >= attendees


def validate_total_cost(total_cost: float, budget: float) -> bool:
    """Total plan cost must not exceed budget."""
    return total_cost <= budget


def is_weather_result_valid(weather_result: Dict[str, Any]) -> bool:
    """
    A weather result is only usable by the Decision Agent if the connector
    call succeeded and returned the expected structured fields.
    """
    if not weather_result:
        return False
    if weather_result.get("status") != "ok":
        return False
    required_keys = {"temperature_c", "condition", "rain_expected"}
    return required_keys.issubset(weather_result.keys())
