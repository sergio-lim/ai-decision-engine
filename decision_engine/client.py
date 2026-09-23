"""Generic Jev (TypeSafe) client over the OpenRouter decisions API.

Reads the API key from the ``OPENROUTER_API_KEY`` environment variable. If that
is missing, it falls back to a local ``.env`` file (see ``.env.example``).
The key is never printed or logged.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = "typesafe/jev-1.13"
FALLBACK_ENV_FILE = Path(os.environ.get("DECISION_ENGINE_ENV", ".env"))


def get_api_key() -> str:
    """Return the OpenRouter key from the environment or the local fallback file.

    Raises:
        RuntimeError: if no key can be found. The message never includes the key.
    """
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if key:
        return key
    if not FALLBACK_ENV_FILE.is_file():
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set and no .env file was found. "
            "Copy .env.example to .env or export OPENROUTER_API_KEY."
        )
    for raw_line in FALLBACK_ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() in ("OPENROUTER_API_KEY", "jev"):
            key = value.strip().strip("\"'")
            if key:
                return key
    raise RuntimeError(
        "OPENROUTER_API_KEY is not set and no jev= entry was found. "
        "Export OPENROUTER_API_KEY before calling the API."
    )


def _redact(text: str, key: str) -> str:
    """Strip the API key from an error string so it cannot leak to logs."""
    if key and key in text:
        return text.replace(key, "[REDACTED]")
    return text


def sanitize_state_text(text: str, *, max_chars: int = 8000) -> str:
    """Drop control characters and cap length before sending untrusted text.

    Jev does not generate prose, but it still *reads* whatever you put in
    ``state``. Treat inbound email/chat as untrusted and sanitize it first.
    """
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    if len(cleaned) > max_chars:
        return cleaned[: max_chars - 1] + "…"
    return cleaned


def decide(
    state: str | dict[str, Any],
    questions: dict[str, Any],
    *,
    model: str = DEFAULT_MODEL,
    timeout: float = 40,
) -> dict[str, Any]:
    """Ask Jev for typed answers to ``questions`` given ``state``.

    Args:
        state: Free-form context (string or JSON-serializable object).
        questions: Map of question name → noul / choice / score spec.
        model: OpenRouter model id. Defaults to ``typesafe/jev-1.13``.
        timeout: Socket timeout in seconds.

    Returns:
        The decoded API payload: ``model``, ``answers``, ``usage``.

    Raises:
        RuntimeError: on HTTP or network failure. API keys are redacted.
    """
    payload = json.dumps(
        {"model": model, "state": state, "questions": questions},
        ensure_ascii=False,
    ).encode("utf-8")
    key = get_api_key()
    last_err_name: str | None = None
    for attempt in range(2):
        request = urllib.request.Request(
            ENDPOINT,
            data=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                status = getattr(response, "status", 200)
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(_redact(f"Jev HTTP {exc.code}: {err_body}", key)) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err_name = type(exc).__name__
            if attempt == 0:
                continue
            raise RuntimeError(f"Jev network error: {last_err_name}") from None
        if status != 200:
            raise RuntimeError(_redact(f"Jev HTTP {status}: {body}", key))
        return json.loads(body)
    raise RuntimeError(f"Jev network error: {last_err_name or 'unknown'}")
