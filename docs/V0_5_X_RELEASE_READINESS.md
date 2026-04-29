# MindForge v0.5.x Release Readiness

## Version Train

- v0.5.1: Local usability made the fake-provider demo path usable end to end.
- v0.5.2: Packaged assets made prompts, templates, and configs install-ready.
- v0.5.3: Obsidian dry-run became safer for disposable non-sensitive vault copies.
- v0.5.4: `today` and `next` made the daily local loop clearer.
- v0.5.5: Local backup/export and doctor recovery checks added safety rails.

## Recommended Local Path

```bash
mindforge doctor --vault examples/demo-vault --paths
mindforge today --vault examples/demo-vault
mindforge scan --vault examples/demo-vault
mindforge process --profile fake --limit 1 --vault examples/demo-vault
mindforge approve list --vault examples/demo-vault
mindforge index rebuild --vault examples/demo-vault
mindforge recall --query "agent" --vault examples/demo-vault
mindforge review weekly --vault examples/demo-vault
mindforge obsidian stage --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --dry-run
mindforge backup export --vault examples/demo-vault
```

## Smoke

```bash
.venv/bin/ruff check .
.venv/bin/pytest
.venv/bin/mindforge commands
.venv/bin/mindforge today --vault examples/demo-vault
.venv/bin/mindforge doctor --vault examples/demo-vault --paths
```

## Still Not Doing

- No real LLM by default.
- No `.env` read on local fake / doctor / onboarding paths.
- No formal Obsidian note writes.
- No RAG / embedding.
- No Obsidian plugin.
- No telemetry upload.

## Next

Proceed to v0.6 Local Product UX: onboarding, command guidance, approval/review
workflow polish, and search usability.
