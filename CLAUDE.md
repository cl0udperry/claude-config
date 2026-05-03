# Workspace Rules

## Token-Efficient Routing

Every message is pre-classified by a Haiku triage hook. You will see a `[TRIAGE:TIER]` line before the user's message. **Always follow it.**

| Triage tag | What to do |
|---|---|
| `[TRIAGE:SIMPLE]` | Answer in 1–3 sentences. No preamble, no summary, no headers. |
| `[TRIAGE:CODE]` | Focus purely on the code problem. Use the `review-pipeline` skill if a file is involved. Skip architecture discussion unless asked. |
| `[TRIAGE:COMPLEX]` | Reason carefully. Use headers if the answer has multiple parts. Cut filler — every sentence must add information. |
| `[TRIAGE:DEEP]` | Invoke the `review-pipeline` or `multi-model-review` skill. Do not answer from a single model pass alone. |

### Hard rules
- Never add trailing summaries ("In summary…", "Hope that helps", etc.).
- Never restate the question back to the user.
- For SIMPLE tasks: if the answer fits in one sentence, use one sentence.
- For DEEP tasks: always surface the multi-model pipeline rather than answering inline.
- If no triage tag appears, default to COMPLEX behavior.

## Projects

Each project lives in its own subdirectory and may have a local `AGENTS.md` or `CLAUDE.md` that overrides these rules for that project only.
