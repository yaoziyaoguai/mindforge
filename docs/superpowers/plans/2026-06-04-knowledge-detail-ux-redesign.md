# Knowledge Detail UX Redesign — Implementation Plan

> **Goal:** Restructure CardWorkspace.tsx to present knowledge cards in a 4-layer information hierarchy so users can understand "what this knowledge is" without being overwhelmed by internal processing detail.

**Tech Stack:** React 18, TypeScript, Vite, vitest + @testing-library/react

---

### Task 1: Update i18n Strings

**Files:**
- Modify: `web/src/lib/i18n.ts`

**Changes:**
- `graph.title`: "知识图谱" → "相关知识"
- `graph.related_by_source`: "同源" → "来自同一来源"
- `graph.shares_tag`: "同标签" → "共享标签"
- `graph.related_by_wiki_section`: "同 Wiki 章节" → "同属章节"
- `library.related_group_same_source`: "同源" → "来自同一来源"
- `library.related_group_same_tag`: "同标签" → "共享标签"
- `library.related_group_same_wiki_section`: "同 Wiki 章节" → "同属 Wiki 章节"
- `library.related_group_same_review_batch`: "同批次" → "同批次审阅"
- `library.related_group_source_location_neighbor`: "源位置相邻" → "来源位置相近"
- `wiki.local_graph_preview`: "局部图谱预览" → "局部关系预览"
- `local_graph.title`: "局部关系预览" (keep)
- `graph.no_relationships`: Update to friendlier text
- Add new keys: `card.understanding_sections`, `card.processing_sections`, `card.key_points`, `card.no_key_points`, `card.related_knowledge`

### Task 2: Add KnowledgeHero Component

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx` (add KnowledgeHero function)

**Changes:**
- Add `KnowledgeHero` component inside CardWorkspace.tsx (keeps file count low, same domain)
- Renders: title, status badge, one-sentence summary, tags, source info, human note preview
- Summary: reuse `stripMarkdown(body).slice(0, 150)` logic
- Key points: extract from `## Key Points / 核心要点` section if present

### Task 3: Refactor CardSections → KnowledgeSections

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx` (replace CardSections)

**Changes:**
- Group sections into "understanding" (AI Summary, Human Note, Key Points) and "processing" (Source Excerpt, AI Inference, Reusable Prompts, Principles)
- Each group is a collapsible panel, default collapsed
- All sections preserved, just grouped

### Task 4: Merge Graph + Related → RelatedKnowledgePanel

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx` (restructure)
- Modify: `web/src/components/GraphNavigationPanel.tsx` (update i18n references)
- Modify: `web/src/components/LocalGraphPreview.tsx` (update i18n references)

**Changes:**
- CardWorkspace: combine GraphNavigationPanel + RelatedCardsPanel under single "相关知识" section
- GraphNavigationPanel: `t("graph.title")` now returns "相关知识"
- LocalGraphPreview: i18n key already updated
- Relation reasons now show human-readable text from updated i18n keys

### Task 5: Ensure Technical Fields Hidden

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx`

**Changes:**
- Verify source_content_hash, run_id, strategy_id, prompt_versions, stage_models all inside `<details>` (already done)
- Add raw relation evidence to tech details if exposed elsewhere
- Verify no raw fields in default-visible areas

### Task 6: Update CardWorkspace Rendering Order

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx`

**New rendering order:**
1. Header (title, status, track, source) — unchanged
2. KnowledgeHero — new Layer 1
3. KnowledgeSections — refactored Layer 2 (collapsible groups)
4. RelatedKnowledgePanel — Layer 3 (merged graph + related)
5. ProvenanceTrail — keep as is
6. Source/History — keep as is
7. TechnicalEvidence — Layer 4 (extended `<details>`)

### Task 7: Update Documentation

**Files:**
- Modify: `docs/zh-CN/web-wiki.md`

**Changes:**
- Update description of knowledge detail page
- Remove references to "知识图谱", use "相关知识"

### Task 8: Test

- `cd web && npm test` (vitest)
- `cd web && npm run build`
- `cd web && npm run lint` (if exists)
- `python -m pytest tests/test_api_topics.py tests/test_topic_presenter.py -q`
- `git diff --check`
- `rg "知识图谱|Same tag|Same source|sha1" web/src`

### Risk: None. All changes are frontend-only, no backend semantics changed.
