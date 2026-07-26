"""
Unit tests for the deterministic Budget Calculator Tool.
Run with: pytest tests/test_budget_tool.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.budget_tool import calculate_budget
from pydantic import ValidationError


def test_budget_calculation_within_budget():
    result = calculate_budget(
        total_budget=70000,
        venue_cost=15000,
        category_percentages={"catering": 60, "decoration": 20, "logistics": 20},
    )
    assert result["within_budget"] is True
    assert result["total_estimated_cost"] <= 70000
    assert result["remaining_budget"] == round(70000 - result["total_estimated_cost"], 2)


def test_budget_calculation_exceeds_budget():
    result = calculate_budget(
        total_budget=10000,
        venue_cost=9000,
        category_percentages={"catering": 100},
    )
    # venue (9000) + all remaining 1000 spent on catering = 10000, exactly at budget
    assert result["within_budget"] is True

    result2 = calculate_budget(
        total_budget=10000,
        venue_cost=12000,
        category_percentages={"catering": 100},
    )
    assert result2["within_budget"] is False


def test_negative_budget_is_rejected():
    with pytest.raises(ValidationError):
        calculate_budget(total_budget=-500, venue_cost=1000, category_percentages={})


def test_negative_venue_cost_is_rejected():
    with pytest.raises(ValidationError):
        calculate_budget(total_budget=5000, venue_cost=-100, category_percentages={})


def test_zero_budget_is_rejected():
    with pytest.raises(ValidationError):
        calculate_budget(total_budget=0, venue_cost=100, category_percentages={})
