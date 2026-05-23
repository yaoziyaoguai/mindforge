# Milestone F Implementation Notes — Knowledge Card Browsing Experience

**Date**: 2026-05-23
**Spec**: `docs/specs/2026-05-23-005-knowledge-card-browsing-experience-spec.md`
**Branch**: main (fast lane)

## Summary

Implemented all 5 units of Milestone F, replacing the Library's 340px sidebar card list with a responsive card grid browsing experience, adding a Summary Panel and Related Cards strip to CardWorkspace, and updating i18n/contract tests.

## Changes

### U1: Card Grid Layout (`web/src/pages/LibraryPage.tsx`)

- Replaced `lg:grid-cols-[340px_1fr]` master-detail layout with full-width responsive card grid
- Grid uses `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4`
- Each card shows: title, status badge, source type chip, track, source path, updated date
- 4px top accent border color-coded by source type (slate/gray/orange/red/blue)
- Clicking a card opens detail pane below the grid with URL `?card=` param sync
- Close button (X) deselects and removes URL param
- "Select a card to view details" hint when no card is selected
- Removed unused `message` state (was never rendered)

### U2: Card Summary Panel (`web/src/components/CardWorkspace.tsx`)

- New `SummaryPanel` component shown in library mode between header and QualityPanel
- Extracts `##` and `###` headings from Markdown body via `extractHeadings()` regex
- `###` headings indented with `ml-4` for visual hierarchy
- Fallback: first 150 chars of body with Markdown stripped via `stripMarkdown()`
- Shows track and strategy_label as metadata pills
- Collapsible with ChevronUp/ChevronDown toggle (default open)
- All extraction is frontend-only — no LLM, no API calls

### U3: Related Cards Horizontal Strip (`web/src/components/CardWorkspace.tsx`)

- New `RelatedCardsStrip` component in library mode between Source & History and Tech Details
- Uses `detail.related_cards` (already provided by `LibraryCardDetailResponse`)
- Horizontal scroll strip with `overflow-x-auto flex gap-3`
- Each mini-card (w-48): title, source type icon, status dot, reasons label
- Clicking navigates to the related card via `onSelectCard` callback
- Reasons displayed as `label · label` (no strength values)
- Only renders when `related_cards.length > 0`

### U4: Card Visual Polish (`web/src/components/CardWorkspace.tsx`, `web/src/pages/LibraryPage.tsx`)

- Source type icon mapping: `FileText` (markdown/txt), `FileCode` (html), `FileType` (pdf), `FileEdit` (docx), `File` (fallback)
- Card grid card hierarchy: title (bold) > metadata line (muted badges) > date (subtle)
- Added `onSelectCard` prop to CardWorkspace for related card navigation
- Status badge styling consistent throughout (bg-safe/10 text-safe vs bg-warn/10 text-warn)

### U5: i18n + Contract Tests

- 10 new i18n keys added to both zh and en dictionaries
- 4 new contract tests in `tests/test_web_product_copy.py`:
  - `test_i18n_library_browsing_keys_complete` — verifies all 10 new keys
  - `test_library_card_grid_uses_friendly_status` — verifies friendlyStatus usage
  - `test_related_cards_do_not_show_strength` — verifies `.strength` not rendered
  - `test_card_summary_is_frontend_only` — verifies frontend-only extraction

## Design Decisions

1. **No tags in card grid**: `LibraryCardResponse` type doesn't include `tags` field (unlike `DraftSummary`). Skipped per spec's "如有" (if present) instruction.
2. **URL sync**: `pushState` used instead of `replaceState` to maintain back-button navigation.
3. **Duplicated helpers**: `sourceTypeLabels` and `sourceTypeBadge` exist in both LibraryPage and CardWorkspace. Kept separate to avoid cross-import complexity.
4. **locale prop in SummaryPanel**: Passed but unused — retained for future date formatting consistency.

## Gate Results

- `npm --prefix web run build`: PASS (exit 0)
- `python -m pytest tests/test_web_product_copy.py -q`: PASS (50/50)
- `git diff --check`: PASS (exit 0)

## Browser Smoke

Deferred per no-real-dogfood constraint. Code-level verification:
- Layout structure reviewed in diff
- All i18n keys verified present in both locales
- No strength values rendered in Related Cards
- Summary Panel uses only frontend regex extraction
- Card grid uses friendlyStatus(), not raw status strings

## Known Limitations

1. Card grid doesn't show tags — `LibraryCardResponse` has no `tags` field
2. Browser smoke not performed (no backend running, no-real-dogfood constraint)
3. `stripMarkdown` is a simple regex-based approach — edge cases like nested formatting may leave artifacts
