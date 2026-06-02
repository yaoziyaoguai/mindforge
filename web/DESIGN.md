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
- **Flat Design**: No physical shadows, no gradients, no glassmorphism.
- **Calmness**: No aggressive colors. All status indicators must be muted.

## 4. Typography
- **Reading Area**: Use high line-height (`leading-relaxed` or `leading-loose`) and constrained widths (`max-w-3xl`) for text.
- **Font**: Prefer clean, highly legible sans-serif (like Inter or system defaults). For long-form reading, high-quality serif fonts may be used if integrated into the editorial theme.

## 5. Color Tokens (Base Palette)
- **Background (Canvas)**: Use warm, paper-like tones.
    - `stone-50` or `zinc-50`. Avoid pure `#FFFFFF` for the main canvas.
- **Text (Ink)**:
    - Primary: `stone-800` or `zinc-800`.
    - Secondary/Meta: `stone-500` or `zinc-500`.
- **Accent (Action)**:
    - `stone-800` (Neutral Bold) or a muted terracotta (`orange-800`) strictly for the `Approve` action.
- **Status Color**:
    - Safe/Approved: Muted green (`emerald-700/800`).
    - Warning/Action Required: Muted amber (`amber-700`).
    - Lab/Internal: Muted purple (`indigo-600`).

## 6. Spacing & Layout
- Follow a strict 4px/8px grid.
- Navigation Sidebar must be distinct but not overwhelming.
- The "Main Desk" area must have generous padding to prevent claustrophobia.

## 7. Component Rules
- **Buttons**: Flat. No shadows. Subtle hover state (`bg-stone-100` or slight opacity change).
- **Cards**: Avoid nested cards. Use simple vertical spacing and typography to separate items.
- **Forms**: Clean, focused inputs. Use labels and clear helper text.

## 8. Navigation Rules
- Main navigation MUST follow the pipeline order: `Sources` -> `Review` -> `Library` -> `Recall / Wiki` -> `Export`.
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
- **Primary accent**: Use a single accent color (`--mf-accent`, currently green `#2d7d5f`) consistently.
- Do NOT introduce new badge/semantic colors beyond the defined token set.
- The Tailwind `primary: #2368d1` (blue) conflicts with CSS `accent: #2d7d5f` (green) — prefer CSS tokens for semantic meaning, Tailwind utilities for layout only.

### 12.5 Density & Breathing Room
- Page sections must have visual breathing room — avoid nesting `border + p-4` inside `border + p-4`.
- Callout sections use `px-4 py-3` (not `p-4`) to reduce vertical weight.
- Text in informational sections uses `text-xs` (not `text-sm`) to reduce visual shouting.

## 12. Accessibility & Readability
- Ensure WCAG AA contrast ratios.
- All interactive elements must have clear focus states.
- Screen reader labels for all icons.
