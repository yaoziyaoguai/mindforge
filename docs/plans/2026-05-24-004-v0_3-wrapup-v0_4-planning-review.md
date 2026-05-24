---
title: v0.3 收尾 & v0.4 方向规划评审
type: docs
status: draft
date: 2026-05-24
---

## v0.3 完成状态

v0.3 六项 Milestone + Milestone H 打磨全部完成：

| Milestone | 状态 | 测试 |
|-----------|------|------|
| M1 Card Quality | 已实现 | 22 tests pass |
| M2 Wiki Quality | 已实现 | 22 tests pass |
| M3 Related Cards | 已实现 | 13 tests pass |
| M4 Source Location | 已实现 | 集成到模板 |
| M5 Knowledge Health | 已实现 | 19 tests pass |
| M6 Local Graph Preview | 已实现 | 30 tests pass |
| H1-H4 Web Polish | 已实现 | 浏览器 smoke 通过 |

## v0.3 Release Criteria 检查

| # | 条件 | 状态 |
|---|------|------|
| 1 | M1-M6 done criteria 达标 | ✓ |
| 2 | 不破坏 v0.2 行为 | ✓ |
| 3 | 新功能 ≥ 80% 测试覆盖 | ✓ |
| 4 | 每个 milestone dogfood 通过 | ✓ |
| 5 | ruff clean + tsc clean | ✓ |
| 6 | CI green | 待验证 |
| 7 | 用户文档更新（中/英） | 未完成 |

## 待完成事项

### Immediate（v0.3 收尾）

1. **用户文档更新**（中/英）
   - 新增页面：Card Quality 面板、Wiki Quality Bar、Related Cards、Local Graph Preview
   - 新增功能：Source Location 来源追溯、Knowledge Health 健康报告
   - 范围：`docs/zh-CN/` 和 `docs/en/` 下现有文件更新 + 可能需要 1-2 新文件
   - 估计：~200 LOC markdown

2. **Wiki Related Sections**（spec §4.5 遗留）
   - i18n key `wiki.related_sections` 已添加但未使用
   - 需要后端 `WikiSectionView.related_sections` 字段 + 前端展示
   - 估计：~50 LOC backend + ~30 LOC frontend

### v0.4 Candidates（按优先级）

| 方向 | 描述 | Effort |
|------|------|--------|
| A. 测试基础设施 | vitest + testing-library 搭建前端测试 | 中 |
| B. 全文搜索增强 | BM25 → 混合搜索（不引入 embedding） | 中 |
| C. 新 Ingestion Format | EPUB/MOBI/RSS/YouTube transcripts | 大 |
| D. 知识图谱全页 | 替代当前的 1-hop preview，做完整可探索的 local graph 页面 | 大 |
| E. Plugin/Hook System | 用户自定义 strategy/hook | 大 |

## 推荐下一步

**推荐：先完成 v0.3 收尾（用户文档 + Wiki Related Sections），再进入 v0.4 规划。**

理由：
- 用户文档是 v0.3 release criteria 最后一条未完成项
- Wiki Related Sections 是 spec 明确描述但未实现的功能（backlog，非新功能）
- v0.4 方向选择需要用户对产品方向做出判断
