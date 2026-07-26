
import os

import requests

from utils.logger import get_logger

logger = get_logger("connectors.weather")

DEFAULT_TIMEOUT_SECONDS = 5


def get_current_weather(location: str) -> dict:
    """
    Fetch current weather for `location` from OpenWeatherMap.

    Returns a structured dict:
      {"status": "ok", "temperature_c": ..., "condition": ..., "rain_expected": bool}
    or on any failure:
      {"status": "unavailable", "error": "<reason>"}
    """
    api_key = os.getenv("WEATHER_API_KEY")
    base_url = os.getenv(
        "WEATHER_API_BASE_URL", "https://api.openweathermap.org/data/2.5/weather"
    )
    timeout = float(os.getenv("WEATHER_API_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))

    if not api_key or api_key.strip() == "" or api_key == "your_openweathermap_api_key_here":
        logger.warning("WEATHER_API_KEY missing - skipping live weather lookup.")
        return {"status": "unavailable", "error": "missing_api_key"}

    if not location:
        logger.warning("No location provided for weather lookup.")
        return {"status": "unavailable", "error": "missing_location"}

    params = {"q": location, "appid": api_key, "units": "metric"}

    try:
        response = requests.get(base_url, params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        logger.error(f"Weather API request timed out after {timeout}s.")
        return {"status": "unavailable", "error": "timeout"}
    except requests.exceptions.ConnectionError:
        logger.error("Weather API network/connection error.")
        return {"status": "unavailable", "error": "network_error"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Weather API request failed: {e}")
        return {"status": "unavailable", "error": "request_exception"}

    if response.status_code != 200:
        logger.error(f"Weather API returned HTTP {response.status_code}.")
        return {"status": "unavailable", "error": f"http_{response.status_code}"}

    try:
        payload = response.json()
        temperature_c = payload["main"]["temp"]
        condition = payload["weather"][0]["main"]
        rain_expected = condition.lower() in ("rain", "thunderstorm", "drizzle")
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Weather API response was malformed: {e}")
        return {"status": "unavailable", "error": "malformed_response"}

    logger.info(f"Weather fetched for '{location}': {condition}, {temperature_c}°C")
    return {
        "status": "ok",
        "temperature_c": temperature_c,
        "condition": condition,
        "rain_expected": rain_expected,
    }
