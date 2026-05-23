# Web i18n Mixed-language Follow-up Implementation Notes

**Date**: 2026-05-23
**Spec**: `docs/specs/2026-05-23-002-web-i18n-mixed-language-follow-up-spec.md`

## Summary

按 spec 完成全站 i18n 混用修复，覆盖 Setup / Sources / Wiki / Trash / SourceAddPanel 及所有 wiki 子组件。所有用户可见 UI copy 现在通过 `t()` 获取，后端 internal id 通过 display mapping 函数映射为本地化文案。

## Files Modified

| File | Change |
|------|--------|
| `web/src/lib/i18n.ts` | +95 zh keys, +95 en keys; fix ~4 zh values still in English (setup.save/validate/revert/unsaved); add TFunc type export |
| `web/src/lib/utils.ts` | Add workflowStepLabel, strategyStatusLabel, strategyNameLabel, sourceStatusLabel, sourceRunStatusLabel, sourceDueStatusLabel |
| `web/src/pages/SetupPage.tsx` | Replace ~20 hardcoded English strings with t(); use display mapping functions |
| `web/src/pages/SourcesPage.tsx` | Replace ~40 hardcoded English strings; use source display mappings; switch to getFrequencyOptions |
| `web/src/pages/TrashPage.tsx` | Full i18n: import useLocale, replace all ~15 hardcoded strings, use friendlyStatus |
| `web/src/pages/WikiPage.tsx` | Replace hardcoded error/status messages with t() |
| `web/src/components/SourceAddPanel.tsx` | Full i18n: useLocale, getFrequencyOptions(t) replaces static frequencyOptions |
| `web/src/components/wiki/WikiHeader.tsx` | useLocale for title/description |
| `web/src/components/wiki/WikiStatusBar.tsx` | useLocale for all labels, status, buttons |
| `web/src/components/wiki/WikiEmptyState.tsx` | useLocale for 3 empty states |
| `web/src/components/wiki/WikiErrorState.tsx` | useLocale for error title/retry |
| `web/src/components/wiki/WikiLoadingState.tsx` | useLocale for loading title/desc |
| `web/src/components/wiki/WikiAdvancedActions.tsx` | useLocale for troubleshooting |
| `web/src/components/wiki/WikiReadingPane.tsx` | useLocale for section headers |
| `web/src/components/wiki/WikiTOC.tsx` | useLocale for TOC labels, aria-label |
| `web/src/components/wiki/WikiSection.tsx` | useLocale for "Knowledge sources" |
| `web/src/components/wiki/WikiReferenceCard.tsx` | useLocale for "Approved" badge/tooltip |
| `web/src/components/wiki/WikiReferencePanel.tsx` | useLocale for default title |
| `web/src/components/wiki/WikiSectionRelationshipPreview.tsx` | useLocale for graph preview |
| `tests/test_web_product_copy.py` | Add 7 test functions for wiki/trash/source_add keys, useLocale coverage, display mappings; fix zh value assertions |

## What Was Fixed

### Category C1 (Backend data displayed directly)
- Source status codes: now mapped via sourceStatusLabel/sourceRunStatusLabel/sourceDueStatusLabel
- Workflow step IDs: now mapped via workflowStepLabel
- Strategy name/status: now mapped via strategyNameLabel/strategyStatusLabel
- Card previous_status in Trash: now mapped via friendlyStatus

### Category C2 (Frontend hardcoded English)
- SetupPage: "Default model", "Processing workflow", "View prompt", "Model", etc. → t()
- SourcesPage: "Process now", "Edit frequency", "Last run summary", etc. → t()
- TrashPage: all labels, buttons, empty state → t()
- Wiki: all 13 components → t()
- SourceAddPanel: all labels, buttons, hints → t()

### Category C3 (Missing i18n keys)
- +95 zh keys: sources.*, trash.*, wiki.*, source_add.*, shared.yes/no
- +95 corresponding en keys

### Category C4 (Incomplete display mappings)
- workflowStepLabel: triage/distill/link_suggestion/review_questions/action_extraction
- strategyStatusLabel, strategyNameLabel
- sourceStatusLabel, sourceRunStatusLabel, sourceDueStatusLabel
- friendlyStatus already existed from Milestone A

## What Was NOT Fixed (by design)

1. **NextAction backend labels**: Home page "Review drafts 有 ai_draft..." comes from backend `/api/home` `next_actions` data. This is C1 (backend hardcoded data). Per spec, backend API not modified.

2. **Source type labels in WikiReferenceCard**: "Markdown", "Text", "HTML", "PDF", "Word" are adapter format identifiers — proper nouns kept as-is with Chinese comment explaining the boundary.

3. **"API key" stays as "API key"**: Universal technical term, Chinese speakers commonly use it in English. zh value intentionally kept identical to en.

4. **Rebuild status messages** (NOW FIXED in follow-up): WikiPage rebuild results now use i18n template `wiki.rebuild_result` / `wiki.rebuild_server_error`. Warnings appended to the message remain in English as they are technical/debug data.

5. **SafetyBar labels**: "Local only", "Explicit approval required", "Safe local read" — these come from backend and are part of the safety/security contract. Not translated to avoid misrepresenting security posture.

## Test Strategy

Enhanced `tests/test_web_product_copy.py` with:
- `test_i18n_wiki_keys_complete` — verifies all 43 wiki-related zh/en keys exist and are non-empty
- `test_i18n_trash_keys_complete` — verifies 13 trash keys
- `test_i18n_source_add_keys_complete` — verifies 26 source_add keys
- `test_all_pages_use_locale` — verifies all 26 page/component files import useLocale
- `test_display_mapping_functions_exist` — verifies all 6 mapping functions
- `test_setup_page_uses_display_mappings` — verifies SetupPage imports mappings
- `test_sources_page_uses_display_mappings` — verifies SourcesPage imports mappings

Also fixed existing test assertions that compared zh values against English strings.

## Gate Results

| Gate | Result |
|------|--------|
| `npm --prefix web run build` | EXIT_CODE=0 |
| `python -m pytest tests/test_web_product_copy.py -q` | 23 passed, EXIT_CODE=0 |
| `git diff --check` | EXIT_CODE=0 |

## Browser Smoke Results

- Chinese mode: Sidebar fully Chinese, Home page Chinese ✓
- English mode: Sidebar fully English, Home page English ✓
- Language toggle works ✓
- No JS console errors ✓
- No raw i18n keys visible ✓
- 404 errors: expected (backend not running for smoke test)

## Deviations from Spec

1. **frequencyOptions removed instead of deprecated**: The backward-compatible export caused a runtime error (`t is not a function`). Removed entirely since SourcesPage now uses `getFrequencyOptions(t)`.

2. **setup.save/validate/revert/unsaved zh values**: These were still in English in the zh block. Fixed as part of this follow-up.

3. **EmptyState.tsx not i18n-ized**: This component receives translated strings via props (`title`, `action.label`). Adding useLocale would be redundant since its parent already translates.

## Remaining P3/P4 (triaged 2026-05-23)

### P3-1: NextAction backend labels — ENTERED FUTURE BACKLOG

**现状**: `NextAction.label` 和 `description` 在 `src/mindforge_web/services/web_facade.py` 的 `_next_actions()` 中硬编码。label 为英文（"Review drafts", "Watch or import source" 等），description 为中英混合。

**为何不能纯前端修**: NextAction 结构只有 `{label, description, command, href, onClick}` 五个字段，没有 `type`/`action_key` 可用于前端 display mapping。label 是后端动态生成的自由文本，前端做字符串匹配太脆弱。

**需要的后端改动** (future spec):
1. 在 `NextAction` schemas 中增加 `action_key: str | None` 字段
2. 后端生成 NextAction 时填入稳定的 `action_key`（如 `"init_vault"`, `"review_drafts"`, `"watch_source"`, `"search_knowledge"`）
3. 前端根据 `action_key` 做 display mapping，`label`/`description` 降级为 fallback

**记录位置**: 建议新增 `docs/specs/2026-05-XX-003-web-next-action-i18n-spec.md` 或纳入下一轮 Web UX plan。

### P3-2: Source type format names — INTENTIONAL RETENTION

**保留原因**:
1. Markdown / HTML / PDF / Word / Text 是文件格式的专有名词（proper nouns），不是 UI copy
2. 在中文软件开发中，"PDF 文档"、"Markdown 文件" 是标准用法，格式名本身不翻译
3. 展示样式为 `font-mono text-[10px] uppercase tracking-wide` badge — 视觉上明确是技术元数据标签，不是主文案
4. 映射已在 `WikiReferenceCard.sourceTypeLabels` 中完成（`plain_markdown` → `Markdown`），将 internal id 转为可读格式名，已满足用户友好要求

**不做的事**: 将这些格式名加入 i18n 字典。它们是格式标识符，翻译反而降低可辨识度。

### P4: Rebuild status messages — FIXED

**修复内容**:
- 新增 i18n key `wiki.rebuild_result`：zh `"Wiki 已重新生成（{mode}）：{cards} 张卡片，{sections} 个章节，模型：{model}"` / en `"Wiki rebuilt ({mode}): {cards} cards, {sections} sections, model: {model}"`
- 新增 i18n key `wiki.rebuild_server_error`：zh `"重新生成失败：{error}"` / en `"Rebuild failed: {error}"`
- `WikiPage.tsx` 中 rebuild 成功/失败消息改为通过 `t()` 获取并使用 `.replace()` 模板替换
- 原动态拼接 `parts.join(", ")` 逻辑替换为单一模板

**Warnings 附加逻辑保留**: warnings 通过 `setMessage(prev => prev + " — Warnings: ...")` 追加，这部分是技术/调试信息，保持英文。
