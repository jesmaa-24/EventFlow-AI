
from typing import Any, Dict, List


from utils.logger import get_logger
from utils.validators import validate_venue_capacity, validate_total_cost

logger = get_logger("agents.decision")

STATUS_APPROVE = "APPROVE"
STATUS_REVISE = "REVISE"
STATUS_REJECT = "REJECT"


class DecisionAgent:
    """Agent responsible for the final APPROVE / REVISE / REJECT decision."""
    name = "Decision Agent"

    def evaluate(self, requirements: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Checking constraints...")

        violations: List[str] = []
        agents_to_retry: List[str] = []
        checks: Dict[str, str] = {}

        attendees = requirements.get("attendees")
        budget = requirements.get("budget")

        venue_info = results.get("venue", {})
        selected_venue = venue_info.get("selected_venue")
        budget_info = results.get("budget", {})
        logistics_info = results.get("logistics", {})

        # --- Venue existence / capacity -----------------------------------
        if venue_info.get("status") == "no_match" or not selected_venue:
            violations.append("No suitable venue found.")
            checks["Venue Capacity"] = "FAIL"
            checks["Venue Preference"] = "FAIL"
            agents_to_retry.append("venue_agent")
        else:
            if validate_venue_capacity(selected_venue, attendees):
                checks["Venue Capacity"] = "PASS"
            else:
                checks["Venue Capacity"] = "FAIL"
                violations.append(
                    f"Venue capacity ({selected_venue.get('capacity')}) is below attendee count ({attendees})."
                )
                agents_to_retry.append("venue_agent")

            if requirements.get("venue_type") and selected_venue.get("type") != requirements.get("venue_type"):
                checks["Venue Preference"] = "FAIL"
                violations.append(
                    f"Venue type '{selected_venue.get('type')}' does not match preference "
                    f"'{requirements.get('venue_type')}'."
                )
                if "venue_agent" not in agents_to_retry:
                    agents_to_retry.append("venue_agent")
            else:
                checks["Venue Preference"] = "PASS"

        # --- Budget ----------------------------------------------------------
        if budget_info.get("status") == "error" or budget_info.get("total_estimated_cost") is None:
            checks["Budget"] = "FAIL"
            violations.append("Budget could not be calculated.")
            agents_to_retry.append("budget_agent")
        elif validate_total_cost(budget_info["total_estimated_cost"], budget):
            checks["Budget"] = "PASS"
        else:
            checks["Budget"] = "FAIL"
            violations.append(
                f"Estimated cost ₹{budget_info['total_estimated_cost']} exceeds budget ₹{budget}."
            )
            agents_to_retry.append("budget_agent")

        # --- Weather (only relevant for outdoor events) -----------------------
        weather = logistics_info.get("weather", {})
        if requirements.get("venue_type") == "outdoor":
            if weather.get("status") == "ok":
                if weather.get("rain_expected"):
                    checks["Weather"] = "FAIL"
                    violations.append("Rain is expected - outdoor event may be unsuitable.")
                    agents_to_retry.append("logistics_agent")
                else:
                    checks["Weather"] = "PASS"
            elif weather.get("status") == "unavailable":
                checks["Weather"] = "UNKNOWN"
                logger.warning("Weather validation could not be completed.")
            else:
                checks["Weather"] = "UNKNOWN"
        else:
            checks["Weather"] = "N/A"

        # --- Missing/invalid requirement fields -------------------------------
        if requirements.get("_problems"):
            violations.extend(requirements["_problems"])

        agents_to_retry = sorted(set(agents_to_retry))

        # --- Determine status --------------------------------------------
        fatal = requirements.get("attendees") in (None, 0) or requirements.get("budget") in (None, 0)
        if fatal:
            status = STATUS_REJECT
        elif not violations:
            status = STATUS_APPROVE
        else:
            status = STATUS_REVISE

        score = self._score(checks)

        result = {
            "status": status,
            "score": score,
            "violations": violations,
            "recommendations": self._build_recommendations(violations),
            "agents_to_retry": agents_to_retry if status == STATUS_REVISE else [],
            "checks": checks,
        }

        for label, outcome in checks.items():
            logger.info(f"{label:.<22}{outcome}")

        result["reason"] = self._default_reason(status)
        logger.info(f"Decision: {status}")
        return result

    @staticmethod
    def _score(checks: Dict[str, str]) -> int:
        relevant = [v for v in checks.values() if v in ("PASS", "FAIL")]
        if not relevant:
            return 0
        passed = sum(1 for v in relevant if v == "PASS")
        return round((passed / len(relevant)) * 100)

    @staticmethod
    def _build_recommendations(violations: List[str]) -> List[str]:
        recs = []
        for v in violations:
            if "exceeds budget" in v:
                recs.append("Consider a lower-cost venue or reduce non-essential category spend.")
            elif "capacity" in v.lower():
                recs.append("Choose a venue with higher capacity.")
            elif "Rain" in v:
                recs.append("Consider an indoor backup venue or reschedule.")
        return recs

    @staticmethod
    def _default_reason(status: str) -> str:
        return {
            STATUS_APPROVE: "All major constraints are satisfied.",
            STATUS_REVISE: "One or more constraints require adjustment before approval.",
            STATUS_REJECT: "Critical requirements are missing or invalid.",
        }.get(status, "")
