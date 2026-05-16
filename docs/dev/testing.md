# MindForge Testing And Smoke Guide

## Standard Quality Gate

Run from the repository root:

```bash
ruff check src tests
git diff --check
git status --short
```

Run the full suite with a temporary HOME so tests never reuse your real
workspace, secret store, or private notes:

```bash
rm -rf /private/tmp/mindforge-test-home
mkdir -p /private/tmp/mindforge-test-home
HOME=/private/tmp/mindforge-test-home python -m pytest -q
```

Run the full suite after documentation governance changes when tests, CLI help,
or product-surface contract docs are touched.

## First Status Commands

新用户首选检查命令：`mindforge status`。

## Onboarding Smoke

The executable onboarding smoke is `tests/test_onboarding_smoke.py`. It uses a
fictional fixture workspace under `tmp_path`, writes runtime state to
`tmp_path/.mindforge`, and keeps the product path asynchronous:

1. `mindforge commands`
2. `mindforge start`
3. `mindforge status`
4. `mindforge watch add <file-or-folder>`
5. `mindforge import <file-or-folder>`
6. `mindforge runs list`
7. `mindforge runs show <run_id>`
8. `mindforge approve list`
9. `mindforge index rebuild`
10. `mindforge recall --query "checkpoint runtime"`

Run it directly:

```bash
pytest tests/test_onboarding_smoke.py
```

## Manual Fixture Smoke

Use only the fictional fixture vault:

```bash
cp configs/mindforge_example.yaml /tmp/mindforge-fixture.yaml
export CONFIG=/tmp/mindforge-fixture.yaml

mindforge --vault examples/fixture-vault doctor --config "$CONFIG"
mindforge --vault examples/fixture-vault next --config "$CONFIG"
mindforge watch add examples/fixture-vault/00-Inbox --config "$CONFIG"
mindforge runs list --config "$CONFIG"
mindforge --vault examples/fixture-vault index rebuild --config "$CONFIG"
mindforge --vault examples/fixture-vault recall --query "checkpoint runtime" --ranking hybrid --config "$CONFIG"
mindforge --vault examples/fixture-vault project context my-first-agent --target claude-code --config "$CONFIG"
mindforge obsidian doctor --vault examples/fixture-vault --config "$CONFIG"
mindforge obsidian links --vault examples/fixture-vault --config "$CONFIG"
mindforge obsidian stage --vault examples/fixture-vault --source 02-Knowledge/agent-runtime-observer.md --dry-run --config "$CONFIG"
```

Obsidian-specific regression coverage lives in `tests/test_v0_5_obsidian.py`.

## Interactive Init Smoke

Use `/tmp`, not personal data:

```bash
mindforge init --interactive --project-root /tmp/mindforge-smoke
mindforge start --config /tmp/mindforge-smoke/configs/mindforge.yaml
mindforge status --config /tmp/mindforge-smoke/configs/mindforge.yaml
mindforge doctor --config /tmp/mindforge-smoke/configs/mindforge.yaml
```

## Local workflow safety notes

- Use local source files or folders that you are comfortable processing; start with non-sensitive material.
- Keep API keys in the local secret store managed by Web Setup; do not put keys in YAML or docs.
- Do not read or print `.env` or `.mindforge/secrets.json` while testing.
- Do not use a real private vault for smoke tests.
- Real model calls require explicit model configuration and an explicit processing action.
- No automatic approve.

## Safety Checks To Preserve

- Test-double model path must not perform HTTP.
- Doctor/start/status/next must not read provider key values.
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
| No cards after processing | Check `mindforge runs show <run_id>`, model setup, source files, and `mindforge status`. |
| PDF/docx dependency error | Install extras or disable those source types. |
| Fixture vault writes runtime state | Use `--config` with `state.workdir` in `/tmp`, as the tests do. |
