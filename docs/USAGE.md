# MindForge Usage

This guide is the canonical user path for local dogfood. It assumes you want to
inspect real local state safely, not run a cloud service.

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
mindforge --help
```

Use a disposable or non-sensitive project vault for the first run. Do not point
MindForge at a real private Obsidian vault until the status and dry-run paths
feel boring.

## First Status Commands

Start with read-only checks:

```bash
mindforge status
mindforge config status
mindforge workspace status
mindforge doctor
```

These commands should explain local-only status, vault path, provider readiness,
Cubox readiness, `.env` key presence, pending drafts, approved cards, recall
availability, warnings, and next actions.

`.env` output is presence-only. MindForge may show a key name such as
`OPENAI_API_KEY` or `UPSTAGE_API_KEY`, but it must not print the value.

## Web Console

```bash
mindforge web
mindforge web --open
mindforge web --port 9876
mindforge web --vault /path/to/project-vault
```

The default host is `127.0.0.1`. The Web console is for one local user and shows
the same safety model as the CLI: local-only status, current vault, provider
state, `.env` presence, write mode, and pending drafts.

## Safe Real Dogfood

Recommended first loop:

```bash
mindforge status
mindforge config status
mindforge workspace status
mindforge sources status
mindforge drafts list
mindforge recall "your query"
```

If using Cubox, prefer an offline JSON export with a small non-sensitive sample.
Readiness and dry-run paths must not call the real Cubox API. If using a vault,
start with a project-only vault and dry-run/staged outputs.

## Draft Review

List drafts:

```bash
mindforge drafts list
```

Show one draft safely:

```bash
mindforge drafts show <draft-id>
```

Ordinary output should avoid dumping private full text. Use explicit content
flags only when you are comfortable seeing that local content in your terminal.

## Approval

Approve only after reading the source and draft context:

```bash
mindforge approve <draft-id> --confirm
```

Approval means `ai_draft -> human_approved`. It is not a casual "OK" button.
Without explicit confirmation, MindForge must not create `human_approved`.
Rejected/deferred states should be honest: if safe persistence is unavailable,
the CLI should say so and suggest the next manual action instead of pretending a
write succeeded.

## Recall

```bash
mindforge recall "project memory"
```

Recall is local lexical search over approved cards. It is not RAG, embedding,
semantic search, or semantic merge. Empty queries should return a friendly
prompt for a search phrase. No-result output should suggest approving relevant
drafts or checking whether the workspace has approved cards.

## Configuration Troubleshooting

When a command reports a configuration issue, read it in four parts:

1. What happened.
2. Why it matters.
3. How to fix it.
4. Safe next command.

Common examples:

- Missing vault: create a project vault or pass `--vault /path/to/vault`.
- Missing provider key: keep using fake provider, or configure a real provider
  only when you intend to opt in.
- Cubox token missing: expected for JSON-export dogfood; token is not needed for
  offline export preview.
- No drafts: inspect sources, run the processing path, or use demo fixtures.
- No approved cards: approve one reviewed draft before expecting recall hits.

## What MindForge Does Not Do By Default

- It does not call a real LLM during readiness/status.
- It does not call the real Cubox API during readiness/status.
- It does not print `.env` secret values.
- It does not automatically modify a real private vault.
- It does not auto-approve.
- It does not run RAG, embeddings, or semantic merge.
