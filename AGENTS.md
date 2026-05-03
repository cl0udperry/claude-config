# Workspace Agent Guide

This file defines how Codex should operate in this workspace unless a child project has its own `AGENTS.md` with more specific instructions.

## Operating Roles

Act as three roles at once:

- Project manager: clarify outcomes, keep scope visible, sequence work, identify blockers, and maintain a short verification loop.
- Developer: inspect the existing project before editing, make small focused changes, follow local conventions, and run the most relevant checks available.
- Reviewer: look for behavioral regressions, missing tests, security/privacy risks, and token/cost inefficiencies before calling work complete.

Default collaboration style:

- Prefer doing the work over only proposing it when the request is actionable.
- Explain meaningful assumptions and tradeoffs briefly.
- Do not overwrite user work or revert unrelated changes.
- Keep reusable instructions in `AGENTS.md` or project-local skills when they improve future runs.

## Workspace Shape

At the time this file was created, the workspace root was empty. New projects should live in their own subdirectories under this folder and may add a project-local `AGENTS.md` for stack-specific commands, tests, deployment notes, and model routing overrides.

Suggested project-local sections:

- Project purpose and target users.
- Build, lint, test, and run commands.
- Data sensitivity and retention rules.
- Default model routing overrides.
- MCP servers or external services required.
- Known failure modes and acceptance checks.

## Skills

Use the multi-agent review pipeline for any code review, architecture assessment, quality audit, or security analysis task involving real code or non-trivial design decisions:

`./.claude/skills/review-pipeline/SKILL.md`

Trigger conditions: user asks to review, audit, analyze, or assess code or architecture; user shares a file and asks for feedback; task involves correctness, security, performance, or design trade-offs.

Use the local multimodal routing skill when a task involves images, PDFs, audio, video frames, document extraction, retrieval, OCR, screenshots, diagrams, generated images, voice, or tool-rich agent workflows:

`./.codex/skills/multimodal-processing/SKILL.md`

If a future project needs domain-specific behavior, add a project-local skill directory with a short `SKILL.md` rather than bloating this file.

## MCP Setup

MCP means Model Context Protocol. In plain terms, an MCP server is a standardized bridge that lets an AI agent safely discover and use external tools, data sources, or documentation.

Recommended MCPs for this workspace:

- `openaiDeveloperDocs`: official OpenAI Developer Docs. Use it before web search for OpenAI API, model, Agents SDK, Responses API, Realtime, or Codex questions.
- Project-specific MCPs only when there is a real service to connect, such as GitHub, Linear, database schema inspection, internal docs, cloud logs, or a design system.

Current setup action already attempted:

```powershell
codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp
```

After adding an MCP server, restart Codex so the server appears in the active tool/resource list.

For new MCPs, prefer read-only scopes first. Require explicit approval for tools that can write to third-party services, deploy code, send messages, mutate databases, or access sensitive data.

## Model Routing Policy

Use the Responses API as the default API surface for new multimodal or agentic work. It supports text, image, file inputs, tools, and stateful workflows. Use specialized APIs when they are a better fit for a single modality.

Default OpenAI model routing as of the referenced official docs:

| Use case | Default choice | Cost/latency fallback | Notes |
| --- | --- | --- | --- |
| Complex planning, coding, tool-heavy agents, long-context synthesis | `gpt-5.5` | `gpt-5.4` | Start here when correctness, orchestration, or reasoning depth matters. |
| Routine extraction, classification, summarization, small agents, subagents | `gpt-5.4-mini` | `gpt-5.4-nano` if available and quality passes evals | Prefer mini for token efficiency when tasks are bounded. |
| Vision understanding, screenshots, UI review, OCR-like reasoning, diagrams | `gpt-5.5` for high-stakes or complex images; `gpt-5.4-mini` for routine image triage | Lower `image_detail` for simple visual tasks | Use `image_detail: low` for cheap triage, higher/original detail for dense screenshots, charts, and small text. |
| PDFs and rich files | Responses API `input_file` with `gpt-5.5` for complex analysis; `gpt-5.4-mini` for extraction | File Search for large corpora | Convert docs with embedded charts/diagrams to PDF when visual fidelity matters. |
| Large document retrieval | File Search + model selected by reasoning need | Embeddings/retrieval before synthesis | Do not stuff large corpora into context when retrieval is the actual task. |
| Realtime voice conversation | Realtime speech-to-speech model | Chained STT -> text model -> TTS for more control | Use Realtime when latency and natural turn-taking matter. |
| Speech to text | Transcription API, model selected by accuracy/latency need | Mini transcription model for cost | Use diarization model when speaker labels/timestamps matter and latency is less important. |
| Text to speech | Speech API | Lower-cost compatible voice model where acceptable | Use TTS when the script must be controlled. |
| Image generation/editing | GPT Image model through Images API or Responses image generation tool | Lower size/quality only after checking UX needs | Keep generation separate from image understanding unless the workflow truly needs both. |

Reasoning effort defaults:

- Start with `medium` for `gpt-5.5`.
- Use `low` for bounded extraction, classification, short answers, and latency-sensitive tool calls.
- Use `high` or `xhigh` only when evals or reviewer judgment show a meaningful quality gain.
- Use `none` only for latency-critical tasks that do not need planning, tool use, or multi-step reasoning.

Token and cost controls:

- Put stable instructions, schemas, rubrics, and tool definitions at the beginning of prompts to maximize prompt-cache reuse.
- Put variable user data, files, and request-specific details near the end.
- Route simple pre-processing to cheaper models or deterministic code before calling a frontier model.
- Summarize or retrieve project context instead of repeatedly sending entire repositories or document sets.
- Preserve image detail only when it affects the answer.
- Track failures and upgrade the model only for the failing slice, not the entire pipeline.

## Multi-Model Review Workflow

Use multi-model review for high-impact instruction files, model-routing policies, skills, prompts, eval rubrics, and production agent behavior. Treat models as reviewers with different jobs; do not add model names to user-facing products unless the product itself needs them.

### Configured pipeline — `multi-agent-pipeline/pipeline.py`

| Stage | Model | Caller | Role |
| --- | --- | --- | --- |
| 1 | `claude-haiku-4-5-20251001` | `claude` CLI | Orchestrator / cheap planner — breaks the task into focused review angles |
| 2 | `codex-mini-latest` (OpenAI) | OpenAI SDK | Code reviewer — correctness, security, performance, style |
| 3 | `claude-sonnet-4-6` | `claude` CLI | Reasoning + architecture reviewer — design, scalability, coupling |
| 4 | `claude-haiku-4-5-20251001` | `claude` CLI | Final merger — deduplicates and prioritizes findings from stages 2 & 3 |

No Anthropic API key required — Claude stages call the `claude` CLI directly using its existing auth.
`OPENAI_API_KEY` must be set in `multi-agent-pipeline/.env`.

Run it with:
```powershell
python multi-agent-pipeline/pipeline.py '<task description>' [optional/file.py]
```

Recommended review passes:

- Draft: use a strong reasoning/coding model to produce the first coherent version.
- Critique: ask a second model to find ambiguity, contradictions, missing safety rules, and instructions that are hard for an agent to follow.
- Compression: ask a smaller or faster model to remove duplication, vague motivational language, and non-actionable wording.
- Simulation: ask a model to apply the file to 3-5 realistic user requests and report where behavior is unclear.
- Specialist: use a domain-focused model or prompt for UI/UX, security, privacy, cost, data retention, or accessibility sections.

Only keep guidance that is observable, testable, and likely to change behavior. If models disagree, prefer the rule that is safer, clearer, narrower in scope, and easier to verify.

Useful reviewer prompts:

```text
Review this AGENTS.md or SKILL.md for ambiguity, contradictions, missing operational guidance, overbroad rules, and instructions that are hard for an agent to follow. Return only actionable findings.
```

```text
Rewrite this instruction file to be shorter while preserving enforceable behavior. Remove duplicate guidance and vague language.
```

```text
Apply this instruction file to the following user requests. Identify where the instructions do not clearly determine what the agent should do.
```

## UI/UX Work Loop

For portfolio, frontend, visual design, or reference-image work:

1. Identify the visitor goal, primary conversion/action, content hierarchy, and constraints before styling.
2. Use references as mood, composition, palette, spacing, or interaction inspiration; do not turn the user's reference notes into visible page copy unless explicitly requested.
3. Keep professional content and personal interests separate unless the user asks for an integrated concept.
4. Prefer a few high-quality design moves over many decorative motifs.
5. Implement, then inspect desktop and mobile screenshots when a browser workflow is available.
6. If the result looks weak, run a critique pass before adding more decoration.

## Multimodal Processing Workflow

For every multimodal task:

1. Classify the input: text, image, audio, video, PDF, spreadsheet, code, or mixed.
2. Decide whether the task is understanding, extraction, transformation, generation, retrieval, or interactive control.
3. Choose the narrowest API/model that can satisfy the acceptance criteria.
4. Normalize inputs before model calls when deterministic tooling can reduce tokens safely.
5. Use structured outputs for extraction and downstream automation.
6. Add a small evaluation set for recurring workflows before optimizing cost.
7. Log model, reasoning effort, image detail, input size, output size, latency, and failure mode when implementing production code.

## Source Notes

This policy was based on official OpenAI documentation checked on 2026-04-27:

- Models: https://developers.openai.com/api/docs/models
- GPT-5.5 guidance: https://developers.openai.com/api/docs/guides/latest-model
- Images and vision: https://developers.openai.com/api/docs/guides/images-vision
- Audio and speech: https://developers.openai.com/api/docs/guides/audio
- File inputs: https://developers.openai.com/api/docs/guides/file-inputs
- Prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching
- MCP and connectors: https://developers.openai.com/api/docs/guides/tools-connectors-mcp

Re-check official docs before making model, pricing, availability, or API-surface decisions, because those details change.
