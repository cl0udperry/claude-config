---
name: review-pipeline
description: Multi-model code and architecture review using the triage-routed pipeline (SIMPLE→Haiku only, CODE→Codex/Opus/Sonnet, COMPLEX→Sonnet+validation, DEEP→both). Produces prioritized findings with token cost summary. UI tasks auto-run Playwright validation.
when_to_use: Use when the user asks to review code, audit a file, check architecture, assess quality or security, plan a feature, or requests thorough analysis of non-trivial code. Prefer this over a single-model answer whenever a real code file or design decision is involved.
argument-hint: "<task description> [path/to/file] [--url https://...]"
allowed-tools: Bash
context: fork
---

Run the multi-agent review pipeline located at `multi-agent-pipeline/pipeline.py`.

Arguments received: $ARGUMENTS

## Routing tiers

| Tier    | When                                             | Models                                         |
|---------|--------------------------------------------------|------------------------------------------------|
| SIMPLE  | Factual lookup, arithmetic, quick one-liner      | Haiku only (speed-first, no pipeline overhead) |
| CODE    | Correctness, security, style, performance        | Haiku → Codex → Opus → Sonnet → Haiku         |
| COMPLEX | Architecture, design, UI work, multi-step plans  | Haiku → Sonnet + validation loop → Haiku       |
| DEEP    | Both code AND architecture concerns              | Haiku → Codex/Opus/Sonnet + validation → Haiku |

Code-stage fallback chain (in order): **Codex → Opus → Ollama → Sonnet**

## Instructions

1. Parse `$ARGUMENTS`: the task description comes first; a file path (ending in an extension like `.py`, `.js`, `.ts`, `.html`, `.css`) is the second argument; `--url <url>` triggers Playwright validation after changes.
2. Run from the workspace root using the Bash tool:

```bash
python multi-agent-pipeline/pipeline.py '<task>' [file_path] [--url https://...]
```

3. Print stage output as it arrives — the script logs each stage header.
4. After the script finishes, present the **merged findings** section prominently, then offer per-stage breakdowns on request.
5. The final status line always appears — confirm it printed:

```
▸ Pipeline: haiku-4-5 → sonnet-4-6 → haiku-4-5 | 4,821 tokens | $0.0312 (saved 61% vs all-Sonnet | ✓ validated)
```

## Validation

Any task mentioning HTML, CSS, portfolio, page, layout, colour, animation, or frontend automatically runs a Playwright smoke-test (checks JS errors, hidden `.reveal` elements, h2 count) when `--url` is passed, and marks the result `✓ validated` or `WARN`.

## Acceptance checks

Before calling a task complete:
1. Status line printed ✓
2. Tier matches the task type (SIMPLE tasks must not hit Sonnet)
3. Playwright result is `OK` for any UI change with `--url`
4. Merged output contains at least one Critical or High finding, or explicitly states none were found

If no file path is given, pass only the task description. If no task is given, ask the user: "What should the pipeline review, and is there a specific file?"
