# MindForge Web Design — Production Implementation Plan

**日期**: 2026-05-26
**状态**: in-progress
**输入**: docs/design/2026-05-26-105-final-web-design-decision.md
**设计方向**: Variant A (Calm Editorial Knowledge Desk) + Variant B card shadows

---

## 1. Implementation Strategy

**Incremental, per-stage commits. No big-bang redesign. Each stage must pass build + product copy tests independently.**

Current Tailwind tokens are already warm-leaning: `surface: #f7f5f1`, `panel: #ffffff`, `ink: #23211d`. The gap from current to target is small — mostly refining warmth, adding serif, improving shadows, and replacing blue accent with Forest Green.

---

## 2. Stage 1 — Design System Foundation

**Goal**: Add CSS variables, fonts, and base tokens. Zero component changes.

### Files Touched
- `web/index.html` — Google Fonts `<link>`
- `web/src/styles.css` — CSS custom properties, base font-family, focus ring color

### Changes
1. Add Google Fonts `<link>` for Source Serif 4, DM Sans, JetBrains Mono
2. Add `--mf-*` CSS variable block in `:root`
3. Update `body` font-family to `var(--mf-font-sans)`
4. Update focus outline from `#2368d1` to `#2d7d5f`
5. Keep existing Tailwind tokens unchanged

### Non-Goals
- No Tailwind config changes
- No component imports changed
- No page layout changes
- No behavior changes

### Gate
```bash
npm --prefix web run build          # must exit 0
git diff --check                     # must exit 0
python -m pytest tests/test_web_product_copy.py -q --tb=short  # must exit 0
```

---

## 3. Stage 2 — AppShell + Sidebar + PageHeader

**Goal**: Navigation polish, lab section collapse, warm paper framework.

### Files Touched
- `web/src/components/Sidebar.tsx` — lab section collapse, Forest Green active state
- `web/src/components/AppShell.tsx` — background, layout refinements
- `web/src/styles.css` — layout utility classes

### Changes
1. Sidebar: Add collapsed "Lab" section with Graph/Sensemaking
2. Sidebar: Replace blue active state with Forest Green left-border accent
3. AppShell: Ensure warm paper background applies consistently
4. Add `.page-header` base style class
5. Keep all routes accessible (URL direct access still works)

### Non-Goals
- No page content changes
- No Graph/Sensemaking page removal
- No API changes

---

## 4. Stage 3 — Review Queue + Approval Panel

**Goal**: Approval experience becomes the emotional center.

### Files Touched
- `web/src/pages/DraftsPage.tsx`
- `web/src/components/DraftList.tsx`
- `web/src/components/DraftViewer.tsx`
- `web/src/components/ApprovalPanel.tsx`
- `web/src/components/ApprovalTimeline.tsx`
- `web/src/pages/DraftDetailPage.tsx`

### Changes
1. Review Queue: Single-column card list with serif titles
2. Cards: 3-layer shadow, warm paper surface, 10px radius
3. Status: 3px left border accent (amber for draft, green for approved)
4. Approved cards: Reduced opacity for visual clearance
5. ApprovalPanel: Forest Green approve button, warm red reject
6. Typography: Serif headings, sans body at 1.6 line-height

### Non-Goals
- No approval logic changes
- No API changes
- No status transition changes

---

## 5. Stage 4 — Library + Card Detail

**Goal**: Library becomes a warm browsing experience with B's tactile shadows.

### Files Touched
- `web/src/pages/LibraryPage.tsx`
- Knowledge card components (may extract `KnowledgeCard` component)
- `web/src/components/StatusCard.tsx`

### Changes
1. KnowledgeCard: White surface, 4-layer B-style shadow, 10px radius
2. Library grid: 1-3 column responsive
3. Status badges: Amber pill for draft, green pill for approved
4. Card Detail: Wide reading column (max-w-3xl), serif title
5. Filter bar: Visual polish only (keep A5 logic)

### Non-Goals
- No filter/sort logic changes
- No API changes

---

## 6. Stage 5 — Recall / Wiki / Export / Supporting Pages

**Goal**: Remaining page polish.

### Files Touched
- `web/src/pages/RecallPage.tsx`
- `web/src/pages/WikiPage.tsx`
- `web/src/pages/SourcesPage.tsx`
- `web/src/pages/HomePage.tsx`
- `web/src/pages/SetupPage.tsx`
- `web/src/components/EmptyState.tsx`
- `web/src/components/SafetyBar.tsx`

### Changes
1. Recall: Serif search placeholder, warm result cards
2. Wiki: Editorial long-form reading layout
3. EmptyState: Unified warm, guiding style
4. SafetyBar: Calm callout treatment

---

## 7. Stage 6 — Design QA

**Goal**: Visual consistency, accessibility, responsive verification.

- Color contrast audit (WCAG AA)
- Focus ring visibility
- Responsive breakpoints (320px-1440px)
- Serif rendering quality check
- Product copy consistency

---

## 8. Per-Stage Gate Requirements

Every stage must pass:
```bash
npm --prefix web run build                          # exit 0
git diff --check                                     # exit 0
python -m pytest tests/test_web_product_copy.py -q --tb=short  # exit 0
```

---

## 9. Stop Conditions

- Any stage fails gate → fix before continuing
- Context < 10% → finish current stage, commit, write handoff
- Unexpected backend change needed → stop, write spec first
- Graph/Sensemaking expansion creeps in → stop, revert
