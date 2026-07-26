
from typing import Any, Dict

from agents import get_llm, parse_json_response, LLMConfigError
from prompts.agent_prompts import requirement_prompt
from utils.logger import get_logger
from utils.validators import validate_requirements

logger = get_logger("agents.requirement")

REQUIRED_KEYS = [
    "event_type", "location", "date", "attendees", "budget",
    "venue_type", "food_preference", "additional_requirements",
]


class RequirementAgent:
    """Agent responsible ONLY for extracting structured requirements."""
    name = "Requirement Agent"

    def run(self, user_request: str) -> Dict[str, Any]:
        logger.info("Extracting structured requirements from user request.")

        llm = get_llm(temperature=0.0)
        chain = requirement_prompt | llm

        response = chain.invoke({"user_request": user_request})
        content = response.content if hasattr(response, "content") else response

        if isinstance(content, list):
            raw_text = "".join(
        block.get("text", "") if isinstance(block, dict) else str(block)
        for block in content
    )
        else:
            raw_text = str(content)

        try:
            data = parse_json_response(raw_text)
        except ValueError as e:
            logger.error(f"Failed to parse requirement JSON: {e}")
            raise

        # Ensure every expected key exists even if the model omitted one.
        for key in REQUIRED_KEYS:
            if key not in data:
                data[key] = [] if key == "additional_requirements" else None

        is_valid, problems = validate_requirements(data)
        data["_valid"] = is_valid
        data["_problems"] = problems

        if is_valid:
            logger.info("Requirements extracted and validated successfully.")
        else:
            logger.warning(f"Requirements incomplete: {problems}")

        return data
