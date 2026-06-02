# MindForge Web Design Audit Matrix

This document baselines the current state of the Web UI against the `DESIGN.md` contract.

## Global Components

### Navigation / Sidebar
- **Current role in main path**: Global navigation.
- **Current observed risk**: Grouping is abstract (`Processing`, `Using`); navigation order doesn't strictly follow the compiler pipeline.
- **DESIGN.md rule affected**: Section 8 (Navigation Rules).
- **Recommended action**: Reorder and rename groups to match: Sources -> Review -> Library -> Recall/Wiki -> Export.
- **Priority**: P0
- **Suggested slice**: Slice 1
- **Acceptance criteria**: Sidebar items match the user journey.

### Provider Status Display (SafetyBar)
- **Current role in main path**: Displaying security and provider state.
- **Current observed risk**: Terminology like "Ready" vs "Demo" is text-based and potentially subtle.
- **DESIGN.md rule affected**: Section 10 (Provider Boundary Rules).
- **Recommended action**: Introduce high-contrast badges/icons for "Sandbox/Demo" vs "Live/Real Provider".
- **Priority**: P0
- **Suggested slice**: Slice 2
- **Acceptance criteria**: Visual clarity on whether LLM calls are "real".

## Main Path Pages

### Setup
- **Current role in main path**: First-time configuration.
- **Current observed risk**: Page is overly complex; mixes system check with provider setup. High visual density.
- **DESIGN.md rule affected**: Section 11 (Anti-patterns), Section 3 (Visual Tone).
- **Recommended action**: Simplify layout, use "Editorial" spacing to separate concern. Clarify LLM opt-in.
- **Priority**: P1
- **Suggested slice**: Slice 2
- **Acceptance criteria**: Clean, step-by-step setup experience.

### Sources / Import
- **Current role in main path**: Input ingestion.
- **Current observed risk**: Mixed types of sources without clear hierarchy.
- **DESIGN.md rule affected**: Section 2 (Product Boundary).
- **Recommended action**: Group sources by adapter type. Focus on "Import" action.
- **Priority**: P2
- **Suggested slice**: Slice 2
- **Acceptance criteria**: Clear view of ingestion status.

### Review
- **Current role in main path**: Human-in-the-loop processing (ai_draft -> approval).
- **Current observed risk**: List-heavy; the actual `Approve` decision is not the primary visual anchor.
- **DESIGN.md rule affected**: Section 9 (Review / Approval Interaction Rules).
- **Recommended action**: Create an "Approval Desk" layout. High visibility for `Approve`/`Reject`.
- **Priority**: P0
- **Suggested slice**: Slice 3
- **Acceptance criteria**: Decision-making is the fastest path.

### Library
- **Current role in main path**: Permanent memory storage.
- **Current observed risk**: Card-heavy; feels more like a dashboard than a library.
- **DESIGN.md rule affected**: Section 1 (Aesthetic), Section 4 (Typography).
- **Recommended action**: Shift towards "Editorial" card design. Improve line-height and text focus.
- **Priority**: P1
- **Suggested slice**: Slice 4
- **Acceptance criteria**: Reading a card feels like reading a well-formatted note.

### Recall / Wiki
- **Current role in main path**: Knowledge retrieval and synthesis.
- **Current observed risk**: Standard search/wiki layout.
- **DESIGN.md rule affected**: Section 4 (Typography), Section 7 (Component Rules).
- **Recommended action**: Enhance focus mode. Remove sidebar distractions during deep reading.
- **Priority**: P2
- **Suggested slice**: Slice 4
- **Acceptance criteria**: Immersive knowledge exploration.

### Export
- **Current role in main path**: Staging content for human workspace (Obsidian).
- **Current observed risk**: Potentially confusing boundaries on where data is going.
- **DESIGN.md rule affected**: Section 10 (Export Boundary Rules).
- **Recommended action**: Explicitly label as "Safe Staging Area". Review content before "Final Commit" to Obsidian.
- **Priority**: P1
- **Suggested slice**: Slice 2
- **Acceptance criteria**: No ambiguity on local file system writes.

## Lab / Internal Pages

### Graph / Sensemaking / Entity / Community
- **Current role in main path**: Experimental features (Internal/Lab).
- **Current observed risk**: Currently visible in the sidebar, competing with the main path.
- **DESIGN.md rule affected**: Section 2 (Product Boundary).
- **Recommended action**: Collapse under a "Lab" section. Use distinct visual treatment to signal "Experimental".
- **Priority**: P0
- **Suggested slice**: Slice 1
- **Acceptance criteria**: Main path remains uncluttered.

## Summary of Priorities
- **P0**: Navigation (S1), Provider Clarity (S2), Review Desk (S3), Lab Hiding (S1).
- **P1**: Setup Simplification (S2), Library Reading (S4), Export Boundaries (S2).
- **P2**: Sources Grouping (S2), Recall/Wiki Polish (S4).
- **P3**: Final Visual Pass (S5).
