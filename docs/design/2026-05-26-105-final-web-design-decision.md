# MindForge Web — Final Design Decision

**日期**: 2026-05-26
**状态**: locked
**输入**: Design Shotgun comparison (docs/archive/design/2026-05-26-104-web-design-shotgun-comparison.md) (archived)
**前置**: Design direction (docs/design/2026-05-26-102-mindforge-web-design-direction.md)

---

## 1. Design Review of All 5 Variants

### Variant A — Calm Editorial Knowledge Desk
**Verdict**: **Adopt as primary direction.**

Serif-forward editorial reading with generous whitespace and single-column focus. Best match for MindForge's identity as a knowledge compiler, not a notes app or SaaS dashboard. The serif/sans distinction (Source Serif 4 for headings, DM Sans for body) gives each knowledge card editorial weight — the user feels like they're reviewing a publication entry, not a ticket.

Concern addressed: serif rendering on Windows (ClearType). Mitigation: Georgia fallback is a credible serif on all platforms. DM Sans body text is the primary reading font, serif is headings only, so FOUT on headings is acceptable.

### Variant B — Warm Research Library
**Verdict**: **Adopt card shadow treatment as secondary ingredient. Do not adopt as standalone direction.**

The 4-layer shadow stack creates genuine paper depth. The catalog-entry metaphor maps naturally to Library browsing. However, the gradient sheen (`linear-gradient` on card surface) adds implementation complexity for diminishing returns. Adopt only the shadow stack, not the gradient sheen.

### Variant C — Precision Review Console
**Verdict**: **Reject as primary direction. Borrow pipeline thinking for sidebar organization.**

The decision-forward grid layout is excellent for scanning many drafts quickly, but MindForge's review experience should prioritize reading quality over decision speed. The pipeline sidebar reorganization (Sources → Review → Library) is conceptually strong — adopt the pipeline grouping for sidebar navigation, but keep the editorial card treatment from A.

### Variant D — Minimal Local-First Notebook
**Verdict**: **Reject.**

Radical subtraction loses the warmth and editorial quality that differentiate MindForge. Border-only cards feel under-designed for a knowledge reading experience. The file-path-on-hover pattern is clever but hidden. This direction reads as "unfinished" rather than "minimal."

One salvageable element: mono font (`JetBrains Mono`) for file paths and provenance display. Already specified in the design direction — keep this.

### Variant E — Quiet AI Knowledge Lab
**Verdict**: **Reject.**

Italic serif for AI-generated summaries is a clever typographic signal, but italic body text reduces readability. The process flow bar (Source → Review → Library → Recall/Wiki) takes vertical space and feels tutorial-like. The concept of "process visibility" is good, but the execution in E over-indexes on the AI distinction rather than the knowledge quality.

Salvageable: the colored left-border accent for draft vs. approved status. Simpler than E's full italic treatment — just a 3px left border in amber (draft) or green (approved) on cards. Adopt this, but on the right edge or as a subtle top-border accent to avoid looking like a notification/alert pattern.

---

## 2. Final Decision

### Primary Direction: Variant A — Calm Editorial Knowledge Desk

**Framework**: Single-column editorial reading, serif headings, generous whitespace, warm paper palette.

### Borrowed from Variant B

- **4-layer card shadow stack** for Library cards and Review Queue cards
- **10px card border radius** (matches A's existing proposal)
- **NOT adopted**: card surface gradient sheen (unnecessary complexity)

### Borrowed from Variant C

- **Pipeline-aware sidebar grouping**: Sources → Review → Library as primary pipeline, Recall/Wiki as tools, Graph/Sensemaking as collapsed lab section

### Borrowed from Variant E

- **Subtle left-border status accent**: 3px amber border for ai_draft cards, 3px green border for human_approved cards. Applied on the left edge of cards as a color cue — not the full italic treatment.

---

## 3. Final Design Adjectives (7)

1. **Calm** — colors don't shout, no animation spam, cards breathe
2. **Editorial** — serif headings, 1.6 line-height body, publication-entry feel
3. **Trustworthy** — approval actions are clear but deliberate, provenance visible
4. **Warm** — warm paper palette, no cold grays, no blue grays
5. **Local-First** — no sync spinners, no cloud indicators, file paths in mono where relevant
6. **Focused** — max 3 primary actions per page, lab features collapsed, navigation minimal
7. **Honest** — BM25 boundaries explained, current limitations visible, no feature over-promise

---

## 4. Final Token Decisions

### Color Tokens (locked)

| Token | Value | Usage |
|-------|-------|-------|
| `--mf-bg` | `#faf9f5` | Page background |
| `--mf-surface` | `#ffffff` | Card, panel surfaces |
| `--mf-surface-alt` | `#f3f1eb` | Sidebar, alternating rows |
| `--mf-text-primary` | `#1c1b18` | Headings, body text |
| `--mf-text-secondary` | `#5e5c56` | Descriptions, metadata |
| `--mf-text-tertiary` | `#8a8880` | Placeholders, disabled |
| `--mf-border` | `rgba(0,0,0,0.08)` | Card borders, dividers |
| `--mf-accent` | `#2d7d5f` | Brand, approve button, links |
| `--mf-accent-hover` | `#236b4f` | Accent hover state |
| `--mf-draft` | `#b8860b` | ai_draft status |
| `--mf-approved` | `#2d7d5f` | human_approved status (same as accent) |
| `--mf-lab` | `#8a8880` | lab/internal status |
| `--mf-warning` | `#cc7a00` | Warning messages |
| `--mf-error` | `#c04040` | Error, reject button |

### Typography Tokens (locked)

| Token | Font Stack | Usage |
|-------|-----------|-------|
| `--mf-font-serif` | `'Source Serif 4', Georgia, serif` | Headings only |
| `--mf-font-sans` | `'DM Sans', system-ui, -apple-system, sans-serif` | Body, UI |
| `--mf-font-mono` | `'JetBrains Mono', 'SF Mono', monospace` | Code, file paths |

**Font loading decision**: Use Google Fonts CDN `<link>` in `index.html`. System fallback fonts are specified in the stack. FOUT is acceptable for headings (serif → Georgia is visually close). No npm font packages.

### Typography Scale (locked)

| Level | Font | Size/Line/Weight | Usage |
|-------|------|------------------|-------|
| Display | Serif | 36px / 1.15 / 500 | Page main title |
| H1 | Serif | 28px / 1.2 / 500 | Section headings |
| H2 | Serif | 22px / 1.25 / 500 | Card titles |
| H3 | Sans | 18px / 1.3 / 600 | Subheadings |
| Body L | Sans | 16px / 1.6 / 400 | Card body text |
| Body | Sans | 15px / 1.5 / 400 | Standard text |
| Body S | Sans | 14px / 1.45 / 400 | Metadata |
| Caption | Sans | 12px / 1.35 / 500 | Labels, badges |
| Code | Mono | 13px / 1.5 / 400 | Paths, code |

### Shadow Tokens (locked — combining A + B)

| Token | Value | Usage |
|-------|-------|-------|
| `--mf-shadow-flat` | `none` | Flat surfaces |
| `--mf-shadow-raised` | `0px 2px 12px rgba(0,0,0,0.03), 0px 1px 4px rgba(0,0,0,0.015), 0px 0.4px 1.5px rgba(0,0,0,0.008)` | Standard cards (A's 3-layer) |
| `--mf-shadow-card` | `0px 0.6px 2.2px rgba(0,0,0,0.006), 0px 1.6px 5.4px rgba(0,0,0,0.009), 0px 3.6px 11px rgba(0,0,0,0.012), 0px 8px 22px rgba(0,0,0,0.018)` | Library/browsing cards (B's 4-layer) |
| `--mf-shadow-overlay` | `0px 4px 24px rgba(0,0,0,0.06)` | Modals, dropdowns |

**Decision**: Two shadow levels. `--mf-shadow-raised` (A, 3-layer) for Review Queue and detail cards. `--mf-shadow-card` (B, 4-layer) for Library browsing grid. This gives the Library page extra tactility without applying the heavier shadow everywhere.

### Border Radius (locked)

| Token | Value |
|-------|-------|
| `--mf-radius-sm` | `4px` |
| `--mf-radius-md` | `8px` |
| `--mf-radius-lg` | `10px` |
| `--mf-radius-xl` | `14px` |
| `--mf-radius-full` | `9999px` |

### Spacing Scale (locked)

| Token | Value |
|-------|-------|
| `--mf-space-2xs` | `4px` |
| `--mf-space-xs` | `8px` |
| `--mf-space-sm` | `12px` |
| `--mf-space-md` | `16px` |
| `--mf-space-lg` | `24px` |
| `--mf-space-xl` | `32px` |
| `--mf-space-2xl` | `48px` |
| `--mf-space-3xl` | `64px` |

---

## 5. Status Accent Border Decision

Adopted from Variant E's colored border concept, simplified:

- **ai_draft cards**: 3px left border in `--mf-draft` (#b8860b) — warm amber signals "needs your review"
- **human_approved cards**: 3px left border in `--mf-approved` (#2d7d5f) — forest green signals "confirmed knowledge"
- **lab/internal features**: 3px left border in `--mf-lab` (#8a8880) — neutral gray, not alarming

This is a 3px `border-left` applied to the card container. It's a single CSS property — no gradient bleed, no italic switching. The color cue is immediate from card edges without reading labels.

---

## 6. Final Component Priorities

| Priority | Component | Source Variant | Notes |
|----------|-----------|---------------|-------|
| P0 | CSS Custom Properties | A (framework) | All tokens above |
| P0 | AppShell + Sidebar | A + C pipeline grouping | Lab section collapsed |
| P0 | Card surface (base) | A | 3-layer shadow, serif title, sans body |
| P0 | Card surface (library) | B shadow stack | 4-layer shadow for grid browsing |
| P1 | Status left-border accent | E (simplified) | 3px colored left border |
| P1 | Status Badge (pill) | A | Amber draft, green approved |
| P1 | Review Queue layout | A | Single-column, reading-first |
| P1 | Approval buttons | A + C | Prominent but deliberate |
| P2 | EmptyState | A | Warm, guiding, not marketing |
| P2 | SafetyNotice | A | Calm callout, not alarming |
| P2 | Provenance display | A + D | Mono font, visible but not dominant |

---

## 7. Page Priority for Implementation

| Priority | Page | Variant | Rationale |
|----------|------|---------|-----------|
| P0 | AppShell + Sidebar | A + C | Every page shares this |
| P0 | Review Queue (DraftsPage) | A | Approval is the core differentiator |
| P1 | Library | A + B shadows | Highest-frequency browsing page |
| P1 | Card Detail | A | Deep reading experience |
| P2 | Recall/Search | A | Second-highest operation |
| P2 | Wiki | A | Editorial long-form reading |
| P2 | Sources/Import | A | Knowledge entry point |
| P3 | Home, Setup, Export | A | Supporting pages |
| Lab | Graph, Sensemaking | A (minimal) | Only style adjustments |

---

## 8. What Must NOT Be Implemented

- No Graph/Sensemaking expansion or main-nav promotion
- No RAG/embedding/vector DB UI
- No AI chatbot interface
- No auto-approve or one-click bulk approval
- No dark mode (wait for separate spec)
- No animation system beyond existing transitions
- No npm font packages (Google Fonts CDN only)
- No backend logic changes
- No API contract changes
- No product copy changes (only visual styling)
- No card surface gradient sheen from Variant B
- No italic AI text treatment from Variant E
- No pipeline flow indicator bar from Variant E

---

## 9. Accessibility Notes

- **Serif rendering**: Georgia fallback is credible on Windows ClearType
- **Color contrast**: `#1c1b18` on `#faf9f5` = ~18:1 (exceeds WCAG AAA)
- **Amber on warm paper**: `#b8860b` needs darkening if used as text — use as border/badge background only, not as text on `#faf9f5`
- **Focus ring**: Replace current `#2368d1` blue with `#2d7d5f` Forest Green
- **Status communication**: Left-border color + pill badge text together ensure status is not color-alone
- **Font loading**: FOUT on serif headings is acceptable (Georgia → Source Serif 4 is visually close)

---

## 10. Implementation Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tailwind theme extension conflicts with existing utility classes | Low | Medium | Only extend, never override; test build after each change |
| Sidebar lab collapse breaks existing navigation tests | Low | Low | Keep all routes accessible; collapse is visual-only |
| Google Fonts CDN blocked in some environments | Low | Medium | System fallback fonts are specified; app works offline |
| 4-layer shadows invisible on low-DPI displays | Low | Low | Test on non-Retina; darken slightly if needed |
| Existing custom Tailwind tokens (`text-ink`, `bg-panel`) conflict with new `--mf-*` variables | Low | Low | These are Tailwind classes, not CSS vars — they coexist |
