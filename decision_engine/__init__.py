"""Typed decision engine: Jev client, confidence routing, and a regex baseline."""

from __future__ import annotations

from decision_engine.client import decide, get_api_key
from decision_engine.router import classify_text, classify_with_confidence

__all__ = [
    "classify_text",
    "classify_with_confidence",
    "decide",
    "get_api_key",
]
__version__ = "1.0.0"
