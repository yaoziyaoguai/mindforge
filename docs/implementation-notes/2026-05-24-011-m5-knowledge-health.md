# M5 Knowledge Health — Implementation Notes

**Date:** 2026-05-24
**Spec:** ~~`docs/design/roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md`~~ (removed 2026-05-27) §9
**Status:** implemented (squash-merged into main via PR #7, commit `9e813d2`)

## 合并说明

M5 与 M3、M6 在 `feat-wiki-llm-synthesis` 分支上一起实现，通过 squash merge (PR #7) 进入 main。M5 的健康检查复用了 M3 的关系计算和卡片索引结构，放在同一分支上实现保证了 API 一致性。

## 已完成内容

M5 实现了确定性 Knowledge Health Report 系统。所有检查只读，不自动修改卡片，不调用 LLM/API。

`src/mindforge/health/health_service.py` (376 lines) 提供 7 种健康检查：

| 检查项 | Code | Severity | 触发条件 |
|--------|------|----------|---------|
| Review Backlog | `review_backlog` | WARN | ≥3 pending drafts |
| Pending Drafts | `pending_drafts` | INFO | 1-2 pending drafts |
| Missing Provenance | `missing_provenance` | WARN | approved card 缺少 source_id/path/type/adapter |
| Low Quality | `low_quality` | CRITICAL/WARN | quality_level=low 的 approved card（≥5 → CRITICAL） |
| Orphans | `orphans` | CRITICAL/WARN | 无 Wiki 引用且无 related cards（>20% → CRITICAL） |
| Duplicates | `duplicates` | INFO | title Jaccard overlap ≥ 0.5 |
| Wiki Stale | `wiki_stale` | WARN | Wiki 缺少 approved cards 或需要重建 |
| Source Warnings | `source_warnings` | INFO | 有 failed/skipped source import 记录 |

### 关键设计决策

- **只读诊断**: `compute_health_report()` 不修改任何卡片，不执行 mutation，不调用外部 API
- **Orphans 条件**: 同时检查 Wiki 引用和 related cards 数量，避免把仅在 Wiki 中引用的卡片标记为 orphan
- **Duplicate 检测**: 使用简单的 title Jaccard token overlap（≥0.5），不做 fuzzy matching
- **真实数据集成**: `build_knowledge_health_report()` 从 MindForge config/vault 读取真实 cards/wiki/state 构建报告
- **Severity 阈值**: ≥5 low-quality cards → CRITICAL；>20% orphans → CRITICAL；其余为 WARN 或 INFO

## 修改文件

| 文件 | 变更 |
|------|------|
| `src/mindforge/health/health_service.py` | new (376 lines) |
| `src/mindforge/health/__init__.py` | new |
| `tests/health/test_health_service.py` | new (16 tests) |

## Gate 验证

| Gate | Result |
|------|--------|
| `ruff check src/` | All checks passed |
| `python -m pytest tests/health/test_health_service.py -q` | 16/16 pass |
| `git diff --check` | exit 0 |
