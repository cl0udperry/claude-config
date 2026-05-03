#!/usr/bin/env python3
"""
Multi-agent pipeline — two modes:

  review   (default)
    Stage 1: Haiku   — orchestrator / cheap planner
    Stage 2: Codex   — code reviewer
    Stage 3: Sonnet  — reasoning + architecture reviewer
    Stage 4: Haiku   — final merger → prioritized findings

  validate
    Stage 1: Haiku   — drafts initial answer
    Stage 2: Codex   — critiques code / implementation details
    Stage 3: Sonnet  — critiques reasoning / architecture
    Stage 4: Haiku   — merges → final answer + change summary + unresolved concerns

Requires:
  - claude CLI authenticated (no Anthropic API key needed)
  - OPENAI_API_KEY in multi-agent-pipeline/.env
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv
import openai

# Load .env from this file's directory
load_dotenv(Path(__file__).parent / ".env")

HAIKU  = "claude-haiku-4-5-20251001"
CODEX  = "codex-mini-latest"
SONNET = "claude-sonnet-4-6"

_openai = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ── model wrappers ────────────────────────────────────────────────────────────

def _claude(model: str, prompt: str) -> str:
    """Call claude CLI in non-interactive mode."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", model],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error:\n{result.stderr.strip()}")
    return result.stdout.strip()


def _codex(prompt: str) -> str:
    r = _openai.chat.completions.create(
        model=CODEX,
        reasoning_effort="medium",
        messages=[{"role": "user", "content": prompt}],
    )
    return r.choices[0].message.content


# ── pipeline stages ───────────────────────────────────────────────────────────

def stage_plan(context: str) -> str:
    prompt = textwrap.dedent(f"""\
        You are a planning orchestrator. Given a task and optional code, output a
        JSON object with exactly three keys:
          "code_review_focus"   — bullet list of what the code reviewer should check,
          "architecture_focus"  — bullet list of what the architecture reviewer should assess,
          "merge_guidance"      — how the merger should weight and combine both reviews.
        Be brief and actionable. Output valid JSON only, no markdown fences.

        {context}""")
    return _claude(HAIKU, prompt)


def stage_code_review(plan: str, context: str) -> str:
    prompt = textwrap.dedent(f"""\
        You are a code reviewer. The planning agent identified these focus areas:
        {plan}

        Review the code for correctness, security, performance, and style.
        Return structured findings, each with a severity label:
          CRITICAL | MAJOR | MINOR | NIT

        {context}""")
    return _codex(prompt)


def stage_arch_review(plan: str, context: str) -> str:
    prompt = textwrap.dedent(f"""\
        You are an architecture and reasoning reviewer. The planning agent identified these focus areas:
        {plan}

        Assess design decisions, scalability, coupling, testability, and conceptual correctness.
        Return structured findings grouped by concern area.

        {context}""")
    return _claude(SONNET, prompt)


def stage_merge(plan: str, code_review: str, arch_review: str) -> str:
    prompt = textwrap.dedent(f"""\
        You are a final reviewer synthesizing two specialist reports into one prioritized action list.
        Rules:
        - Merge duplicates; keep the more actionable wording.
        - Group output as: CRITICAL → MAJOR → MINOR → NIT.
        - If an item appears in both reviews, note that (adds weight).
        - End with a one-sentence overall verdict.

        Orchestration plan:
        {plan}

        Code review (Codex):
        {code_review}

        Architecture review (Sonnet):
        {arch_review}""")
    return _claude(HAIKU, prompt)


# ── validate mode stages ──────────────────────────────────────────────────────

def vstage_draft(question: str) -> str:
    prompt = textwrap.dedent(f"""\
        You are a knowledgeable assistant. Draft a clear, complete answer to the question below.
        Be thorough but concise. If the answer involves code, include it.

        Question: {question}""")
    return _claude(HAIKU, prompt)


def vstage_code_critique(question: str, draft: str) -> str:
    prompt = textwrap.dedent(f"""\
        You are a code and implementation reviewer. You will receive a question and a draft answer.
        Your job: find flaws in the code or implementation details only.
        - Do NOT rewrite the entire answer.
        - Flag specific errors, edge cases, security issues, or inefficiencies.
        - If the answer has no code or implementation details, say "No code to review."
        - Be direct. List findings as: [WRONG] / [MISSING] / [RISKY] / [IMPROVE]

        Question: {question}

        Draft answer:
        {draft}""")
    return _codex(prompt)


def vstage_reasoning_critique(question: str, draft: str) -> str:
    prompt = textwrap.dedent(f"""\
        You are a reasoning and architecture reviewer. You will receive a question and a draft answer.
        Your job: find flaws in the logic, reasoning, or architectural decisions only.
        - Do NOT rewrite the entire answer.
        - Flag incorrect assumptions, missing trade-offs, weak reasoning, or better approaches.
        - Be direct. List findings as: [WRONG] / [MISSING] / [WEAK] / [BETTER]

        Question: {question}

        Draft answer:
        {draft}""")
    return _claude(SONNET, prompt)


def vstage_merge(question: str, draft: str, code_critique: str, reasoning_critique: str) -> str:
    prompt = textwrap.dedent(f"""\
        You are the final merger. You have a draft answer and two critiques.
        Your rules:
        - Accept only critique points that are clearly correct. Reject vague or wrong feedback.
        - Produce the improved final answer.
        - After the answer, add two short sections:
            CHANGES: bullet list of what you changed from the draft and why.
            UNRESOLVED: bullet list of any concerns you chose NOT to fix and why (or "None").

        Question: {question}

        Draft:
        {draft}

        Code critique (Codex):
        {code_critique}

        Reasoning critique (Sonnet):
        {reasoning_critique}""")
    return _claude(HAIKU, prompt)


# ── public entry points ───────────────────────────────────────────────────────

def run(task: str, code: str = "") -> dict:
    context = f"Task:\n{task}"
    if code:
        context += f"\n\nCode:\n```\n{code}\n```"

    print("[1/4] Haiku  — planning...")
    plan = stage_plan(context)

    try:
        json.loads(plan)
    except json.JSONDecodeError:
        pass  # Non-fatal; pass raw text forward

    print("[2/4] Codex  — code review...")
    code_review = stage_code_review(plan, context)

    print("[3/4] Sonnet — architecture review...")
    arch_review = stage_arch_review(plan, context)

    print("[4/4] Haiku  — merging...")
    final = stage_merge(plan, code_review, arch_review)

    return {
        "plan":        plan,
        "code_review": code_review,
        "arch_review": arch_review,
        "final":       final,
    }


def run_validate(question: str) -> dict:
    print("[1/4] Haiku  — drafting answer...")
    draft = vstage_draft(question)

    print("[2/4] Codex  — critiquing code/implementation...")
    code_critique = vstage_code_critique(question, draft)

    print("[3/4] Sonnet — critiquing reasoning/architecture...")
    reasoning_critique = vstage_reasoning_critique(question, draft)

    print("[4/4] Haiku  — merging...")
    final = vstage_merge(question, draft, code_critique, reasoning_critique)

    return {
        "draft":              draft,
        "code_critique":      code_critique,
        "reasoning_critique": reasoning_critique,
        "final":              final,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _divider(label: str):
    print(f"\n{'─' * 60}\n  {label}\n{'─' * 60}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Multi-agent pipeline")
    parser.add_argument("task", help="Task description or question")
    parser.add_argument("file", nargs="?", help="Optional file to review (review mode only)")
    parser.add_argument(
        "--mode",
        choices=["review", "validate"],
        default="review",
        help="review = code/architecture findings  |  validate = cross-check an answer",
    )
    args = parser.parse_args()

    if args.mode == "validate":
        result = run_validate(args.task)

        _divider("FINAL ANSWER  (Haiku merger)")
        print(result["final"])

        _divider("Draft  (Haiku)")
        print(result["draft"])

        _divider("Code Critique  (Codex)")
        print(result["code_critique"])

        _divider("Reasoning Critique  (Sonnet)")
        print(result["reasoning_critique"])

    else:
        code = ""
        if args.file:
            with open(args.file, encoding="utf-8") as fh:
                code = fh.read()

        result = run(args.task, code)

        _divider("FINAL REVIEW  (Haiku merger)")
        print(result["final"])

        _divider("Orchestration Plan  (Haiku planner)")
        print(result["plan"])

        _divider("Code Review  (Codex)")
        print(result["code_review"])

        _divider("Architecture Review  (Sonnet)")
        print(result["arch_review"])
