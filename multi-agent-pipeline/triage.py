#!/usr/bin/env python3
"""
UserPromptSubmit hook — classifies every incoming message via Haiku
and outputs a routing instruction Claude Code follows.

Classification tiers:
  simple  — factual questions, short explanations, quick lookups
  code    — code review, debugging, writing/fixing code
  complex — architecture, design, multi-step reasoning, trade-offs
  deep    — cross-checking, high-stakes decisions, multi-model needed
"""

import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

HAIKU = "claude-haiku-4-5-20251001"

ROUTING = {
    "simple":  "Answer directly and concisely. No heavy reasoning or long output.",
    "code":    "Focus on the code. Use the review-pipeline skill if reviewing a file; otherwise solve efficiently.",
    "complex": "Use structured reasoning. Be thorough but avoid padding and repetition.",
    "deep":    "Route through the multi-model pipeline (review-pipeline or multi-model-review skill).",
}

VALID = set(ROUTING.keys())


def classify(prompt: str) -> str:
    classify_prompt = f"""Classify this task with ONE word: simple, code, complex, or deep.

simple  = factual question, short explanation, quick lookup, chit-chat
code    = write/fix/review code, debug, implement a feature
complex = architecture decision, design trade-off, multi-step reasoning
deep    = cross-check correctness, high-stakes answer, needs multiple expert views

Task (first 600 chars):
{prompt[:600]}

Reply with ONLY the one classification word."""

    result = subprocess.run(
        ["claude", "-p", classify_prompt, "--model", HAIKU],
        capture_output=True,
        text=True,
    )
    word = result.stdout.strip().lower().split()[0] if result.stdout.strip() else ""
    return word if word in VALID else "complex"


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)  # Malformed input — don't block

    prompt = data.get("prompt", "").strip()
    if not prompt:
        sys.exit(0)

    tier = classify(prompt)

    log_path = Path(__file__).parent / "triage_log.csv"
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["timestamp", "tier", "prompt_preview"])
        w.writerow([datetime.now(timezone.utc).isoformat(), tier, prompt[:80]])

    print(f"[TRIAGE:{tier.upper()}] {ROUTING[tier]}", flush=True)


if __name__ == "__main__":
    main()
