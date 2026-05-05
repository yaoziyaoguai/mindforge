# MindForge

MindForge is a local-first personal AI learning memory workbench. It helps one
person turn local sources into reviewable `ai_draft` cards, explicitly approve
useful cards into `human_approved` memory, and search that approved knowledge
locally from CLI or Web.

Current state: MindForge has a real-data CLI usability path and a first local
Web console slice. It is ready for careful real dogfood on non-sensitive local
data. It is not a SaaS product, not a multi-user admin system, not a RAG stack,
and not an Obsidian plugin.

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'

mindforge demo            # no API key, no network, no real provider
mindforge status
mindforge config status
mindforge workspace status
mindforge web --open
```

For the first real-data run, use a disposable or non-sensitive project vault and
start with read-only/status commands before any write-capable action.

## Strategy Discovery

```bash
mindforge strategies list
```

Built-in strategies include `default_knowledge_card` and `five_stage`.
Strategy status has three meanings: `implemented` is ready to run, `preview` is
usable but still evolving, and `planned` is registered for visibility but is not
executed.

## Core Safety Rules

- Local-first by default: CLI and Web read local files and bind Web to
  `127.0.0.1` unless explicitly changed.
- Fake provider is the safe default. Real LLM providers are opt-in and readiness
  checks must not call the provider.
- `.env` handling is presence-only in user output. Secret values must never be
  printed, logged, snapshotted, or committed.
- AI can only create `ai_draft`. `human_approved` requires an explicit human
  approve action.
- Approval writes must show the target and require confirmation.
- Recall is local lexical search over approved cards. It is not RAG, embedding,
  or semantic search.
- MindForge does not automatically organize a real Obsidian vault.

## Canonical Docs

- [Architecture](docs/ARCHITECTURE.md) - product shape, data flow, boundaries,
  and non-goals.
- [Implementation](docs/IMPLEMENTATION.md) - code tour for CLI, Web, services,
  readiness, approval, recall, and tests.
- [Roadmap](docs/ROADMAP.md) - current state, completed milestones, next work,
  and explicit non-directions.
- [Usage](docs/USAGE.md) - safe local install, status checks, real dogfood,
  draft review, approval, recall, and troubleshooting.

Additional focused references remain available when needed:
[DESIGN.md](DESIGN.md) for the Web design system,
[docs/SECURITY.md](docs/SECURITY.md) for safety invariants, and
[docs/TESTING.md](docs/TESTING.md) for verification commands.
