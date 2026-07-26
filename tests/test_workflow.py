"""
Workflow-level tests: tool selection, weather failure handling, and the
Decision Agent's constraint checking / APPROVE-REVISE-REJECT logic and
retry protection.

These tests avoid making real Gemini calls: DecisionAgent.evaluate()
wraps its LLM "reason" call in a try/except and falls back to a default
reason if GEMINI_API_KEY is not configured in the test environment, so
these tests exercise the deterministic logic exactly as it runs in
production, without needing a live API key.

Run with: pytest tests/test_workflow.py -v
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure no real Gemini key leaks into these deterministic-logic tests.
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("WEATHER_API_KEY", None)

from agents.coordinator_agent import CoordinatorAgent, MAX_RETRIES
from agents.decision_agent import DecisionAgent, STATUS_APPROVE, STATUS_REVISE, STATUS_REJECT
from connectors.weather_api import get_current_weather


# ---------------------------------------------------------------------------
# Weather failure handling
# ---------------------------------------------------------------------------
def test_weather_api_missing_key_does_not_crash():
    result = get_current_weather("Chennai")
    assert result["status"] == "unavailable"
    assert "error" in result


# ---------------------------------------------------------------------------
# Intelligent tool selection
# ---------------------------------------------------------------------------
def test_weather_tool_selected_for_outdoor_event():
    coordinator = CoordinatorAgent()
    requirements = {"venue_type": "outdoor", "location": "Chennai"}
    selection = coordinator.select_agents_and_tools(requirements)
    assert "WeatherTool" in selection["tools"]


def test_weather_tool_skipped_for_indoor_event():
    coordinator = CoordinatorAgent()
    requirements = {"venue_type": "indoor", "location": "Chennai"}
    selection = coordinator.select_agents_and_tools(requirements)
    assert "WeatherTool" not in selection["tools"]


# ---------------------------------------------------------------------------
# Decision Agent constraint checks
# ---------------------------------------------------------------------------
def _base_requirements(**overrides):
    req = {
        "event_type": "College Technical Event",
        "location": "Chennai",
        "attendees": 200,
        "budget": 70000,
        "venue_type": "indoor",
        "_problems": [],
    }
    req.update(overrides)
    return req


def test_decision_agent_detects_budget_violation():
    requirements = _base_requirements()
    results = {
        "venue": {
            "status": "ok",
            "selected_venue": {"venue_id": "V001", "name": "Hall", "capacity": 250, "type": "indoor", "price": 20000},
        },
        "budget": {"status": "ok", "total_estimated_cost": 90000, "within_budget": False},
        "logistics": {"status": "ok", "schedule": [], "recommendations": [], "weather": {"status": "not_applicable"}},
    }
    decision = DecisionAgent().evaluate(requirements, results)
    assert decision["status"] == STATUS_REVISE
    assert "budget_agent" in decision["agents_to_retry"]
    assert decision["checks"]["Budget"] == "FAIL"


def test_decision_agent_detects_insufficient_venue_capacity():
    requirements = _base_requirements(attendees=500)
    results = {
        "venue": {
            "status": "ok",
            "selected_venue": {"venue_id": "V001", "name": "Small Hall", "capacity": 100, "type": "indoor", "price": 10000},
        },
        "budget": {"status": "ok", "total_estimated_cost": 30000, "within_budget": True},
        "logistics": {"status": "ok", "schedule": [], "recommendations": [], "weather": {"status": "not_applicable"}},
    }
    decision = DecisionAgent().evaluate(requirements, results)
    assert decision["status"] == STATUS_REVISE
    assert "venue_agent" in decision["agents_to_retry"]
    assert decision["checks"]["Venue Capacity"] == "FAIL"


def test_approve_workflow():
    requirements = _base_requirements()
    results = {
        "venue": {
            "status": "ok",
            "selected_venue": {"venue_id": "V001", "name": "Hall", "capacity": 250, "type": "indoor", "price": 20000},
        },
        "budget": {"status": "ok", "total_estimated_cost": 65000, "within_budget": True},
        "logistics": {"status": "ok", "schedule": [], "recommendations": [], "weather": {"status": "not_applicable"}},
    }
    decision = DecisionAgent().evaluate(requirements, results)
    assert decision["status"] == STATUS_APPROVE
    assert decision["violations"] == []
    assert decision["score"] == 100


def test_revise_workflow_flags_correct_agent():
    requirements = _base_requirements(budget=20000)
    results = {
        "venue": {
            "status": "ok",
            "selected_venue": {"venue_id": "V001", "name": "Hall", "capacity": 250, "type": "indoor", "price": 20000},
        },
        "budget": {"status": "ok", "total_estimated_cost": 35000, "within_budget": False},
        "logistics": {"status": "ok", "schedule": [], "recommendations": [], "weather": {"status": "not_applicable"}},
    }
    decision = DecisionAgent().evaluate(requirements, results)
    assert decision["status"] == STATUS_REVISE
    assert decision["agents_to_retry"] == ["budget_agent"]


def test_maximum_retry_protection():
    """
    Simulates the main.py retry loop: if the Decision Agent keeps
    returning REVISE, the loop must stop after MAX_RETRIES and not run
    forever.
    """
    requirements = _base_requirements(budget=1000)  # impossible to satisfy
    results = {
        "venue": {
            "status": "ok",
            "selected_venue": {"venue_id": "V001", "name": "Hall", "capacity": 250, "type": "indoor", "price": 20000},
        },
        "budget": {"status": "ok", "total_estimated_cost": 25000, "within_budget": False},
        "logistics": {"status": "ok", "schedule": [], "recommendations": [], "weather": {"status": "not_applicable"}},
    }

    decision_agent = DecisionAgent()
    retries = 0
    decision = decision_agent.evaluate(requirements, results)

    while decision["status"] == STATUS_REVISE and retries < MAX_RETRIES:
        retries += 1
        decision = decision_agent.evaluate(requirements, results)  # same bad data -> still REVISE

    assert retries == MAX_RETRIES
    assert decision["status"] == STATUS_REVISE  # loop exits due to retry cap, not resolution
