# MindForge 测试与 Smoke 指南

## 本地 Push 关口

推荐开发者 push 前运行统一验证脚本，等价于 full pytest + ruff + diff check：

```bash
./scripts/check.sh
```

该脚本不读取 `.env`、不调用真实 provider，所有测试默认使用 fake / safe local 路径。

## Dogfood Smoke 测试

非敏感 dogfood 闭环一键验证（fake provider，不需要 API key）：

```bash
./scripts/dogfood_smoke.sh
```

覆盖 markdown import → process → ai_draft 验证 → approve → recall 全链路。

## 真实 LLM Dogfood 测试

真实 LLM opt-in 端到端验证（需要 API key，需显式 opt-in）：

**推荐路径：Web-first**。新用户通过 Web Setup 页面配置 provider，在 Web UI 中完成 import → process → review → approve → recall 全链路验证。

**高级路径：CLI/YAML 批量执行器**。`scripts/real_llm_dogfood.sh` 是批量 E2E / CI-like / 开发者验证脚本，不是新用户首选入口：

```bash
# preflight — 验证配置就绪，不调用 LLM
./scripts/real_llm_dogfood.sh

# real-run — 完整批量端到端 pipeline
./scripts/real_llm_dogfood.sh --real-llm --confirm-cost
```

覆盖 6 份非敏感样本的 scan → process（真实 LLM）→ ai_draft 结构校验 → 安全边界验证 → 人工 approve → index rebuild（BM25）→ recall → friction log。

## 标准质量关口

从仓库根目录运行：

```bash
python -m pip install -e ".[dev,pdf,docx]"
ruff check src tests
git diff --check
git status --short
```

完整 pytest 会覆盖 PDF / DOCX adapter 与 Web DOCX dedup 路径。开发机和 CI
应使用 `.[dev,pdf,docx]` 安装口径，确保 `pypdf` 与 `python-docx` 都来自项目
extras，而不是在测试里跳过可读文档覆盖。

使用临时 HOME 运行完整测试套件，确保测试不会重用你的真实工作区、secret store 或私人笔记：

```bash
rm -rf /private/tmp/mindforge-test-home
mkdir -p /private/tmp/mindforge-test-home
HOME=/private/tmp/mindforge-test-home python -m pytest -q
```

在文档治理变更（涉及测试、CLI help 或 product-surface 契约文档）后运行完整测试套件。

## 首选状态命令

新用户首选检查命令：`mindforge status`。

## 新手 Smoke 测试

可执行的 onboarding smoke 脚本是 `tests/test_onboarding_smoke.py`。它在 `tmp_path` 下使用虚构的 fixture 工作区，将运行时状态写入 `tmp_path/.mindforge`，并保持产品路径异步：

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

直接运行：

```bash
pytest tests/test_onboarding_smoke.py
```

## 手动 Fixture Smoke 测试

仅使用虚构的 fixture vault：

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

Obsidian 特定的回归覆盖在 `tests/test_v0_5_obsidian.py` 中。

## 交互式初始化 Smoke 测试

使用 `/tmp`，不要使用个人数据：

```bash
mindforge init --interactive --project-root /tmp/mindforge-smoke
mindforge start --config /tmp/mindforge-smoke/configs/mindforge.yaml
mindforge status --config /tmp/mindforge-smoke/configs/mindforge.yaml
mindforge doctor --config /tmp/mindforge-smoke/configs/mindforge.yaml
```

## 本地工作流安全说明

- 使用你愿意处理的本地源文件或文件夹；从非敏感材料开始。
- 将 API key 保留在 Web Setup 管理的本地 secret store 中；不要将 key 放入 YAML 或文档中。
- 测试时不要读取或打印 `.env` 或 `.mindforge/secrets.json`。
- 不要使用真实的私人 vault 进行 smoke 测试。
- 真实模型调用需要显式模型配置和明确的处理操作。
- 没有自动审批。

## 需保留的安全检查

- Test-double 模型路径不得发起 HTTP 请求。
- Doctor/start/status/next 不得读取 provider key 值。
- `00-Inbox/` 下的原始源文件必须保持不变。
- `process` 不得生成 `human_approved`。
- Telemetry 必须仅使用白名单。
- Recall 不得索引原始源文件或包含机密信息的工件。
- Obsidian 绑定不得编辑正式笔记、移动文件、重写 wikilink 或将运行时状态写入 vault。
- 自定义策略保持纯声明式。
- 未来门控能力在明确授权之前保持不可用。

## 故障排查

| 症状 | 检查项 |
|---|---|
| `mindforge: command not found` | 激活 venv 并运行 `pip install -e .`。 |
| 缺少配置 | 运行 `mindforge init --interactive` 或传入 `--config`。 |
| 处理后没有卡片 | 检查 `mindforge runs show <run_id>`、模型配置、源文件和 `mindforge status`。 |
| DOCX / PDF 可选依赖跳过 | `pytest.importorskip` 设计；安装 `python-docx` / `pypdf` 即可运行：`pip install python-docx pypdf`；无需修改代码 |
| Fixture vault 写入运行时状态 | 使用带有 `state.workdir` 指向 `/tmp` 的 `--config`，就像测试中所做的那样。 |
