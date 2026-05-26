# Stage 6 Design QA — Handoff

**Date:** 2026-05-26
**Status:** `HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN`
**Session:** context < 5%, cannot safely execute full browser QA loop

---

## What was completed (Stages 1-5)

All 5 implementation stages of the production plan are committed and pushed to main:

| Stage | Commit | Scope |
|-------|--------|-------|
| 1 | `a138177` | Design system foundation: CSS tokens, Google Fonts, focus ring |
| 2 | `ffd4bdd` | AppShell + Sidebar + PageHeader |
| 3 | `af3aeb1` | Review Queue + Approval Panel editorial redesign |
| 4 | `29155ac` | Library cards with B-style 4-layer shadows + editorial styling |
| 5 | `03d4ba5` | Recall/Home/EmptyState editorial polish |

**HEAD:** `03d4ba5`
**Branch:** main, clean, 0 0 aligned with origin/main

## Build gate

```
npm --prefix web run build → EXIT 0
```

---

## Stage 6 — Full Design QA Checklist (deferred to new session)

### Pre-flight

```bash
cd /Users/jinkun.wang/work_space/mindforge
git status --short          # must be clean
git rev-parse --abbrev-ref HEAD  # must be main
git log --oneline -5        # top commit must be 03d4ba5
npm --prefix web run build  # must exit 0

# Start dev server
npm --prefix web run dev -- --host 127.0.0.1 --port 5174 &
# Wait for "ready" / "Local:" line
```

### Pages to inspect (minimum 8)

| # | Page | Route | Key things to check |
|---|------|-------|---------------------|
| 1 | Home (empty/first-run) | `/` | Onboarding guide gradient, step cards, accent colors |
| 2 | Home (with data) | `/` | Overview cards, lifecycle bar, attention feed |
| 3 | Review Queue | `/drafts` | Serif titles, amber left-border on drafts, 55% opacity on approved |
| 4 | Draft Detail + Approval | `/drafts?card=<id>` | ApprovalPanel: Forest Green approve, warm red reject, raised shadow |
| 5 | Library | `/library` | B-style 4-layer shadow cards, serif titles, source type top-border |
| 6 | Card Detail | `/library?card=<id>` | Raised shadow detail card, editorial layout |
| 7 | Recall/Search | `/recall` | Search button accent color, result card shadows |
| 8 | Wiki | `/wiki` | Content layout, editorial headings |
| 9 | Export/Settings | `/export` or `/setup` | Button styles, form elements |
| 10 | Lab (collapsed sidebar) | any page | Sidebar lab section collapse/expand |

### QA Dimensions

**A. Visual Consistency**
- [ ] All `.page-header` h1 headings use serif font (Source Serif 4)
- [ ] All body/UI text uses DM Sans
- [ ] All primary CTAs use `--mf-accent` (#2d7d5f) — no remaining blue (#2368d1)
- [ ] Forest Green appears consistently across: sidebar active, approve button, QuickAction icons, onboarding steps, "查看 →" links
- [ ] Amber (#b8860b) used for draft/ai_draft status only
- [ ] Green (#2d7d5f) used for approved/human_approved status only
- [ ] Gray (#8a8880) used for lab items only

**B. Shadow Audit**
- [ ] Review Queue cards: `--mf-shadow-raised` (3-layer)
- [ ] Draft Detail: `--mf-shadow-raised` (3-layer)
- [ ] Library grid cards: `--mf-shadow-card` (4-layer)
- [ ] StatusCard: `--mf-shadow-raised` (3-layer)
- [ ] Recall result cards: `--mf-shadow-raised` (3-layer)

**C. Inline Style Audit (code-level)**
- [ ] HomePage.tsx: no `style` prop on Lucide Icon components (wrapped in `<span>` instead)
- [ ] All `style={{ }}` use CSS variable references, not hardcoded hex values
- [ ] No duplicate or conflicting inline styles

**D. Accessibility**
- [ ] Focus ring visible on all interactive elements: `outline: 2px solid var(--mf-accent)`
- [ ] All form inputs have associated labels (`aria-label` at minimum for search)
- [ ] Color contrast: text on `--mf-bg` (#faf9f5), `--mf-surface` (#ffffff), `--mf-surface-alt` (#f3f1eb)
- [ ] `alt` text on informational images (if any)
- [ ] Links are keyboard-navigable (Tab/Enter)

**E. Responsive**
- [ ] 320px: no horizontal overflow, cards stack vertically
- [ ] 768px: 2-column grids work
- [ ] 1024px: sidebar + content layout intact
- [ ] 1440px: max-width content, no stretching

**F. Product Fit**
- [ ] No regressions: all nav links work, search functions, approval workflow intact
- [ ] Lab items in sidebar are collapsed by default
- [ ] No Graph/Sensemaking pages have been modified
- [ ] Empty states show correct CTA (no broken links)

### Fixes (if needed)

If findings are minor (inline style cleanup, color corrections, spacing tweaks):
1. Fix directly
2. Rebuild: `npm --prefix web run build`
3. Commit as `style: Stage 6 — Design QA polish`
4. Continue

If findings are major (broken layout, missing pages, accessibility violations):
1. Fix the most critical items
2. Document remaining items
3. Commit and continue or handoff again

### Gate (after fixes)

```bash
npm --prefix web run build          # must exit 0
python -m pytest tests/test_web_product_copy.py -q --tb=short  # must exit 0
git diff --check                     # must exit 0
```

---

## Inline Style Cleanup Notes (known issues from implementation)

These were noted during Stage 1-5 implementation as potential cleanup items:

1. **Duplicate style patterns**: Several components repeat the same inline style blocks (e.g., card surface with raised shadow). Could extract to CSS utility classes like `.mf-card-raised`, `.mf-card-grid`.
2. **Lucide icon wrapping**: `HomePage.tsx:289` already fixed — icons wrapped in `<span className="text-[var(--mf-accent)]">`. Verify no other files have the same pattern.
3. **Hardcoded fallbacks**: Some components have `#2d7d5f` or `#236b4f` as fallback values in comments — these are informational, not functional, but verify.

## Deferred (not in scope)

- Tailwind config changes (not needed for this design refresh)
- New frontend dependencies
- Major component refactoring
- Backend changes
- Graph/Sensemaking UI changes
- New pages or features
