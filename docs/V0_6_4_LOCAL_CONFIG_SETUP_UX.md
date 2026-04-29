# v0.6.4 Local Config / Setup UX

## Goal

Make first-run local setup easier to inspect and safer to repeat without editing YAML blindly.

## Recommended First-day Commands

```bash
mindforge setup --dry-run --vault examples/demo-vault
mindforge config show --vault examples/demo-vault
mindforge config doctor --vault examples/demo-vault
mindforge config init --output /tmp/mindforge.yaml --vault /tmp/mindforge-vault --dry-run
```

## Safe-by-default Boundary

Config/setup UX uses the bundled default config, defaults to `active_profile: fake`, does not read `.env`, does not call a real LLM, does not write formal Obsidian notes, and does not upload telemetry.

## Non-goals

- No Web UI or TUI wizard.
- No real LLM setup automation.
- No RAG / embedding.
- No Obsidian plugin.
- No overwrite of existing config unless `--force` is explicit.
