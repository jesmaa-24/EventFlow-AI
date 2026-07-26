"""
Centralized logging configuration for EventFlow AI.

All agents and tools import `get_logger(name)` from this module so that
every log line is consistently formatted and API keys are never printed.
"""

import logging
import sys

_CONFIGURED = False


def _configure_root_logger() -> None:
    """Configure the root logger exactly once."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger("eventflow")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.propagate = False

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger, e.g. get_logger('agents.budget')."""
    _configure_root_logger()
    return logging.getLogger(f"eventflow.{name}")


def mask_secret(value: str, keep: int = 4) -> str:
    """Utility to safely display a secret (e.g. API key) in logs if ever needed."""
    if not value:
        return "<empty>"
    if len(value) <= keep:
        return "*" * len(value)
    return f"{'*' * (len(value) - keep)}{value[-keep:]}"
