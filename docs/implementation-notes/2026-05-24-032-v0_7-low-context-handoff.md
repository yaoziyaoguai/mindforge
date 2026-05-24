# v0.7 Low-Context Handoff

## 日期
2026-05-24

## Stop Reason
**HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN** — context 仅剩 3% until auto-compact，按 `docs/dev/engineering-workflow.md` 和 `/mf-autopilot` context policy，<5% 必须收口，不得开启新 implementation unit。

## 当前 Repo 状态

| 项目 | 值 |
|------|-----|
| Branch | main |
| HEAD | b37f06e |
| Working tree | clean |
| vs origin/main | 0 0 |

## 已完成

### v0.7 U1: Evidence Text Quality Upgrade
- `src/mindforge/relations/graph_builder.py` — 新增 `_build_evidence_text()`，evidence 从机器格式 `"same_source: card_1 ↔ card_2"` 升级为用户可读格式（包含共享 entity 名称）
- 覆盖 same_source / same_tag / same_wiki_section / wiki_section_reference / 通用 fallback

### v0.7 U2: Relation Reason Granularity
- 所有 `RelationEvidence` 创建时填充 `detail={"relation_reason": raw.reason.value}`
- 下游可从 `evidence.detail.relation_reason` 区分精确原因

### v0.7 U3: Graph UI Copy Audit & Polish
- GraphExplorer 组件中 4 处硬编码英文 → `t()` i18n 调用
- 新增 6 个 i18n key：`graph.node_type_*` (3) + `graph.placeholder_*` (3)

### v0.7 U4: Test Gap Characterization & Closure
- 新增 12 个测试（test_graph_builder.py +8, test_discovery_context.py +3, test_graph_api.py +3）
- 总测试数 relations: 84 → 96

## 未完成

### v0.7 U5: Browser / API Smoke
- **状态**: 未执行
- **原因**: auto mode classifier 拒绝在 port 8767 启动 web server；port 8766 返回 503（已有 python process LISTEN 但不 serving）
- **影响**: Graph API 和 GraphExplorer UI 的 browser smoke 验证缺失

## 已知限制

- GraphExplorer 的 edge type badge 仍显示英文技术标识符（fallback 到 edge_type 字符串），后续可添加完整的 edge_type → i18n key 映射
- `_source_centered_graph()` 和 `_tag_centered_graph()` 的 evidence 格式未与 `_card_centered_graph()` 统一
- 上一轮报告中 "no hard-stop" 的描述不严谨，已修正为 HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN

## Evidence Limitation 标记

上一轮 gate report 中 `npm run build` 使用 tail 截断输出展示，但这不影响 gate 判定（build 的 exit code 为 0 且输出完整）。所有 gate 均为真实 exit code 而非伪造。

## 下一会话 Entrypoint

`/mf-autopilot` 恢复时应：

1. **首先处理 v0.7 U5 browser/API smoke verification** — 用户需手动处理 auto mode permission 或手动启动 server，或在允许的 permission mode 下让 agent 启动 server
2. U5 通过或显式 defer（附 evidence）后，再继续 v0.8 Lexical Retrieval Foundation
3. **不要跳过 U5 直接进入 v0.8**
