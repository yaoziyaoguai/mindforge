---
title: MindForge v0.3 M2 — Wiki Quality Integration Spec
type: feat
status: spec
date: 2026-05-24
roadmap: V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP
---

# M2: Wiki Quality Integration

## 1. Background

v0.3 M2 Wiki Quality 的计算模块（`src/mindforge/wiki/wiki_quality.py`）已存在，提供 coverage、faithfulness、staleness、conflicting claims 等确定性计算函数，但处于独立未集成状态——未在 rebuild 流程中调用、未通过 API 暴露、未在 Web UI 展示。

本 spec 定义的是**集成工作**：将 wiki_quality 计算接入 rebuild flow → 持久化 → API → Web UI。

## 2. Goals

1. Wiki rebuild 后自动生成质量报告
2. 质量报告持久化到 Wiki 文件末尾（appendix section）
3. Web API 暴露 quality report 数据
4. Web Wiki 页面展示 quality overview
5. 确定性 golden quality test
6. 不引入 LLM、embedding、新依赖

## 3. Non-Goals

- 不重写 wiki quality 算法（已存在且可测试）
- 不自动 rebuild Wiki
- 不做 LLM-based quality analysis
- 不做 real-time conflict detection（只在 rebuild 时计算）
- 不修改 human_approved 卡片
- 不新增 npm/Python 依赖

## 4. Design Decisions

### 4.1 Quality 计算时机

在 `rebuild_main_wiki()` / `llm_rebuild_wiki()` 返回前调用 wiki_quality 计算函数，生成 `WikiQualityReport`。quality report 作为 Wiki markdown 的 appendix section 写入 Wiki 文件末尾。

备选：单独文件存储。否决——与 Wiki 文件耦合的 report 更易发现和维护。

### 4.2 Quality Report 存储格式

Quality report 作为 Wiki markdown 的最后一个 section：

```markdown
## Wiki Quality Report

<!-- WIKI_QUALITY_REPORT_START -->
- **Coverage**: 8/10 approved cards used (80%)
- **Unused cards**: card-1, card-2
- **Faithfulness**: avg 0.78
- **Stale sections**: Section A (new related card detected)
- **Knowledge gaps**: 2 topics missing coverage
<!-- WIKI_QUALITY_REPORT_END -->
```

同时，quality data 以 JSON 形式存储在 `<!-- WIKI_QUALITY_JSON ... -->` comment 中，供 API 解析。

备选：只存 JSON。否决——用户需要在阅读 Wiki 时直接看到质量摘要。

### 4.3 API 设计

扩展现有 `/api/wiki/status` 或新增 `/api/wiki/quality` endpoint，返回结构化 quality data：

```json
{
  "exists": true,
  "coverage": { "used": 8, "unused": 2, "total": 10, "rate": 0.8 },
  "unused_cards": [{"id": "...", "title": "...", "reason": "..."}],
  "faithfulness": { "average": 0.78, "by_section": {"Section A": 0.85, ...} },
  "stale_sections": ["Section A"],
  "knowledge_gaps": ["topic 1", "topic 2"],
  "conflicting_claims": [{"card_a": "...", "card_b": "...", "topic": "..."}],
  "last_checked_at": "2026-05-24T..."
}
```

### 4.4 Web 展示

- WikiPage 底部新增 quality overview bar（覆盖率百分比 + 警告数）
- 点击展开详细 quality report
- stale section 在 TOC 中标记 amber dot
- 无 quality report 时（旧 Wiki）不展示

### 4.5 向后兼容

- 已有 Wiki（无 quality report appendix）：API 返回 `exists: false`，Web 不展示
- 确定性 rebuild 生成 quality report，LLM rebuild 同样生成
- Quality report 缺失时不报错

## 5. Implementation Units

### U1. Quality Report 生成集成

**Goal:** rebuild 流程中调用 wiki_quality 函数生成质量报告

**Files:**
- Modify: `src/mindforge/wiki_service.py`（在 rebuild 后调用 quality 计算）
- Modify: `src/mindforge/wiki/wiki_quality.py`（如需要补充函数）

**Approach:**
- 在 `rebuild_main_wiki()` 返回前：收集 used card ids → 计算 coverage、faithfulness、staleness
- 在 `llm_rebuild_wiki()` 返回前：从 LLM output 中收集 used card ids → 计算 coverage、faithfulness、staleness
- 生成 `WikiQualityReport`，序列化为 markdown appendix + JSON comment
- 将 appendix 追加到 Wiki markdown 末尾

**Verification:**
- rebuild 后的 Wiki 文件末尾含 quality report
- quality report 中的数据与实际情况匹配
- 无 approved cards 时 quality report 正确表示 "无数据"

---

### U2. Quality API

**Goal:** 新增 `/api/wiki/quality` endpoint 返回结构化 quality data

**Files:**
- Modify: `src/mindforge_web/routers/wiki.py`（新增 quality endpoint）
- Modify: `src/mindforge_web/schemas.py`（如需要新 schema）
- Modify: `web/src/api/wiki.ts`（前端 API 调用）

**Approach:**
- 从 Wiki markdown 中解析 `<!-- WIKI_QUALITY_JSON ... -->` comment
- 返回结构化 JSON
- 无 quality report 时返回 `{"exists": false}`

**Verification:**
- rebuild 后的 Wiki 可查询到 quality data
- 无 quality report 的 Wiki 返回 exists: false
- TypeScript 编译无错误

---

### U3. Web Quality Display

**Goal:** Wiki 页面展示 quality overview

**Files:**
- Modify: `web/src/pages/WikiPage.tsx`（底部加 quality bar）
- Modify: `web/src/lib/i18n.ts`（新 i18n keys）

**Approach:**
- WikiPage 底部新增 quality overview bar
- 显示 coverage（X/Y cards used）、faithfulness avg、warnings count
- 点击展开详细 breakdown
- 新增 i18n keys: `wiki.quality_coverage`, `wiki.quality_faithfulness`, `wiki.quality_stale`, `wiki.quality_gaps`, `wiki.quality_conflicts`

**Verification:**
- 有 quality report 的 Wiki 展示 quality bar
- 无 quality report 的旧 Wiki 不展示
- zh/en 切换正确

---

### U4. Golden Quality Tests

**Goal:** 验证 wiki quality 计算在 golden fixture 上的确定性

**Files:**
- Create: `tests/test_wiki_quality.py`

**Approach:**
- 构造已知 approved cards + Wiki markdown fixture
- 断言 coverage、faithfulness、staleness 计算结果正确
- 覆盖 edge cases：empty wiki、单 card wiki、全部 unused

**Verification:**
- coverage 计算正确
- faithfulness score 在合理范围
- staleness 检测正确

---

## 6. Dependencies

- U1 → U2 → U3（rebuild → API → Web）
- U4 可与 U1 并行

## 7. Gate Requirements

- `ruff check src tests` exit 0（src 目录）
- `pytest tests/test_wiki_quality.py -q` 全部通过
- `pytest tests/ -q` 全部通过（除已知前置失败）
- `npm --prefix web run build` exit 0
- `python -m pytest tests/test_web_product_copy.py -q` 全部通过
- `git diff --check` exit 0

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Faithfulness 假阳性率高 | 使用 Jaccard similarity 阈值，标记而非阻止 |
| Wiki 文件体积增长 | Quality report appendix ~15 lines，可接受 |
| 已有 Wiki 无 quality report | API 返回 exists: false，Web 条件渲染 |
| 性能退化 | wiki_quality 是确定性规则计算，无 LLM 调用，~10ms |
