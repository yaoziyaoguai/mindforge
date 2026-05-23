---
title: MindForge v0.3 M1 — Card Quality Integration Spec
type: feat
status: spec
date: 2026-05-24
roadmap: V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP
---

# M1: Card Quality Integration

## 1. Background

v0.3 M1 Card Quality 的 rubric 评分、警告检测、卡片分类、建议生成模块已存在（`src/mindforge/quality/`），但处于独立库状态 — 未集成到卡片 pipeline、未持久化到 frontmatter、未在 Web UI 展示。

本 spec 定义的是**集成工作**，不是重写 quality 模块。核心目标：让 quality metadata 从 pipeline 流向 frontmatter 流向 Web UI。

## 2. Goals

1. Card quality scoring 集成到卡片生成/审批 pipeline
2. Quality metadata 持久化到 card frontmatter
3. `CardSummary` 暴露 quality 字段（用于 Web API）
4. Web Card detail / Drafts 页面展示 quality score + warnings
5. 确定性 golden quality test
6. 不引入 LLM、embedding、新依赖

## 3. Non-Goals

- 不重写 quality rubric 算法（已存在且可测试）
- 不自动 approve/reject（保留 human_approved 语义）
- 不做 embedding-based quality
- 不修改 Wiki rebuild 逻辑
- 不做 card regeneration 自动化（仅展示建议）
- 不新增 npm/Python 依赖

## 4. Design Decisions

### 4.1 Quality 计算时机

在 `process_one_result()` 中，card body 写入后、frontmatter 最终写入前，调用 `score_quality()`。此时 body 和 metadata 都已完成，quality 评分所需信息齐全。

备选：在 `CardWriter.write()` 中计算。否决 — writer 只管 IO，不应混入业务逻辑。

### 4.2 Quality 持久化格式

Quality metadata 写入 card frontmatter 为嵌套 YAML：

```yaml
quality:
  overall_score: 72
  overall_level: medium   # high | medium | low
  card_type: insight
  dimensions:
    completeness: 3      # 0-5
    structure: 4
    specificity: 3
    source_citation: 4
    consistency: 3
  warnings:
    - code: vague_language
      severity: low
      message: "检测到模糊表述 (显著, 可能)"
  regenerate_suggestion: null
  split_candidate: false
  merge_candidate: false
```

### 4.3 CardSummary 扩展

`CardSummary` dataclass 新增两个可选字段：

```python
quality_score: int | None = None       # 0-100
quality_level: str | None = None       # "high" | "medium" | "low"
```

`CardSummary` 是 frozen dataclass — 通过 `from_frontmatter()` 解析时填充。

### 4.4 Web 展示

- **Card detail (Library)**: 在 metadata 区域新增 "Quality" badge
  - High (≥70): 绿色 badge "高质量"
  - Medium (40-69): 琥珀色 badge "中等质量"
  - Low (<40): 红色 badge "待改进"
- **Drafts/Review**: 在 draft card 列表中展示 quality score + 主要 warning
- **Quality Detail**: 点击 badge 展开 dimension breakdown + warnings list

### 4.5 向后兼容

- 已有卡片（无 `quality` frontmatter 字段）：`quality_score` 和 `quality_level` 为 `None`，Web 不展示 quality badge
- Quality 缺失时不报错、不阻塞 pipeline
- `score_quality()` 调用包裹在 try/except 中，quality 计算失败不影响卡片生成主线

## 5. Implementation Units

### U1. Quality Frontmatter Serialization

**Goal:** Card writer 在写入时计算并存储 quality metadata

**Files:**
- Modify: `src/mindforge/process_executor.py`（在 `process_one_result()` 中调用 quality scoring）
- Modify: `src/mindforge/assets/templates/knowledge_card.md.j2`（添加 quality frontmatter 块）
- Modify: `src/mindforge/card_envelope.py`（可选：在 normalize 阶段附上 quality）

**Approach:**
- 在 `process_one_result()` 的 `writer.write()` 调用前，构造 `CardQuality` 所需输入（title + full body text）
- 调用 `score_quality(title, body)` → 得到 `CardQuality`
- 将 quality 数据注入 card_payload → 模板渲染
- try/except 包裹，失败时 log warning 但不阻塞

**Verification:**
- 新生成的 ai_draft 卡片 frontmatter 含 `quality:` 块
- quality scoring 失败时卡片仍正常生成（无 quality 字段）
- 已有卡片不受影响

**Test scenarios:**
- Happy path: `score_quality()` 返回完整 quality metadata → 渲染到 frontmatter
- Edge case: 极短 body → 触发 `too_short` warning → frontmatter 含 warning
- Error path: `score_quality()` 抛异常 → frontmatter 无 quality 字段，卡片正常生成

---

### U2. CardSummary Quality Fields

**Goal:** `CardSummary.from_frontmatter()` 解析 quality frontmatter

**Files:**
- Modify: `src/mindforge/cards.py`（`CardSummary` dataclass + `from_frontmatter()` 解析逻辑）

**Approach:**
- `CardSummary` 新增 `quality_score: int | None = None`、`quality_level: str | None = None`
- `from_frontmatter()` 中解析嵌套 `quality:` YAML 块 → 提取 `overall_score` 和 `overall_level`
- 无 `quality` 字段时保持 `None`（向后兼容）

**Verification:**
- 有 quality frontmatter 的卡片 → `CardSummary.quality_score` 非 None
- 无 quality frontmatter 的旧卡片 → `CardSummary.quality_score` 为 None

---

### U3. Web API Quality Exposure

**Goal:** Library/Drafts API 响应中暴露 quality 数据

**Files:**
- Modify: `src/mindforge/web/routes/library.py`（card detail 响应）
- Modify: `web/src/api/types.ts`（TypeScript 类型）
- Possibly modify: `web/src/api/library.ts`

**Approach:**
- Library card detail endpoint 在 response 中附加 `quality_score` 和 `quality_level`
- Drafts list endpoint 同样附加 quality 字段
- TypeScript 类型同步更新

**Verification:**
- Library API 响应含 `quality_score` / `quality_level` 字段
- TypeScript 编译无错误

---

### U4. Web Quality Display

**Goal:** Web UI 展示卡片质量 score + warnings

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx`（metadata 区域加 quality badge）
- Modify: `web/src/lib/i18n.ts`（新 i18n keys）
- Modify: `web/src/lib/utils.ts`（quality 相关的 display helper）
- Modify: `tests/test_web_product_copy.py`（i18n key 回归）

**Approach:**
- 在 CardWorkspace 的 metadata 区域新增 quality badge
- Badge 点击展开 dimension breakdown + warnings list
- 新增 i18n keys: `card.quality_high`, `card.quality_medium`, `card.quality_low`, `card.quality_score`, `card.quality_dimensions`, `card.quality_warnings`
- Drafts 页面的 draft card 列表中展示简版 quality indicator

**Verification:**
- 有 quality 数据的卡片展示 badge
- 无 quality 数据的旧卡片不展示 badge
- zh/en 切换正确
- i18n contract tests 通过

---

### U5. Golden Quality Tests

**Goal:** 验证 quality rubric 在 golden cards 上的确定性评分

**Files:**
- Create: `tests/test_card_quality.py`

**Approach:**
- 构造已知好/坏/中等的 synthetic card body
- 断言 `score_quality()` 返回的 `overall_level` 和关键 warnings
- 覆盖 7 种 card type 分类
- 覆盖 5 个 rubric 维度
- 覆盖 5 种 warning 检测

**Verification:**
- 好卡片 → HIGH
- 坏卡片（极短、缺 section、模糊表述）→ LOW
- 中等卡片 → MEDIUM

---

## 6. Dependencies

- U1 → U2 → U3 → U4 (pipeline → data model → API → Web)
- U5 可与 U1 并行（测试 quality 模块本身）

## 7. Gate Requirements

- `ruff check src tests` exit 0
- `pytest tests/test_card_quality.py -q` 全部通过
- `./scripts/check.sh` 或 `pytest -q` 全部通过
- `npm --prefix web run build` exit 0
- `python -m pytest tests/test_web_product_copy.py -q` 全部通过
- `git diff --check` exit 0

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Quality scoring 在 pipeline 中增加延迟 | rubric 是纯规则计算（无 LLM），~5ms per card |
| Quality 字段增加 frontmatter 体积 | ~15 行 YAML，可接受 |
| 已有卡片无 quality 向后兼容 | quality_score/level 为 Optional，Web 条件渲染 |
