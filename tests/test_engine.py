from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from decision_engine.baseline import classify_regex
from decision_engine.benchmark import load_labeled_set, render_markdown
from decision_engine.client import decide, get_api_key, sanitize_state_text
from decision_engine.presets import FLAG_KEYS
from decision_engine.router import classify_text, classify_with_confidence

ROOT = Path(__file__).resolve().parents[1]
LABELED = ROOT / "data" / "labeled_set.json"
FIXTURE_KEY = "sk-fixture-not-a-real-key"


def _ack_answers(
    *,
    confidence: float,
    choice: str = "acuse_simple",
    flags: dict[str, float] | None = None,
    probabilities: dict[str, float] | None = None,
) -> dict:
    answers = {
        "tipo": {
            "choice": choice,
            "confidence": confidence,
            "probabilities": probabilities
            or {"acuse_simple": confidence, "requiere_decision": 1.0 - confidence},
        }
    }
    for key in FLAG_KEYS:
        answers[key] = {"noul": (flags or {}).get(key, 0.05)}
    return answers


def test_regex_thanks_short_circuits_even_when_salary_is_asked() -> None:
    text = "Thanks for your interest. Could you share your salary expectations?"
    assert classify_regex(text) == "simple_ack"


def test_regex_interview_without_courtesy_words_needs_judgment() -> None:
    assert classify_regex("Please book an interview for Tuesday.") == "needs_judgment"


def test_regex_empty_or_unmatched_text_defaults_to_simple_ack() -> None:
    assert classify_regex("") == "simple_ack"
    assert classify_regex("Agenda para una entrevista la semana que viene.") == "simple_ack"


def test_router_high_confidence_ack_auto_routes() -> None:
    result = classify_with_confidence(_ack_answers(confidence=0.91))
    assert result["classification"] == "simple_ack"
    assert result["route"] == "simple_ack"
    assert result["review"] is False
    assert result["hot_flags"] == []


def test_router_mid_confidence_goes_to_human_review() -> None:
    result = classify_with_confidence(_ack_answers(confidence=0.62))
    assert result["route"] == "review"
    assert result["review"] is True
    assert result["classification"] == "simple_ack"


def test_router_hot_flag_blocks_simple_ack() -> None:
    result = classify_with_confidence(
        _ack_answers(confidence=0.96, flags={"menciona_salario": 0.88})
    )
    assert result["classification"] == "needs_judgment"
    assert result["route"] == "needs_judgment"
    assert "menciona_salario" in result["hot_flags"]


def test_router_malformed_answers_are_safe() -> None:
    result = classify_with_confidence(
        {
            "tipo": ["not", "a", "dict"],
            "pide_info": "hot",
            "propone_entrevista": {"noul": "nope"},
        }
    )
    assert result["choice"] == ""
    assert result["confidence"] == 0.0
    assert result["route"] == "needs_judgment"
    assert result["flags"]["pide_info"] == 0.0
    assert result["flags"]["propone_entrevista"] == 0.0


def test_sanitize_strips_controls_and_truncates() -> None:
    cleaned = sanitize_state_text("hello\x00\x01world\nkeep")
    assert cleaned == "helloworld\nkeep"
    long_text = "x" * 9000
    capped = sanitize_state_text(long_text, max_chars=8000)
    assert len(capped) == 8000
    assert capped.endswith("…")


def test_get_api_key_reads_env_and_errors_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", f"  {FIXTURE_KEY}  ")
    assert get_api_key() == FIXTURE_KEY

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    missing = tmp_path / "missing.env"
    monkeypatch.setattr("decision_engine.client.FALLBACK_ENV_FILE", missing)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        get_api_key()


def test_decide_mocked_http_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", FIXTURE_KEY)
    payload = {
        "model": "typesafe/jev-1.13",
        "answers": {"tipo": {"choice": "acuse_simple", "confidence": 0.9}},
        "usage": {"cost": 0.0001},
    }

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return json.dumps(payload).encode("utf-8")

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: _Resp())
    out = decide({"text": "thanks, received"}, {"tipo": {"type": "choice", "criteria": {"a": "b"}}})
    assert out["answers"]["tipo"]["choice"] == "acuse_simple"
    assert out["usage"]["cost"] == 0.0001


def test_decide_http_error_redacts_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", FIXTURE_KEY)

    def _boom(*args: object, **kwargs: object) -> None:
        raise HTTPError(
            "https://example.invalid/decisions",
            401,
            "Unauthorized",
            None,
            BytesIO(f"invalid key {FIXTURE_KEY}".encode("utf-8")),
        )

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    with pytest.raises(RuntimeError) as exc:
        decide("state", {"q": {"type": "noul", "criteria": {"true": "y", "false": "n"}}})
    message = str(exc.value)
    assert FIXTURE_KEY not in message
    assert "[REDACTED]" in message
    assert "401" in message


def test_decide_retries_then_fails_without_leaking_network_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", FIXTURE_KEY)

    def _offline(*args: object, **kwargs: object) -> None:
        raise URLError("simulated-offline")

    monkeypatch.setattr("urllib.request.urlopen", _offline)
    with pytest.raises(RuntimeError, match="Jev network error: URLError"):
        decide("state", {"q": {"type": "noul", "criteria": {"true": "y", "false": "n"}}})


def test_classify_text_uses_router_on_mocked_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "decision_engine.router.decide",
        lambda *args, **kwargs: {
            "answers": _ack_answers(confidence=0.93),
            "usage": {"cost": 0.0},
            "model": "typesafe/jev-1.13",
        },
    )
    result = classify_text("Thanks, we received the application.")
    assert result["route"] == "simple_ack"
    assert result["classification"] == "simple_ack"
    assert "\x00" not in result["text"]


def test_labeled_set_loads_and_rejects_non_list(tmp_path: Path) -> None:
    cases = load_labeled_set(LABELED)
    assert len(cases) == 16
    assert {row["label"] for row in cases} <= {"simple_ack", "needs_judgment"}

    bad = tmp_path / "labeled.json"
    bad.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON list"):
        load_labeled_set(bad)


def test_render_markdown_includes_accuracy_and_escapes_pipes() -> None:
    report = {
        "n": 2,
        "regex_accuracy": 0.5,
        "jev_accuracy": 1.0,
        "regex_errors": [2],
        "jev_errors": [],
        "jev_cost": 0.001,
        "jev_latency_mean": 0.4,
        "conclusion": "Jev wins on this fixture.",
        "rows": [
            {
                "id": 1,
                "label": "simple_ack",
                "regex": "simple_ack",
                "jev": "simple_ack",
                "confidence": 0.9,
                "route": "simple_ack",
                "hot_flags": [],
                "cost": 0.0005,
                "latency_s": 0.4,
                "text": "thanks | recibido",
            },
            {
                "id": 2,
                "label": "needs_judgment",
                "regex": "simple_ack",
                "jev": "needs_judgment",
                "confidence": 0.88,
                "route": "needs_judgment",
                "hot_flags": ["menciona_salario"],
                "cost": 0.0005,
                "latency_s": 0.4,
                "text": "salary ask",
            },
        ],
    }
    markdown = render_markdown(report)
    assert "50.0%" in markdown
    assert "100.0%" in markdown
    assert "thanks \\| recibido" in markdown
    assert "Jev wins on this fixture." in markdown
