# MindForge Testing And Smoke Guide

## Local Push Gate

推荐开发者 push 前运行统一验证脚本，等价于 full pytest + ruff + diff check：

```bash
./scripts/check.sh
```

该脚本不读取 `.env`、不调用真实 provider，所有测试默认使用 fake / safe local 路径。

## Dogfood Smoke

非敏感 dogfood 闭环一键验证（fake provider，不需要 API key）：

```bash
./scripts/dogfood_smoke.sh
```

覆盖 markdown import → process → ai_draft 验证 → approve → recall 全链路。

## Real LLM Dogfood

真实 LLM opt-in 端到端验证（需要 API key，需显式 opt-in）：

**推荐路径：Web-first**。新用户通过 Web Setup 页面配置 provider，在 Web UI 中完成 import → process → review → approve → recall 全链路验证。

**Advanced path：CLI/YAML batch runner**。`scripts/real_llm_dogfood.sh` 是批量 E2E / CI-like / 开发者验证脚本，不是新用户首选入口：

```bash
# preflight — 验证配置就绪，不调用 LLM
./scripts/real_llm_dogfood.sh

# real-run — 完整批量端到端 pipeline
./scripts/real_llm_dogfood.sh --real-llm --confirm-cost
```

覆盖 6 份非敏感样本的 scan → process（真实 LLM）→ ai_draft 结构校验 → 安全边界验证 → 人工 approve → index rebuild（BM25）→ recall → friction log。

## Standard Quality Gate

Run from the repository root:

```bash
python -m pip install -e ".[dev,pdf,docx]"
ruff check src tests
git diff --check
git status --short
```

完整 pytest 会覆盖 PDF / DOCX adapter 与 Web DOCX dedup 路径。开发机和 CI
应使用 `.[dev,pdf,docx]` 安装口径，确保 `pypdf` 与 `python-docx` 都来自项目
extras，而不是在测试里跳过可读文档覆盖。

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
| DOCX / PDF optional dependency skip | `pytest.importorskip` design；install `python-docx` / `pypdf` to run：`pip install python-docx pypdf`；no code change needed |
| Fixture vault writes runtime state | Use `--config` with `state.workdir` in `/tmp`, as the tests do. |
