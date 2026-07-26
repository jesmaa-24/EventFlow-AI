
import json
from typing import Any, Dict, List

from agents import get_llm, parse_json_response
from agents.budget_agent import BudgetAgent
from agents.venue_agent import VenueAgent
from agents.logistics_agent import LogisticsAgent
from prompts.agent_prompts import coordinator_prompt
from utils.logger import get_logger

logger = get_logger("agents.coordinator")

MAX_RETRIES = 2


class CoordinatorAgent:
   
    name = "Coordinator Agent"

    def __init__(self):
        self.budget_agent = BudgetAgent()
        self.venue_agent = VenueAgent()
        self.logistics_agent = LogisticsAgent()

    # ------------------------------------------------------------------
    # Tool / agent selection
    # ------------------------------------------------------------------
    def select_agents_and_tools(self, requirements: Dict[str, Any]) -> Dict[str, List[str]]:
        """Deterministically decide which agents/tools this request needs."""
        agents_needed = ["venue_agent", "budget_agent", "logistics_agent"]

        tools_needed = ["VenueSearchTool", "BudgetCalculatorTool"]
        if requirements.get("venue_type") == "outdoor":
            tools_needed.append("WeatherTool")

        return {"agents": agents_needed, "tools": tools_needed}

    def log_tool_selection(self, selection: Dict[str, List[str]], requirements: Dict[str, Any]):
        logger.info("Required tools identified:")
        all_possible = ["BudgetCalculatorTool", "VenueSearchTool", "WeatherTool"]
        for tool_name in all_possible:
            if tool_name in selection["tools"]:
                logger.info(f"  ✓ {tool_name}")
            else:
                reason = "not required for indoor events" if tool_name == "WeatherTool" else "not required"
                logger.info(f"  ○ {tool_name} skipped – {reason}")

    # ------------------------------------------------------------------
    # Running the specialized agents for one planning cycle
    # ------------------------------------------------------------------
    def run_cycle(
        self,
        requirements: Dict[str, Any],
        retry_only: List[str] = None,
        previous_results: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Run one planning cycle. If `retry_only` is provided, only those
        agents are re-run and the rest are carried over from
        `previous_results` (used for the REVISE workflow).
        """
        retry_only = retry_only or []
        previous_results = previous_results or {}
        results = dict(previous_results)  # carry over anything not being retried

        selection = self.select_agents_and_tools(requirements)

        if not retry_only:
            logger.info("Analyzing required tasks...")
            self.log_tool_selection(selection, requirements)
        else:
            logger.info(f"Re-running only affected agent(s): {retry_only}")

        run_venue = (not retry_only) or ("venue_agent" in retry_only)
        run_budget = (not retry_only) or ("budget_agent" in retry_only)
        run_logistics = (not retry_only) or ("logistics_agent" in retry_only)

        # Venue must run before Budget (budget needs venue_cost) and before
        # Logistics (schedule references the venue).
        if run_venue:
            max_venue_budget = requirements.get("budget")
            results["venue"] = self.venue_agent.run(requirements, max_venue_budget=max_venue_budget)

        venue_info = results.get("venue", {})
        selected_venue = venue_info.get("selected_venue")
        venue_cost = selected_venue.get("price", 0) if selected_venue else 0

        if run_budget:
            results["budget"] = self.budget_agent.run(requirements, venue_cost=venue_cost)

        if run_logistics:
            use_weather = "WeatherTool" in selection["tools"]
            results["logistics"] = self.logistics_agent.run(
                requirements, venue=selected_venue, use_weather_tool=use_weather
            )

        # Optional narrative summary from Gemini (best-effort, never blocks the flow).
        try:
            llm = get_llm(temperature=0.3)
            chain = coordinator_prompt | llm
            response = chain.invoke(
                {
                    "requirements": json.dumps(requirements),
                    "selected_agents": ", ".join(selection["agents"]),
                }
            )
            summary = response.content if hasattr(response, "content") else str(response)
            logger.info(f"Coordinator summary: {summary.strip()}")
        except Exception as e:
            logger.debug(f"Coordinator summary skipped ({e}).")

        return results
