---
name: review-pipeline
description: Multi-model code and architecture review using the 4-stage pipeline (Haiku planner → Codex code reviewer → Sonnet architecture reviewer → Haiku merger). Produces prioritized findings across correctness, security, performance, and design.
when_to_use: Use when the user asks to review code, audit a file, check architecture, assess quality or security, plan a feature, or requests thorough analysis of non-trivial code. Prefer this over a single-model answer whenever a real code file or design decision is involved.
argument-hint: "<task description> [path/to/file]"
allowed-tools: Bash
context: fork
---

Run the multi-agent review pipeline located at `multi-agent-pipeline/pipeline.py`.

Arguments received: $ARGUMENTS

Instructions:
1. Parse `$ARGUMENTS`: everything before a file path is the task description; if a file path is present (anything ending in a file extension like `.py`, `.js`, `.ts`, etc.), treat it as the second argument.
2. Run from the workspace root using the Bash tool:

```
python "C:\Users\Jordan\OneDrive\Desktop\Projects\multi-agent-pipeline\pipeline.py" "<task>" [file_path]
```

3. Stream the output as it arrives (the script prints stage progress).
4. After the script finishes, present the **FINAL REVIEW** section prominently, then offer to show the detailed per-stage breakdowns if the user wants them.

If no file path is given, pass only the task description. If no task is given, ask the user: "What should the pipeline review, and is there a specific file?"
