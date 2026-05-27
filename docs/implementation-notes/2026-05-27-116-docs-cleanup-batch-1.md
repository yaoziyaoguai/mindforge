# Documentation Cleanup Batch 1 — Implementation Notes

- **Date**: 2026-05-27
- **Trigger**: `/mf-autopilot` docs_cleanup — execute documentation-reset-plan.md batch 1
- **Status**: Complete

---

## 1. Scope

按 `docs/dev/documentation-reset-plan.md` 的 Batch 1 清单删除 8 个明显过时文档。

## 2. Files Deleted

| # | 文件 | 原因 |
|---|------|------|
| 1 | `docs/design/roadmap/V0_2_ROADMAP.md` | v0.2 路线，已被后续取代 |
| 2 | `docs/design/roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md` | v0.3 路线，已被后续取代 |
| 3 | `docs/design/tdd/TDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md` | 早期 TDD 文档 |
| 4 | `docs/design/sdd/SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md` | v0.3 SDD，已被实现取代 |
| 5 | `docs/internal/V0_2_DEVELOPMENT_RULES.md` | v0.2 开发规则 |
| 6 | `docs/internal/V0_3_DEVELOPMENT_RULES.md` | v0.3 开发规则 |
| 7 | `docs/plans/2026-05-21-001-feat-dogfood-readiness-plan.md` | 早期 dogfood plan |
| 8 | `docs/plans/2026-05-22-001-feat-real-llm-dogfood-plan.md` | 早期真实 LLM plan |

## 3. Files Updated (reference cleanup)

| 文件 | 变更 |
|------|------|
| `docs/dev/documentation-reset-plan.md` | 标记 Batch 1 为 completed；添加已知残留引用说明 |
| `docs/dev/documentation-inventory.md` | 移除已删除文件的 archive candidate 条目 |
| `docs/dev/docs-reset-index.md` | 移除两行已删除 dogfood plan 引用 |

## 4. Known Stale References (Not Blocked)

以下历史文档仍引用已删除文件。这些引用存在于 already-stale docs 中，不影响当前 canonical docs，留给后续 batch 处理：

- `docs/design/rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md` → V0_3_ROADMAP, SDD_KNOWLEDGE, V0_2/V0_3_RULES
- `docs/design/sdd/SDD_WIKI_PRESENTATION_V2.md` → V0_2_ROADMAP
- `docs/design/sdd/SDD_SOURCE_ADAPTER_V2.md` → V0_2_ROADMAP
- `docs/implementation-notes/2026-05-24-010-m3-related-cards.md` → V0_3_ROADMAP
- `docs/implementation-notes/2026-05-24-011-m5-knowledge-health.md` → V0_3_ROADMAP
- `docs/implementation-notes/2026-05-24-012-m6-local-graph-preview.md` → V0_3_ROADMAP
- `docs/specs/2026-05-24-007-m1-card-quality-integration-spec.md` → V0_3_ROADMAP
- `docs/specs/2026-05-24-008-m2-wiki-quality-integration-spec.md` → V0_3_ROADMAP

## 5. Safety

- 不涉及产品代码
- 不涉及审计证据
- 不涉及 canonical docs
- 不读取 .env / secrets
- 不调用真实 LLM

## 6. Gates

| Gate | Command | Exit Code |
|------|---------|-----------|
| git diff --check | `git diff --check` | 0 |
| ruff check | `ruff check docs/ .claude/commands/` | 0 |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 |
