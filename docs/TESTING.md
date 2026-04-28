# MindForge Testing And Smoke Guide

## Standard Quality Gate

Run from the repository root:

```bash
ruff check src tests
pytest
git diff --check
git status --short
```

At tag `v0.4.3`, the full test suite was:

```text
344 passed, 2 skipped
```

## Onboarding Smoke

The executable onboarding smoke is `tests/test_onboarding_smoke.py`. It copies `examples/demo-vault/` to `tmp_path`, writes runtime state to `tmp_path/.mindforge`, and runs:

1. `mindforge commands`
2. `mindforge next`
3. `mindforge doctor`
4. `mindforge scan`
5. `mindforge process --profile fake --limit 1`
6. `mindforge approve list`
7. `mindforge index rebuild`
8. `mindforge recall --query "checkpoint runtime"`
9. `mindforge project context my-first-agent --target claude-code`

Run it directly:

```bash
pytest tests/test_onboarding_smoke.py
```

## Manual Demo Smoke

Use only the fictional demo vault:

```bash
mindforge --vault examples/demo-vault doctor
mindforge --vault examples/demo-vault next
mindforge --vault examples/demo-vault scan
mindforge --vault examples/demo-vault index rebuild
mindforge --vault examples/demo-vault recall --query "checkpoint runtime" --ranking hybrid
mindforge --vault examples/demo-vault project context my-first-agent --target claude-code
```

## Interactive Init Smoke

Use `/tmp`, not personal data:

```bash
mindforge init --interactive --project-root /tmp/mindforge-smoke
mindforge doctor --config /tmp/mindforge-smoke/configs/mindforge.yaml
mindforge next --config /tmp/mindforge-smoke/configs/mindforge.yaml
mindforge next --config /tmp/mindforge-smoke/configs/mindforge.yaml --format json
```

## Safety Checks To Preserve

- Fake provider path must not perform HTTP.
- Doctor/next must not read `.env` contents.
- Raw source files under `00-Inbox/` must remain unchanged.
- `process` must not produce `human_approved`.
- Telemetry must use the whitelist only.
- Recall must not index raw sources or secret-bearing artifacts.

## Troubleshooting

| Symptom | Check |
|---|---|
| `mindforge: command not found` | Activate venv and run `pip install -e .`. |
| Missing config | Run `mindforge init --interactive` or pass `--config`. |
| No cards after process | Check `active_profile`, source files, and `mindforge status`. |
| PDF/docx dependency error | Install extras or disable those source types. |
| Demo vault writes runtime state | Use `--config` with `state.workdir` in `/tmp`, as the tests do. |
