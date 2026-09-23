#!/usr/bin/env python3
"""CLI for the typed decision engine.

Examples:
    python3 main.py --classify "Hola, recibido. Cualquier novedad te aviso."
    python3 main.py --benchmark
    python3 main.py --demo
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from decision_engine.baseline import classify_regex
from decision_engine.benchmark import print_report, run_benchmark
from decision_engine.client import get_api_key
from decision_engine.router import classify_text

ROOT = Path(__file__).resolve().parent


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_classify(text: str) -> int:
    result = classify_text(text)
    _print_json(
        {
            "classification": result["classification"],
            "route": result["route"],
            "review": result["review"],
            "confidence": result["confidence"],
            "choice": result["choice"],
            "probabilities": result["probabilities"],
            "flags": result["flags"],
            "hot_flags": result["hot_flags"],
            "usage": result["usage"],
        }
    )
    return 0


def cmd_benchmark() -> int:
    report = run_benchmark()
    print_report(report)
    print(f"\nWrote {ROOT / 'results' / 'benchmark.md'}", file=sys.stderr)
    return 0


def cmd_demo() -> int:
    samples = [
        "Hola Sergio, recibido! Cualquier novedad te aviso.",
        "Could you share your salary expectations?",
        "Hola Sergio, te comparto mi agenda para agendar una entrevista.",
    ]
    print("AI Decision Engine — regex vs typed decisions")
    print("=" * 64)
    for index, text in enumerate(samples, start=1):
        regex = classify_regex(text)
        jev = classify_text(text)
        print(f"\n[{index}] {text}")
        print(f"    regex : {regex}")
        print(
            "    jev   : {cls}  conf={conf:.2f}  route={route}  flags={flags}".format(
                cls=jev["classification"],
                conf=jev["confidence"],
                route=jev["route"],
                flags=",".join(jev["hot_flags"]) or "—",
            )
        )
        if regex != jev["classification"]:
            print("    note  : regex and Jev disagree — this is the fragile case.")
    print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replace fragile regex routing with typed Jev decisions.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--classify", metavar="TEXT", help="Classify one inbound message.")
    group.add_argument(
        "--benchmark",
        action="store_true",
        help="Run regex vs Jev on data/labeled_set.json.",
    )
    group.add_argument(
        "--demo",
        action="store_true",
        help="Classify a few canned examples side by side.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        get_api_key()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        if args.classify is not None:
            return cmd_classify(args.classify)
        if args.benchmark:
            return cmd_benchmark()
        return cmd_demo()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
