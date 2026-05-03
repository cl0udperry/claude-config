---
name: multi-model-review
description: Triage-router skill. Haiku classifies the task first; only escalates to Codex, Sonnet, or the full pipeline if the task genuinely needs it. Replaces the default single-model answer for any non-trivial request.
when_to_use: Use for any task where the triage tag is DEEP, or when the user explicitly asks to cross-check, validate, or get a second opinion. Also use when a single-model answer feels insufficient.
argument-hint: "<question or task>"
allowed-tools: Bash
context: fork
---

Run the triage pipeline for: $ARGUMENTS

Step 1 — Classify with Haiku:
```
python "C:\Users\Jordan\OneDrive\Desktop\Projects\multi-agent-pipeline\triage.py"
```
(pass the task via stdin as JSON: `{"prompt": "$ARGUMENTS"}`)

Step 2 — Route based on classification:

| Classification | Action |
|---|---|
| `simple` | Answer directly. No pipeline needed. |
| `code` | Run: `python "C:\Users\Jordan\OneDrive\Desktop\Projects\multi-agent-pipeline\pipeline.py" "$ARGUMENTS"` |
| `complex` | Run: `python "C:\Users\Jordan\OneDrive\Desktop\Projects\multi-agent-pipeline\pipeline.py" --mode validate "$ARGUMENTS"` |
| `deep` | Run full pipeline with `--mode validate`, then cross-check with review-pipeline if code is involved. |

Step 3 — Return:
- **Final answer** (prominent)
- **CHANGES**: what improved from the draft
- **UNRESOLVED**: concerns not addressed (or "None")

Do not blindly accept all reviewer feedback — the merger is instructed to reject vague or incorrect critique.
