"""Confidence-aware router on top of Jev's typed answers.

``simple_ack`` is auto-applied only when the choice is ``acuse_simple``,
confidence is at or above the threshold, and no noul flag is hot.
A mid-confidence band is sent to a human (``review``) instead of
auto-routing.
"""

from __future__ import annotations

from typing import Any

from decision_engine.client import decide, sanitize_state_text
from decision_engine.presets import FLAG_KEYS, REPLY_CLASSIFY_QUESTIONS

DEFAULT_THRESHOLD = 0.80
DEFAULT_FLAG_THRESHOLD = 0.50
DEFAULT_REVIEW_LOW = 0.50


def _noul_value(answer: Any) -> float:
    if not isinstance(answer, dict):
        return 0.0
    try:
        return float(answer.get("noul", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _choice_fields(tipo: Any) -> tuple[str, float, dict[str, float]]:
    if not isinstance(tipo, dict):
        return "", 0.0, {}
    choice = str(tipo.get("choice") or "")
    try:
        confidence = float(tipo.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    raw_probs = tipo.get("probabilities") or {}
    probabilities: dict[str, float] = {}
    if isinstance(raw_probs, dict):
        for key, value in raw_probs.items():
            try:
                probabilities[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
    return choice, confidence, probabilities


def classify_with_confidence(
    answers: dict[str, Any],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    flag_threshold: float = DEFAULT_FLAG_THRESHOLD,
    review_low: float = DEFAULT_REVIEW_LOW,
) -> dict[str, Any]:
    """Turn typed Jev answers into a route the rest of the code can branch on.

    Routing rule:
      * ``simple_ack`` only if ``tipo.choice == "acuse_simple"`` AND
        ``tipo.confidence >= threshold`` AND no flag exceeds ``flag_threshold``.
      * otherwise ``needs_judgment``.
      * if choice confidence is in ``[review_low, threshold)``, do not
        auto-route — set ``route`` to ``review`` (human in the loop).

    Args:
        answers: ``response["answers"]`` from Jev.
        threshold: Minimum confidence to auto-accept ``acuse_simple``.
        flag_threshold: Noul values above this count as a hot flag.
        review_low: Lower bound of the human-review confidence band.

    Returns:
        A dict with ``classification``, ``route``, ``review``, ``confidence``,
        ``choice``, ``flags``, ``hot_flags``, and ``probabilities``.
    """
    tipo = answers.get("tipo") or {}
    choice, confidence, probabilities = _choice_fields(tipo)
    flags = {key: _noul_value(answers.get(key)) for key in FLAG_KEYS}
    hot_flags = [key for key, value in flags.items() if value > flag_threshold]
    would_be_ack = choice == "acuse_simple" and not hot_flags

    if review_low <= confidence < threshold:
        route = "review"
        classification = "simple_ack" if would_be_ack else "needs_judgment"
        review = True
    elif would_be_ack and confidence >= threshold:
        route = "simple_ack"
        classification = "simple_ack"
        review = False
    else:
        route = "needs_judgment"
        classification = "needs_judgment"
        review = False

    return {
        "classification": classification,
        "route": route,
        "review": review,
        "confidence": confidence,
        "choice": choice,
        "flags": flags,
        "hot_flags": hot_flags,
        "probabilities": probabilities,
    }


def classify_text(
    text: str,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    model: str | None = None,
    timeout: float = 40,
) -> dict[str, Any]:
    """Classify one inbound message with Jev and the confidence router.

    Args:
        text: Raw message body (treated as untrusted).
        threshold: Auto-route threshold for ``simple_ack``.
        model: Optional Jev model override.
        timeout: HTTP timeout in seconds.

    Returns:
        Router result plus ``text``, ``answers``, and ``usage``.
    """
    cleaned = sanitize_state_text(text)
    state = {
        "context": "Inbound recruiter or company reply after a job application.",
        "text": cleaned,
    }
    kwargs: dict[str, Any] = {"timeout": timeout}
    if model:
        kwargs["model"] = model
    raw = decide(state, REPLY_CLASSIFY_QUESTIONS, **kwargs)
    answers = raw.get("answers") or {}
    routed = classify_with_confidence(answers, threshold=threshold)
    routed["text"] = cleaned
    routed["answers"] = answers
    routed["usage"] = raw.get("usage") or {}
    routed["model"] = raw.get("model")
    return routed
