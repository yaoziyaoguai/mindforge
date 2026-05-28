# MindForge Web Design Shotgun — Variant Comparison

**日期**: 2026-05-26
**输入**: docs/design/2026-05-26-102-mindforge-web-design-direction.md
**参考**: docs/design/prototypes/2026-05-26-shotgun/

---

## Variants Generated

| # | Name | Prototype |
|---|------|-----------|
| A | Calm Editorial Knowledge Desk | `prototypes/2026-05-26-shotgun/variant-a-review.html` |
| B | Warm Research Library | `prototypes/2026-05-26-shotgun/variant-b-review.html` |
| C | Precision Review Console | `prototypes/2026-05-26-shotgun/variant-c-review.html` |
| D | Minimal Local-First Notebook | `prototypes/2026-05-26-shotgun/variant-d-review.html` |
| E | Quiet AI Knowledge Lab | `prototypes/2026-05-26-shotgun/variant-e-review.html` |

**Comparison board**: `prototypes/2026-05-26-shotgun/index.html` (side-by-side iframe view)

All prototypes show the same Review Queue content — 2 pending AI drafts + 1 approved card — styled per variant direction.

**Note**: Visual mockup PNGs were not generated. The `$D` design binary requires an OpenAI API key which is not configured per project constraints (no real LLM calls). All variants use static HTML/CSS with Google Fonts CDN (no npm dependencies).

---

## Variant A: Calm Editorial Knowledge Desk

### Visual Mood
Magazine-layout reading experience. Single-column layout (max-width: 720px), generous vertical whitespace, serif headlines establish editorial authority. The Review Queue feels like a literary editor's desk — cards are long-form reading items, not tickets.

### Key Design Decisions
- **Serif-forward**: Source Serif 4 for all card titles, DM Sans for body at 1.6 line-height
- **3-layer shadows**: Subtle depth without tactile overload
- **Wide reading column**: 720px max-width signals "this is for reading"
- **Amber pill badges**: Soft rounded status indicators for ai_draft
- **Approved cards dim to 55% opacity**: Clears visual field for pending items

### Pros
- Best reading experience for long-form knowledge cards
- Serif headlines give each card editorial weight — knowledge feels substantive
- Generous whitespace reduces cognitive load during review
- Most clearly different from SaaS dashboards and chatbot UIs
- Matches the "editorial authority" pillar of the design direction exactly

### Cons
- Single-column is space-inefficient on wide screens (though intentional)
- Serif rendering quality varies across OS/browsers
- May feel too slow/sparse for users who want to scan quickly
- Requires good font loading strategy (FOUT risk with Google Fonts)

### Scores
| Dimension | Score | Note |
|-----------|-------|------|
| Product fit | 9/10 | Perfect match for knowledge compiler identity |
| Implementation risk | Low | Mostly CSS + font import, no structural changes |
| Accessibility risk | Low | High contrast text, serif/sans distinction helps scanning |
| Differentiation | 9/10 | Unlike Notion (no serif), Linear (no warmth), Claude (no editorial) |
| Best page: Review Queue | 9/10 | Reading-first review experience |
| Best page: Card Detail | 10/10 | Where serif reading truly shines |
| Best page: Library | 7/10 | Grid browsing less natural in single-column |

---

## Variant B: Warm Research Library

### Visual Mood
Browsing a physical card catalog in a sunlit library. Cards have 4-layer paper-like shadows, warm surface gradient (white to subtly warm at top 40%), and catalog-entry density. The Library page is the conceptual center — even the Review Queue borrows the card-catalog metaphor.

### Key Design Decisions
- **4-layer shadow stack**: `0px 0.6px` to `0px 22px` with sub-0.02 opacity — tactile paper depth
- **Card surface gradient**: `linear-gradient(180deg, rgba(255,255,255,0.4) 0%, transparent 40%)` — subtle paper sheen
- **Pill badges**: Rounded status markers as "catalog slips"
- **10px card radius**: Softer than A but not as round as Apple
- **Serif for H1/H2 only**: DM Sans handles subheadings, keeping the library navigable

### Pros
- Most tactile and warm — the "paper" feel is immediately felt
- Multi-layer shadows create genuine depth without heaviness
- Catalog metaphor maps naturally to library browsing
- Works well in both list and grid layouts
- The gradient sheen on cards is a subtle delight

### Cons
- 4-layer shadows may feel over-designed to minimalism-oriented users
- Gradient sheen is a non-standard pattern — harder to implement consistently
- Card-catalog metaphor may feel old-fashioned to some
- Highest CSS complexity among the 5 variants

### Scores
| Dimension | Score | Note |
|-----------|-------|------|
| Product fit | 8/10 | Catalog metaphor fits, but less editorial authority |
| Implementation risk | Medium | 4-layer shadows + gradient sheen more complex |
| Accessibility risk | Low-Medium | Shadows don't affect contrast, but sheen could on some surfaces |
| Differentiation | 8/10 | Distinct from standard flat/material design |
| Best page: Library | 10/10 | The catalog metaphor is perfect here |
| Best page: Review Queue | 8/10 | Works but less decision-forward |
| Best page: Card Detail | 7/10 | Tactile but less reading-optimized |

---

## Variant C: Precision Review Console

### Visual Mood
The Review Queue is unmistakably the center of the product. Swiss-precision layout with DM Sans-dominant typography, minimal serif use (display only), compact decision cards with grid-column layout (content left, actions right). The sidebar is reorganized around pipeline stages, not pages.

### Key Design Decisions
- **CSS Grid card layout**: `grid-template-columns: 1fr auto` — content on left, approve/reject buttons stacked on right
- **Sans-dominant**: Serif only for brand name and display headings
- **Pipeline sidebar**: Navigation organized by workflow stage (Sources → Review → Library), not by feature
- **2-layer functional shadows**: Clean, precise, no decorative depth
- **Compact cards**: 18px padding, 2-line summaries — optimized for scanning and deciding

### Pros
- Most decision-forward — approve/reject actions are impossible to miss
- Pipeline sidebar reinforces the approval workflow as product structure
- Compact layout enables faster review of many drafts
- Cleanest visual hierarchy for "what needs my attention right now"
- Grid layout for cards is a novel pattern in knowledge tools

### Cons
- Less warm — precision trades some of the "paper" feeling
- Pipeline sidebar is a conceptual change from feature-based navigation
- Serif reduction loses editorial authority for card titles
- May feel too task-manager-like for a knowledge tool
- Compacting cards reduces reading comfort for long summaries

### Scores
| Dimension | Score | Note |
|-----------|-------|------|
| Product fit | 7/10 | Great for approval workflow, less for knowledge browsing |
| Implementation risk | Medium | Pipeline sidebar restructure + grid card layout |
| Accessibility risk | Low | High contrast, clear action hierarchy |
| Differentiation | 8/10 | Pipeline nav is unique in knowledge tools |
| Best page: Review Queue | 10/10 | This is where precision console shines |
| Best page: Library | 6/10 | Pipeline metaphor less natural for browsing |
| Best page: Card Detail | 6/10 | Compact style conflicts with deep reading |

---

## Variant D: Minimal Local-First Notebook

### Visual Mood
Radical subtraction. No shadows (border-only cards), no serif typography, no decorative elements. The "local-first" identity is felt through extreme simplicity — file paths are visible (in mono font) on hover, cards stack edge-to-edge in a single bordered list. Content is the only decoration.

### Key Design Decisions
- **Zero shadows**: Cards use `border: 1px solid` only — flat design
- **Sans-only**: No serif anywhere, DM Sans for everything
- **Mono file paths**: Provenance shown on hover — `~/.mindforge/sources/docs/architecture.md → ai_draft → needs review`
- **Edge-to-edge card list**: Cards share borders (no border-top except first), creating a continuous reading list
- **Compact stats**: Stats in a single bordered row, not separate cards

### Pros
- Most honest about local-first identity — nothing is hidden
- Fastest to implement — minimal CSS, no shadow stacks
- File path visibility builds trust (users see where data lives)
- Cleanest separation from "designed" SaaS products
- Least likely to feel dated in 2 years

### Cons
- Feels under-designed for a knowledge reading experience
- No serif means no editorial authority — all text feels equal
- Border-only cards lack the warmth specified in the design direction
- May read as "unfinished" rather than "minimal"
- Mono font paths on hover are clever but hidden — discoverability issue
- Loses the "warm paper" feeling that differentiates from tools like Obsidian

### Scores
| Dimension | Score | Note |
|-----------|-------|------|
| Product fit | 5/10 | Honest but missing warmth and editorial quality |
| Implementation risk | Very Low | Minimal CSS, no complex shadows or gradients |
| Accessibility risk | Low | Simple, high contrast |
| Differentiation | 5/10 | Minimal is common; this doesn't stand out |
| Best page: Card Detail | 7/10 | Content-first works for deep reading |
| Best page: Library | 6/10 | Clean but flat — lacks browsing delight |
| Best page: Review Queue | 5/10 | Approval actions feel undifferentiated |

---

## Variant E: Quiet AI Knowledge Lab

### Visual Mood
The UI tells the story of knowledge transformation. AI-generated draft cards use italic serif for summaries (signaling "this is provisional") with an amber left border accent. Human-approved cards use roman (non-italic) with a green left border. The process flow indicator (Source → Review → Library → Recall/Wiki) sits above the content, making the knowledge pipeline visible. The aesthetic is process-awareness, not AI hype.

### Key Design Decisions
- **Italic serif for AI drafts**: `font-family: var(--font-serif); font-style: italic` — typographic signal that this content is provisional
- **Colored left border accents**: Amber 4px border for drafts, Forest Green 4px border for approved — immediate visual status recognition without reading labels
- **Process flow bar**: Horizontal step indicators above the page header — shows where review sits in the full pipeline
- **Gradient card backgrounds**: Subtle color bleed from the left border (8% gradient stop)
- **Status as typography**: The core differentiator — AI content looks different from human-approved content

### Pros
- Most innovative concept — typography as status signal is elegant
- Process flow bar gives users orientation in the knowledge pipeline
- Italic-for-AI pattern is memorable without being gimmicky
- Colored left borders allow status recognition from card edges alone
- Strongest expression of "knowledge transformation" identity

### Cons
- Italic body text reduces readability (italic is harder to read at length)
- Process flow bar takes vertical space and may feel like a tutorial element
- Two different serif treatments (italic/non-italic) doubles font loading weight
- May feel like it's trying too hard to signal "AI is here"
- Gradient bleed from borders is subtle but adds implementation complexity
- Risk: users may interpret italic as "less important" rather than "AI-generated"

### Scores
| Dimension | Score | Note |
|-----------|-------|------|
| Product fit | 7/10 | Innovative process visibility, but italic readability concern |
| Implementation risk | Medium | Gradient bleed + italic switching across pages |
| Accessibility risk | Medium | Italic body text reduces readability; process flow may confuse screen readers |
| Differentiation | 9/10 | Most unique — no other knowledge tool uses typography this way |
| Best page: Review Queue | 8/10 | Process-aware review is conceptually strong |
| Best page: Library | 6/10 | Italic/roman distinction less meaningful for approved-only library |
| Best page: Card Detail | 7/10 | Colored borders guide status but italic body fatigues |

---

## Head-to-Head Comparison

| Dimension | A (Editorial) | B (Library) | C (Precision) | D (Minimal) | E (Lab) |
|-----------|---------------|-------------|---------------|-------------|---------|
| **Warmth** | 9 | 9 | 6 | 4 | 7 |
| **Editorial authority** | 10 | 7 | 4 | 2 | 7 |
| **Approval clarity** | 7 | 7 | 10 | 5 | 8 |
| **Reading comfort** | 10 | 8 | 5 | 7 | 6 |
| **Differentiation** | 9 | 8 | 8 | 5 | 9 |
| **Implementation ease** | 8 | 6 | 6 | 10 | 6 |
| **Accessibility** | 9 | 8 | 9 | 9 | 6 |
| **Library browsing fit** | 7 | 10 | 6 | 6 | 6 |
| **Overall fit** | **9.0** | **7.9** | **6.9** | **5.8** | **7.1** |

---

## Recommended Top 2

### 1st: Variant A — Calm Editorial Knowledge Desk (9.0/10)

**Why**: Best balance of warmth, editorial authority, and reading comfort. The serif-forward approach most clearly differentiates MindForge from Notion, Obsidian, SaaS dashboards, and AI chatbots. It centers the knowledge reading experience while keeping approval actions clear. Implementation risk is low — mostly CSS and font loading.

**Risk to watch**: Serif rendering quality on Windows. Mitigation: Georgia fallback is a credible serif on all platforms.

### 2nd: Variant B — Warm Research Library (7.9/10)

**Why**: Strongest tactile warmth and best browsing experience (Library page is the conceptual home). The catalog metaphor is charming and different. However, the 4-layer shadow + gradient sheen approach adds implementation complexity for diminishing returns vs. Variant A's cleaner editorial approach.

**Best as**: The Library page design within Variant A's overall editorial framework. The two are complementary — A for reading/approval, B's card treatment for library browsing.

---

## What to Test in /plan-design-review

1. **Serif rendering quality**: Test Source Serif 4 on Windows (ClearType), macOS (Core Text), and Linux. Verify Georgia fallback.
2. **Serif vs. warm paper contrast**: Ensure `#1c1b18` on `#faf9f5` meets WCAG AA (4.5:1) for body text at 15px.
3. **Card shadow perception**: Verify 3-layer shadows are visible on common displays (not just Retina). May need slight darkening.
4. **Approval button prominence**: Test that `#2d7d5f` approve button is distinguishable from `#c04040` reject for color-blind users (add icon differentiation if needed).
5. **Font loading strategy**: FOUT handling — system sans-serif must not cause layout shift when serif loads.
6. **Amber draft badge on warm paper**: Ensure `#b8860b` on `#faf9f5` has sufficient contrast (may need to darken slightly).
7. **Mobile sidebar**: Confirm sidebar collapse behavior on viewports < 768px.
8. **Merge candidates**: Can Variant B's card shadows be selectively applied to the Library page within Variant A's framework? Worth exploring.

---

## Self-Review

| Check | Verdict |
|-------|---------|
| Are variants too generic? | No — each has a distinct typographic, spatial, and material personality |
| Too close to Notion/Obsidian/Linear/Claude? | No — serif editorial approach is distinct from all four |
| Do they center Review/Approval? | Yes — all prototypes show Review Queue as the primary page |
| Are they implementable without backend changes? | Yes — all are CSS + font loading only |
| Are they calm but not boring? | Yes — warmth + editorial authority is quietly distinctive |
| Are they refined but not gimmicky? | A/B pass this. E risks gimmick (italic AI). D risks under-designed. |
| Do they preserve local-first / approval-first identity? | Yes — no cloud syncing UI, no auto-approve patterns |
