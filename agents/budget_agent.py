from typing import Any, Dict

from tools.budget_tool import calculate_budget, BudgetCalculationError
from utils.logger import get_logger

logger = get_logger("agents.budget")

DEFAULT_ALLOCATION = {
    "catering": 45,
    "decoration": 15,
    "logistics": 15,
    "marketing": 10,
    "contingency": 15,
}


class BudgetAgent:
    """Agent responsible for budget allocation and feasibility."""

    name = "Budget Agent"

    def run(self, requirements: Dict[str, Any], venue_cost: float) -> Dict[str, Any]:
        logger.info("Analyzing budget...")

        total_budget = requirements.get("budget")

        # Use predefined allocation to avoid unnecessary API calls
        allocation = DEFAULT_ALLOCATION

        logger.info("Using standard budget allocation strategy.")

        logger.info("Invoking BudgetCalculatorTool...")

        try:
            result = calculate_budget(
                total_budget=total_budget,
                venue_cost=venue_cost,
                attendees=requirements.get("attendees"),
            )
            

        except BudgetCalculationError as e:
            logger.error(f"Budget calculation failed: {e}")

            return {
                "status": "error",
                "error": str(e),
                "total_estimated_cost": None,
                "within_budget": False,
            }

        result["status"] = "ok"

        if not result["within_budget"]:
            over_by = round(
                result["total_estimated_cost"] - result["total_budget"],
                2
            )

            result["recommendation"] = (
                f"Reduce spending by at least ₹{over_by} - "
                f"consider a cheaper venue or lowering "
                f"contingency/decoration allocation."
            )

            logger.warning(f"Budget exceeded by ₹{over_by}.")

        else:
            logger.info("✓ Budget calculated")

        return result