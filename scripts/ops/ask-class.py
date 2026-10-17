#!/usr/bin/env python3
"""Classify one user ask and write .raven/state/ask-route.json.

Bug, error, or fix -> andie-jr. Everything else -> andie.
A bare approval (go ahead / approved / GO / proceed) keeps the current class.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROUTE = Path(".raven") / "state" / "ask-route.json"
APPROVAL = {"go ahead", "approved", "go", "proceed"}
FIX_PHRASES = (
    "bug",
    "error",
    "exception",
    "stack trace",
    "traceback",
    "regression",
    "not working",
    "broken",
    "failing",
    "failure",
)


def classify(prompt: str) -> tuple[str, str] | None:
    """Return (class, skill). None means keep the route already on disk."""
    text = (prompt or "").strip().lower()
    if text in APPROVAL:
        return None
    if re.search(r"\bfix\b", text) or any(phrase in text for phrase in FIX_PHRASES):
        return "fix", "andie-jr"
    return "enhance", "andie"


def write_route(prompt: str) -> dict:
    decision = classify(prompt)
    ROUTE.parent.mkdir(parents=True, exist_ok=True)
    if decision is None and ROUTE.is_file():
        try:
            current = json.loads(ROUTE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = {}
        if current.get("skill") in {"andie", "andie-jr"}:
            return current
        decision = ("enhance", "andie")
    if decision is None:
        decision = ("enhance", "andie")
    data = {
        "class": decision[0],
        "skill": decision[1],
        "prompt_preview": (prompt or "")[:120],
    }
    ROUTE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    prompt = ""
    if "--prompt" in args:
        i = args.index("--prompt")
        prompt = args[i + 1] if i + 1 < len(args) else ""
    data = write_route(prompt)
    reviewer = "Andie Jr" if data["skill"] == "andie-jr" else "Andie"
    print(
        f"ASK class={data['class']} skill={data['skill']} — "
        f"{reviewer} validates, then Guided, before any edit"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
