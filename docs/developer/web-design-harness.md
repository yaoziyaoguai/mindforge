# MindForge Web Design Harness & Engineering Plan

## 1. Why MindForge Needs a Design Harness
MindForge is a local-first, knowledge-intensive tool. As an AI-assisted project, it is susceptible to "UI drift" where different AI agents introduce inconsistent styles, unnecessary complexities, or violate the core "approval-first" philosophy. 

The **Design Harness** provides a stable, machine-readable boundary that ensures:
1. **Consistency**: All agents follow the same visual language.
2. **Predictability**: UI changes are driven by a central contract (`DESIGN.md`).
3. **Safety**: Critical boundaries (Fake vs. Real providers) are never blurred.

## 2. DESIGN.md and Harness Engineering
In Harness Engineering, we don't just write code; we build the *harness* that guides and validates the code. 
- `web/DESIGN.md` is the **Contract**.
- This document (`web-design-harness.md`) is the **Execution Plan**.
- `web-design-audit.md` is the **Baseline & Validation Matrix**.

## 3. Why Documents First?
We write documentation before changing any code to:
- Establish a "Stability Barrier" before implementation.
- Allow AI Agents to verify their own plans against these documents.
- Prevent accidental scope creep or architectural violations.

## 4. UI Refactoring Loop
Every future UI slice MUST follow this loop:
1. **Design Intent**: Reference `web/DESIGN.md` to state the goal.
2. **Small Slice Plan**: Define a minimal, testable set of changes.
3. **Implementation**: Coding Agent applies changes following the plan.
4. **Frontend Gate**: Run linting and basic checks.
5. **Browser Smoke**: Verify the page loads and is interactive.
6. **Screenshot / Visual Evidence**: Capture proof of the change.
7. **Design Review**: Verify against `web/DESIGN.md`.
8. **Focused Fix**: Correct any deviations.

## 5. UI Refactoring Queue (Slices)

### Slice 1: Navigation / IA Cleanup
- **Goal**: Align the sidebar with the compiler pipeline.
- **Entry**: `DESIGN.md` established.
- **Exit**: Sidebar reordered: Sources -> Review -> Library -> Recall -> Export. Lab features collapsed.
- **Acceptance Criteria**: 
    - Navigation order matches pipeline.
    - Lab features do not distract from main path.

### Slice 2: Provider / Source / Export Boundary Clarity
- **Goal**: Clear visual distinction between different data states.
- **Exit**: Explicit "Demo" vs "Live" badges. Clear separation of SourceAdapter and Export targets.
- **Acceptance Criteria**:
    - User can immediately tell if a provider is real or fake.
    - Export destination is clearly marked as "Safe Staging".

### Slice 3: Review Approval Desk
- **Goal**: Focus the `Review` page on the `Approve` decision.
- **Exit**: High-contrast, unambiguous `Approve` action. Distilled "ai_draft" view.
- **Acceptance Criteria**:
    - The `Approve` button is the primary visual anchor.
    - AI-generated text is visually distinct.

### Slice 4: Library / Wiki Reading Experience
- **Goal**: Enhance the "Knowledge Desk" feeling.
- **Exit**: Improved typography, line-height, and padding in reading areas.
- **Acceptance Criteria**:
    - Text blocks are readable and focused.
    - No distracting dashboard elements.

### Slice 5: Validation Readiness Visual Pass
- **Goal**: Final polish for human users.
- **Exit**: Global CSS cleanup, consistent spacing, final alignment with `DESIGN.md`.

## 6. When to Stop & Ask User
Stop and ask the user if:
- A change requires a new dependency.
- A design rule in `DESIGN.md` is ambiguous or conflicting.
- The UI change requires modifying backend API semantics.
- A "Small Slice" exceeds 300 lines of change.
