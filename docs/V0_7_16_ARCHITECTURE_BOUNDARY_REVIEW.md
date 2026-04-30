# v0.7.16 Architecture Boundary Review

## Goal

This release is not about reducing `cli.py` line count. Line count is a symptom; the goal is higher cohesion, lower coupling, clearer dependency direction, and easier direct testing.

## Boundary Audit

- `recall_service.py`: healthy. It owns BM25/hybrid recall, ranking, filtering, explain data, and safe result shaping. It has service-level tests. Risk: a few user-facing next-action strings remain here; acceptable for now because they are recall-domain recovery guidance.
- `recall_presenter.py`: healthy. It renders structured recall results to JSON/Markdown/Rich formats and does not rank or filter. It has presenter-level tests. Risk: future presenters should not all be dumped into one giant file.
- `obsidian_stage.py`: mostly healthy. It owns staged export, manifest, staged diff, and preflight display plan. Risk: it still re-exports workflow helpers for compatibility; this should stay temporary.
- `obsidian.py`: healthy but broad. It owns scan/link/stage/preflight domain logic. Risk: preflight is still inside this broad module rather than a dedicated `obsidian_preflight.py`.
- `obsidian_workflow.py`: healthy. It owns `obsidian next` / dogfooding next-action plan and has no Typer/Rich dependency.
- `app_context.py`: healthy. It owns config loading, vault override, and path snapshot. It does not load `.env`; CLI keeps that decision.
- `cli.py`: still broad. It keeps Typer commands, orchestration, many presenters, and some safety wording. The direction is improving, but CLI remains the main monolith.

## Safety Policy Decision

Safety boundaries repeat across recall, Obsidian workflow, staged manifest, and preflight. They share one domain meaning: local-first safe-by-default operating boundaries. This is cohesive enough for a small `safety_policy.py`.

Created `src/mindforge/safety_policy.py` with:

- structured local safety boundaries;
- Obsidian manifest safety flags;
- reusable recall/workflow boundary lines;
- forbidden machine-derived path part detection.

It intentionally does not render output, parse config, read `.env`, call LLMs, write files, or mutate approval/review/Obsidian state.

## Still Needs Work

- `obsidian_preflight` can become a dedicated service module later.
- CLI presentation outside recall is still mixed into `cli.py`.
- approve/review command orchestration still deserves service extraction.
- safety policy should stay narrow; do not turn it into a generic text bucket.

## Next Candidates

- v0.7.17 approval/review service extraction.
- v0.7.17 obsidian CLI handler extraction.
- v0.8 Real LLM Opt-in after architecture boundaries are stable.
