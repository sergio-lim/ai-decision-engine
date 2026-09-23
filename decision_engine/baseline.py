"""Old-school regex classifier.

Keyword lists and a thanks-first short-circuit. This is the kind of
brittle rule pile that looks fine on the first ten emails and then
silently misroutes the eleventh.

Kept here so the benchmark has something honest to beat.
"""

from __future__ import annotations

import re

# Thanks-like language is treated as "nothing to do" — the classic trap
# when a rejection or a salary question also starts with "Thanks".
_ACK_RE = re.compile(
    r"\b(thanks|thank you|gracias|recibido|appreciate|pass this along|"
    r"share (your|this) profile)\b",
    re.IGNORECASE,
)

# English-heavy keywords. Spanish "entrevista" / "salarial" are easy to forget
# when the first version of the regex was written against English mail.
_JUDGMENT_RE = re.compile(
    r"\b(salary|interview|sponsorship|visa|assessment|references|"
    r"start date|not moving forward|rejected|rejection)\b",
    re.IGNORECASE,
)

Label = str


def classify_regex(text: str) -> Label:
    """Classify ``text`` with brittle keyword rules.

    Order is the bug: an acknowledgment match wins even when the same
    message also asks for salary or work authorization.

    Args:
        text: Inbound message body.

    Returns:
        ``simple_ack`` or ``needs_judgment``.
    """
    body = text or ""
    if _ACK_RE.search(body):
        return "simple_ack"
    if _JUDGMENT_RE.search(body):
        return "needs_judgment"
    return "simple_ack"
