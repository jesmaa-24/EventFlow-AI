import json
import os
import re

from langchain_google_genai import ChatGoogleGenerativeAI

from utils.logger import get_logger

logger = get_logger("agents.llm_client")

_llm_instance = None


class LLMConfigError(Exception):
    """Raised when the Gemini client cannot be constructed (e.g. missing key)."""


def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """
    Build (and cache) a single ChatGoogleGenerativeAI client for the whole
    process. Raises LLMConfigError with a clear message if GEMINI_API_KEY
    is missing, instead of letting a cryptic exception bubble up later.
    """
    global _llm_instance

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or api_key == "your_gemini_api_key_here":
        raise LLMConfigError(
            "GEMINI_API_KEY is missing or not set. Copy .env.example to .env "
            "and add a valid Gemini API key from https://aistudio.google.com/app/apikey"
        )

    if _llm_instance is None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        _llm_instance = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
        )
        logger.info(f"Gemini client initialized (model={model_name})")

    return _llm_instance


def parse_json_response(raw_text: str) -> dict:
    """
    Gemini sometimes wraps JSON in ```json ... ``` fences or adds stray
    whitespace. This strips that safely and parses the JSON, raising a
    clear error on malformed output instead of crashing the whole run.
    """
    if raw_text is None:
        raise ValueError("Empty response from Gemini.")

    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned.strip(), flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned.strip()).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON from Gemini: {e}\nRaw output: {raw_text[:500]}")