# MindForge v0.4.3 Review

## Scope

v0.4.3 是 CLI onboarding polish #3：不新增大功能，只把首次使用与日常自检做顺手，为后续 1-2 周真实 dogfooding 做准备。

## Shipped

- `mindforge init --interactive`
  - 交互式询问 vault 路径、本地 telemetry、`active_profile`。
  - vault 路径会拒绝已有的非空非 MindForge 目录。
  - 中断时 fail-fast，写文件前已经完成全部 prompt，不留下半成品。
  - 仍复用 `init_cmd.build_plan` / `execute_plan`，不读 `.env`、不调 LLM、不联网。

- 错误信息中文化收口
  - 配置对象、frontmatter、常见 adapter 文件缺失 / PDF / Docx 解析错误转为中文用户提示。
  - 内部 invariant 保留技术错误，以便开发调试。

- `doctor` / `next` 产品化
  - `doctor` 输出分为 Runtime / Vault / Optional installs / Safety / Action items。
  - 状态使用 `✓` / `⚠` / `✗` / `·`，Action items 带 `critical` / `recommended` / `info`。
  - `next` 文本输出最多 5 条建议；JSON schema 升到 `version=2`，保留 `command` / `reason` 并新增 `priority`。

- Onboarding smoke
  - `tests/test_onboarding_smoke.py` 固化 demo vault 主路径：commands / next / doctor / scan / process(fake) / approve list / index rebuild / recall / project context。
  - 运行时产物写入 `tmp_path/.mindforge`，不污染 `examples/demo-vault/.mindforge`。

## Safety

- 没有读取 `.env` 内容。
- 没有调用真实 LLM。
- 没有联网。
- 没有修改 raw source。
- 没有自动 approve。
- 没有引入 RAG / embedding / OCR / Obsidian plugin / 后台 daemon / 系统日历。

## Next

建议进入 1-2 周真实 dogfooding，只记录痛点与命令使用数据；v0.5 相关 Obsidian plugin / RAG 仅在 dogfooding 后写设计文档，不直接进主干代码。
