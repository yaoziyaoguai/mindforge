# MindForge Web Design System (DESIGN.md)

> **Agent Instruction**: This is a structured design system and visual identity document. Any future UI changes MUST read this file first. Adherence to these rules is non-negotiable to maintain the "Harness Engineering" stability of MindForge.

## 1. Design Philosophy
- **Identity**: A local-first, approval-first personal knowledge compiler.
- **Aesthetic**: Calm, Editorial, Knowledge Desk, Trustworthy, Low-distraction.
- **Goal**: The UI should be an "invisible desk" that supports deep focus on knowledge processing. Visuals must prioritize information hierarchy and reading comfort over flair.

## 2. Product Boundary & Core User Journey
The UI MUST rigidly reflect the compiler pipeline:
1. **Sources / Import**: Gathering raw input (Cubox, Markdown files, etc.).
2. **Review (ai_draft)**: The critical human-in-the-loop stage. AI proposes, human disposes.
3. **Library (human_approved)**: The immutable long-term memory.
4. **Recall / Wiki**: Using and exploring the approved knowledge.
5. **Export**: Safe, staged output (e.g., preparing content for Obsidian).

**CRITICAL**: Lab/Internal features (Graph, Sensemaking, Entity, Community) are NOT part of the main path and must be visually secondary.

## 3. Visual Tone & Rules
- **Editorial Experience**: Use whitespace as a structural element rather than borders.
- **Reference-image Direction (Batch 1)**: Clean, modern, light, spacious, soft pastel cards, and a calm purple accent.
- **Depth**: Subtle shadows and very soft gradients are allowed for shell/cards/primary CTA hierarchy. They must stay quiet and product-like, never glossy or marketing-heavy.
- **Calmness**: No aggressive colors. Status indicators must be muted and consistent.

## 4. Typography
- **Reading Area**: Use high line-height (`leading-relaxed` or `leading-loose`) and constrained widths (`max-w-3xl`) for text.
- **Font**: Prefer clean, highly legible sans-serif (like Inter or system defaults). For long-form reading, high-quality serif fonts may be used if integrated into the editorial theme.

## 5. Color Tokens (Base Palette)
- **Background (Canvas)**: Use light white / warm off-white / lavender-tinted neutrals.
    - Prefer `--mf-bg`, `--mf-app-bg`, `--mf-surface`, and `--mf-sidebar`.
- **Text (Ink)**:
    - Primary: deep blue-black (`--mf-text-primary`).
    - Secondary/Meta: muted blue-gray (`--mf-text-secondary`, `--mf-text-tertiary`).
- **Accent (Action)**:
    - Soft purple (`--mf-accent`) for navigation active state, setup CTA, and first-run guidance.
- **Status Color**:
    - Safe/Approved: muted green (`--mf-approved`).
    - Warning/Action Required: muted amber (`--mf-warning`).
    - Lab/Internal: muted neutral / secondary text. Do not make lab features look like a main path.

## 6. Spacing & Layout
- Follow a strict 4px/8px grid.
- Navigation Sidebar must be distinct but not overwhelming.
- The "Main Desk" area must have generous padding to prevent claustrophobia.

## 7. Component Rules
- **Buttons**: Primary CTAs may use a soft purple gradient and restrained shadow. Secondary buttons stay white with a fine border.
- **Cards**: Rounded cards, subtle borders, and restrained shadows are allowed for repeated items and framed tools. Avoid heavy report panels.
- **Forms**: Clean, focused inputs. Use labels and clear helper text.

## 8. Navigation Rules
- Sidebar is Home-first for first-run clarity, then the knowledge pipeline: `Sources` -> `Review Drafts` -> `Library` -> `Recall / Wiki` -> `Export`.
- The sidebar must include a clear Demo Mode / Configure Real Model card when provider readiness is not `ready`.
- `Lab` features must be grouped, collapsed by default, and visually distinct (e.g., using a "Lab" icon or different accent).

## 9. Review / Approval Interaction Rules
- **Approval Desk**: The `Review` page is a high-stakes area.
- The `Approve` action must be the most unambiguous element on the page.
- AI-generated content (ai_draft) must be clearly labeled and distinguished from human-approved content.

## 10. Provider / Source / Export Boundary Rules
- **Fake vs. Real**:
    - **Real Provider** (LLM Provider): Must be explicitly opted-in. Show a "Live/Real" status only when active.
    - **Fake Provider**: Default safe/demo path. Use a "Demo/Sandbox" badge.
- **Source vs. Workspace**:
    - **SourceAdapter** (e.g., Cubox): Input only.
    - **Human Workspace** (e.g., Obsidian): Staged binding/safe export. Do NOT write directly to the real vault without a "safe export" review.

## 11. Anti-patterns (Do NOT implement)
- ❌ **SaaS Dashboard**: No charts, no complex metrics, no "Overview" widgets.
- ❌ **Dark Mode**: Currently out of scope. Stick to the "Paper" theme.
- ❌ **Auto-Approval**: All changes must be explicitly approved by a human.
- ❌ **Blurry Boundaries**: Never hide whether a provider is real or fake.

## 12. Visual Remediation Rules (Slice 2.5 — 2026-06-02)

These rules capture the visual corrections applied to move the UI from "engineering dashboard" toward "calm knowledge desk."

### 12.1 BoundaryBadge Rules
- **Single neutral chip style** for all boundary types except `live` (which uses a muted warm tone).
- Never more than 2 badge color variants visible at once.
- Never use `text-[10px] font-bold uppercase` — badges are metadata, not stickers.
- Badge should blend into the reading flow, not interrupt it.

### 12.2 Boundary Callout Rules
- Use **one unified callout style** (`border-stone-200/70 bg-stone-50/50`) across all pages.
- Never use page-specific callout colors (purple/blue/green variants).
- Callout text must be **one short sentence** — not a paragraph of rules.
- Callout is a contextual note, not a rule announcement banner.

### 12.3 SafetyBar Rules
- SafetyBar is a **status indicator**, not a system alert bar.
- Reduce icon density — shield icon for local-only status + subtle checkmark for "all clear" is sufficient.
- Never use `AlertTriangle` for routine status display; reserve for genuine warnings only.
- Never use heavy `border-r` separators between segments — whitespace separation is sufficient.
- Background: `bg-stone-50/50`, text: `text-xs text-muted`.

### 12.4 Color Token Discipline
- **Primary accent**: Use a single accent color (`--mf-accent`, currently purple `#5b46f6`) consistently.
- Do NOT introduce new badge/semantic colors beyond the defined token set.
- Tailwind semantic utilities are globally overridden in `styles.css` during Batch 1 to keep legacy pages aligned with the CSS token direction. Prefer CSS tokens for semantic meaning, Tailwind utilities for layout.

### 12.7 Reference-Image Batch 1 Rules (2026-06-02)

- **Shell**: Sidebar uses a light lavender-white surface, rounded active items, purple active indicator, and a visible workspace footer.
- **Home / Welcome Desk**: The first viewport must show Configure Real Model, demo/real provider state, overview cards, and the Knowledge Flow: Import -> AI Draft -> Human Review -> Approved Knowledge -> Export.
- **Setup / Model Configuration**: Setup must read as a guided model configuration flow, not a raw engineering form. The visible guide is Provider -> Connection -> Model -> Validate/Test.
- **Reality Boundary**: Beautiful UI must never imply unsupported backend capability. Missing capabilities are represented as disabled, empty, hidden, or explicitly documented gaps.

### 12.6 Product Quality Pass (Slice 2.6 — 2026-06-02)

- **Home Knowledge Desk**: The Home page must act as a welcoming mission control. Use metric cards with soft pastel icon backgrounds to provide immediate state awareness.
- **Visual Pipeline**: Ground the user in the compiler philosophy using a horizontal "Knowledge Flow" diagram. Clearly label the human-in-the-loop "Human Review" step.
- **First-run Guidance**: Prioritize the "Configure Real Model" action for demo users. It should be an elegant product card, not a system warning.
- **Depth & Dimension**: Use very subtle multi-layer shadows (`cssShadows.raised`) on main canvas cards to provide a sense of hierarchy without breaking the "Flat" philosophy (no heavy gradients).
- **Navigation Clarity**: The sidebar should have a distinct header with the product logo/icon. Group labels should be uppercase, small, and low-contrast metadata.
- **Safety as a Service**: The top-right header area should provide quiet reassurance of local-only status and demo/live mode, rather than a full-width alert bar.

## 12. Accessibility & Readability
- Ensure WCAG AA contrast ratios.
- All interactive elements must have clear focus states.
- Screen reader labels for all icons.
