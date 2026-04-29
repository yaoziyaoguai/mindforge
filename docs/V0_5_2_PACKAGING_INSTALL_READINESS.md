# MindForge v0.5.2 Design — Packaging / Install Readiness

## Problem

The v0.5.1 local usability path works from a development checkout because the
CLI can find these repo-root assets:

- `prompts/<stage>/v1.md`
- `templates/knowledge_card.md.j2`
- `configs/learning_tracks.yaml`
- `configs/mindforge.yaml` and `configs/llm.example.yaml` for `mindforge init`

That is not enough for packaged install. A wheel installs the `mindforge`
package, not the repository root. If runtime defaults keep using
`Path("prompts")`, `Path("templates/...")`, or `repo_root / "configs"`, the CLI
can fail as soon as the user runs it from a vault directory, `/tmp`, or any
location that is not the source checkout.

## Why Development Checkout Success Is Not Enough

Editable installs hide packaging bugs because the repository is still present on
disk. A packaged install should treat prompt files, templates, and default
configs as package resources, not as loose files next to the current working
directory.

## Runtime Assets Required By Defaults

- Prompt files for the five-stage pipeline:
  `triage`, `distill`, `link_suggestion`, `review_questions`,
  `action_extraction`.
- Prompt manifests kept beside the prompt files for schema/version context.
- Knowledge Card template: `knowledge_card.md.j2`.
- Default `learning_tracks.yaml` used by `process`.
- Default `mindforge.yaml`, `learning_tracks.yaml`, and `llm.example.yaml` used
  by `mindforge init`.

## Resource Loading Strategy

Use `importlib.resources` for bundled defaults:

- user-supplied paths always win;
- if the user omits `--prompts-dir`, `--tracks`, or `--template`, resolve the
  bundled package asset;
- if `mindforge init` needs default configs, copy them from package resources;
- keep any extracted temporary resources alive for the duration of the command.

This keeps packaged install independent of repo root and current working
directory while preserving explicit user overrides.

## Non-Goals

- No RAG / embedding.
- No Obsidian plugin.
- No live LLM calls.
- No real private vault processing.
- No SourceAdapter / SourceDocument / processor / approval / recall architecture
  changes.
- No new heavy dependencies.

## Acceptance

- `process --profile fake` works from a non-repo current directory.
- `commands` and `next` do not depend on repo-root assets.
- Explicit `--prompts-dir`, `--tracks`, and `--template` remain honored.
- Package assets are covered by tests using `importlib.resources`.

## Implementation Notes

- Bundled assets live under `src/mindforge/assets/`.
- `process` uses package resources when asset options are omitted.
- `mindforge init` copies default configs from package resources.
- `CardWriter` can render from either a user template path or bundled template
  text.
- `prompts_runtime.load_prompt` accepts both `Path` and importlib Traversable
  objects.
- Relative `state.workdir` is resolved from current working directory to avoid
  treating copied config locations as fake repository roots.

## Quality Gate

- `ruff check .` clean.
- `pytest` passes: **365 passed, 2 skipped**.
- Repo-root smoke passed with a copied demo vault in `/tmp`:
  `doctor`, `next`, `scan`, `commands`, and `process --profile fake --limit 1`.
- Non-repo cwd smoke passed from `/tmp` with an explicit config path and a
  copied demo vault: `commands`, `doctor`, `next`, `scan`, and
  `process --profile fake --limit 1`.
- Smoke used only fake provider and fictional demo fixtures; it did not read
  `.env`, call a real LLM, process a real private vault, or modify real
  Obsidian notes.
