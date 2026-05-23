# Web UX Milestone C Implementation Notes

**Date**: 2026-05-23
**Plan**: docs/plans/2026-05-22-002-feat-web-ux-improvement-plan.md
**Spec**: docs/specs/2026-05-23-001-web-ux-milestone-c-mini-spec.md

## What Was Implemented

### U12: Form Field Accessibility (R13)
- Added `id` and `aria-label` to frequency combobox `<select>` in SourcesPage
- Minimal change: 2 lines in `web/src/pages/SourcesPage.tsx`

### U11: Spacing/Typography Consistency (R12)
- Added `.page-grid { gap: 1rem; }` rule in `web/src/styles.css` for consistent card grid spacing
- 5 lines, no token changes (tailwind.config.ts untouched)

### U10: Recall Copy Refinement (R11)
- Updated BM25 explanation: "基于 BM25 词法匹配算法，根据关键词频率和文档长度计算相关性，非语义或向量检索。"
- Empty state descriptions now explain BM25 lexical matching
- All copy extracted to i18n dictionary

### U8+U9: Review Card Visual Hierarchy + Provenance (R9, R10)
- ApprovalPanel restructured: info section (title → description → value score box) separated from action section by `border-t` divider
- CardWorkspace provenance labels made user-friendly: "来源路径" → "文件位置" (File Location)
- Technical details fold with translated labels for all internal fields
- Source path display uses `copy_display_path` pattern (safe, not raw path)

### U13: Chinese-English UI Switching (R14)
- Created `web/src/lib/i18n.ts` — lightweight locale dictionary system
  - `Locale` type: `"zh" | "en"`
  - `copy` object with ~85 zh/en translation keys organized by page
  - `t(key, locale)` function with 3-level fallback: current locale → en → key
  - `LocaleContext` (React Context) for cross-component locale state sharing
  - `LocaleProvider` component wrapping entire app
  - `useLocale()` hook reading from context
  - `localStorage` key `mindforge-locale` persists preference
- Updated all components (Sidebar, ApprovalPanel, CardWorkspace, DraftList, StatusCard, HomePage, SetupPage, DraftsPage, LibraryPage, RecallPage) + `lib/utils.ts` `friendlyStatus()`/`statusLabel()`
- Sidebar footer language toggle: Globe icon button switching zh↔en
- `friendlyStatus()` now accepts optional `locale` parameter for translated status labels
- Internal business fields (`ai_draft`, `human_approved`, `source_id`) remain English; only user-facing display copy is translated

## Decisions Made (Not in Plan)

### React Context for locale state sharing
**Problem**: Each component independently calling `useState` for locale caused split-brain — Sidebar locale changed but page content stayed in previous language.
**Fix**: Implemented React Context (`LocaleContext` + `LocaleProvider`) so all components share one locale state.

### `.ts` extension kept (not `.tsx`)
**Problem**: JSX syntax in `.ts` files causes TypeScript build errors.
**Fix**: Used `React.createElement(LocaleContext.Provider, ...)` instead of JSX in `i18n.ts`, keeping `.ts` extension.

### `copy` object placed before `LocaleProvider`
**Problem**: `const` declarations aren't hoisted; `LocaleProvider` references `t()` which references `copy`.
**Fix**: Moved `copy` and `t()` above `LocaleProvider` in the file.

## Deviations

- **test_web_product_copy.py updated**: 8 tests were verifying hardcoded Chinese/English strings in components. After i18n extraction, these strings moved to the i18n dictionary. Tests were updated to:
  1. Parse the i18n dictionary via regex helpers `_read_i18n_zh()` / `_read_i18n_en()`
  2. Verify correct Chinese/English values for i18n keys
  3. Keep "forbidden string" checks on component source (to prevent internal field leakage)
  4. Verify components use `useLocale` hook instead of hardcoded strings

## What Was NOT Done

- No backend changes (no `src/mindforge/**` modified)
- No new dependencies added
- No tailwind.config.ts token changes
- No React Router / Redux / Zustand introduced
- No RAG / embedding / vector DB
- No real LLM calls
- No .env / secrets reading
- No mail storage / email / SMTP
- No tag / release / PR

## Test/Gate Results

- `npm --prefix web run build`: exit code 0
- `git diff --check`: exit code 0
- `python -m pytest -q`: exit code 0 (all 16 product copy tests updated and passing)
- Browser smoke: all pages verified (Home, Setup, Sources, Drafts, Library, Recall, Wiki, Trash)
- Language toggle: works cross-component (zh↔en), no console errors

## Risks / Deferred

- **Deferred**: Backend API error messages remain English-only (per non-goal)
- **Deferred**: No Playwright E2E tests for language toggle (no test stack for it)
- **Risk**: i18n dictionary parsing in tests uses regex; fragile if dictionary format changes significantly
