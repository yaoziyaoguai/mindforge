# v0.6.x Local Product UX Readiness

## Version Train Summary

- v0.6.1 Onboarding / Command Guidance: added first-day status and command navigation.
- v0.6.2 Approval / Review Flow Polish: made human approval and review read like a daily learning workflow.
- v0.6.3 Recall / Search UX: clarified query results, index status, match reasons, and recovery actions.
- v0.6.4 Local Config Setup UX: added CLI-first config/setup guidance with safe defaults.
- v0.6.5 Non-sensitive Dogfooding Pack: added a disposable-vault dogfooding path and checklist.

## Recommended Local Dogfooding Path

Use a disposable, non-sensitive vault copy. The commands below are the local CLI path to verify source → draft → explicit approve → recall → review without touching private data.

```bash
mindforge start --vault examples/demo-vault
mindforge commands
mindforge config show --vault examples/demo-vault
mindforge config doctor --vault examples/demo-vault
mindforge setup --dry-run --vault examples/demo-vault
mindforge doctor --vault examples/demo-vault --paths
mindforge scan --vault examples/demo-vault
mindforge process --profile fake --limit 1 --vault examples/demo-vault
mindforge approve list --vault examples/demo-vault
mindforge approve show --card <card-path> --vault examples/demo-vault
mindforge recall --query "agent" --vault examples/demo-vault
mindforge recall --query "agent" --explain --vault examples/demo-vault
mindforge review weekly --vault examples/demo-vault
mindforge backup export --vault examples/demo-vault --output-dir /tmp/mindforge-backup
mindforge obsidian stage --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --dry-run
mindforge today --vault examples/demo-vault
mindforge next --vault examples/demo-vault
```

## Safety Boundary

- No real LLM by default.
- No `.env` read in local product UX commands.
- No writes to real Obsidian notes.
- No automatic approve.
- Telemetry remains local-only and is not uploaded.
- BM25 / lexical recall is not RAG and does not use embeddings.
- Obsidian support remains read-only / dry-run / preview-first.

## Still Not Implemented

- No RAG / embedding platform.
- No Obsidian plugin.
- No Web UI or TUI.
- No real LLM default path.
- No automatic vault cleanup or formal-note rewrite.
- No telemetry upload.

## v0.7 Prep

The recommended next milestone is v0.7 Obsidian Integration UX. It should start from read-only, dry-run, preview, explicit approve, and stronger safety checks.

Candidate tasks:

- stronger stage preview;
- diff preview;
- include/exclude rules;
- vault safety doctor;
- staged export directory;
- formal Obsidian note writes remain gated behind future diff preview + backup + rollback + explicit approval.

This document does not start v0.7 implementation.
