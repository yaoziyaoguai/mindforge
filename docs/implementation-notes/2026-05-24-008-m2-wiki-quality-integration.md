# M2 Wiki Quality Integration — Implementation Notes

**Date:** 2026-05-24
**Spec:** `docs/specs/2026-05-24-008-m2-wiki-quality-integration-spec.md`
**Status:** implemented

## 已完成内容

M2 Wiki Quality 将已有的 `src/mindforge/wiki/wiki_quality.py` 计算模块集成到 Wiki rebuild 流程 → API → Web UI。

### U1 — Quality Report 生成集成
- `wiki_quality.py`: 新增 `compute_knowledge_gaps()` 确定性知识缺口检测
- `wiki_service.py`: 新增 `_generate_quality_report_appendix()` → 解析 WIKI_SECTION_START 标记提取 used card IDs → 计算 coverage/faithfulness/staleness/gaps → 生成 markdown appendix + 嵌入式 JSON
- `rebuild_main_wiki()`: 写入前追加 quality appendix
- `llm_rebuild_wiki()`: 写入前追加 quality appendix（保存 approved_cards 列表用于计算）

### U2 — Quality API
- `routers/wiki.py`: 新增 `GET /api/wiki/quality` — 从 WIKI_QUALITY_JSON comment 解析结构化数据
- `wiki.ts`: 新增 TypeScript 类型（WikiQualityCoverage, WikiQualityResponse 等）

### U3 — Web Quality Display
- `WikiPage.tsx`: 加载时并行 fetch quality 数据，底部展示 quality bar（覆盖率、忠实度、未引用卡片、过期章节、知识缺口 badge）
- `i18n.ts`: zh/en 新增 7 个 quality 相关 key

### U4 — Golden Quality Tests
- `test_wiki_quality.py` (22 tests): 覆盖 coverage、faithfulness、staleness、knowledge gaps、appendix 生成、JSON 结构、确定性

## 修改文件

| 文件 | 变更 |
|------|------|
| `src/mindforge/wiki/wiki_quality.py` | +39 行 compute_knowledge_gaps() |
| `src/mindforge/wiki_service.py` | +199 行 quality appendix 生成 + 集成 |
| `src/mindforge_web/routers/wiki.py` | +28 行 quality endpoint |
| `web/src/api/wiki.ts` | +32 行 TypeScript 类型 |
| `web/src/lib/i18n.ts` | +14 行 i18n keys |
| `web/src/pages/WikiPage.tsx` | +42 行 quality bar |
| `docs/specs/2026-05-24-008-m2-wiki-quality-integration-spec.md` | new |
| `tests/test_wiki_quality.py` | new (22 tests) |

## Gate 验证

| Gate | Result |
|------|--------|
| `ruff check src/` | All checks passed |
| `npm --prefix web run build` | exit 0 |
| `python -m pytest tests/test_wiki_quality.py -q` | 22/22 pass |
| `python -m pytest tests/test_web_product_copy.py -q` | 50/50 pass |
| `git diff --check` | exit 0 |
| Full test suite | 372/373 pass (1 pre-existing failure) |

## 设计决策记录

- **Quality report 存储位置**: Wiki markdown 末尾 appendix section + 嵌入式 JSON comment（非单独文件）——用户可在阅读 Wiki 时直接看到质量摘要，API 可从 JSON 解析结构化数据
- **Faithfulness 计算**: Jaccard similarity of key terms（确定性，无 LLM）——阈值 0.3 以下标记 issue
- **Knowledge gaps**: 基于 topic_keywords 的简单关键词匹配（从 section→card tags/titles 推导）
- **向后兼容**: 无 quality appendix 的旧 Wiki → API 返回 exists: false → Web 不展示 quality bar

## 未完成内容（不在 M2 scope）

- Dedup suggestions 计算（wiki_quality.py 有字段无函数）
- Conflicting claims 集成到 rebuild 流程（检测函数已存在，未接入 appendix 生成）
- Quality trend over time（需多次 rebuild 历史对比）
- Real-time quality check（当前只在 rebuild 时计算）
