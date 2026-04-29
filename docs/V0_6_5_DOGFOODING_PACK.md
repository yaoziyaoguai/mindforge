# v0.6.5 Non-sensitive Dogfooding Pack

## Goal

Make it easy to run one realistic local MindForge loop on a disposable, non-sensitive vault copy and record product friction.

## Copyable Path

```bash
mindforge dogfood plan --vault /tmp/mindforge-dogfood-vault
mindforge doctor --vault /tmp/mindforge-dogfood-vault --paths
mindforge scan --vault /tmp/mindforge-dogfood-vault
mindforge process --profile fake --limit 1 --vault /tmp/mindforge-dogfood-vault
mindforge approve list --vault /tmp/mindforge-dogfood-vault
mindforge approve show --card <card-path> --vault /tmp/mindforge-dogfood-vault
mindforge recall --query "agent" --vault /tmp/mindforge-dogfood-vault
mindforge review weekly --vault /tmp/mindforge-dogfood-vault
mindforge backup export --vault /tmp/mindforge-dogfood-vault --output-dir /tmp/mindforge-backup
mindforge obsidian stage --vault /tmp/mindforge-dogfood-vault --source <note.md> --dry-run
mindforge today --vault /tmp/mindforge-dogfood-vault
```

## Checklist

Use `docs/templates/NON_SENSITIVE_DOGFOODING_CHECKLIST.md` to record which steps worked, which messages were unclear, and whether the source → draft → approve → recall → review loop felt usable.

## Non-goals

- No real private/work vault.
- No `.env` reading.
- No real LLM call.
- No automatic approve.
- No formal Obsidian note writes.
- No RAG / embedding.
- No Obsidian plugin.
- No Web UI / TUI.
