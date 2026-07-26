from typing import Dict

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from utils.logger import get_logger

logger = get_logger("tools.budget")


class BudgetCalculationError(Exception):
    """Raised when budget tool inputs are invalid."""


class BudgetCalculatorInput(BaseModel):
    total_budget: float = Field(..., description="Total event budget")
    venue_cost: float = Field(..., description="Venue cost")
    attendees: int = Field(..., description="Number of attendees")

    @field_validator("total_budget")
    @classmethod
    def check_total_budget(cls, v):
        if v <= 0:
            raise ValueError("total_budget must be greater than zero.")
        return v

    @field_validator("venue_cost")
    @classmethod
    def check_venue_cost(cls, v):
        if v < 0:
            raise ValueError("venue_cost cannot be negative.")
        return v

    @field_validator("attendees")
    @classmethod
    def check_attendees(cls, v):
        if v <= 0:
            raise ValueError("attendees must be greater than zero.")
        return v


def calculate_budget(
    total_budget: float,
    venue_cost: float,
    attendees: int,
) -> Dict:
    """
    Deterministically estimate event expenses.

    Venue cost is fixed.
    Other expenses are estimated using attendee count.
    """

    validated = BudgetCalculatorInput(
        total_budget=total_budget,
        venue_cost=venue_cost,
        attendees=attendees,
    )

    # -------- Estimated event expenses --------

    # Approximate catering cost per person
    catering_cost = validated.attendees * 100

    # Basic decoration estimate
    decoration_cost = 2000

    # Transport/setup/miscellaneous logistics
    logistics_cost = 1000

    # Emergency/extra expense reserve
    contingency_cost = 1000

    allocations = {
        "venue": round(validated.venue_cost, 2),
        "catering": round(catering_cost, 2),
        "decoration": round(decoration_cost, 2),
        "logistics": round(logistics_cost, 2),
        "contingency": round(contingency_cost, 2),
    }

    total_estimated_cost = round(
        validated.venue_cost
        + catering_cost
        + decoration_cost
        + logistics_cost
        + contingency_cost,
        2,
    )

    remaining_budget = round(
        validated.total_budget - total_estimated_cost,
        2,
    )

    within_budget = total_estimated_cost <= validated.total_budget

    result = {
        "total_budget": validated.total_budget,
        "venue_cost": validated.venue_cost,
        "category_allocations": allocations,
        "total_estimated_cost": total_estimated_cost,
        "remaining_budget": remaining_budget,
        "within_budget": within_budget,
    }

    logger.info(
        f"Budget calculated: total_cost={total_estimated_cost}, "
        f"remaining={remaining_budget}, "
        f"within_budget={within_budget}"
    )

    return result


@tool("budget_calculator_tool")
def budget_calculator_tool(
    total_budget: float,
    venue_cost: float,
    attendees: int,
) -> Dict:
    """Calculate estimated event expenses and remaining budget."""

    return calculate_budget(
        total_budget=total_budget,
        venue_cost=venue_cost,
        attendees=attendees,
    )