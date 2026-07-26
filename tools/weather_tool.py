"""
Weather Tool.

Thin LangChain tool wrapper around connectors/weather_api.py. This tool
is only ever invoked when the Coordinator determines it is relevant
(e.g. outdoor events) - it is never called automatically for every
request. See agents/coordinator_agent.py for the selection logic.
"""

from langchain_core.tools import tool

from connectors.weather_api import get_current_weather
from utils.logger import get_logger
from utils.validators import is_weather_result_valid

logger = get_logger("tools.weather")


def check_weather(location: str) -> dict:
    """Direct callable used by tests and agents without going through the @tool wrapper."""
    result = get_current_weather(location)
    if not is_weather_result_valid(result) and result.get("status") != "unavailable":
        logger.warning("Weather result failed structural validation; marking unavailable.")
        return {"status": "unavailable", "error": "invalid_structure"}
    return result


@tool("weather_tool")
def weather_tool(location: str) -> dict:
    """
    Retrieve current weather conditions for a location, for outdoor
    event feasibility checks. Returns {"status": "unavailable", ...} if
    the API call fails for any reason - never fabricates data.
    """
    return check_weather(location)
