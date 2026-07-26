"""
Logistics / Event Planning Agent.

Generates a schedule and logistics recommendations. Uses WeatherTool
ONLY when the Coordinator flags weather as relevant (typically outdoor
events) - see agents/coordinator_agent.py's tool-selection logic.
"""

import json
from typing import Any, Dict, Optional

from agents import get_llm, parse_json_response
from prompts.agent_prompts import logistics_prompt
from tools.weather_tool import check_weather
from utils.logger import get_logger

logger = get_logger("agents.logistics")


class LogisticsAgent:
    """Agent responsible for schedule/logistics generation and optional weather checks."""
    name = "Logistics Agent"

    def run(
        self,
        requirements: Dict[str, Any],
        venue: Optional[Dict[str, Any]],
        use_weather_tool: bool,
    ) -> Dict[str, Any]:
        logger.info("Generating event logistics...")

        weather_result = {"status": "not_applicable"}
        if use_weather_tool:
            logger.info("Invoking WeatherTool...")
            weather_result = check_weather(requirements.get("location"))
            if weather_result.get("status") == "ok":
                logger.info("✓ Weather information retrieved")
            else:
                logger.warning(
                    f"WARNING: Weather API unavailable "
                    f"({weather_result.get('error', 'unknown')})."
                )
        else:
            logger.info("○ WeatherTool skipped – not required for this event type.")

        if weather_result.get("status") == "ok":
            weather_summary = (
                f"{weather_result['condition']}, {weather_result['temperature_c']}°C, "
                f"rain expected: {weather_result['rain_expected']}"
            )
        elif use_weather_tool:
            weather_summary = "unavailable (API call failed)"
        else:
            weather_summary = "not applicable (indoor event)"

        schedule = [
            "9:00 AM - Registration & Check-in",
            "9:30 AM - Opening Ceremony",
            "10:00 AM - Main Event Sessions",
            "1:00 PM - Lunch Break",
            "2:00 PM - Afternoon Sessions",
            "5:00 PM - Closing & Vote of Thanks",
        ]
        recommendations = []

        try:
            llm = get_llm(temperature=0.4)
            chain = logistics_prompt | llm
            response = chain.invoke(
                {
                    "requirements": json.dumps(requirements),
                    "venue": json.dumps(venue) if venue else "none selected",
                    "weather_summary": weather_summary,
                }
            )
            content = response.content if hasattr(response, "content") else response

            if isinstance(content, list):
                raw_text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
    )
            else:
                raw_text = str(content)

            parsed = parse_json_response(raw_text)
            schedule = parsed.get("schedule", schedule)
            recommendations = parsed.get("recommendations", recommendations)
        except Exception as e:
            logger.warning(f"Falling back to default schedule template ({e}).")

        return {
            "status": "ok",
            "schedule": schedule,
            "recommendations": recommendations,
            "weather": weather_result,
        }
