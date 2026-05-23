# M1 Card Quality Integration — Implementation Notes

**Date:** 2026-05-24
**Spec:** `docs/specs/2026-05-24-007-m1-card-quality-integration-spec.md`
**Status:** implemented

## 已完成内容

M1 Card Quality 将已有的 `src/mindforge/quality/` rubric 模块集成到卡片 pipeline → frontmatter → Web API → Web UI。

### U1 — Quality Frontmatter Serialization
- `process_executor.py`: 新增 `_compute_quality_for_card()` → 在 `process_one_result()` 中 `writer.write()` 之前调用，提取 card_payload 中的 title/body 部件、构造近似 body、调用 `score_quality()` / `classify_card_type()` / `detect_warnings()` / `generate_suggestions()`；try/except 包裹，失败不阻塞主线
- `writer.py`: `write()` 新增 `quality: dict | None` 参数，透传给 `template.render()`
- `knowledge_card.md.j2`: 新增 `{% if quality %}` 条件块，渲染 nested YAML `quality:` frontmatter（overall_score, overall_level, card_type, dimensions, warnings, suggestions）

### U2 — CardSummary Quality Fields
- `cards.py`: `CardSummary` 新增 `quality_score: int | None` 和 `quality_level: str | None`，新增 `_quality_field()` 从 nested quality frontmatter 提取值

### U3 — Web API Quality Exposure
- `schemas.py`: `LibraryCardResponse` 新增 `quality_score` / `quality_level` 可选字段
- `web_facade.py`: `_library_card_response()` 和 `_library_card_summary_response()`  populate quality 字段
- `types.ts`: `LibraryCardResponse` 新增 `quality_score?: number | null` / `quality_level?: string | null`

### U4 — Web Quality Display
- `CardWorkspace.tsx`: header metadata 区新增 inline quality badge（绿/琥珀/红），仅当 quality_score 非 null 时展示
- `i18n.ts`: zh/en 均新增 `card.quality_high` / `card.quality_medium` / `card.quality_low` / `card.quality_score`

### U5 — Golden Quality Tests
- `tests/test_card_quality.py` (27 tests): 覆盖 high/medium/low synthetic cards 评分、确定性、card type 分类、warning 检测、5 维度存在性、CardSummary 质量字段解析

## 修改文件

| 文件 | 变更 |
|------|------|
| `src/mindforge/process_executor.py` | +125 行 quality 计算集成 |
| `src/mindforge/cards.py` | +13 行 quality 字段解析 |
| `src/mindforge/writer.py` | +2 行 quality 参数透传 |
| `src/mindforge/assets/templates/knowledge_card.md.j2` | +24 行 quality YAML 块 |
| `src/mindforge_web/schemas.py` | +3 行 quality 字段 |
| `src/mindforge_web/services/web_facade.py` | +5 行 quality 字段 populate |
| `web/src/api/types.ts` | +2 行 TypeScript 类型 |
| `web/src/components/CardWorkspace.tsx` | +16 行 quality badge + helper |
| `web/src/lib/i18n.ts` | +8 行 i18n keys |
| `docs/specs/2026-05-24-007-m1-card-quality-integration-spec.md` | new |
| `tests/test_card_quality.py` | new (27 tests) |

## Gate 验证

| Gate | Result |
|------|--------|
| `python -m pytest tests/test_card_quality.py -q` | 27/27 pass |
| `python -m pytest tests/test_web_product_copy.py -q` | 50/50 pass |
| `npm --prefix web run build` | exit 0 (tsc + vite build) |
| `git diff --check` | exit 0 |
| `ruff check` (changed files only) | All checks passed |
| Full test suite (`pytest tests/ -q`) | 1 pre-existing failure (see below) |

## Pre-existing Test Failure

`tests/test_web_api.py::test_sources_page_uses_source_path_view_not_raw_path_for_display_or_copy` — fails on clean tree (verified via `git stash` + run test + `git stash pop`). This test checks for `?? source.path` pattern in `SourcesPage.tsx`; the current source contains a `display_path ?? source.path ?? "-"` fallback. This failure is **unrelated to M1 changes** and should be fixed separately.

## 未完成内容（不在 M1 scope）

- Drafts 页面 quality 展示（DraftSummary 未加 quality 字段 — 可按需扩展）
- QualityPanel 改用 stored frontmatter quality 而非每次 re-compute（当前 QualityPanel 仍调 `/api/quality/cards/{card_id}` 做动态评分）
- 自动化 card regenerate（仅展示建议）

## Handoff: 不要继续下一阶段

**ctx < 15%** — 当前会话上下文已严重不足，不能继续 v0.3 M2/M3/M4 工作。

新会话应以 `/mf-autopilot` 启动，按 `docs/plans/` 中的 roadmap 继续 v0.3 下一 milestone。
v0.3 roadmap 顺序: M1 Card Quality → M4 Source Location → M2 Wiki Quality → M3 Related Cards → M5 Knowledge Health → M6 Local Graph Preview。

## 设计决策记录

- **Quality 计算位置**: 在 `process_one_result()` 中，`writer.write()` 之前。不在 writer 中计算（writer 只管 IO）。
- **Quality 持久化格式**: nested YAML `quality:` frontmatter 块（非 flat fields）— 便于将来扩展维度
- **向后兼容**: quality 字段均为 Optional，旧卡片不展示 badge
- **确定性**: rubric 是纯规则计算（无 LLM），同一输入始终相同 score
