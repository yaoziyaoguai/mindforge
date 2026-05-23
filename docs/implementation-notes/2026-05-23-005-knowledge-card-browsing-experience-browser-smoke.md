# Milestone F Browser Smoke Report — Knowledge Card Browsing Experience

**Date**: 2026-05-23
**Commit**: `70c7782` feat(web): upgrade library from sidebar list to card grid browsing experience
**Spec**: `docs/specs/2026-05-23-005-knowledge-card-browsing-experience-spec.md`

## Smoke Summary

Browser smoke passed on all 5 units. No P0/P1/P2 issues found. One P4: favicon.ico 404 (pre-existing, not introduced by this milestone).

## Environment

- **Backend**: `python -m mindforge web --port 8766 --no-open` (default config, port 8765 was occupied by Chrome MCP)
- **Frontend**: `npm --prefix web run dev` → http://127.0.0.1:5173
- **Vite proxy**: `/api` → `http://127.0.0.1:8766` (temporary port override for smoke, reverted after test)
- **Browser**: Chrome DevTools MCP
- **Test data**: 1 approved card (本地优先系统安全设计原则, cubox_markdown)

## Unit-by-Unit Verification

### U1: Card Grid Layout

- ✅ Card grid rendered with responsive columns (1 card visible, confirmed grid structure)
- ✅ Stats cards shown above grid (Approved Knowledge: 1, Pending Drafts: 0, Search Index: Ready, Total Cards: 1)
- ✅ Card shows: title, status badge (Approved/已确认), source type chip (CUBOX_MARKDOWN), track (unrouted), source path (note-b), updated date (May 8, 2026 / 2026年5月8日)
- ✅ colored accent border-top present on card
- ✅ Clicking card opens detail pane below grid
- ✅ URL sync: `?card=local-first-security-principles` added via pushState
- ✅ Close button (X) deselects card, removes URL param
- ✅ "Select a card to view details" hint shown when no card selected

### U2: Card Summary Panel

- ✅ "Card Overview" header with collapsible toggle
- ✅ 9 headings extracted from Markdown body: Source Excerpt, AI Summary, AI Inference (low confidence), Human Note, Reusable Prompts / Principles, Project Hooks, Review Questions, Action Items, Suggested Links
- ✅ Metadata pills: track: unrouted, Knowledge Card Workflow (strategy_label)
- ✅ Collapsible toggle present (open by default)
- ✅ All extraction is frontend-only (verified via contract test, test_card_summary_is_frontend_only)

### U3: Related Cards Strip

- ✅ Component conditionally renders (not shown when related_cards.length === 0)
- ✅ Local Graph Preview shown with "0 related cards" message
- ⚠️ Could not verify mini-card rendering since the test card has no related cards — but code path verified via diff review and contract test (test_related_cards_do_not_show_strength)

### U4: Card Visual Polish

- ✅ Source type chip displayed as uppercase badge (CUBOX_MARKDOWN)
- ✅ Card hierarchy in grid: title (bold) > metadata line > date (muted)
- ✅ Status badge styled with bg-safe/10 text-safe (Approved) or bg-warn/10 text-warn
- ✅ `onSelectCard` prop wired through CardWorkspace for related card navigation

### U5: i18n / Contract Tests

- ✅ English locale: "Library", "Approved", "Select a card to view details", "Updated May 8, 2026"
- ✅ Chinese locale: "知识库", "已确认", "选择卡片查看详情", "更新于 2026年5月8日"
- ✅ Language switch button toggles correctly between zh/en
- ✅ All 10 new i18n keys verified present in both locales (via contract test)
- ✅ friendlyStatus used in both card grid and detail view
- ✅ No `.strength` rendering in Related Cards (via contract test)

## Regression Check

All pages navigated without errors:

| Page | Status | Notes |
|------|--------|-------|
| Home | ✅ | All status cards correct, Next Actions rendered |
| Setup | ✅ | Connect Models page loaded, workflow steps visible |
| Review Drafts | ✅ | "No AI Drafts Pending" empty state |
| Library | ✅ | All U1-U4 features verified |
| Wiki | ✅ | Card visible in wiki with TOC, provenance, tags |
| Safety Bar | ✅ | Consistent across all pages |

## Console & Network

- **Console**: No JS errors. Only informational: Vite connect, React DevTools hint. One 404 for `/favicon.ico` (pre-existing, not from this milestone).
- **Network**: All 28 API calls returned 200:
  - `/api/home/status` (4×)
  - `/api/workflow/summary` (2×)
  - `/api/library/cards` (2×)
  - `/api/library/card` (3×)
  - `/api/quality/cards` (4×)
  - `/api/config/status` (1×)
  - `/api/config/editable` (2×)
  - `/api/drafts` (1×)
  - `/api/wiki/status` (3×)
  - `/api/wiki/page` (3×)
- **No unexpected 4xx/5xx**

## Gate Re-verification

All gates re-run with real exit codes (not from memory):

- `npm --prefix web run build` → exit 0 (2.05s, no timeout)
- `python -m pytest tests/test_web_product_copy.py -q` → exit 0 (50/50 passed)
- `git diff --check` → exit 0

## Findings

| Severity | Finding | Action |
|----------|---------|--------|
| P4 | `/favicon.ico` returns 404 | No action — pre-existing, not from this milestone, zero user impact |
| None | No tags in card grid | Expected — `LibraryCardResponse` has no `tags` field, per spec "如有" instruction |
| None | No related cards to test strip | Test data has only 1 card; code path verified via contract test and code review |

## Known Limitations

1. Browser smoke tested with only 1 card — multi-card grid layout, related cards strip, and scroll behavior not visually verified
2. No real LLM or dogfood — summary panel heading extraction verified via contract test only
3. Port 8765 was occupied by Chrome MCP helper — used port 8766 with temporary vite proxy change (reverted)

## Conclusion

Milestone F passes browser smoke with zero regressions. All 5 implementation units verified functional. No code changes needed.

**Verification**: Pass ✅
**P0 found**: No
**P1 found**: No
**P2 found**: No
**Hotfix needed**: No
**Real dogfood needed**: No — all features are visual/layout only, contract tests cover i18n and extraction logic
