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

For a disposable packaged sample:

```bash
mindforge dogfood init-demo --target /tmp/dogfood-vault
mindforge dogfood readiness --vault /tmp/dogfood-vault
mindforge dogfood quickstart --vault /tmp/dogfood-vault
```

`quickstart` prints a manual runbook. It does not execute the listed commands,
does not read `.env` contents, does not call a real LLM, does not write formal
Obsidian notes, and does not produce `human_approved`. no real LLM is part of
the default dogfood contract.

For a non-sensitive Cubox JSON export:

```bash
mindforge cubox dry-run --export /path/to/cubox-export.json
mindforge cubox preview-ai-draft --export /path/to/cubox-export.json --limit 5
```

Start with `--limit 5`. Do not exceed `--limit 20` during the first few runs.
MindForge does not support full Cubox account sync, has no `--all` ingestion
flag, and does not call the real Cubox API on this path.

Obsidian dogfood remains a dry-run/staged workflow:

```bash
mindforge obsidian next --vault /path/to/project-vault
mindforge obsidian doctor --vault /path/to/project-vault
mindforge obsidian scan --vault /path/to/project-vault --limit 20
mindforge obsidian links --vault /path/to/project-vault
mindforge obsidian stage --vault /path/to/project-vault --source <note.md> --dry-run
mindforge obsidian preflight --vault /path/to/project-vault --manifest <export>.manifest.json
```

Use a disposable, non-sensitive vault copy. No formal Obsidian notes are
written by the dry-run path. No formal Obsidian note writes. No formal Obsidian
notes are written. No `.env`, real LLM, RAG / embedding, Obsidian plugin,
telemetry upload, or automatic vault cleanup is involved. include/exclude
filters and diff preview are review aids only.

Obsidian dogfood boundaries:

- No formal Obsidian notes are written.
- No default real LLM path.
- No Obsidian plugin.
- No RAG / embedding.
- No telemetry upload.
- No automatic approve.

Rollback rule: first dogfood runs should happen in a disposable or git-tracked
project vault. Staged Obsidian writes, when explicitly requested, are confined
to staging output; use `git status`, `git restore`, or removal of the specific
staging files to roll back. Do not run broad destructive cleanup commands
against a real vault.

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

Approval safety checklist:

- Review the source context.
- Review the draft.
- Confirm the exact target.
- Use the explicit confirmation flag or Web confirmation UI.
- Do not batch approve private material on a first dogfood run.

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

## Real Provider Opt-In

Use readiness first:

```bash
mindforge provider readiness
mindforge llm ping --profile <real-profile>
```

These commands show configured/missing key presence only. They must not print
secret values. Real smoke requires explicit opt-in and should use synthetic or
non-sensitive input only:

```bash
mindforge provider smoke --allow-real --profile <real-profile>
```

Real provider output remains review-only and must not become `human_approved`
without explicit approval.

## What MindForge Does Not Do By Default

- No RAG / embedding.
- No Obsidian plugin.
- No automatic approve.
- It does not call a real LLM during readiness/status.
- It does not call a real LLM during quickstart or dry-run dogfood.
- It does not call the real Cubox API during readiness/status.
- It does not call the real Cubox API during JSON-export preview.
- It does not print `.env` secret values.
- It does not automatically modify a real private vault.
- It does not auto-approve.
- It does not run RAG, embeddings, or semantic merge.
