# MindForge Testing And Smoke Guide

## Standard Quality Gate

Run from the repository root:

```bash
ruff check src tests
pytest
git diff --check
git status --short
```

Run the full suite after documentation governance changes when tests or CLI help
references are touched.

## Onboarding Smoke

The executable onboarding smoke is `tests/test_onboarding_smoke.py`. It copies
`examples/fixture-vault/` to `tmp_path`, writes runtime state to
`tmp_path/.mindforge`, and runs:

1. `mindforge commands`
2. `mindforge next`
3. `mindforge doctor`
4. `mindforge scan`
5. `mindforge process --limit 1`
6. `mindforge approve list`
7. `mindforge index rebuild`
8. `mindforge recall --query "checkpoint runtime"`
9. `mindforge project context my-first-agent --target claude-code`

Run it directly:

```bash
pytest tests/test_onboarding_smoke.py
```

## Manual Fixture Smoke

Use only the fictional fixture vault:

```bash
mindforge --vault examples/fixture-vault doctor
mindforge --vault examples/fixture-vault next
mindforge --vault examples/fixture-vault scan
mindforge --vault examples/fixture-vault index rebuild
mindforge --vault examples/fixture-vault recall --query "checkpoint runtime" --ranking hybrid
mindforge --vault examples/fixture-vault project context my-first-agent --target claude-code
mindforge obsidian doctor --vault examples/fixture-vault
mindforge obsidian scan --vault examples/fixture-vault --limit 5
mindforge obsidian links --vault examples/fixture-vault
mindforge obsidian stage --vault examples/fixture-vault --source 02-Knowledge/agent-runtime-observer.md --dry-run
```

Obsidian-specific regression coverage lives in `tests/test_v0_5_obsidian.py`.

## Interactive Init Smoke

Use `/tmp`, not personal data:

```bash
mindforge init --interactive --project-root /tmp/mindforge-smoke
mindforge doctor --config /tmp/mindforge-smoke/configs/mindforge.yaml
mindforge next --config /tmp/mindforge-smoke/configs/mindforge.yaml
mindforge next --config /tmp/mindforge-smoke/configs/mindforge.yaml --format json
```

## Safety Checks To Preserve

- Test-double model path must not perform HTTP.
- Doctor/next must not read `.env` contents.
- Raw source files under `00-Inbox/` must remain unchanged.
- `process` must not produce `human_approved`.
- Telemetry must use the whitelist only.
- Recall must not index raw sources or secret-bearing artifacts.
- Obsidian binding must not edit formal notes, move files, rewrite wikilinks, or
  write runtime state into the vault.
- Custom strategies remain declarative-only.
- Future-gated capabilities stay absent until explicitly authorized.

## Troubleshooting

| Symptom | Check |
|---|---|
| `mindforge: command not found` | Activate venv and run `pip install -e .`. |
| Missing config | Run `mindforge init --interactive` or pass `--config`. |
| No cards after process | Check model setup, source files, and `mindforge status`. |
| PDF/docx dependency error | Install extras or disable those source types. |
| Fixture vault writes runtime state | Use `--config` with `state.workdir` in `/tmp`, as the tests do. |
