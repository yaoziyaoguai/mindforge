# v0.4.2 复盘 — 产品体验闭环 + SourceAdapter 架构审计 + 示例 vault

## 范围

1. **SourceAdapter 架构审计**
   - 结论：**已经是插件化结构**（v0.1 起即如此）。
   - `SourceAdapter` 抽象基类 + `_BUILTIN_ADAPTERS` registry +
     `build_active_adapters()` 都已经存在；scanner / processor / pipeline /
     cli **无任何 source_type 写死分支**。
   - 唯一缺位：`SourceDocument` 没有 `adapter_name` 字段，仅 `ScanResult`
     旁路记录。本轮新增字段（默认空 → 兼容），由 Scanner 在 `_safe_load`
     中统一回填，避免每个 adapter 重复 boilerplate。
   - 协议正式化为独立文档 [`docs/SOURCE_ADAPTER_PROTOCOL.md`](./SOURCE_ADAPTER_PROTOCOL.md)。

2. **`mindforge commands`**：按"任务场景"分组列出全部命令，每条配中文一句话用途；
   静态脚本生成，不读 vault / 不读 .env / 不调 LLM / 不发 HTTP。

3. **`mindforge next [--format text|json]`**：根据 vault 当前状态推断"下一步该
   做什么"。判定全部基于文件系统可观察事实（vault 是否存在 / inbox 文件数 /
   state.json 中 raw|triaged 数 / 卡片 frontmatter status / 索引文件存在 /
   review_after 是否 overdue / 项目笔记数）。
   - 8 类可能建议：`init` / `inbox 放原料` / `scan` / `process` /
     `approve list` / `index rebuild` / `review backlog` / `project list`；
   - 都没命中时降级提示 `doctor`；
   - JSON 输出 `version=1`，便于脚本消费。

4. **示例 vault** `examples/demo-vault/`
   - 1×Cubox-style + 1×WebClip + 1×ChatExport + 1×ManualNote 的虚构 markdown；
   - 3 张已加工 Knowledge Card（2 个 human_approved + 1 个 ai_draft，
     其中 1 张已 `review_after` overdue）；
   - 1 个 `30-Projects/my-first-agent.md`（带完整 profile frontmatter）；
   - **完全虚构、不含任何敏感信息**；
   - `examples/demo-vault/.mindforge/` 进 `.gitignore`，跑 smoke 不会污染仓库。

5. **新增/更新文档**
   - 新：[`docs/SOURCE_ADAPTER_PROTOCOL.md`](./SOURCE_ADAPTER_PROTOCOL.md)
   - 新：本文件
   - 新：[`examples/demo-vault/README.md`](../examples/demo-vault/README.md)
   - 更新：`README.md`（v0.4.2 段 + 当前状态）、`docs/ROADMAP.md`（M5.9 行）
   - 注：`GETTING_STARTED.md` / `USER_GUIDE.md` 在 v0.4.1 已写完，
     v0.4.2 在 README + commands 输出中追加 `mindforge commands` / `mindforge next`
     入口即可，避免文档双写漂移。

6. **测试**：14 项新增（`tests/test_v0_4_2.py`）
   - commands 覆盖关键 group / 不泄漏 secret
   - next 在缺 config / 空 vault / 有 ai_draft / 缺索引 各场景
   - next JSON schema 稳定
   - next 不读 .env、不发 socket
   - AdapterRegistry 6 个内置 adapter 在册
   - Scanner 自动回填 `SourceDocument.adapter_name`
   - SourceDocument 是 frozen dataclass（下游不能改）
   - 示例 vault 至少包含约定资产
   - 示例 vault 不含 `sk-ant-` / `Bearer ` / `ANTHROPIC_API_KEY=` 等敏感片段

## 不做（明示）

- 不调真实 LLM；
- 不读 .env 内容；
- 不联网；
- 不做 RAG / embedding / Obsidian 插件 / OCR；
- 不自动 approve；
- 不修改原始 source 文件；
- 不上传 telemetry。

## 测试 / 质量

- pytest: **339 passed, 2 skipped**（v0.4.1 的 325 + 14 新）
- ruff: clean
- git diff --check: clean
- 真实 smoke：commands / next / next --format json / doctor / scan /
  index rebuild / recall hybrid / project context my-first-agent — 全绿
  （demo vault 内）

## 兼容性

- `SourceDocument.adapter_name` 是带默认值（`""`）的新字段，旧 adapter 不
  动也能继续工作；Scanner 在 adapter 没填时自动回填。
- 没有命令被改名或弃用。
- 旧测试（325/2）全部继续通过。

## 下一步建议

1. **真实 dogfooding 1–2 周**（最强烈推荐）— 从 v0.2.6 起 init/approve/
   recall/review/project context/commands/next 全部到位，已经具备
   end-to-end 使用价值，再加功能不如先验证产品假设。
2. 如果继续推进：
   - **CLI polish #3**：`init --interactive` + 错误信息中文化全覆盖；
   - **demo vault 文档化**：把 README 的"一键 5 命令演示"做成 `docs/DEMO.md`；
   - **adapter 扩展示范**：基于 `SOURCE_ADAPTER_PROTOCOL.md` 实操 1 个新
     adapter（如 `NotionAdapter`），验证插件协议。
3. 仍**不**进入 RAG / Obsidian 插件 / OCR / 后台 daemon。
