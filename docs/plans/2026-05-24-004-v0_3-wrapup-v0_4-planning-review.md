---
title: v0.3 收尾 & v0.4 方向规划评审
type: docs
status: reviewed
date: 2026-05-24
---

## v0.3 完成状态

v0.3 六项 Milestone + Milestone H 打磨全部完成：

| Milestone | 状态 | 测试 | 实现笔记 |
|-----------|------|------|---------|
| M1 Card Quality | 已实现 | 27 tests pass | [notes](../implementation-notes/2026-05-24-007-m1-card-quality-integration.md) |
| M2 Wiki Quality | 已实现 | 22 tests pass | [notes](../implementation-notes/2026-05-24-008-m2-wiki-quality-integration.md) |
| M3 Related Cards | 已实现 | 13 tests pass | [notes](../implementation-notes/2026-05-24-010-m3-related-cards.md) |
| M4 Source Location | 已实现 | 集成到模板 | [notes](../implementation-notes/2026-05-24-004-m4-source-location-handoff.md) |
| M5 Knowledge Health | 已实现 | 16 tests pass | [notes](../implementation-notes/2026-05-24-011-m5-knowledge-health.md) |
| M6 Local Graph Preview | 已实现 | 13 tests pass | [notes](../implementation-notes/2026-05-24-012-m6-local-graph-preview.md) |
| H1-H4 Web Polish | 已实现 | 浏览器 smoke 通过 | [notes](../implementation-notes/2026-05-24-009-milestone-h-web-polish.md) |

M3/M5/M6 代码通过 squash merge PR #7 (commit `9e813d2`) 进入 main。三者在 `feat-wiki-llm-synthesis` 分支上一起实现，共享同一批卡片索引结构，squash merge 保持了跨层原子一致性。

## v0.3 Release Criteria 检查

| # | 条件 | 状态 |
|---|------|------|
| 1 | M1-M6 done criteria 达标 | ✓ |
| 2 | 不破坏 v0.2 行为 | ✓ |
| 3 | 新功能 ≥ 80% 测试覆盖 | ✓ |
| 4 | 每个 milestone dogfood 通过 | ✓ |
| 5 | ruff clean + tsc clean | ✓ |
| 6 | CI green | 待验证 |
| 7 | 用户文档更新（中/英） | ✓ |

## 待完成事项

### Immediate（v0.3 收尾）

1. **用户文档更新**（中/英）✅ 已完成
   - `docs/zh-CN/user-guide.md`: 新增 Card Quality、Related Cards、Local Graph Preview、Wiki Quality、Source Location 章节
   - `docs/en/user-guide.md`: 同上（英文）
   - `docs/implementation-notes/`: 新增 M3/M5/M6 实现笔记

2. **Wiki Related Sections**（spec §4.5 遗留）→ 移入 v0.4
   - i18n key `wiki.related_sections` 已添加但未使用
   - 需要后端 `WikiSectionView.related_sections` 字段 + 前端展示
   - 作为 v0.4 Knowledge Relationship Experience 的 Wiki Related Sections 单元实现

### v0.4 方向（已确定）

**v0.4 — Knowledge Relationship Experience**

目标：把 MindForge 从"知识卡片库"升级为"个人知识关系工作台"。

v0.4 范围（用户已确认）：

- Wiki Related Sections
- Card Relationship Panel 增强
- Source Trail / Provenance Trail
- Local Graph Lite：deterministic 1-hop relationship only
- Knowledge Health：orphan cards / low-quality cards / no-source cards / duplicate/conflict hints
- Relationship tests and browser smoke

v0.4 边界：
- 不做 RAG / embedding / vector DB
- 不做 full graph 大屏
- 不调用真实 LLM
- 不处理真实私人资料
- 不写真实 Obsidian vault
- 不做 mail storage
- 不改变 approval / human_approved 安全语义
- 测试是支撑，不是主创新方向

## 推荐下一步

v0.3 收尾完成。下一阶段：编写 v0.4 Knowledge Relationship Experience spec → 自审 → 实现第一批最小闭环。
