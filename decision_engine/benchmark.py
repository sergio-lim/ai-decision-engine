"""Compare the regex baseline against Jev on a labeled set."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

from decision_engine.baseline import classify_regex
from decision_engine.client import get_api_key
from decision_engine.router import classify_text

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LABELED = ROOT / "data" / "labeled_set.json"
DEFAULT_OUTPUT = ROOT / "results" / "benchmark.md"


def load_labeled_set(path: Path = DEFAULT_LABELED) -> list[dict[str, Any]]:
    """Load the labeled evaluation cases."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"labeled set must be a JSON list: {path}")
    return payload


def _accuracy(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    hits = sum(1 for row in rows if row[key] == row["label"])
    return hits / len(rows)


def _error_ids(rows: list[dict[str, Any]], key: str) -> list[int]:
    return [int(row["id"]) for row in rows if row[key] != row["label"]]


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    """Render the benchmark report as GitHub-flavored markdown."""
    rows: list[dict[str, Any]] = report["rows"]
    lines = [
        "# Benchmark: regex baseline vs Jev",
        "",
        "Same 16 labeled recruiter replies. The baseline is a thanks-first "
        "keyword regex. Jev is a typed decision model with confidence routing.",
        "",
        "## Summary",
        "",
        f"- Cases: **{report['n']}**",
        f"- Regex accuracy: **{report['regex_accuracy']:.1%}** "
        f"(errors: {report['regex_errors'] or 'none'})",
        f"- Jev accuracy: **{report['jev_accuracy']:.1%}** "
        f"(errors: {report['jev_errors'] or 'none'})",
        f"- Jev total cost: **${report['jev_cost']:.6f}**",
        f"- Jev mean latency: **{report['jev_latency_mean']:.2f}s** "
        f"(n={report['n']})",
        "",
        "## Cases",
        "",
        "| id | label | regex | jev | jev conf | route | flags | cost | latency |",
        "|---:|:------|:------|:----|-------:|:------|:------|-----:|--------:|",
    ]
    for row in rows:
        flags = ",".join(row["hot_flags"]) if row["hot_flags"] else "—"
        lines.append(
            "| {id} | {label} | {regex} | {jev} | {conf:.2f} | {route} | {flags} "
            "| ${cost:.6f} | {lat:.2f}s |".format(
                id=row["id"],
                label=row["label"],
                regex=row["regex"],
                jev=row["jev"],
                conf=row["confidence"],
                route=row["route"],
                flags=flags,
                cost=row["cost"],
                lat=row["latency_s"],
            )
        )
    lines.extend(
        [
            "",
            "## Texts",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- **#{row['id']}** `{row['label']}` — {_md_escape(row['text'])}")
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            report["conclusion"],
            "",
        ]
    )
    return "\n".join(lines)


def _conclusion(report: dict[str, Any]) -> str:
    regex_acc = report["regex_accuracy"]
    jev_acc = report["jev_accuracy"]
    delta = jev_acc - regex_acc
    if jev_acc > regex_acc:
        winner = (
            f"Jev beats the regex baseline by {delta:.0%} absolute accuracy "
            f"({jev_acc:.0%} vs {regex_acc:.0%})."
        )
    elif jev_acc == regex_acc:
        winner = (
            f"Both scored {jev_acc:.0%} on this set. The typed API still "
            "gives probabilities and flags the regex cannot."
        )
    else:
        winner = (
            f"Regex scored {regex_acc:.0%} vs Jev {jev_acc:.0%} on this small "
            "set — inspect the error ids before drawing a trend."
        )
    return (
        f"{winner} The baseline short-circuits on courtesy words (`thanks`, "
        "`gracias`, `recibido`), so salary asks, interview invites, and "
        "bounces that start politely get filed as `simple_ack`. Jev returns "
        "a typed choice plus six noul flags; the router only auto-applies "
        f"`simple_ack` when confidence ≥ {0.80:.2f} and no flag is hot. "
        f"Total model cost on {report['n']} calls: ${report['jev_cost']:.6f}."
    )


def run_benchmark(
    labeled_path: Path = DEFAULT_LABELED,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    """Run regex vs Jev on every labeled case and write ``results/benchmark.md``.

    Raises:
        RuntimeError: if no API key is configured.
    """
    get_api_key()
    cases = load_labeled_set(labeled_path)
    rows: list[dict[str, Any]] = []

    for case in cases:
        text = str(case["text"])
        label = str(case["label"])
        case_id = int(case["id"])
        regex_pred = classify_regex(text)

        started = time.perf_counter()
        result = classify_text(text)
        latency = time.perf_counter() - started

        usage = result.get("usage") or {}
        try:
            cost = float(usage.get("cost") or 0.0)
        except (TypeError, ValueError):
            cost = 0.0

        rows.append(
            {
                "id": case_id,
                "text": text,
                "label": label,
                "regex": regex_pred,
                "jev": result["classification"],
                "route": result["route"],
                "confidence": float(result.get("confidence") or 0.0),
                "hot_flags": list(result.get("hot_flags") or []),
                "cost": cost,
                "latency_s": latency,
            }
        )

    latencies = [row["latency_s"] for row in rows]
    report: dict[str, Any] = {
        "n": len(rows),
        "rows": rows,
        "regex_accuracy": _accuracy(rows, "regex"),
        "jev_accuracy": _accuracy(rows, "jev"),
        "regex_errors": _error_ids(rows, "regex"),
        "jev_errors": _error_ids(rows, "jev"),
        "jev_cost": sum(row["cost"] for row in rows),
        "jev_latency_mean": statistics.mean(latencies) if latencies else 0.0,
    }
    report["conclusion"] = _conclusion(report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(report), encoding="utf-8")
    return report


def print_report(report: dict[str, Any]) -> None:
    """Print a compact table to stdout."""
    print(render_markdown(report))
