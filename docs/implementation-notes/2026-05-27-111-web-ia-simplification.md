# Web IA Simplification — Implementation Notes

**Date**: 2026-05-27
**Branch**: main
**Commits**: `54110d4`, `f0427e7`

## Audit Document

Browser-driven accessibility snapshot audit of all 11 reachable MindForge Web pages.

## Pages Audited

| Page | Method | Status |
|------|--------|--------|
| Home | Chrome MCP snapshot | Clean — P2: "note-b" internal source name (backend data) |
| Setup | Chrome MCP snapshot | FIXED: `__model_routing__` → "按阶段路由" |
| Sources | Chrome MCP snapshot (prior session) | FIXED: progressive disclosure |
| Drafts | Chrome MCP snapshot | Clean — good empty state |
| Library | Chrome MCP snapshot (prior session) | FIXED: friendlyTrack, source labels, filter dropdowns |
| Card Workspace | Chrome MCP snapshot (prior session) | FIXED: enum labels, track/source display |
| Recall | Chrome MCP snapshot | FIXED: BM25 jargon → "关键词搜索" |
| Wiki | Chrome MCP snapshot | FIXED: timestamp formatting, friendlyTrack in ref cards |
| Dogfood | Chrome MCP snapshot | FIXED: timestamp formatting |
| Export | Chrome MCP snapshot | NOT A STANDALONE PAGE — falls through to Home. No route in App.tsx. Requires product decision. |
| Graph | Chrome MCP snapshot | FIXED: breadcrumb "graph" → "知识图谱" |
| Sensemaking | Chrome MCP snapshot | FIXED: breadcrumb "sensemaking" → "知识理解" |
| Health | Chrome MCP snapshot | Backend-generated English text, can't fix from frontend |
| Trash | Chrome MCP snapshot | Clean — good empty state |

## Changes Made

### Loop 1 (Session 1, commit `3a83078`)
- P0 fix: React Hooks ordering crash in GraphNavigationPanel (useMemo before early return)
- Missing i18n keys for graph grouping ("按关系类型", "按知识社区")

### Loop 2 (Session 1, commit `54110d4`)
- `friendlyTrack()`: map "unrouted" → "未分类"/"Unrouted"
- `friendlyProviderName()`: map `__model_routing__` → "按阶段路由"/"Per-stage routing"
- `sourceTypeLabels` + `sourceTypeIcons`: add Cubox entry
- Remove "track:", "source:", "approved:" English prefixes from card badges
- Fix filter dropdowns to use friendly labels

### Loop 3 (Session 2, commit `f0427e7`)
- WikiStatusBar: raw ISO timestamp → `toLocaleString()` formatted
- WikiReferenceCard: `ref.track` → `friendlyTrack(ref.track, locale)`
- Breadcrumb: add `/graph` ("知识图谱") and `/sensemaking` ("知识理解") route labels
- BM25 jargon removal across all i18n strings (zh + en):
  - `home.onboarding.step4_desc`: "BM25 词法匹配" → "关键词搜索"
  - `drafts.why_review`: same
  - `recall.subtitle`: "基于 BM25 词法匹配算法…" → "支持关键词搜索，结果按相关度排序"
  - `recall.empty_prompt_desc`: "BM25 根据词频匹配" → removed
  - `recall.empty_no_results_desc`: "当前使用 BM25 词法匹配，非语义检索" → removed
  - `recall.explain_lexical_boundary`: "BM25 词法检索根据关键词精确匹配，不进行语义理解或向量搜索" → "关键词搜索根据输入词语进行精确匹配"

## Known Remaining Issues (Not Fixable from Frontend)

1. **Backend-generated English text**: Health page summaries, wiki body metadata (Provenance, Source card, Card path, Strategy, Value score, Action Items), graph evidence sha1 hashes, local graph preview text
2. **Backend internal data in markdown**: `__model_routing__` in card body comments, workflow stage IDs (triage, distill, etc.)
3. **Export page**: No standalone route — falls through to Home. Requires product/architecture decision.
4. **"note-b" source name**: Backend data (source_title) — no generic mapping possible from frontend
5. **Raw timestamps in wiki body**: "Last rebuilt: 2026-05-08T21:55:23+0800" — backend-generated markdown
6. **Dogfood file path exposure**: Search index path shown in dogfood report — backend data

## Files Changed

```
web/src/components/Breadcrumb.tsx
web/src/components/wiki/WikiReferenceCard.tsx
web/src/components/wiki/WikiStatusBar.tsx
web/src/lib/i18n.ts
web/src/lib/utils.ts
web/src/pages/DogfoodPage.tsx
web/src/pages/SetupPage.tsx
```

## Gate Results

| Gate | Command | Exit Code | Timeout |
|------|---------|-----------|---------|
| git diff --check | `git diff --check` | 0 | No |
| Frontend build | `npm --prefix web run build` | 0 | No |
| Product copy tests | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | No |

## Deferred Items

- Priority 3: Stage 6 Design QA residual fixes (visual consistency, responsive, accessibility)
- Priority 4: Documentation debt closure
- Backend English text fixes (requires backend changes, separate loop)
- Export page implementation (requires product decision + spec)

## Safety

- No backend/API semantics changed
- No approval semantics changed
- No real LLM/Cubox/Upstage called
- No private data processed
- No Obsidian vault written
- No RAG/embedding/vector DB introduced
- No new dependencies added
