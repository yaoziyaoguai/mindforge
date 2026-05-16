# MindForge Local Console Design System

## Product Identity

MindForge Local Console is the local-first Web surface for MindForge. It is a
single-user, localhost-only personal knowledge workbench for people who want to
configure, inspect, review, approve, reject, and recall their own knowledge
cards without living in a CLI.

It is not a SaaS product, not an admin dashboard, and not a marketing website.
It should feel like a quiet local tool sitting over the user's own files:
transparent, reversible where possible, and explicit whenever a write can
change long-term memory.

## Design Principles

- Calm: default surfaces are quiet, readable, and low-drama. The UI avoids
  marketing copy, busy gradients, and decorative animation.
- Trustworthy: every page shows what local state it is reading and what action
  will happen next.
- Beginner-safe: empty states explain the next command or local action instead
  of assuming CLI fluency.
- Review-focused: drafts are treated as work awaiting human judgment, not as
  generated content to rubber-stamp.
- Local-first: the product language, status labels, and Safety Bar emphasize
  localhost, current vault, and local files.
- Explicit write actions: write-capable controls are visually distinct and
  state exactly what will be written.
- Transparent configuration: model setup status is shown as configured/missing
  only; secret values never appear.
- No hidden automation for approval: `human_approved` can only be produced by
  an explicit user confirmation.

## Layout

The app uses a fixed left sidebar, a top Safety Bar, and a main content area.
Review detail pages may add a right detail panel when there is enough horizontal
space.

- Left sidebar: persistent navigation for Home, Setup / Config, Sources,
  Drafts / Review, and Recall / Knowledge.
- Top Safety Bar: visible on every page and never hidden behind a drawer. It
  summarizes local-only status, active vault, model setup status,
  write mode, and pending draft count.
- Main content area: one primary task per page. Avoid nested cards and avoid
  landing-page hero structures.
- Optional right detail panel: used for draft metadata, source context, or the
  approval panel. On narrow screens it stacks below the draft body.

## Core Navigation

- Home: current workspace, vault, model setup, draft, approved, recall, and
  next-action status.
- Setup / Config: configuration checklist, model setup readiness, source
  import readiness, vault path readiness, safety mode, and next steps.
- Sources: source registry status and read-only scan/source state when
  available. Import controls only appear when the backend can perform the
  operation safely.
- Drafts / Review: `ai_draft` queue, draft status, safe source summary, tags,
  metadata, and clear empty state.
- Recall / Knowledge: local lexical recall over approved cards and simple
  knowledge status. No RAG, embeddings, or semantic merge in the first version.

## Safety Bar Rules

Safety Bar content is part of the product contract:

- Show "Local only" and the host when running on `127.0.0.1` / `localhost`.
- Show the current vault path. If it looks like a real user vault, use amber
  tone and plain warning language.
- Show model setup status as `configured` or `missing`.
- Show model setup indicator. Never show API key values.
- Show write mode as `read-only` or `explicit approval required`.
- Show pending draft count.
- Warn when a real vault or real provider is active.

The bar should use short labels and avoid raw stack traces or config dumps.

## Color Semantics

- Green: safe, local, ready, local-default, completed.
- Amber: needs attention, real environment, incomplete config, missing index,
  real vault warning.
- Red: destructive or irreversible write, failed safety condition, dangerous
  action.
- Blue / primary: the next recommended action and ordinary navigation focus.
- Neutral: reading, review, metadata, informational state.

These colors carry meaning. Do not use red for decoration or green for ordinary
branding.

## Component Semantics

- `ConfigChecklist`: checklist rows for required config paths, model setup
  status, source import readiness, and vault readiness.
- `StatusCard`: compact status summary with a label, value, state color, and
  one optional next action.
- `SafetyBar`: always-on local safety summary; consumes only secret-safe status
  data from the API.
- `SourceList`: lists available source adapters and read-only source state.
- `DraftList`: lists `ai_draft` candidates only, using safe frontmatter fields.
- `DraftViewer`: shows draft content and source metadata for one selected card.
- `ApprovalPanel`: holds approve/reject controls and confirmation state.
- `EmptyState`: explains what is empty, why it matters, and the next action.
- `ErrorState`: human-readable failure explanation plus next action; raw
  traceback is hidden unless the user explicitly runs debug tooling outside the
  ordinary UI.
- `NextActionCard`: one recommended next action, not a generic marketing CTA.

## Approval Interaction

Approve is not a casual button. It means `ai_draft -> human_approved`, which
allows the card to enter recall and project context as long-term memory.

Rules:

- The approval panel must show source/draft context before the approve control.
- Approve requires a second confirmation.
- The user must explicitly confirm that they reviewed the source.
- The API payload must include `confirm: true` and `reviewed_source: true`.
- Reject may include an optional reason.
- The first version does not need inline draft editing.
- The first version does not need undo.
- No background process can mark a card `human_approved`.

## Empty And Error States

Every empty state tells the user what to do next:

- No vault: configure `vault.root` or run the setup command.
- No sources: place supported files in the configured inbox or use a supported
  import path.
- No drafts: check model setup, then add source via Watch Add or Import.
- No approved cards: review and approve at least one draft before recall.
- No recall index: search can still do memory rebuild when supported; suggest
  `mindforge index rebuild` when applicable.

Every error includes:

- A short human-readable explanation.
- Whether the action read local files, attempted a write, or did neither.
- One next action.
- No raw traceback for ordinary users.

## Accessibility

- Use semantic `nav`, `main`, `section`, `article`, and `button` elements.
- Every interactive control has a clear accessible label.
- Keyboard focus states are visible and high-contrast.
- Buttons are real buttons, not clickable divs.
- Color is supported by text labels, not the only signal.
- Text contrast must remain readable in calm/neutral states and warning states.

## First-Version Visual Thesis

MindForge Local Console should feel like an Obsidian-adjacent local workbench
with Linear-like status clarity and Raycast-like command precision. It is dense
enough for repeated personal use, but simple enough that a beginner can open it
and understand the next local action without reading CLI docs first.
