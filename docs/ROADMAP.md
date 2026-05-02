# MindForge Roadmap

This roadmap tracks product direction and explicit non-goals. Completed release details are summarized in [CHANGELOG.md](./CHANGELOG.md); current completion state is in [ROADMAP_PROGRESS.md](./ROADMAP_PROGRESS.md).

## Current Position

Current version: **v0.7.22**.

MindForge v0.x is a local-first CLI for personal learning memory:

- local source ingestion through adapters;
- five-stage LLM processing with safe fake default;
- explicit human approval;
- local lexical/hybrid recall;
- local review planning;
- project context packs;
- local-only telemetry;
- CLI onboarding and demo vault.
- read-only Obsidian Binding / Bridge.
- Local Usability as a formal milestone.
- packaged default prompts, templates, and configs.

## Product Shape & Phase Plan

This section is the **canonical product framing** for MindForge v0.x. The
historical milestone sections below (v0.4.3 / v0.5.x / v0.6.x / v0.7.x) are
preserved as audit trail and are summarized here through the Phase lens.

### Product Shape

MindForge v0.x is a **local-first, CLI-as-first-product personal learning
memory tool** organized around an **Obsidian-centered knowledge workspace**.
Concretely, this means the following statements are normative and must hold
for every Phase 1 commit:

- **CLI is the first product shape.** The CLI is not a debug entry point. It
  is the only user-facing surface in v0.x. Web UI, TUI, and Obsidian plugin
  are explicit non-goals for the entire v0.x line.
- **Obsidian-centered workspace.** Obsidian is the central knowledge
  workbench, not merely an export target. CLI-generated `ai_draft` /
  `human_approved` artifacts and the review workspace must integrate
  naturally with Obsidian's file workflow. Obsidian holds **only
  human-readable knowledge assets**; runtime / state / cache / index / logs
  / SQLite / vector / graph data are kept strictly outside Obsidian.
- **Pluggable, configurable data ingestion.** The data entry point is the
  `SourceAdapter` port. Cubox is a first-class adapter, but the system is
  **not** Cubox-only. `LocalFolderAdapter` / `MarkdownInboxAdapter` /
  `CuboxMarkdownAdapter` / `CuboxExportMockAdapter` (and future adapters)
  are equal implementations of the same port. The processor depends on
  `SourceDocument` and never on Cubox-specific details. Adapter discovery,
  registry, and configuration are first-class Phase 1 capabilities.
- **Pluggable, configurable knowledge strategies.** Different sources and
  different intents must not be funneled through one mindless summarization
  recipe. The Processing Pipeline depends on a strategy interface
  (provisionally `KnowledgeStrategy` / `ExtractionStrategy` /
  `MergeStrategy`), not on a hard-coded summarizer. The strategy set will
  grow to cover reading-note, concept-card, project-context,
  evidence-append, question-extraction, and claim-extraction shapes. Phase 1
  may ship the minimum strategy set, but the architectural seam must be
  reserved.
- **Explicit human approval is the load-bearing wall.** The AI may only
  produce `ai_draft`. The transition to `human_approved` is reachable only
  via an explicit user `approve` command; auto-approval is permanently
  forbidden. Merge semantics (approve-as-new-card / append-as-evidence /
  link-to-existing-card / merge-candidate / reject / defer / split) must
  be modeled as first-class outcomes of the review/approve flow, not as
  ad-hoc CLI flags.
- **Local-first safety by default.** Fake provider is the default; real LLM
  is opt-in only. `.env` is read only through the dedicated env loader. No
  network IO in the default path. No formal Obsidian note writes outside
  the staged-export workflow.

### The CLI closed loop (Phase 1 acceptance scenario)

A v0.x user must be able to walk this loop end-to-end **using only the
CLI**, on a disposable demo vault, with the fake provider, with zero `.env`
reads, and with zero network IO:

1. Configure at least one safe data source (default: `plain_markdown` over
   `examples/demo-vault`).
2. Load that source.
3. Produce a `SourceDocument`.
4. Choose / apply a knowledge strategy appropriate to the source and intent.
5. Run the Processing Pipeline to generate `ai_draft`.
6. Review / edit / approve the draft via explicit CLI commands.
7. Produce `human_approved` only via that explicit approval path.
8. Output the result into the Obsidian-centered workspace (staged where the
   write-gate requires it).
9. Use `recall` / `review` / project-context queries to retrieve the
   approved knowledge locally.

This loop is the Phase 1 acceptance scenario. `doctor` and `next` must
guide the user along it; `commands` and `docs/` must make every step
discoverable.

### Phase 0 — Architecture Quality Milestone (CLOSED)

**Status: closed 2026-05.** Service, presenter, and CLI-adapter boundaries
are locked by 106 architecture fitness functions (5 boundary test files
across `process_service` / `review_service` / `approval_service` / 3
presenters / 2 CLI adapters). Detailed scope and closure summary are in the
[v0.7.20–v0.7.23 Architecture Quality Milestone](#v0720v0723-architecture-quality-milestone)
section below.

Phase 0 deliverables that Phase 1 must continue to honor:

- Reverse-dependency direction (CLI → presenter → service → data) is
  one-way.
- `ai_draft` is generated only by AI; `human_approved` is reachable only
  via the explicit approve chain.
- Fake provider remains the default; real LLM is opt-in only.
- Services do not import Typer / Rich / `dotenv`; presenters do not mutate
  state.
- Real LLM SDKs / `dotenv` / RAG / vector store / UI-framework imports are
  banned where they would represent boundary violations.

### Phase 1 — CLI Product Shape Completion (CURRENT)

**Status: in progress.** Goal: the CLI closed loop above is real, smooth,
and discoverable end-to-end on a disposable demo vault with the fake
provider.

**Completion definition (11 criteria):**

1. CLI is documented as the only v0.x user entry point; `doctor` and `next`
   reflect that explicitly.
2. The user can configure at least one safe data source through
   `configs/mindforge.yaml`, with `plain_markdown` over the bundled
   `examples/demo-vault` working out of the box.
3. **Cubox is documented as a first-class adapter** in the Roadmap and
   user-facing docs. Short-term, the Cubox adapter contract is validated
   against Cubox export samples and a `CuboxExportMockAdapter`-style
   fixture; real Cubox API integration is deferred to Phase 3.
4. The adapter mechanism is pluggable and configurable: discovery via
   `sources/registry.py`, enable/disable via
   `configs/mindforge.yaml.sources.enabled`, no Cubox-only assumptions in
   any non-adapter module.
5. `SourceAdapter` → `SourceDocument` is documented as the product
   backbone, not as a v0.1 implementation detail. The boundary is enforced
   by `tests/test_process_service_boundaries.py` (Phase 0 deliverable).
6. The Processing Pipeline depends only on `SourceDocument` (already true
   at code level — must remain true through Phase 1).
7. A `KnowledgeStrategy` / `ExtractionStrategy` / `MergeStrategy` seam is
   reserved. Phase 1 may ship the minimum strategy set, but the strategy
   interface must exist as a stable extension point and must be referenced
   in the Processing Pipeline rather than written around.
8. The fake provider produces `ai_draft` reliably and is the default in
   every CLI command path.
9. The user can list / show / approve / bulk-approve drafts. Merge
   outcomes (approve-as-new-card / append-as-evidence /
   link-to-existing-card / merge-candidate / reject / defer / split) are
   modeled as first-class outcomes of the review/approve flow, even if
   only a subset is implemented in the first Phase 1 cut.
10. `human_approved` is produced only via the explicit approve chain;
    boundary is enforced by `tests/test_approval_service_boundaries.py`
    and `tests/test_cli_adapter_boundaries.py` (Phase 0 deliverables).
11. The Obsidian-centered workspace output paths are explicit: where
    `ai_draft` is shown, where the user reviews/edits, where
    `human_approved` lands, and how `recall` / `review` / project-context
    serve the Obsidian workflow are all documented and surfaced through
    `doctor` / `next`.

**Phase 1 closed-loop dogfood test (living regression spine):**

`tests/test_phase1_cubox_e2e.py` is the canonical executable specification
of the 9-step closed loop. It uses the Cubox first-class adapter
(`CuboxMarkdownAdapter`) on a real-shape sample fixture, drives the
`KnowledgeStrategy` seam (criterion 7) via `build_strategy(...)`, and
promotes the resulting `ai_draft` card to `human_approved` via the
`ApprovalDecision.APPROVE` seam (criterion 9). Any regression in either
seam, in the Cubox adapter contract, or in the workspace safety boundary
fails this test before it can reach a release.

**Phase 1 Non-Goals (explicit):**

- No Web UI, no TUI, no Obsidian plugin.
- No real LLM in the default path; no automatic `.env` reads.
- No real Cubox API (deferred to Phase 3).
- No RAG / embedding / vector store / graph database.
- No automatic approve, no automatic Obsidian vault rewrites, no automatic
  formal-note edits.
- No writing of formal Obsidian notes outside the staged-export workflow.
- No remote telemetry, no cloud sync, no background daemon.
- No file-count / line-count KPIs.
- No mechanical splitting of cohesive modules.

### Phase 2 — Repair & Polish

**Status: planned.** Goal: harden the closed loop without expanding scope.

Targets:

- Patch any gap discovered while users walk the closed loop.
- Improve adapter configuration UX (clearer errors, better defaults,
  better `doctor` diagnostics).
- Improve error messages and `next` recommendations along the loop.
- Improve `doctor` coverage for adapter / strategy / approval / Obsidian
  workspace health.
- Improve the review / approve / merge UX, especially around the merge
  outcomes listed in Phase 1 criterion 9.
- Strengthen the Obsidian-centered file workflow (staged export polish,
  manifest UX, write-gate ergonomics).
- Documentation and tests follow the loop, not the file structure.
- Fake provider remains the default safety path; nothing in Phase 2
  weakens it.

Phase 2 inherits all Phase 1 Non-Goals.

### Phase 3 — Capability Expansion

**Status: deferred.** Each item in Phase 3 requires its own scoping doc,
its own safety review, and its own explicit authorization. None of these
are blanket-approved.

Candidate expansions (each independently gated):

- Real Cubox API integration.
- Real LLM opt-in (with hard safety gates around `.env`, network, cost,
  and provider rotation).
- Additional source adapters (PDF/DOCX hardening, ChatExport variants,
  WebClip variants, etc.).
- Richer knowledge strategies beyond the Phase 1 minimum set.
- Web UI.
- Obsidian plugin.
- Disposable-vault dogfooding flows beyond `examples/demo-vault`.

Phase 3 work may not begin until Phase 1 is complete and Phase 2 has
addressed identified gaps. Re-opening any Phase 0 invariant (boundary
tests, fake-default, explicit approval, no-`.env`-by-default) requires
explicit Roadmap-level authorization.

### Historical milestone sections

The dated sections below (v0.4.3 follow-up through v0.7.20–v0.7.23
Architecture Quality Milestone) are preserved as audit trail. They are
**not** the canonical product framing — this Product Shape & Phase Plan
section is. When the historical sections and this section disagree on
direction, this section wins.

## Completed v0.4.3 Follow-Up

The docs cleanup after v0.4.3 is complete: active docs were consolidated into
user, developer, roadmap, changelog, and archive layers. Historical milestone
reviews and superseded design notes now live under `docs/archive/`.

## v0.5 Completed

v0.5 implements the minimal safe Obsidian bridge:

- configure an Obsidian vault path;
- scan Markdown read-only;
- parse frontmatter, tags, `[[wikilinks]]`, and directory structure;
- introduce `ObsidianVaultSourceAdapter` in the SourceAdapter system;
- add `mindforge obsidian doctor|scan|links|stage`;
- write candidate output only to Obsidian staging/review;
- never modify real vault source notes in the first phase;
- keep machine indexes, caches, runtime logs, and intermediate state in derived
  layers such as `.mindforge/`, SQLite, vector stores, or graph stores rather
  than formal Obsidian notes.

## v0.5.1 Local Usability Completed

v0.5.1 promotes **Local Usability / 本地友好使用** to a first-class roadmap
milestone. It is not a new feature class, not RAG, and not an Obsidian plugin.
The goal is to let a local user complete the loop from initialization to
knowledge use with fake/offline defaults and clear next actions.

Acceptance criteria:

- initialize with `mindforge init` or `mindforge init --interactive`;
- check health with `mindforge doctor`;
- discover next actions with `mindforge next`;
- discover commands with `mindforge commands`;
- add demo markdown / webclip / chat export sources;
- scan with `mindforge scan`;
- process with `mindforge process --profile fake`;
- inspect drafts with `mindforge approve list`;
- manually approve with `mindforge approve --card ...`;
- rebuild search with `mindforge index rebuild`;
- recall with `mindforge recall --query ...`;
- review with `mindforge review weekly` and `mindforge review schedule`;
- generate project context with `mindforge project context ...`;
- use the read-only Obsidian bridge with
  `mindforge obsidian doctor|scan|links|stage --dry-run`.

v0.5.1 also accepts the user-natural `mindforge next --vault PATH` form for
non-Obsidian commands, fixes command-map rendering for `[[wikilinks]]`, avoids
reading `.env` in the fake-provider local smoke path, and makes fake-provider
demo output inherit source titles instead of producing `Untitled` cards.

## v0.5.2 Packaging / Install Readiness Completed

v0.5.2 keeps the v0.5.1 local product loop intact while removing a packaged
install footgun: runtime defaults no longer assume a source checkout or repo
root current directory.

Completed scope:

- default prompts are bundled under `src/mindforge/assets/prompts/`;
- default Knowledge Card template is bundled under
  `src/mindforge/assets/templates/`;
- default configs used by `mindforge init` and default learning tracks are
  bundled under `src/mindforge/assets/configs/`;
- default asset loading uses `importlib.resources`;
- explicit user paths such as `--prompts-dir`, `--tracks`, and `--template`
  still take priority;
- SourceAdapter, SourceDocument, processor, approval, and recall architecture
  remain unchanged.

Non-goals remain explicit: no RAG / embedding, no Obsidian plugin, no live LLM
default path, no real private vault processing, and no automatic approval.

## v0.6.x Local Product UX Completed

v0.6.x polished the local product loop introduced by v0.5.x without adding new
feature classes: onboarding command UX (`init` / `doctor` / `next` /
`commands`), approval and review UX, recall search UX, local config setup UX,
and a dogfooding pack. Detailed per-version notes live under
`docs/V0_6_*.md`. v0.6.x preserved the fake-provider default safety path,
explicit human approval, and the read-only Obsidian binding.

## v0.7.0–v0.7.10 Feature Phase Completed

v0.7.0 through v0.7.10 continued user-visible work on top of v0.6.x: Obsidian
stage preview / staged export, processor and pipeline polish, recall and
review service primitives, and the first round of CLI service-boundary
cleanup. Detailed per-version notes live under `docs/V0_7_1_*.md` through
`docs/V0_7_10_*.md`. v0.7.0–v0.7.10 remained inside the "feature / UX" track.

## v0.7.20–v0.7.23 Architecture Quality Milestone

**Status: CLOSED 2026-05.** This milestone is now considered complete. All
items in the Definition of Done have been satisfied, Stop Condition #9
(default return to feature roadmap once v0.7.23 boundary tests pass) has
been reached, and no in-flight follow-up slice is planned. The milestone
is preserved here as an audit trail and as the contract that future feature
work must continue to honor (see "Closure summary" below).

This milestone is **technical debt repayment**, not feature stagnation. After
the local-usable MVP (v0.5.x), the local product UX phase (v0.6.x), and the
v0.7.0–v0.7.10 feature phase, `cli.py` had grown into a monolithic command
file mixing CLI parameter parsing, business semantics, presentation, and side
effects. Continuing to add features on top of that monolith would compound
design cost. This milestone hardens module boundaries before the next feature
phase begins.

It is **not** open-ended optimization. It has a named scope, an acceptance
checklist, explicit stop conditions, and a default trigger to return to the
feature roadmap once v0.7.23 is complete.

It is inserted **after the last user-visible feature phase (v0.7.0–v0.7.10)**
and **before any new feature class** because the cost of new features goes up
sharply when service / presenter / CLI adapter boundaries are unstable.

### Closure summary (2026-05)

This subsection is the canonical statement that the milestone is closed.

**Why we are stopping here, deliberately and not by exhaustion.** The
milestone declared in advance that v0.7.23 boundary tests would be the final
scoped slice and that the default action upon their completion is to return
to the feature roadmap rather than open a v0.7.24 governance slice (see Stop
Condition 9 below). All four scoped commits have landed and pass quality
gates; the next reasonable architectural slice (Layer 3: `policy` / `context`
/ `workflow` boundary tests) has clearly diminishing marginal value relative
to user-visible feature work, and there is no current evidence of a concrete
component regressing. Continuing past this point would convert the milestone
into open-ended optimization, which the milestone itself explicitly forbids.

**Commits that constitute the milestone:**

1. `0f9e8b0` — `docs(roadmap): add architecture quality milestone`. Roadmap
   formalization: scoped this milestone with three optimization axes, ten
   Definition-of-Done items, nine stop conditions, and an explicit
   "return-to-feature-roadmap" trigger.
2. `386df60` — `test(architecture): add process service boundary checks`.
   Layer 1 (service) — `process_service` AST static boundary tests.
3. `d0189d8` — `test(architecture): add review and approval service boundary
   checks`. Layer 1 follow-up — `review_service` and `approval_service` AST
   boundary tests, completing the service-layer triad.
4. `b7b798c` — `test(architecture): add presenter and cli boundary checks`.
   Layer 2 (presenter + CLI adapter) — parametrized AST boundary tests across
   all three presenters and both CLI adapter modules.

**Boundary test coverage at closure** (architecture fitness functions):

- `tests/test_process_service_boundaries.py` — 15 tests
- `tests/test_review_service_boundaries.py` — 16 tests
- `tests/test_approval_service_boundaries.py` — 16 tests
- `tests/test_presenter_boundaries.py` — 45 parametrized tests
  (3 presenters × 15 checks)
- `tests/test_cli_adapter_boundaries.py` — 14 tests
  (5 parametrized × 2 CLI files + 4 standalone)

Total: **106 AST boundary tests across 5 services + 3 presenters + 2 CLI
adapters**. Plus the v0.7.20-era hybrid behavior + AST suite
(`tests/test_process_service.py`) and `tests/test_safety_policy.py`, which
remain in force.

**Three optimization axes — closure assessment:**

- **Module optimization (模块优化).** CLI is now a thin adapter (parameter
  parsing + IO + service/presenter orchestration); use-case business semantics
  live in `process_service` / `review_service` / `approval_service` /
  `recall_service`; user-visible rendering lives in `approve_presenter` /
  `recall_presenter` / `review_presenter`. Each component has a stable
  surface area locked by an `__all__` snapshot or AST-derived public-name
  snapshot, plus function and dataclass count caps to prevent silent
  regrowth. Component responsibilities are explicit and small without being
  fragmented into anemic helpers.
- **Architecture optimization (架构优化).** Service / presenter / CLI
  adapter boundaries are now enforced by AST tests rather than relying on
  documentation alone. Reverse-dependency direction is enforced (services
  cannot import CLI or presenters; presenters cannot import CLI or
  cross-`use-case` services; `obsidian_cli` cannot reverse-import `cli`).
  Real LLM SDK / `dotenv` / RAG / embedding / vector store / UI-framework
  imports are explicitly banned where they would represent boundary
  violations. The fake-provider default safety path is protected by both
  behavior tests (`test_process_service.py`) and the `safety_policy`
  alignment assertion in the boundary suite. The `ai_draft` /
  `human_approved` boundary is locked at five layers (process, review,
  approval, presenters, CLI), each with an appropriately-tuned literal
  assignment rule.
- **Programming art (编程艺术).** No production code was modified during
  the four boundary-test commits. No file was split to reduce line count.
  No anemic helper module was created. The five `*_boundaries.py` files are
  intentionally structurally similar but **not** sharing fixtures — each
  component's boundary declaration remains independently readable and
  modifiable. CLI is intentionally **not** locked by line count or file size,
  as a deliberate anti-KPI decision: "thin" is defined here as "business
  semantics live in services," not as "few lines." Each test function carries
  Chinese learning-style commentary explaining *why* the boundary matters,
  not only what it checks.

**Why we did not extend to Layer 3 (policy / context / workflow):**

- `safety_policy.py` is already covered by `tests/test_safety_policy.py`
  behavior tests, and is reverse-referenced by
  `test_process_service_boundaries.py::test_safety_policy_declares_relevant_boundaries`,
  which keeps three named safety boundaries (`fake_provider_default` /
  `no_real_llm` / `no_env_read`) honest from the consumer side.
- `app_context.py` / `project_context.py` / `multi_project_context.py` are
  already covered by behavior tests.
- `obsidian_workflow.py` is the v0.7.14 extracted workflow and has its own
  behavior tests.
- There is **no current evidence** that any of these components are
  regressing toward monolith status, importing forbidden dependencies, or
  bypassing safety boundaries. The marginal value of adding AST static
  boundary tests for them now is substantially below the marginal value of
  resuming user-visible feature work.
- This is consistent with the earlier statement in this milestone:
  "Future `*_boundaries.py` slices on `recall_service` / `policy` /
  `context` / `workflow` are possible but **not** part of this milestone
  unless evidence shows a concrete component is regressing."
- Should a regression signal appear later (e.g., a forbidden import sneaks
  into one of these modules during feature work), a small follow-up slice
  can add the matching boundary file using the same template, without
  reopening this milestone.

**Residual risks honestly stated:**

- AST boundary tests prevent **silent** boundary erosion — they do not
  guarantee that the production code inside each module is maximally elegant
  or fully refactored. Several modules (notably `cli.py` at ~4500 lines)
  remain large by design choice; the milestone explicitly accepted this in
  exchange for keeping all user-facing commands discoverable in one place.
- The presenter and service layers are protected by snapshot locks and
  count caps; these caps have +1 buffer and will require an intentional
  test update when legitimate growth occurs. That is by design (force a
  PR-level conversation), but it does mean that future contributors must
  understand the boundary tests rather than treat them as inscrutable red.
- The `human_approved` literal rule has different shapes per layer
  (banned-everywhere in `approval_service`, `status=`-keyword-only in
  services that read the status, plus `Compare` / `in` / f-string / Typer
  Option allowances in CLI). Future contributors editing these files must
  consult the boundary test docstring before adding a new literal.
- Behavior tests outside the boundary suite were not refactored in this
  milestone. Some legacy test files still mix concerns, but this is
  deliberately out of scope: tests are protective, not architectural.

**Return to feature roadmap — preserved invariants.**

When user-visible feature work resumes, the following invariants — now
encoded as boundary tests — must continue to hold and **must not be
weakened to make a feature pass**:

1. `ai_draft` is generated only by AI; `human_approved` is reachable only
   via `approver.approve_card`, called only by
   `approval_service.approve_explicit_card`, called only by an explicit
   user `approve` command in `cli.py`. No new path is allowed to bypass
   this chain.
2. The fake provider remains the default; real LLM use is opt-in only,
   gated by the `mindforge.llm.build_providers` factory and the
   `requires_real_env` flag in `process_service`.
3. `.env` loading flows only through `mindforge.env_loader.load_dotenv_silently`.
   No other module — including any future feature module — may import
   `dotenv` directly.
4. No formal Obsidian note write is performed without the explicit dogfood
   workflow boundary; presenters and services do not call `write_text`.
5. No RAG / embedding / vector store / Obsidian plugin / Web UI / TUI
   without an explicit roadmap-authorized scoping doc and a fresh review
   of these boundary tests.
6. Reverse-dependency direction (CLI → presenter → service → data /
   helper modules) is one-way. New features may extend this chain but
   may not create the reverse.

If a planned feature would require relaxing any of these invariants, that
is a roadmap-level decision and triggers a fresh planning round; it is
not a license to weaken the boundary tests.

**Next planning round.** The next planning round is explicitly **not** an
extension of this milestone. See "Return to feature roadmap" below.

### Three optimization axes

The milestone is organized along three explicit axes. Every governance commit
must serve at least one axis without violating the others.

**1. Module optimization (模块优化)**

- CLI becomes a thin adapter (parameter parsing, IO, side-effect orchestration
  only).
- Service layer owns business semantics and use-case orchestration.
- Presenter layer owns user-visible rendering (Markdown / JSON / Rich).
- Policy / context / workflow layers respectively own safety policy, runtime
  context, and integration flow.
- Every new module must have a clear responsibility, a stable input/output
  shape, and independent test value.
- Do **not** split a monolith into many low-cohesion fragments.

**2. Architecture optimization (架构优化)**

- Service / presenter / CLI adapter / policy / context / workflow boundaries
  remain stable across releases.
- `process_service` / `review_service` / `approval_service` / `recall_service`
  must not regress into new small monoliths.
- Critical boundaries are locked by AST / dependency boundary tests, not by
  documentation alone.
- Fake provider default safety path stays stable.
- `ai_draft` / `human_approved` boundary stays explicit (only AI generates
  `ai_draft`; only explicit approve transitions to `human_approved`).
- No real LLM by default; no `.env` reads; no formal Obsidian note writes; no
  RAG / embedding / Obsidian plugin / Web UI / TUI.

**3. Programming art (编程艺术)**

- Do not split files just to reduce line count.
- Do not perform mechanical relocation.
- Do not introduce anemic helpers.
- Do not produce low-cohesion fragmentation.
- Prefer clear naming, stable boundaries, and small but complete modules.
- Tests must protect architectural intent, not just implementation details.
- Documentation must explain *why* a design exists, not only *what* was done.

### Completed governance

- **v0.7.20 — `process_service` extraction.** Goal: separate `process`
  use-case business semantics from CLI. Not new feature; not line-count KPI.
  Boundary protected: `process_service` does not import Typer / Rich / Console
  / RunLogger / dotenv; fake-safety boundary expressed as a single
  `requires_real_env` flag. Acceptance: `tests/test_process_service.py`
  covers AST bans on the listed forbidden imports plus structured-error
  behavior.
- **v0.7.21 — `approve_presenter` extraction.** Goal: lift approve list /
  show / bulk / single-card / routing rendering out of `cli.py`. Not new
  feature. Boundary: presenter does not mutate state, does not call
  `approve_card` / `approve_explicit_card`, accepts a Rich `Console` from the
  caller. Acceptance: full byte-level CLI parity vs prior tag plus AST static
  bans.
- **v0.7.21 checkpoint** (`docs/V0_7_21_APPROVE_PRESENTER_CHECKPOINT.md`):
  independent audit, scoring, and residual-issue capture for v0.7.21.
- **v0.7.22 — `review_presenter` extraction (weekly only).** Goal: lift
  weekly-review Markdown + JSON + Rich rendering out of `cli.py`, strictly
  scoped to `review weekly`. Not new feature. Boundary: presenter consumes
  only `WeeklyReviewResult`; does not import Typer / Rich / RunLogger;
  returns `str` / `dict` so CLI keeps `json.dumps` decisions. The other five
  review subcommands (`due` / `mark` / `schedule` / `backlog` / `stats`)
  remain inline in `cli.py` because they do not yet have a service-layer
  result shape; forcing them into the presenter would pollute the presenter
  boundary. Acceptance: byte-level parity for `review weekly` Markdown and
  `--format json`.
- **v0.7.22 checkpoint** (`docs/V0_7_22_REVIEW_WEEKLY_PRESENTER_CHECKPOINT.md`):
  independent audit including a `process_service` size / cohesion read-only
  audit (9.2/10, no monolith risk).

### Current / next governance candidate

- **v0.7.23 — `process_service` AST static boundary tests (completed
  2026-05).** Goal: add automated architectural guardrails around
  `process_service` so it cannot silently regress into a small monolith or
  silently grow dependencies on CLI / presenter / Typer / Rich / RunLogger /
  real LLM SDKs / `.env` / Obsidian write layer / RAG / embedding. v0.7.23
  was **explicitly not new feature** and **did not modify production code**;
  it added `tests/test_process_service_boundaries.py` (15 AST tests) covering
  reverse-dependency bans, real-LLM SDK bans, `os.environ` access bans,
  status-mutation call bans, `human_approved` literal-assignment ban,
  `__all__` snapshot lock, function and dataclass count caps, an import
  allow-list, and `safety_policy` boundary alignment.

- **v0.7.23 second follow-up — presenter + CLI adapter AST boundary tests
  (completed 2026-05).** Extended the architecture-fitness-function pattern
  from Layer 1 (service) to Layer 2 (presenter + CLI adapter). Added
  `tests/test_presenter_boundaries.py` (45 parametrized AST tests across
  `approve_presenter` / `recall_presenter` / `review_presenter`) and
  `tests/test_cli_adapter_boundaries.py` (14 tests across `cli.py` +
  `obsidian_cli.py`). **Zero production code change.** Together with Layer 1,
  the boundary test suite now totals **106 AST tests** locking import graphs,
  reverse-dependency direction, real-LLM SDK / dotenv / UI-framework / RAG
  bans, file-write and `os.environ` bans (where applicable), and public
  surface snapshots across **5 services + 3 presenters + 2 CLI adapters**.
  Layer 2 specifics:
  - **presenters** are pure transformations: per-presenter import allow-list,
    no `approver` / `reviewer`, no cross-`use-case` service imports, no
    status mutation calls, no `write_text` / `open()`, no `os.environ`,
    `"human_approved"` only as `status=` keyword.
  - **CLI adapters** are **not** locked by line / function caps (anti-KPI;
    "thin" means business semantics live in services, not row count). Hard
    bans: real LLM SDK direct import, real LLM credential string literals
    (`OPENAI_API_KEY`, etc.), direct `dotenv` import, RAG/embedding,
    `obsidian_cli` reverse-importing `cli`. Positive assertions: must
    `import mindforge.env_loader` + call `load_dotenv_silently`; must
    `import mindforge.llm` + call `build_providers`; must call
    `approve_explicit_card` (approval delegation must exist).
  - **CLI `human_approved` literal rule** is more permissive than for
    services: allowed as `keyword`, list/tuple/set/dict element, `Compare`
    right-hand side (`c.status == "human_approved"`), `in` expression, and
    f-string fragment. Banned only as Assign / Return value (which would
    indicate CLI bypassing the approval delegation).
  Layer 3 candidates (policy / context / workflow / `recall_service`) are
  possible but **not** part of this milestone unless evidence shows a
  concrete regression.

### Definition of Done

The milestone is complete when **all** of the following hold:

1. `cli.py` no longer carries primary business semantics (only parameter
   parsing, IO, and orchestration of services and presenters).
2. The `process` / `approval` / `review` / `recall` main paths each have a
   service or presenter boundary owning their business or rendering logic.
3. `process_service` is protected by AST boundary tests (delivered by
   v0.7.23).
4. Presenter modules do not mutate business state.
5. Service modules do not perform Rich / Typer / `console` output.
6. The fake-provider default safety path is protected by tests (not only by
   documentation).
7. The `ai_draft` / `human_approved` boundary is protected by tests.
8. `ruff`, `pytest`, smoke, and `git diff --check` all pass — or, when a
   given step intentionally skips `pytest` (for documentation-only work), the
   skip decision has been confirmed via an explicit Ask User round and
   recorded in the corresponding checkpoint.
9. `docs/ARCHITECTURE_MAP.md` and the per-version checkpoint documents stay
   in sync with the source tree.
10. After acceptance, work returns to the next user-visible feature phase
    rather than continuing further architectural rework.

### Stop conditions

Trigger **any** of the following and the milestone halts (or the in-progress
slice is rolled back / asked back to the user):

1. Governance starts introducing a new user-visible feature.
2. The change is justified only by reducing line counts.
3. The change is mechanical relocation (file moves without responsibility
   change).
4. Low-cohesion fragmentation appears (the same use-case is now spread across
   many small files with no independent semantics).
5. CLI external behavior must change → stop and Ask User.
6. The change requires reading real `.env`, calling a real LLM, or writing
   formal Obsidian notes → stop.
7. The change requires RAG / embedding / Obsidian plugin / Web UI / TUI →
   stop.
8. Findings indicate a manual review / push should happen first → stop.
9. Once v0.7.23 boundary tests are complete and passing, the default action
   is to return to the feature roadmap rather than open a v0.7.24 governance
   slice.

### Return to feature roadmap

After v0.7.23 acceptance, the next planning round is **explicitly not** an
extension of this milestone. It is the next feature-phase scoping round, with
candidate directions including (each requires its own scoping doc and is
**not** an architectural-quality slice):

- Real-LLM opt-in (with hard safety gates).
- Realistic Obsidian dogfooding on disposable vault copies.
- Packaging / install readiness polish.
- Source adapter expansion.
- Other user-visible features.

None of those directions are part of the Architecture Quality Milestone.

## v0.8 Local AI Knowledge Loop (CLOSED, planning closure)

**Status: stage-closed.** v0.8 ran as an autonomous 8-stage milestone built
on Phase 1 (CLI Product Shape Completion). It did **not** activate any real
LLM, did **not** call any real Cubox API, and did **not** write any real
Obsidian vault. The full loop ran on the bundled fake provider, on offline
Cubox export fixtures, and on disposable demo-vault paths only. v0.8 is
**not yet pushed and not yet tagged**; closure is gated on human review of
the v0.8 commits before any push or tag is performed.

What v0.8 delivered (planning-stage, not user-visible behavior change):

- KnowledgeStrategy seam (Protocol + StrategyContext + registry) with
  21 AST guard tests; `build_strategy(...)` is the single seam used by
  `process` and by the closed-loop e2e test.
- ApprovalDecision first-class enum (7 members) + `apply_decision`
  dispatcher; only `APPROVE` is wired (byte-identical to existing
  `approve_card`); the other 6 raise `NotImplementedDecisionError`.
- `CuboxApiAdapter` skeleton with `parse_export` (offline) only;
  `fetch_inbox` is **explicitly** `NotImplementedError`. Credential
  redaction is enforced by `__repr__` overrides + tests; metadata never
  carries the credential.
- `SourceMux` + `MuxStats` for cross-source deterministic dedup
  (first-seen wins); not wired into the default Scanner / CLI path
  (boundary enforced by AST tests). Dedup is **not** semantic merge.
- `mindforge cubox dry-run --export` and `mindforge cubox preview-ai-draft`
  as opt-in offline dogfood entries; preview forces `active_profile=fake`
  and uses a `_NoOpRunLogger` so no run-state, no card payload, and no
  vault write can leak from the preview path.
- Boundary tests: `test_provider_opt_in_boundary.py` (fake-default,
  no-secret-env, no-network, no-source-import, redacted repr/str) and
  `test_review_approval_boundary.py` (only the explicit approve chain
  produces `human_approved`; cubox CLI cannot import approve/review/vault).
- Active-safety promotion of provider `__repr__` / `__str__` in
  `OpenAICompatibleProvider` and `AnthropicCompatibleProvider`: explicit
  safe repr exposes only `name` and `credential_present`, never `api_key`
  or `base_url`. `tests/test_provider_opt_in_boundary.py` §9 enforces
  this as an active invariant rather than relying on Python's default
  `object.__repr__`.
- `docs/WORKSPACE_HUMAN_APPROVED_MERGE_PLAN.md` writes the workspace
  writer / human-approved merge boundary down as a **planning** doc with
  no production code; the writer remains a stub.

v0.8 explicit non-goals (preserved):

- No real LLM activation.
- No real Cubox API call.
- No real Obsidian vault write.
- No automatic `human_approved` promotion.
- No automatic approve.
- No RAG / embedding / semantic merge.
- No Web UI / TUI / Obsidian plugin.
- No PDF / Doc / cloud-drive source adapter.
- No new heavy dependency.
- No `.env` read in any default path.

v0.8 closure rule: closure means "stage-locally complete and ready for
human review"; it does **not** mean tagged or pushed. Tagging and pushing
require explicit human authorization.

## v0.9 Data Source & Plugin Architecture Readiness (PLANNED)

**Status: planned, planning-only.** v0.9 is the **planning** milestone that
moves MindForge from "Cubox-first with one offline adapter" toward a
**multi-source-ready** architecture **without** changing user-visible
behavior, **without** implementing new sources, and **without** activating
any real provider or API. v0.9 is plan-on-paper plus boundary tests; any
new adapter implementation is its own follow-up milestone with its own
safety review.

### Goal

Make `SourceAdapter` → `SourceDocument` strong enough as a contract that:

- a future PDF / DOCX / cloud-drive / new-vendor adapter can be added
  without touching `processor` / `KnowledgeStrategy` / `review` /
  `approval`;
- the absence of such adapters today is an honest design choice, not a
  hidden coupling;
- Cubox is and remains **one** `SourceAdapter`, not the architectural
  center.

### Core principles (12, inherited and tightened)

1. Cubox is a `SourceAdapter`, not a core architectural concept.
2. Sources are pluggable; the current stage stays Cubox-first in
   dogfooding.
3. `Processor` and `KnowledgeStrategy` depend only on `SourceDocument` —
   never on `CuboxApiAdapter`, never on `CuboxMarkdownAdapter`.
4. Every new source adapter must emit `SourceDocument` (no parallel data
   path, no Cubox-shaped shortcut).
5. `SourceMux` + deterministic dedup is the only multi-source merge
   primitive; semantic merge is explicitly out of scope.
6. v0.9 does **not** implement PDF / DOCX / cloud-drive `SourceAdapter`.
7. v0.9 does **not** read or process real private corpora.
8. v0.9 does **not** add RAG / embedding / vector store / semantic merge.
9. v0.9 does **not** add an Obsidian plugin.
10. v0.9 does **not** write real Obsidian vault content.
11. v0.9 does **not** introduce a new heavy dependency.
12. v0.9 does **not** rewrite the architecture; existing seams
    (`SourceAdapter`, `SourceMux`, `KnowledgeStrategy`, `ApprovalDecision`)
    are the foundation.

### Sub-stages (planning-only)

#### A. SourceAdapter interface hardening

- Document the **minimum** `SourceAdapter` interface (load / can_handle /
  parse semantics, error contract, where credential lives, where it
  must not leak).
- Document `SourceDocument` as the **only** cross-adapter data contract.
- Add AST/boundary tests asserting `processor.py`, `pipeline.py`,
  `strategies/*`, `review_service.py`, `approval_service.py`,
  `approver.py` do not import any concrete `*_adapter` / source-specific
  module (extending the existing `cubox_api` / `cubox_markdown` guards
  to a generic invariant: "no concrete source name appears in any
  non-source module").
- This is **tests + docs only**; no new production code.

#### B. Source plugin registry planning

- Plan a lightweight, **explicit** local plugin registry (single
  `sources/registry.py` extension; no dynamic class loading; no entry
  points; no plugin discovery from `sys.path`).
- Plugins must be enumerable, auditable, and disable-able from
  `configs/mindforge.yaml`.
- Out of scope: dynamic loading, plugin entry points, third-party plugin
  install paths, package-discovery hooks.
- This stage produces only a planning doc + boundary tests asserting
  the registry never reaches network, never reads `.env`, never imports
  unlisted modules.

#### C. SourceMux / deterministic dedup readiness

- Document who owns dedup across sources, when it runs in the pipeline,
  and what the keying contracts are (default `content_hash`; alternate
  `key_fn` injection point; first-seen wins).
- Document the explicit boundary: `SourceMux` is **not** a
  knowledge-merge layer and **not** a semantic-merge layer. Anything
  beyond byte-level dedup belongs to a future explicit milestone with
  its own safety review.
- No embedding. No vector similarity. No LLM-mediated merge.

#### D. Cubox-first dogfood continuation

- Cubox stays the **first** real adapter for dry-run / preview-ai-draft
  dogfood scenarios.
- No real Cubox API call. No real private corpus. Fixture-first,
  fake-provider-first, dry-run-first.
- The existing offline `parse_export` path is the only Cubox path
  exercised in v0.9.

#### E. Future source candidates (docs only)

- It is allowed to **list** candidate future source types that already
  fit the offline-fixture-first model: local Markdown vaults (already
  supported), exported web clippings, manually imported notes,
  exported chat transcripts.
- It is **not** allowed to implement PDF / DOCX / cloud-drive / Obsidian
  auto-organization in v0.9.
- It is **not** allowed to add a new heavy dependency to satisfy any
  future source candidate.

#### F. Architecture guardrails (tests-first)

- Boundary tests enforce, statically and at runtime:
  - `processor.py` does not import any concrete `*_adapter`;
  - `strategies/*` does not import any concrete `*_adapter`;
  - `approval_service.py` / `approver.py` do not import source modules;
  - `review_service.py` / `recall_service.py` do not import source
    modules;
  - `ai_draft` / `human_approved` boundary cannot be bypassed by any
    source plugin (the explicit `approve_card` chain remains the only
    promotion path);
  - no source plugin can write outside `staged/` / `runs/` / `state/`
    boundaries documented in
    `docs/WORKSPACE_HUMAN_APPROVED_MERGE_PLAN.md`.
- Information Hiding remains the design north star: each module exposes
  the minimum public surface needed to satisfy the contract.
- No mechanical file splitting. No new monolith. No anemic abstraction.
  Every new module must have a clear responsibility, a stable I/O
  surface, and independent test value.

### Definition of Done (v0.9)

- `SourceAdapter` minimum interface is documented and frozen for v0.9.
- `SourceDocument` is documented as the unique cross-adapter contract.
- Boundary tests for "no concrete source name in non-source modules"
  pass for `processor`, `pipeline`, `strategies`, `review`, `approval`.
- A planning doc (`docs/SOURCE_PLUGIN_READINESS.md` or equivalent)
  records the registry / mux / dogfood / future-candidates / guardrails
  decisions in one place.
- No new source adapter is implemented.
- No `.env` read. No real LLM call. No real Cubox API call. No real
  vault write. No new heavy dependency.
- ruff / pytest / `git diff --check` green.

### Stop conditions (v0.9)

- Any sub-stage starts implementing a real new adapter → STOP, move to
  a dedicated milestone.
- Any sub-stage requires a heavy dependency → STOP, scope to a separate
  decision.
- Any sub-stage requires touching the explicit-approval chain → STOP,
  human authorization required.
- Any sub-stage drifts into RAG / embedding / semantic merge → STOP,
  out of v0.9 scope by definition.

### Return to feature roadmap

After v0.9 closes (planning + guardrails complete), candidate next
milestones — each independently scoped, gated, and authorized — include
real Cubox API opt-in, real LLM provider activation, workspace writer
TDD, additional `SourceAdapter` implementations. None of these are
implied or pre-approved by v0.9.

### External research alignment — Source ingestion (research addendum)

This addendum records the public-domain landscape consulted while
shaping the `SourceAdapter` / `SourceMux` / `SourceDocument` contract
above, and locks the deliberate **borrow / do-not-copy** stance
MindForge takes against each pattern. None of these references
introduces a dependency, a runtime call, or a default behavior
change; this is purely a documentation alignment to prevent future
drift toward "MindForge is just a connector hub / MCP wrapper /
LangChain-loader registry / Obsidian importer".

**Industry references consulted**:

1. **Model Context Protocol (MCP) — Resources / Tools / Prompts**
   distinction. MCP frames *resources* as passive context the model
   can read, *tools* as active actions the model can invoke, and
   *prompts* as templated instructions. Source: MCP architecture
   discussions (publicly indexed, 2024).
2. **Airbyte source connector specification** — `spec` (config
   schema) + `discover` (capability discovery: streams, sync modes,
   primary keys, CDC support) + sync-mode contract (Full Refresh /
   Incremental / Deduped / CDC). Source: Airbyte connector docs
   (`docs.airbyte.com/connector-development/`).
3. **LangChain document loaders / LlamaIndex readers** — broad
   "load anything into a document object" surface, with documented
   limitations: weak provenance, no sandboxing, third-party API
   coupling, limited input validation, rate-limit fragility. Source:
   LangChain + LlamaIndex documentation (publicly indexed).
4. **Content-addressable storage + content-hash deduplication**
   (CAS / SHA-256 / BLAKE3) — the standard pattern of
   "fingerprint → key-value lookup → store-once". Source: classic
   CAS literature + cloud-storage best practices.
5. **Local-first software principles** — data-on-device, no cloud
   round-trip required for read/write, explicit user agency over
   sync, auditable local state. Source: Ink & Switch local-first
   essay + downstream PKM-tool design discussions.
6. **PKM second-brain ingestion patterns** — "send-to-app" (Obsidian
   Web Clipper, Readwise Reader, Cubox), file-watch import (Obsidian
   sync), API pull (Notion / Readwise integrations). Source: tool
   docs + community write-ups.

**What MindForge borrows (selectively)**:

- The **MCP "resource vs tool vs prompt" boundary**: MindForge's
  `SourceAdapter` lives strictly on the **resource / ingestion**
  side. It produces normalized `SourceDocument`s; it never exposes
  itself as a *tool* the LLM can invoke, and it never doubles as a
  *prompt* surface. (Adapters expose `load(...)` that the
  `SourceMux` / processor calls deterministically, not LLM-decided
  invocations.)
- The **Airbyte-style explicit capability declaration**: each
  `SourceAdapter` declares its capabilities (`can_handle`, sync
  surface, dry-run support, credential requirements) as part of
  the v0.9 §A "minimum interface" so the runtime knows what the
  adapter is allowed to do **before** invoking it. Capability
  declarations are local-first config; no remote registry is
  consulted to discover them.
- The **content-addressable dedup pattern**: `SourceMux` uses
  `content_hash` (SHA-256 over a normalized representation) as the
  default dedup key — the canonical CAS pattern, applied
  in-process and offline. This is already documented in v0.9 §C.
- The **local-first data-on-device principle**: defaults read
  exports / files / fixtures already on disk; any real network
  pull is opt-in per adapter, per profile, with an explicit
  credential surface.
- The **PKM "send-to-app then review" model**: the canonical user
  workflow is "save / export / drop a file locally → MindForge
  ingests → review → approve". MindForge does **not** reach into
  cloud accounts by default.

**What MindForge deliberately does NOT copy**:

- **MindForge is not an MCP wrapper.** `SourceAdapter` is not an
  MCP server; it does not expose itself as a tool surface for an
  LLM to call. Adapters are called by the deterministic processing
  pipeline, not by model decisions. (A future "MindForge as MCP
  resource provider" milestone, if ever proposed, would be its
  own dedicated milestone with its own safety review and would
  not change this layer.)
- **No LangChain document-loader registry framing.** LangChain
  loaders advertise breadth ("we load anything"); MindForge keeps
  the input surface small, owned, and provenance-preserving. Each
  adapter is a deliberate, audited integration, not a discovered
  pip package.
- **No LlamaIndex reader-as-RAG-frontend framing.** LlamaIndex
  readers feed an embedding/index pipeline; MindForge readers
  feed `SourceDocument` → `KnowledgeStrategy` → `ai_draft` →
  explicit approve. There is no embedding step on the default
  ingestion path.
- **No silent credential or `.env` consumption inside an
  adapter.** Real-API adapters must declare an explicit credential
  surface (e.g. `CuboxApiCredential`); they must never read
  `.env` implicitly during normal operation, must never print
  secrets in `__repr__`, and must default to a fake / dry-run
  path that requires no credential at all.
- **No "auto-sync everything" connector framing.** Airbyte's full
  sync-mode matrix (CDC / dedup-history / full-refresh-overwrite)
  is intentionally **not** ported. The v0.9 ingestion contract
  is single-shot, idempotent, dry-run-first; continuous-sync
  semantics belong to a different product shape.
- **No "auto-organize Obsidian" framing.** PKM tools that reach
  into the user's vault and rewrite files are explicitly
  rejected; Obsidian / OPS is the human review workspace, not a
  machine target. (Already locked by v0.9.x Anti-positioning #4.)
- **No global / cloud plugin registry.** Adapters live in-tree or
  are loaded from a local config; there is no remote discovery
  service that can introduce a new ingestion path without an
  explicit code review and explicit user opt-in.
- **No adapter that bypasses `KnowledgeStrategy`.** A
  `SourceAdapter` produces `SourceDocument`s; it must never
  generate `ai_draft` directly, must never approve, must never
  promote to `human_approved`, and must never write the human
  workspace. Each of these boundaries is already a v0.9 §B / §C /
  §D constraint and is enforced by AST + runtime boundary tests.

**Differentiation summary**:

Industry source-ingestion frameworks solve "give me a document
object I can feed to an LLM / index / chat surface". MindForge
solves "give me an `auditable, provenance-carrying` `SourceDocument`
that downstream `KnowledgeStrategy` can compile into a
`reviewable ai_draft`, gated by explicit human approve before any
state becomes `human_approved`". The distinction is:

- **MindForge's input layer** is a small, owned, audited adapter
  set with explicit capability declarations, fake / dry-run
  defaults, content-addressable dedup, and zero workspace-write
  authority.
- **Industry's input layer** is typically a large, discoverable,
  pip-installable connector marketplace optimized for breadth, not
  for personal-knowledge auditability.

The architectural surface where this difference lives is the
combination of `SourceAdapter` (input boundary), `SourceDocument`
(normalized contract), and `SourceMux` (deterministic dedup) —
each kept deliberately small, source-agnostic downstream, and
upstream of the explicit approve chain.

### Implementation execution slices — Source ingestion (planning-only, awaits human authorization)

This subsection records how the v0.9 Source ingestion guardrails will
be **hardened into code**, given that an extensive source layer
already exists in-tree (`src/mindforge/sources/` with 8 adapters,
`src/mindforge/sources/registry.py`, `src/mindforge/source_mux.py`
with `MuxStats`, `tests/test_source_interface_contract.py`,
`tests/test_source_mux.py`, `tests/test_sources_base.py`, etc.).

The work is therefore **contract hardening, boundary-test extension,
and explicit capability surfaces** — not a greenfield rebuild. Each
slice is large, self-contained, has its own DoD, Stop conditions, and
requires human authorization to start.

**Repository baseline (as of f92fff1)**:

- `src/mindforge/sources/base.py` — `SourceDocument` (frozen, 13
  fields), `Highlight` (frozen), `SourceAdapter` (ABC with `name`,
  `source_type`, `can_handle`, `load`), `compute_content_hash`.
- `src/mindforge/sources/registry.py` — `_BUILTIN_ADAPTERS` dict +
  `build_active_adapters(SourcesConfig)` driver.
- 8 in-tree adapters: `cubox_markdown`, `cubox_api` (raises
  `NotImplementedError` on real fetch), `plain_markdown`,
  `webclip_markdown`, `pdf`, `docx`, `chat_export`,
  `obsidian_vault`.
- `src/mindforge/source_mux.py` — `SourceMux` with
  `content_hash`-keyed first-seen-wins dedup + `MuxStats`.
- 4 boundary-test files already covering the source interface,
  the mux, base contracts, and the Cubox export mapping.

#### Slice 1 — `SourceDocument` contract freeze + provenance / fingerprint hardening

- **Goal**: Promote the existing 13-field `SourceDocument` to a
  frozen, documented v0.9 contract. Add explicit boundary tests
  that pin: (a) field set is closed, (b) `content_hash` is
  deterministic over a documented normalized representation,
  (c) provenance fields (`source_id`, `source_type`,
  `source_path`, `adapter_name`, `captured_at`) are required to
  be set on every produced doc by every adapter, (d) no
  `human_approved` / no draft / no card payload field can leak
  into `SourceDocument`.
- **In-scope files** (test additions / docs only):
  `tests/test_sources_base.py` (extend), new
  `tests/test_source_document_contract.py`, optional doc note
  in `docs/MINDFORGE_PROTOCOL.md` reaffirming the freeze.
- **Out-of-scope**: changing `SourceDocument` field set; touching
  any adapter implementation; touching `SourceMux`; touching
  `KnowledgeStrategy`; renaming fields; adding new fields.
- **Tests**: schema-shape pinning; `content_hash` determinism on
  identical inputs; `content_hash` divergence on differing
  `raw_text` / key metadata; provenance-presence checks per
  adapter; AST guard preventing `SourceDocument` from gaining
  approval / card / draft fields.
- **Quality gate**: `git diff --check`, `ruff check .`,
  `pytest --no-header -q`. New tests added but no production
  change → test count grows by ~10–15.
- **Stop conditions**: any test would require changing
  `SourceDocument` shape → STOP, escalate; any adapter is found
  not to set required provenance → STOP, do **not** silently
  patch the adapter, escalate as a separate slice.
- **Human authorization required**: yes, before Slice 1 starts.
- **Why high-cohesion / low-coupling**: the slice owns one
  concern (input contract) and protects it without expanding
  it; downstream layers depend on the contract, not on adapter
  internals; Information Hiding is preserved because adapter
  metadata stays in the open `metadata` dict.

#### Slice 2 — `SourceAdapter` capability declaration + fake-default boundary

- **Goal**: Introduce an explicit, additive `capabilities()`
  method on `SourceAdapter` (default returns a `frozenset`
  describing `{"local_file", "fake_safe", "dry_run"}` etc.)
  so callers can ask "what is this adapter authorized to do"
  before invoking it. Borrows the Airbyte capability-declaration
  pattern; rejects the LangChain "loader registry" pattern by
  keeping registration in-tree only. Pin via boundary tests
  that no adapter declares a capability it cannot satisfy with
  fake / dry-run data alone, and that real-API capabilities
  (e.g. `cubox_api` real fetch) are gated behind explicit
  opt-in (the existing `NotImplementedError` is the lock).
- **In-scope files**: `src/mindforge/sources/base.py` (add
  `capabilities` method with safe default), each adapter (only
  if it needs to override — most use the default), new
  `tests/test_source_adapter_capabilities.py`. May extend
  `tests/test_source_interface_contract.py` for AST guards.
- **Out-of-scope**: changing `load(...)` / `can_handle(...)`
  signatures; introducing real network calls; adding
  credential surfaces; introducing a remote registry.
- **Tests**: every adapter declares a `capabilities()` set;
  capabilities are a `frozenset[str]` (no mutation); no
  adapter declares `real_api` without an explicit gate; AST
  guard preventing `capabilities()` from doing IO.
- **Quality gate**: as Slice 1; production change is small
  (~30 SLOC in `base.py`, ≤5 SLOC per adapter override). If
  the slice grows beyond ~150 SLOC of production code → STOP.
- **Stop conditions**: any adapter requires reading `.env` to
  declare its capabilities → STOP; any capability requires
  network access to enumerate → STOP.
- **Human authorization required**: yes, after Slice 1 review.
- **Why high-cohesion / low-coupling**: capability is metadata
  about the adapter itself, locally cohesive with the adapter;
  callers depend on a small declarative surface, not on
  internal IO.

#### Slice 3 — `SourceMux` dedup audit-trail hardening + non-semantic pin

- **Goal**: Extend `MuxStats` with an explicit dedup
  audit-trail that records, for each dropped `ScanResult`,
  `(kept_source_id, dropped_source_id, dedup_key)` so the
  user can answer "why was this Cubox markdown skipped" from
  a single artifact. Add boundary tests that pin: (a) dedup
  is content-hash-based by default, (b) dedup never invokes
  any embedding / semantic similarity API, (c) dedup never
  modifies the `ScanResult.document`, (d) failed
  `ScanResult`s pass through untouched.
- **In-scope files**: `src/mindforge/source_mux.py` (extend
  `MuxStats` with optional audit list, default empty for
  back-compat); `tests/test_source_mux.py` (extend); new
  AST guard test ensuring `source_mux.py` does not import any
  `embedding` / `vector` / `transformer` / `numpy` symbol.
- **Out-of-scope**: semantic merge; near-duplicate detection;
  changing the default dedup key from `content_hash`;
  introducing per-source priority configuration.
- **Tests**: audit trail records correct `(kept, dropped,
  key)`; first-seen-wins still holds; failed results still
  pass through; AST import-guard green.
- **Quality gate**: as Slice 1; production change small
  (≤ ~80 SLOC).
- **Stop conditions**: any test would require changing the
  default key → STOP; any dedup decision starts depending on
  similarity → STOP.
- **Human authorization required**: yes, after Slice 2 review
  (or in parallel — Slice 3 is independent of Slice 2).
- **Why high-cohesion / low-coupling**: audit trail is a
  read-only addition to `MuxStats`, fully internal to the
  mux layer; downstream code depends only on the public
  `iter_deduped` / `feed` surface, unchanged.

#### Slice 4 — Cubox adapter boundary lockdown (no real-API drift)

- **Goal**: Lock the existing `cubox_api` adapter's
  fake-default / `NotImplementedError` real-fetch boundary
  with explicit boundary tests so future contributors cannot
  silently flip it on. Pin: (a) instantiating `CuboxApiAdapter`
  reads no env / no network, (b) calling `fetch_inbox` (or
  equivalent real-API method) without explicit credential
  injection raises `NotImplementedError`, (c) `__repr__` /
  `__str__` never expose secret material, (d)
  `CuboxMarkdownAdapter` has no real-network code path at all.
- **In-scope files**: new
  `tests/test_cubox_adapter_safety_boundary.py`. May extend
  `tests/test_cubox_api_adapter.py`. **No** production change
  unless a leak is discovered (in which case STOP and
  escalate as a separate slice — do not bundle a fix into a
  test-only slice).
- **Out-of-scope**: implementing real Cubox API fetch; adding
  a credential surface; rewriting Cubox export mapping.
- **Tests**: import-time safety; instantiation safety;
  real-API call gated; secrets-in-repr guard mirroring the
  LLM provider repr invariants from `23af47e`.
- **Quality gate**: as Slice 1; ideally **zero** production
  change.
- **Stop conditions**: any production fix is needed → STOP,
  escalate.
- **Human authorization required**: yes, after Slice 3 review
  (or in parallel — Slice 4 is independent).
- **Why high-cohesion / low-coupling**: this slice owns one
  adapter's safety boundary, mirrors the LLM-provider
  safety pattern already in `tests/test_provider_opt_in_boundary.py`,
  and adds zero coupling between the adapter and any new
  module.

#### Slice 5 — CLI / processor consumption boundary tests

- **Goal**: Pin via AST + behavioral tests that: (a) no CLI
  command imports a concrete adapter class directly (only the
  registry), (b) no `KnowledgeStrategy` implementation imports
  any adapter module, (c) no adapter is reachable from
  `approval_service` / `review_service` / `recall_service`
  import graphs, (d) no CLI command can write to a real
  Obsidian vault path that wasn't explicitly passed via
  `--vault`. Closes the v0.9 §B "approve chain remains the
  only writer" guarantee with static + runtime guards.
- **In-scope files**: new
  `tests/test_source_consumption_boundary.py`. May extend
  existing CLI boundary tests if the same guard already lives
  there.
- **Out-of-scope**: refactoring CLI; refactoring services;
  changing the registry surface; changing the strategy seam.
- **Tests**: AST scan over `src/mindforge/cli.py`,
  `src/mindforge/strategies/*.py`,
  `src/mindforge/{approval,review,recall}_service.py`;
  vault-path guard test using a fake vault under `tmp_path`.
- **Quality gate**: as Slice 1; ideally **zero** production
  change.
- **Stop conditions**: any CLI command genuinely needs a
  direct adapter import → STOP, escalate as a CLI registry
  cleanup slice; any service is found to import an adapter
  → STOP, escalate as a service-layer remediation slice.
- **Human authorization required**: yes, after Slices 1–4
  review (or in parallel — Slice 5 is independent of all
  others).
- **Why high-cohesion / low-coupling**: the slice owns one
  concern (consumption boundary integrity); it adds no
  production code; it makes existing implicit boundaries
  explicit, raising the cost of accidental future drift.

**Slice independence summary**: Slices 1, 2, 3, 4, 5 are
mutually independent in terms of code changes (different files,
different test areas). They can be authorized in any order or
in parallel by separate reviews. None of them implements a
new feature; none changes CLI external behavior; none reads
`.env`; none calls a real LLM, real Cubox API, or writes a
real Obsidian vault; none introduces a new dependency.

**What this planning explicitly does NOT cover** (each would be
its own milestone with its own authorization):

- Real Cubox API opt-in — separate `v0.9 → v0.10` milestone.
- Cubox API credential surface (`CuboxApiCredential`,
  `.env` opt-in) — separate milestone.
- New adapter implementations (Notion, Readwise, RSS, etc.)
  — each its own milestone.
- `SourcePlugin` as a plugin-loading mechanism (entry-points,
  pip-installable adapters) — explicitly **not** in v0.9 per
  the do-not-copy stance above; would be a separate
  product-shape decision.
- Semantic dedup / near-duplicate detection — explicitly
  rejected by Slice 3 Stop conditions.
- MCP-resource exposure of MindForge content — explicitly
  rejected by the External research alignment do-not-copy
  stance; would be its own dedicated milestone if ever
  proposed.

### v0.9 Slice 1–5 implementation status (recorded after the fact)

| Slice | Status | Production change | Test commits | Production commits |
|---|---|---|---|---|
| 1 SourceDocument contract freeze | ✅ done | `sources/base.py`: `is_provenance_complete()` query method (+35) | `bdfc7a5` | `774b62c` |
| 2 SourceAdapter capabilities | ✅ done | `sources/base.py` default `capabilities()` (+45); `cubox_api.py` `real_api` override (+11) | `29a1885` | `957edee` |
| 3 SourceMux audit-trail | ✅ done | `source_mux.py`: `DedupAuditEntry` + `MuxStats.audit_trail` (+47/-9) | `3d6bd37` | `2aa1b34` |
| 4 Cubox boundary lockdown | ✅ done — test-only | none (current code already complies) | `9135483` | n/a |
| 5 Consumption boundary | ✅ done — test-only | none (current code already complies) | `e0fd78c` | n/a |

What v0.9 ingestion does **not** include after Slices 1–5:

- real Cubox API activation (still NotImplementedError under both
  credential states; locked by Slice 4 tests);
- real LLM activation;
- Upstage / RAG / embedding / semantic merge;
- Obsidian writer / automatic approve / human_approved
  auto-generation;
- new source adapter (PDF / Doc / cloud / Notion / Readwise);
- Web UI / TUI;
- new heavy dependency (no network library imported by Cubox
  modules — Slice 4 AST guard);
- KnowledgeStrategy production implementation (only the
  `strategies/base.py` seam is consumed; production
  KnowledgeStrategy is a separate v0.9.x milestone).

## v0.9.x Product Differentiation & Knowledge Lifecycle Guardrails (PLANNED)

**Status: planned, planning + boundary tests only.** v0.9.x is not a new
feature class. It is a **product positioning lock** + **knowledge lifecycle
guardrail** layer that runs alongside (or just after) v0.9 Data Source &
Plugin Architecture Readiness. Its sole purpose is to prevent MindForge
from drifting into shapes it explicitly is **not**:

- not a generic AI second brain;
- not a RAG knowledge base / multi-source retrieval middleware;
- not an Obsidian AI plugin / vault auto-organizer;
- not a multi-source RAG connector hub;
- not a coding-agent context server with mixed `ai_draft` /
  `human_approved` state.

This milestone is **docs + boundary tests only**. It introduces no new
production module, no new dependency, no new user-visible feature.

### Positioning (normative)

MindForge is a **local-first, personal, reviewable knowledge compiler**:

> It compiles multi-source raw material into **auditable, reviewable,
> recallable, and project-context-injectable human-approved knowledge
> cards**, with explicit human approval as the load-bearing wall.

Each clause is load-bearing:

- **local-first** — defaults never leave the machine; no cloud sync, no
  remote telemetry, no background daemon.
- **personal** — single-user, single-machine workflow; no multi-tenant
  features, no shared workspace abstractions.
- **reviewable** — every promotion, every approval, every recall query
  is human-inspectable and auditable from CLI + workspace artifacts.
- **knowledge compiler** — the system **compiles** raw sources into
  cards through an explicit pipeline (source → SourceDocument → strategy
  → ai_draft → explicit approve → human_approved). It is not a chat
  surface, not a retrieval surface, not an embedding surface.
- **human-approved knowledge cards as the unit of value** — recall,
  review, and project-context injection consume `human_approved` cards
  (or **explicitly labeled** `ai_draft` previews); never silently mix
  the two states.

### Anti-positioning (explicit non-shapes)

The following framings are explicitly rejected and must not creep into
production code, CLI surface, docs, prompts, templates, or default
configs:

1. **Not a generic AI second brain.** MindForge does not auto-summarize
   everything you read. Every card requires explicit human approval.
2. **Not a RAG knowledge base.** No embeddings, no vector store, no
   semantic similarity search in the default product shape. Lexical
   recall (BM25 + hybrid ranking) is the only built-in recall path.
3. **Not a multi-source RAG connector hub.** `SourceAdapter` is an
   **ingestion normalization** boundary, not a retrieval connector.
   Adding a `SourceAdapter` does **not** add a new retrieval backend.
4. **Not an Obsidian AI plugin.** MindForge runs as a local CLI;
   Obsidian is its human workspace, not its embed target. Obsidian
   plugin shape is permanently out of scope for v0.x.
5. **Not a coding-agent context server with mixed state.** Project
   context packets must declare provenance and approval state per card;
   `ai_draft` and `human_approved` cannot be silently merged into one
   "context" blob.

### Source plugin contract (positive framing)

Tightening v0.9 §A: every `SourceAdapter` exists to **normalize**
heterogeneous inputs into a single `SourceDocument` shape. This is an
input-side normalization contract, **not** a retrieval-side connector
contract:

- A `SourceAdapter` produces `SourceDocument`s that the Processing
  Pipeline can consume offline; it does **not** open retrieval channels,
  vector stores, or live external queries during recall.
- `SourceMux` deduplicates equivalent `SourceDocument`s deterministically
  (default key: `content_hash`); it is not a semantic merge layer and
  does not consult any LLM or embedding model.
- A future "RAG-flavored" recall path, if ever proposed, would be its
  own dedicated milestone with its own safety review; it does not enter
  through the `SourceAdapter` plugin door.

### Coding agent collaboration chain (normative)

The intended downstream chain — to be **planned, not implemented** in
this milestone — is:

```
human_approved card
  → project context packet (filtered, labeled, source-attributed)
    → review packet (recently changed / due for review / explicitly pinned)
      → coding agent prompt support (read-only context; never executes)
```

Hard rules that this chain must obey before it is implemented:

- Every card surfaced into a coding-agent prompt must carry its
  approval state (`human_approved`, or **explicitly labeled**
  `ai_draft` preview) and source attribution.
- The prompt-support path must never silently mix `ai_draft` and
  `human_approved` cards into a single unattributed blob.
- The prompt-support path is **read-only**; it cannot promote, edit,
  reject, or merge cards. Only the explicit approve chain can mutate
  card state.
- The prompt-support path must be auditable: every selection decision
  (which cards entered the packet, why) must be reproducible from
  CLI invocation + repo state.

### Architecture quality principles (first-class)

These principles are already executed in commit history; v0.9.x
promotes them to first-class Roadmap principles so they survive
contributor turnover:

1. **High cohesion (高内聚).** Each module has one clear reason to
   change.
2. **Low coupling (低耦合).** Modules depend on stable contracts
   (`SourceDocument`, `KnowledgeStrategy`, `ApprovalDecision`,
   `LLMProvider`), not on each other's internals.
3. **Information Hiding.** Each module exposes the minimum public
   surface needed by its callers; secrets, IO seams, and domain
   internals stay private. Examples already in code: provider
   `__repr__` redacts credentials; `CuboxApiCredential.__repr__`
   never prints token; `_item_to_source_document` error messages
   expose only keys, never bodies.
4. **CLI is a thin adapter.** Parameter parsing, IO, and side-effect
   orchestration only; business semantics live in services.
5. **Service / strategy / provider / presenter / approval / workspace
   boundaries are stable and tested.** AST and runtime boundary tests
   are the load-bearing enforcement, not code review alone.
6. **Reuse existing logic.** New seams must compose existing services
   rather than parallel-implement them.
7. **No mechanical file splitting.** File count and line count are not
   KPIs; cohesion is.
8. **No new monolith.** New service/seam additions must not become the
   next `cli.py`.
9. **No anemic abstraction.** A new module must have a clear
   responsibility, a stable I/O surface, and independent test value;
   otherwise it should not exist.
10. **Tests固化架构意图 (tests freeze architectural intent).**
    Architectural decisions (no source name in non-source modules,
    no LLM SDK in default path, no `.env` read in default path,
    fake-default, explicit-approve-only) are AST + runtime tests,
    not policy memos.
11. **中文学习型注释/docstring (Chinese pedagogical
    comments/docstrings) for load-bearing seams.** Key modules,
    boundary classes, and boundary tests carry Chinese docstrings
    that explain **why** the boundary exists and **what** it
    forbids, not just **what** the code does. Examples already in
    code: `tests/test_provider_opt_in_boundary.py` §9 docstring;
    `src/mindforge/cubox_preview_presenter.py` 职责边界段;
    `src/mindforge/strategies/registry.py` UnknownStrategyError
    rationale.
12. **编程的艺术 (programming as craft).** Solutions should be the
    smallest correct change that preserves the principles above. A
    sloppier shortcut that violates a principle is worse than a
    cleaner change that takes longer.

### Definition of Done (v0.9.x)

- Positioning + anti-positioning sections are present in this Roadmap
  and reflected (in summary form) in `README.md` so external readers
  cannot mistake MindForge for a RAG KB / second brain / Obsidian
  plugin.
- Source plugin contract clarification (input-side normalization, not
  retrieval connector) is documented in this Roadmap and in the v0.9
  source plugin readiness milestone.
- Coding-agent collaboration chain is documented as **planned**, with
  the four hard rules above written down before any implementation
  begins.
- Architecture quality principles are first-class in this Roadmap.
- Boundary test candidates are listed (planning-only): which
  invariants would be enforced by AST/runtime tests in the
  implementation milestone (e.g., "project context packet must record
  per-card approval state", "recall path does not import any
  embedding/vector library", "coding-agent prompt support module
  cannot import `approver.approve_card` or `approval_service`").
- ruff / pytest / `git diff --check` green.
- No production code change. No new dependency. No `.env` read. No
  network. No real LLM. No real Cubox API. No real vault write.

### Stop conditions (v0.9.x)

- Any sub-stage tries to implement project-context coding-agent prompt
  support → STOP, that is a separate implementation milestone.
- Any sub-stage tries to add embeddings / vector store / semantic
  recall to satisfy the "coding agent" framing → STOP, this milestone
  is positioning + guardrails only.
- Any sub-stage tries to write or auto-organize a real Obsidian vault
  → STOP, workspace writer is its own milestone.

### Return to feature roadmap

Once v0.9.x closes (positioning + guardrails documented; boundary test
candidates enumerated), the next implementation milestones may include
v0.9 source plugin readiness completion, source adapter implementation
work (each independently authorized), and the coding-agent
collaboration chain implementation. None of these are pre-approved by
v0.9.x.

## v0.9.x KnowledgeStrategy Customization Readiness (PLANNED)

**Status: planned, planning + boundary tests only.** This milestone
clarifies what `KnowledgeStrategy` actually means as a **product
differentiation surface**, separate from `SourceAdapter` (which solves
"where material comes from"). It is **docs + boundary tests only**: no
new production module, no new dependency, no real LLM, no schema-bound
runtime validation library, no replacement of the existing `five_stage`
strategy.

### Why this milestone exists

The existing `KnowledgeStrategy` Protocol + `StrategyContext` +
`build_strategy` registry give MindForge a structural seam, but the
Roadmap does not yet articulate **what users can customize**, **what
the default strategy should produce for generic learning material**,
or **how strategy selection will stay deterministic and auditable**.
Without this clarification, future contributors are likely to either
(a) collapse `KnowledgeStrategy` into "just a prompt template", or
(b) over-grow it into a RAG pipeline. Both drift away from the
positioning locked by v0.9.x Product Differentiation.

`SourceAdapter` and `KnowledgeStrategy` are deliberately split:

- `SourceAdapter` solves **where material comes from** (Cubox export,
  manual file, future plugin) and normalizes it into `SourceDocument`.
- `KnowledgeStrategy` solves **how that material is understood,
  extracted, and turned into a structured `ai_draft` knowledge card
  candidate**. It never decides whether the result becomes
  `human_approved` — that is always the explicit approve chain.

### KnowledgeStrategy contract (positive framing)

A `KnowledgeStrategy`:

- accepts a single `SourceDocument` (already normalized by a
  `SourceAdapter`);
- produces a single `PipelineOutcome` whose `card_payload` is an
  in-memory `ai_draft` candidate;
- never reads `.env`, never opens sockets, never writes to the
  Obsidian / OPS workspace, never calls `approver.approve_card`,
  never produces `status = human_approved`;
- never imports `cubox_*`, `source_mux`, `scanner`, `sources.cubox_*`,
  or `obsidian` modules (already enforced by AST boundary tests in
  `tests/test_strategy_seam_boundary.py`);
- accepts any `LLMProvider` via `StrategyContext.client`, and stays
  fake-default safe (no real provider activation by virtue of being
  selected).

A `KnowledgeStrategy` is **not** a prompt string repository. Prompts
are one input to a strategy; the strategy also owns its output
contract, its evidence-collection rules, its safety policy, and its
review-readiness criteria.

### Customization dimensions (what "灵活可自定义" actually means)

A future strategy author can vary, independently of every other
strategy and without touching CLI / processor / approval / review:

1. **Extraction goal** — what the strategy is *for*: generic learning
   notes, paper-style structured summary, code-snippet capture,
   meeting transcript distill, etc.
2. **Card family / card type** — which card family the output belongs
   to; family is a stable label for review/recall filters.
3. **Output schema** — the typed shape of `card_payload` (which keys
   are required, which are optional, what each means). Schema lives
   with the strategy, not with the CLI or the processor.
4. **Prompt / instruction surface** — the prompt template(s) the
   strategy uses; treated as one input, not as the contract itself.
5. **Strategy selection rule** — how this strategy is chosen (by
   `source_type`, by `content_type`, by `user_goal`, by
   `project_context`, or by explicit config). Selection must remain
   deterministic and auditable; no LLM-based black-box selection.
6. **Provider policy** — which provider profiles the strategy is
   allowed to run under (default: `fake` only; any real-LLM path is
   explicit opt-in per profile).
7. **Safety policy** — what the strategy refuses to do (e.g. never
   echo source body verbatim past a length cap, never include
   credentials, never embed external URLs without redaction).
8. **Evaluation criteria** — how the strategy decides whether its own
   output is good enough to be a review candidate vs. a triage-only
   record.
9. **Review-readiness criteria** — whether the produced `ai_draft` is
   marked as ready for human review, or as low-confidence triage.
10. **Project-context usage boundary** — whether and how the strategy
    is allowed to consume already-`human_approved` cards as input
    context (read-only; never silently merging `ai_draft` material).

### Strategy selection (planned, not implemented)

A future selector layer must be:

- **deterministic** — same `(SourceDocument, config)` always selects
  the same strategy;
- **auditable** — every selection decision is reproducible from the
  CLI invocation + repo state, with no hidden network call;
- **local-first** — selection runs without any provider / LLM call;
- **testable** — selection is a pure function over `SourceDocument`
  metadata + explicit config;
- **never default to a real LLM** — fake-default safety is preserved
  by the selector, not relied on at the leaf;
- **never delegated to an LLM** — strategy selection itself must not
  ask a model "which strategy to use".

The selector is **not** part of this milestone. This milestone only
locks the contract.

### Default strategy proposal — `DefaultKnowledgeCardStrategy`

The current registered default `five_stage` strategy is shaped around
the existing 5-stage prompt pipeline. The next planned addition (its
own future implementation milestone, not v0.9.x) is
`DefaultKnowledgeCardStrategy` (final name TBD;
`DefaultLearningKnowledgeStrategy` is the alternative under
discussion):

- **Input**: a single `SourceDocument` (web clipping / manual text
  fixture / generic learning material).
- **Output**: a structured `ai_draft` `card_payload` containing:
  - `title`
  - `one_sentence_summary`
  - `key_takeaways` (list)
  - `concepts` (list)
  - `questions_for_review` (list)
  - `source_evidence` (list of provenance pointers)
  - `tags` (list)
  - `confidence` (numeric or qualitative)
  - `limitations` (free text — known weak spots, missing context)
  - `status = "ai_draft"` (constant; never `human_approved`)
- **Provider policy**: fake-default; real-LLM provider only via
  explicit opt-in profile.
- **Safety policy**: never writes a vault, never approves, never
  imports source / approval / writer modules; produced payload is
  pure in-memory `dict`.
- **Schema discipline**: schema lives in the strategy module; the
  strategy is the **only** writer of its own schema. CLI / processor
  / approval / review treat the payload as opaque structured data and
  do not redefine its keys.
- **Not in scope**: no JSON-schema validation library dependency, no
  pydantic dependency, no embedding, no semantic merge, no auto
  approval, no project-context coding-agent prompt support.

`DefaultKnowledgeCardStrategy` is not implemented in this milestone.
This milestone only locks its contract so any future implementation
PR has a stable target.

### Boundary test candidates (planning-only)

When `DefaultKnowledgeCardStrategy` (or any new strategy) is later
implemented, the following invariants must be enforced by AST or
runtime tests (extending the existing
`tests/test_strategy_seam_boundary.py` family):

- a strategy's only declared input type is `SourceDocument`;
- a strategy module does not import `cubox_*`, `source_mux`,
  `scanner`, `sources.cubox_*`, `obsidian`, `vault_writer`,
  `approver`, `approval_service`, `review_service`, `recall_service`;
- a strategy never produces a payload with `status == "human_approved"`;
- a strategy never returns a payload that already carries the
  `human_approved` field;
- the registry default never resolves to a real-LLM provider strategy
  unless explicitly opted in;
- swapping the strategy name in `build_strategy(name, ctx)` does not
  require any change in CLI / processor / approval / review;
- selecting any strategy with the default fake provider produces a
  deterministic fixture-shaped payload;
- approval remains the **only** path that promotes `ai_draft` to
  `human_approved`;
- a strategy module does not import any embedding / vector / RAG
  library, and does not import `httpx` / network clients directly.

### Definition of Done (v0.9.x KnowledgeStrategy Customization Readiness)

- This Roadmap section explicitly distinguishes `SourceAdapter`
  ("where material comes from") from `KnowledgeStrategy` ("how
  material is understood and turned into structured `ai_draft`").
- The ten customization dimensions above are documented as the
  contract for "flexible, customizable" strategy.
- The `DefaultKnowledgeCardStrategy` contract (input / output schema
  / provider policy / safety policy / non-goals) is documented as
  planned, not implemented.
- Strategy-selection guarantees (deterministic / auditable /
  local-first / testable / never default real LLM / never
  LLM-decided) are documented.
- Boundary test candidates are listed for the future implementation
  PR.
- ruff / pytest / `git diff --check` green.
- No production code change. No new dependency. No `.env` read. No
  network. No real LLM. No real Cubox API. No real vault write.

### Stop conditions (v0.9.x KnowledgeStrategy Customization Readiness)

- Any sub-stage tries to implement `DefaultKnowledgeCardStrategy` →
  STOP, that is a separate implementation milestone with its own
  authorization.
- Any sub-stage tries to add JSON-schema validation, pydantic, or
  any typed-output runtime dependency → STOP, schema discipline is
  enforced by tests, not by a new library.
- Any sub-stage tries to add embedding / RAG / semantic merge to
  satisfy "structured extraction" framing → STOP, that is a
  different product shape rejected by v0.9.x Product Differentiation.
- Any sub-stage tries to let an LLM decide which strategy to apply
  → STOP, selection must be deterministic and auditable.
- Any sub-stage tries to bind `KnowledgeStrategy` to a specific
  `SourceAdapter` (e.g. CuboxAdapter) → STOP, the seam is meant to
  stay source-agnostic.

### Return to feature roadmap

Once this milestone closes (contract documented; selection
guarantees documented; default-strategy contract documented; boundary
test candidates enumerated), the next candidate implementation
milestones become independently authorizable:

- `DefaultKnowledgeCardStrategy` implementation (its own milestone);
- strategy selector / registry config surface (its own milestone);
- per-source-type strategy mapping (its own milestone).

None of these are pre-approved by v0.9.x KnowledgeStrategy
Customization Readiness.

### Implementation execution slices (planning-only, awaits human authorization)

When `DefaultKnowledgeCardStrategy` implementation is later
authorized, it must be split into the following slices. Slices are
intentionally **few and large** (not many small file moves) to
preserve cohesion and to make each slice independently reviewable
and revertable. Each slice ends with a hard stop until the next
slice is explicitly authorized.

**Audit baseline (informs the slicing)**:

- `src/mindforge/strategies/{base,registry,five_stage}.py` already
  exists; `KnowledgeStrategy` Protocol + `StrategyContext` +
  `build_strategy(name, ctx)` already in place. `DEFAULT_STRATEGY_NAME
  = "five_stage"` today.
- `src/mindforge/processors/pipeline.py` already produces a
  `PipelineOutcome.card_payload` (a fixed-shape dict for the
  `five_stage` strategy). The new strategy emits a **different**
  payload shape (the 10-field knowledge-card schema above), so it
  must be registered as an **additional** strategy alongside
  `five_stage`, not as a replacement.
- `src/mindforge/sources/base.py` defines `SourceDocument` (the only
  permitted strategy input).
- `src/mindforge/llm/fake.py` provides `FakeProvider`
  (deterministic, no socket, no `.env`, no LLM SDK).
- `src/mindforge/approver.py` is the only `human_approved`
  promotion path; `ApprovalDecision` enum lives there.
- `tests/test_strategy_seam_boundary.py` already enforces
  source-agnostic / no-`.env` / no-socket / no-`human_approved` /
  no-vault-write invariants; the new slices extend, not replace,
  this test family.

#### Slice 1 — Strategy contract + payload schema TDD (Red → Green)

- **Goal**: lock the 10-field `DefaultKnowledgeCardStrategy`
  payload contract in tests **before** any production code exists.
- **Allowed scope**:
  - new `tests/test_default_knowledge_card_strategy.py` (Red
    initially);
  - new `tests/test_default_knowledge_card_strategy_boundary.py`
    extending the existing `test_strategy_seam_boundary.py` AST
    invariants for the new strategy module path;
  - no production code in this slice; the production module is
    introduced by Slice 2.
- **Forbidden scope**:
  - no change to `Pipeline` / `five_stage` / `processors/`;
  - no change to `approver.py` / `approval_service.py`;
  - no change to `cli.py` / any presenter;
  - no change to `configs/mindforge.yaml`;
  - no new dependency.
- **Tests** (each is a strict invariant; not a smoke):
  - the strategy module's only declared input type is
    `SourceDocument`;
  - the strategy module does not import `cubox_*`, `source_mux`,
    `scanner`, `sources.cubox_*`, `obsidian`, `vault_writer`,
    `approver`, `approval_service`, `review_service`,
    `recall_service`;
  - the strategy module does not import any embedding / vector /
    `httpx` / `requests` library;
  - calling the (yet-to-be-implemented) strategy with a fixture
    `SourceDocument` + `FakeProvider` returns a payload whose
    keys are exactly the 10 contract keys and whose `status` is
    `"ai_draft"`;
  - the payload never carries `human_approved`, `approved_by`,
    `approved_at`, or any Obsidian path;
  - calling the strategy never opens a socket and never writes
    any file under repo root.
- **Quality gate**: `git diff --check` / `ruff` / `pytest -q`. Tests
  in this slice are expected to be Red until Slice 2 lands.
- **Stop conditions**:
  - any slice instinct to "just inline the production module here
    to make tests green" → STOP, that is Slice 2;
  - any test that requires a real provider / `.env` / network →
    STOP, fake-default is the only allowed path.
- **Human authorization required**: yes, before slice begins.

#### Slice 2 — `DefaultKnowledgeCardStrategy` minimal implementation + registry

- **Goal**: implement the smallest production module that turns
  Slice-1 tests green, while keeping `five_stage` as the existing
  default and adding the new strategy as a second registered name.
- **Allowed scope**:
  - new `src/mindforge/strategies/default_knowledge_card.py`
    containing:
    - one `@dataclass` for the typed payload (or a typed `dict`
      builder — whichever is cleaner with the existing project
      idiom; do **not** introduce Pydantic);
    - one `class DefaultKnowledgeCardStrategy` exposing
      `run(doc: SourceDocument) -> PipelineOutcome` with a
      mutable `logger` attribute (so it satisfies the existing
      `KnowledgeStrategy` Protocol structurally);
    - one `build_default_knowledge_card_strategy(ctx)` factory;
  - registry update in
    `src/mindforge/strategies/registry.py`: add
    `"default_knowledge_card"` (final name TBD during slice) to
    `_FACTORIES`; do **not** change `DEFAULT_STRATEGY_NAME`;
  - any docstring additions are written as 中文学习型 docstrings
    explaining (a) what boundary the module sits on, (b) why
    the strategy never produces `human_approved`, (c) why the
    schema lives with the strategy rather than with the CLI /
    processor.
- **Forbidden scope**:
  - no change to `cli.py` / any presenter / any service;
  - no change to `configs/mindforge.yaml`;
  - no change to `Pipeline` or `five_stage`;
  - no `LLMProvider` change; if the strategy needs a real LLM
    later, that is its own opt-in milestone;
  - no Pydantic / JSON-schema validator dependency;
  - no new top-level package; the new file lives inside the
    existing `strategies/` package.
- **Tests**: Slice-1 tests must turn fully green; no new tests
  added in this slice (all behavior was specified in Slice 1).
- **Quality gate**: `git diff --check` / `ruff` / `pytest -q` all
  green; `tests/test_strategy_seam_boundary.py` must remain green
  unchanged.
- **Stop conditions**:
  - Slice 2 grows beyond ~150 SLOC of production code → STOP and
    re-evaluate; the strategy should be small;
  - any temptation to wire the new strategy into CLI / processor
    in this slice → STOP, that is Slice 3.
- **Human authorization required**: yes, after Slice 1 review.

#### Slice 3 — Optional CLI / processor opt-in seam (deferred by default)

- **Goal**: only if explicitly authorized, expose the new strategy
  to the CLI as an opt-in choice, **without changing the default
  user-visible behavior**.
- **Allowed scope** (only with explicit human authorization):
  - extend `processor` invocation to accept a strategy name
    parameter (which it can already do via `build_strategy`); CLI
    surface remains unchanged unless explicitly extended;
  - if CLI extension is authorized: a single new `--strategy`
    flag on the existing `process` command, defaulting to the
    current behavior (no behavioral default change);
  - tests: a single end-to-end test with `--strategy
    default_knowledge_card` against the example fixture vault,
    confirming `ai_draft` payload shape and confirming nothing
    is approved automatically.
- **Forbidden scope**:
  - no removal or rename of existing CLI commands / flags;
  - no change to `configs/mindforge.yaml` defaults;
  - no change to `approver` / `approval_service` /
    `review_service` semantics;
  - no auto-approval, no auto-merge, no workspace write
    behavior change.
- **Tests**: one CLI integration test with the new flag; existing
  CLI / approval / review tests stay green unchanged.
- **Quality gate**: `git diff --check` / `ruff` / `pytest -q` all
  green; `mindforge --help` / `mindforge process --help` smoke shows
  the new flag is opt-in, not default.
- **Stop conditions**:
  - the CLI flag changes default behavior in any way → STOP;
  - the slice attempts to add a "selector" beyond by-name → STOP,
    selector is its own milestone;
  - the slice grows beyond a single new flag + one integration
    test → STOP and split.
- **Human authorization required**: yes, separate from Slice 2.
  This slice is the **first** time anything user-visible changes,
  and may legitimately be deferred indefinitely.

#### Slice 4 — Docs + boundary-test consolidation

- **Goal**: update `docs/ARCHITECTURE_MAP.md` and the relevant
  checkpoint doc to reflect the new strategy module; freeze the new
  invariants as first-class architecture boundary tests next to
  the existing `test_strategy_seam_boundary.py` family.
- **Allowed scope**:
  - `docs/ARCHITECTURE_MAP.md` add one entry for the new strategy
    module and its boundary;
  - one new architecture-boundary test file (or extension to
    `tests/test_strategy_boundaries.py`) consolidating the
    Slice-1 invariants into a permanent regression net;
  - one checkpoint doc under the existing `docs/` checkpoint
    convention summarizing the implementation milestone.
- **Forbidden scope**:
  - no production code change;
  - no change to existing tests' semantics (only additions);
  - no `pyproject.toml` change; no new dependency.
- **Tests**: full suite green; no flake.
- **Quality gate**: `git diff --check` / `ruff` / `pytest -q`.
- **Stop conditions**:
  - any urge to "also fix something unrelated while I am in
    docs" → STOP, separate milestone.
- **Human authorization required**: yes, after Slice 3 (or after
  Slice 2 if Slice 3 is deferred).

### Architecture quality reminders for implementation

These are not new principles; they are reminders specific to the
above slices, drawn from the v0.9.x §Architecture quality
principles 1-12:

- The new strategy module must own its own payload schema; no
  other module (CLI, processor, approval, review, presenter,
  workspace) is allowed to redefine or read schema-internal keys.
- The new strategy must be independently testable with a
  fixture `SourceDocument` + `FakeProvider`, with no test
  scaffolding requiring a real provider, a real vault, or a real
  Cubox export.
- Adding the new strategy must not require any change to
  `cli.py`, `Pipeline`, `approver.py`, `approval_service.py`,
  `review_service.py`, `recall_service.py`, or any presenter; if
  any such change feels necessary, the design has drifted and the
  slice should stop.
- 中文学习型 docstrings are required on the new production
  module and on the boundary tests, explaining **why** the
  boundary exists and **what** it forbids — not just what the
  code does. Examples to match in tone:
  `src/mindforge/strategies/registry.py` `UnknownStrategyError`
  rationale, `tests/test_provider_opt_in_boundary.py` §9.
- File / line-count is not a goal. Cohesion is. If splitting a
  slice produces an anemic helper module, fold it back into the
  strategy module.

### External research alignment (research addendum)

This addendum records the public-domain landscape consulted while
shaping the `KnowledgeStrategy` contract above, and locks the
deliberate **borrow / do-not-copy** stance MindForge takes against
each pattern. None of these references introduces a dependency, a
runtime call, or a default behavior change; this is purely a
documentation alignment to prevent "is it just a LangChain wrapper?"
drift.

**Industry references consulted**:

1. **OpenAI structured outputs / function calling + Pydantic typed
   schemas** — the dominant production pattern for "LLM emits typed
   JSON validated against a schema". Source: OpenAI structured
   output docs + Pydantic docs (publicly indexed).
2. **LangChain `with_structured_output(schema)`** — wraps a chat
   model so its return is parsed into a typed object (Pydantic /
   dict) instead of free text. Source: LangChain docs
   (`python.langchain.com`).
3. **DSPy signatures + declarative LM pipelines** — describe a task
   as `inputs → outputs` (a "signature") rather than as a prompt
   string; let the framework optimize prompts. Source: Stanford
   DSPy documentation.
4. **LlamaIndex metadata extractors / Pydantic metadata extractor**
   — per-document structured metadata extraction with a typed
   schema. Source: LlamaIndex docs.
5. **Anki + spaced-repetition + LLM-generated flashcards** — the
   widespread "auto-generate Q&A cards from notes" workflow used in
   PKM communities (incl. Obsidian-to-Anki plugins).
6. **Strategy pattern (GoF) for pluggable extraction** — the
   classic OO pattern of "one interface, many algorithms,
   selectable at runtime". Already structurally present in
   MindForge as the `KnowledgeStrategy` Protocol + registry.

**What MindForge borrows (selectively)**:

- The **typed I/O contract** idea (DSPy signatures / Pydantic
  schemas / LangChain `with_structured_output`): a strategy is
  defined by its **input contract + output schema**, not by a
  prompt string. This is already locked above as customization
  dimension #3 (output schema) and the `DefaultKnowledgeCardStrategy`
  10-field payload.
- The **strategy pattern** of one Protocol + many concrete
  implementations selectable through a registry: already structurally
  present (`build_strategy(name, ctx)`), already enforced by
  boundary tests.
- The **idea of separating extraction goal from prompt phrasing**
  (DSPy): captured by customization dimension #1 (extraction goal)
  and the explicit statement "prompt is one input to a strategy,
  not the contract".
- The PKM insight that **review-ready cards (flashcards / atomic
  notes) are a unit of value distinct from raw clippings**: locked
  by `status = "ai_draft"` + `questions_for_review` + explicit
  approve gate.

**What MindForge deliberately does NOT copy**:

- **No new schema-validation runtime dependency** (Pydantic / JSON
  Schema validator / `instructor` / similar). Schema discipline is
  enforced by the strategy module owning its own payload shape and
  by AST/runtime boundary tests, not by importing a typed-output
  library. Pydantic-style models can be written as plain
  `@dataclass` if needed; this is already the project's idiom.
- **No LangChain / LlamaIndex / DSPy wrapper.** MindForge is not
  positioned as "yet another LLM orchestrator". The
  `KnowledgeStrategy` Protocol is intentionally minimal
  (`run(doc) -> PipelineOutcome`, plus a settable `logger`), so
  swapping in a different orchestrator is a strategy implementation
  detail, not an architectural commitment.
- **No automatic "summarize everything you read" pipeline.** The
  PKM-LLM-flashcard workflow that generates and *commits* cards
  without human review is explicitly rejected; MindForge requires
  explicit human approve to promote `ai_draft → human_approved`.
  This stance is already locked by v0.9.x Product Differentiation
  Anti-positioning #1.
- **No RAG / embedding / vector store** as the recall surface. The
  industry default in PKM-AI products is vector recall; MindForge
  defaults to lexical recall (BM25 + hybrid ranking) and keeps
  vector recall out of the default product shape (Anti-positioning
  #2).
- **No LLM-decided strategy selection.** Some LangChain / DSPy
  patterns let a model pick the next step; MindForge's selector is
  required to be deterministic, auditable, and pure over
  `SourceDocument` metadata + explicit config (Strategy selection
  guarantees above).
- **No prompt-template registry framing.** `KnowledgeStrategy` is
  not a prompt repository; prompt phrasing is just one input to a
  strategy, alongside output schema, evaluation criteria, safety
  policy, etc.

**Differentiation summary** (why this still ships even though the
industry has many extraction frameworks):

MindForge is not "LLM extraction-as-a-service". It is a **local-first,
personal, reviewable knowledge compiler** in which:

- the **input** is heterogeneous personal sources, normalized by a
  pluggable `SourceAdapter` (not a retrieval connector);
- the **transformation** is a pluggable `KnowledgeStrategy` that
  emits structured `ai_draft` candidates with a strategy-owned
  schema;
- the **trust boundary** is explicit human approve — `human_approved`
  is the only state consumed by recall and project-context
  injection; `ai_draft` is always explicitly labeled when surfaced;
- the **workspace** (Obsidian / OPS) is the human review surface,
  not a machine cache, runtime, log, or vector store;
- the **defaults** never call a real LLM, never read `.env`, never
  open a network socket, never write a real vault.

Industry typed-extraction frameworks solve "give me JSON I can
parse"; MindForge solves "give me a reviewable knowledge artifact I
can later trust as approved memory". The first is a building block;
the second is a product shape. The `KnowledgeStrategy` seam is the
specific architectural surface where MindForge expresses that
difference.

## v0.11–v0.13 Strategy Flexibility Forward Plan (PLANNED)

**Status: planned, no production work authorized yet.** This section
records the **forward sequencing** of strategy flexibility after the
v0.10 KnowledgeStrategy milestone (Slices 1–4 above) closes. It exists
because the product judgement evolved past v0.10:

> MindForge cannot ship with a single fixed `KnowledgeStrategy`.
> Users will need **multiple built-in strategies** and, eventually,
> **declarative custom strategies** — but every step must remain
> fake-first, schema-disciplined, and approval-gated.

This section does **not** authorize any implementation. It locks the
*shape* of the next three milestones so that contributors do not (a)
collapse the seam into "just another prompt", (b) jump straight to
arbitrary user Python plugins, or (c) light up real providers by
default to make customization "easier".

### Product judgement (locked)

1. `KnowledgeStrategy` is the **product differentiation seam**, not a
   prompt template repository. Multiple strategies must be selectable
   without changing the CLI surface beyond the existing opt-in flag.
2. Strategy selection is **always explicit and deterministic**: by CLI
   flag, by config, or by source-type policy — never by an LLM
   choosing its own next step.
3. Custom strategies are first **declarative** (YAML/JSON metadata +
   prompt template + output schema + safety policy). Arbitrary
   user-supplied Python is out of scope for the foreseeable future.
4. `ai_draft` remains the only state any strategy may emit.
   `human_approved` stays an explicit `approver.approve_card` action.
5. `StrategyContext.client` stays Optional (v0.10 seam stabilization).
   Real LLM activation remains an explicit, separately-authorized
   provider opt-in — never a side effect of selecting a strategy.

### v0.11 StrategyRegistry & multiple built-ins (PLANNED)

**Goal**: introduce a richer `StrategyRegistry` surface and ship one
or two additional **deterministic, fake-first** built-in strategies so
users see real choice from the CLI.

- **Allowed**:
  - `StrategyDefinition` dataclass (id / display_name / description /
    accepted source_types / output_schema reference / safety_policy /
    provider_mode ∈ {fake, deterministic, real_opt_in} / version);
  - `StrategyRegistry.list()` returning ordered `StrategyDefinition`s
    for `mindforge process --help` and a future `mindforge strategy
    list` subcommand;
  - additional built-in strategies, each its own module under
    `strategies/`, each independently fake-first testable;
  - per-source-type strategy mapping (config-driven, not LLM-driven).
- **Forbidden**:
  - no real LLM provider activation by virtue of selecting a strategy;
  - no embedded Pydantic / JSON-schema validator runtime dependency;
  - no LangChain / LlamaIndex / DSPy import;
  - no automatic approve, no automatic merge, no workspace write
    semantics change;
  - no anemic helper modules: each new strategy must own its payload
    schema and have boundary tests in the
    `test_strategy_seam_boundary.py` family.
- **Definition of done**:
  - at least one additional deterministic strategy ships alongside
    `five_stage` and `default_knowledge_card`;
  - `StrategyRegistry.list()` is consumed by `--help` and tested;
  - boundary tests forbid any new strategy from importing source
    adapters / `.env` / network libraries.

### v0.12 Declarative custom strategy preview (PLANNED)

**Goal**: let users define a strategy via a YAML/JSON file plus a
prompt template + output schema, run it in `--dry-run`, and review
the resulting `ai_draft` — without writing Python.

- **Allowed**:
  - `StrategyDefinition` loadable from a user-supplied file path with
    explicit opt-in flag (e.g. `--strategy-file path.yaml`);
  - schema validation done by hand-rolled checker (no new dependency)
    against the same shape as built-in strategies;
  - dry-run preview command that prints the would-be `ai_draft`
    without writing anything.
- **Forbidden**:
  - no arbitrary user Python execution;
  - no shell / script invocation from a strategy file;
  - no network access initiated by loading a strategy file;
  - no `.env` read triggered by a custom strategy;
  - no automatic approve; no workspace write from preview;
  - no real provider activation triggered by a custom strategy;
    real-provider use must still be a separately-authorized opt-in.
- **Definition of done**:
  - a sample declarative strategy ships under `examples/`;
  - boundary tests pin "loading a custom file does not import Python
    modules outside `strategies/`" and "preview never writes vault";
  - clear, friendly error messages on schema violation (registry-level
    UX consistency with `UnknownStrategyError`).

### v0.13 Real provider opt-in (PLANNED)

**Goal**: allow strategies (built-in or declarative) to call a real
LLM provider via an explicit, audited opt-in. Default behavior remains
fake-first.

- **Allowed**:
  - explicit provider activation flag with audit log entry;
  - structured-output use of provider-native features when available,
    still validated by the strategy's own schema;
  - safe fallback to `ai_draft` skip / clearly-failed status on
    provider error — never a silent partial card.
- **Forbidden**:
  - no default-on real provider;
  - no implicit `.env` read (user must opt in to the env-loading path);
  - no auto-approve of LLM-emitted drafts;
  - no streaming side-effects to vault;
  - no provider SDK imported at module top-level — gate behind the
    activation flag so fake-default suite remains import-clean.
- **Definition of done**:
  - opting in produces a clearly logged provider call, fake-default
    suite continues to pass with provider SDK uninstalled;
  - provider activation cannot be set inside a `StrategyDefinition`
    file (separation of concerns: file = what to extract, CLI/config
    = whether to use real provider).

### Stop conditions (forward plan)

- Any milestone tries to let an LLM pick the strategy → STOP.
- Any milestone proposes arbitrary user Python plugins before v0.13
  closes → STOP, declarative-only is the contract.
- Any milestone proposes a Pydantic / JSON-schema runtime dependency
  → STOP, schema discipline stays test-enforced.
- Any milestone tries to bind a strategy to a `SourceAdapter` concrete
  class → STOP, the seam stays source-agnostic.
- Any milestone tries to make real provider opt-in default-on → STOP.

### Position relative to v0.10

The v0.10 KnowledgeStrategy milestone (Slices 1–4 above) ships:
`DefaultKnowledgeCardStrategy` + `--strategy` opt-in CLI flag +
`StrategyContext` fake-first stabilization. v0.10 deliberately stops
**before** introducing `StrategyRegistry.list()`, multiple new
deterministic built-ins, declarative custom files, or real provider
opt-in — those are the v0.11 / v0.12 / v0.13 surfaces above.

## v0.12 Declarative Custom Strategy Preview Completed

> **Status:** v0.12 closed locally (commits ad99707 + 4a38a50 ahead of
> origin pre-final-push); 5 TDD slices Red→Green; 1153 tests passing,
> 3 skipped; no tag, fake-first preserved, no real LLM, no `.env`,
> no vault writes, no auto-approve, no custom strategy runtime.

### What v0.12 delivers

| Slice | Subject | Outcome |
| --- | --- | --- |
| 1 | `StrategyDefinition` declarative dataclass + validation | done |
| 2 | Safe loading from explicit path (no implicit scanning) | done |
| 3 | CLI discovery via `--custom-path` (no execution) | done |
| 4 | Registry integration: build_strategy refuses custom + duplicate-id rejection | done |
| 5 | Review-only `preview_packet` data + presenter | done |

Plus two innovations:

- **Capability matrix** (`docs/V0_12_CAPABILITY_MATRIX.md`) — explicit
  per-stage allowed/forbidden table inspired by OpenAI Agents SDK
  guardrails, LangGraph interrupt, Dify Knowledge Pipeline node
  isolation.
- **AST import-boundary tests**
  (`tests/test_custom_strategy_import_boundaries.py`) — hard-fail when
  custom-strategy files reverse-import CLI / approval / writer / llm /
  IO modules.

### Boundaries held throughout v0.12

- Loading is not execution.
- Discovery is not execution.
- Preview packet is **review-only** (`kind=preview_only`,
  `executable=False`); it is **not** ai_draft, **not** human_approved,
  and never touches `ApprovalService` / `CardWriter`.
- Custom strategies cannot register a factory; `build_strategy` raises
  `NotYetImplementedStrategyError` with friendly preview tokens.
- Source-scan + AST tests pin: no subprocess / eval / dotenv /
  `.obsidian` / network / approved-flag literal in custom paths.
- No tag created. Final closure commits remain local pending explicit
  push approval.

### What v0.12 deliberately does **not** ship

- No custom strategy runtime execution.
- No real LLM provider activation by default.
- No arbitrary Python plugin / shell / script strategy.
- No RAG / embedding / semantic merge.
- No real vault writes / real `.env` reads / real Cubox API.
- No auto-approval of any kind.

### Industry-research distillation

| Source | Pattern adopted | Pattern explicitly rejected |
| --- | --- | --- |
| OpenAI Agents SDK | Guardrail invariants as tests | Auto-approve LLM output |
| LangGraph | Interrupt = preview-only checkpoint | Implicit state mutation |
| Dify | Knowledge pipeline node isolation, capability matrix UX | Visual editor / marketplace plugin runtime |
| Obsidian + local-first AI tools | Local-first ownership, no implicit scan | Community plugin sandbox (we go stricter) |
| Second-brain (Readwise / Logseq / Cubox / Tana) | capture → process → review → approve → recall loop | Vendor lock-in, hidden background sync |

### v0.12 → v0.13 hand-off (planning only, no implementation)

v0.13 candidates (see also "Real provider opt-in" block above):

1. Non-sensitive dogfooding readiness (demo fixtures + dry-run
   examples; still fake-first; no real private data).
2. Packaging / install readiness polish (`pip install` smoke, README
   onboarding sweep).
3. Explicit-approval UX review (terminal wording, JSON shape stability).
4. v0.12 capability matrix kept in sync as new strategies land.

**v0.13 explicit non-goals** (carried over): no real LLM by default,
no real Obsidian writes, no Cubox real API, no custom runtime, no
arbitrary plugin, no shell strategy, no RAG, no semantic merge.

### Stop conditions for closing v0.12

All satisfied as of `4a38a50`:

- ✅ Slices 1–5 Green; targeted + full test suite pass.
- ✅ ruff clean; `git diff --check` clean.
- ✅ Capability matrix doc exists.
- ✅ AST import-boundary guard exists.
- ✅ No tag, no force push, no remote modification beyond reviewed
  baseline pushes (a3bf24e..ad99707 already pushed; 4a38a50 + closure
  commits await explicit push approval).

## Near-Term Priority

Phase 1 (CLI Product Shape Completion) is the active focus. See
[Product Shape & Phase Plan](#product-shape--phase-plan) above for the
canonical closed-loop scenario, the eleven completion criteria, and Phase 1
Non-Goals. Validate progress on disposable, non-sensitive vault copies
(default: `examples/demo-vault`) before adding new feature classes.

## Future Candidate Work

See [M5_BACKLOG.md](./M5_BACKLOG.md) for current spike candidates. The active future set is intentionally small:

- Obsidian Binding polish from dry-run feedback.
- Local Usability polish from real non-sensitive dogfooding.
- Install smoke polish after packaged asset migration.
- PDF/docx performance baselines.
- More onboarding and cross-platform terminal polish.
- RAG / embedding only as a later design spike if lexical recall proves
  insufficient after Obsidian binding.

## Explicit Non-Goals For v0.x

- No OCR.
- No remote telemetry.
- No cloud sync.
- No automatic approval.
- No background daemon.
- No system calendar or notification integration.
- No SM-2 / FSRS automation.
- No RAG/embedding in mainline without a separate design and review.
- No graph database or vector database implementation in v0.5.
- No automatic Obsidian vault reorganization.
- No automatic formal-note edits, file moves, or wikilink rewrites.
- No large-scale real-vault dogfooding before read-only Obsidian binding is
  designed and tested.
- No real LLM calls, `.env` reads, private data handling, or automatic approve
  in the local usability smoke path.

## Stable Architecture References

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [SECURITY.md](./SECURITY.md)
- [MINDFORGE_PROTOCOL.md](./MINDFORGE_PROTOCOL.md)
- [SOURCE_ADAPTER_PROTOCOL.md](./SOURCE_ADAPTER_PROTOCOL.md)
- [OBSIDIAN_BINDING.md](./OBSIDIAN_BINDING.md)
- [LLM_PROVIDER_CONFIG.md](./LLM_PROVIDER_CONFIG.md)

## When To Update This Roadmap

Update this file when a future direction changes. Use [CHANGELOG.md](./CHANGELOG.md) for completed version history and `docs/archive/` for detailed historical reviews.

## v0.13 Stage 1 — Real-Capable Opt-in Readiness (Completed Locally)

**Status**: local-only commits, not yet pushed, no tag. Default path remains
fake-safe; real LLM provider becomes an explicit opt-in path with
secret-safe handling, synthetic-only smoke input, and approval-boundary
protection (real output ≠ `human_approved`).

### Delivered

- `src/mindforge/provider_readiness.py` — pure-data report module
  (`build_readiness_report`, `render_readiness_report`,
  `classify_real_opt_in`); presence-only env check, never returns or
  prints any value.
- `src/mindforge/real_smoke.py` — gated `run_synthetic_real_smoke`
  helper; refuses unless `allow_real=True` AND `active_profile != fake`
  AND target alias `api_key` present; output is `ai_draft_preview`
  only; `human_approved` and `written` fields are constants `False`.
- `src/mindforge/provider_cli.py` + `mindforge provider {readiness, smoke}`
  Typer commands; `--allow-real` flag, `--alias` selector, no secret
  printing.
- `docs/V0_13_INDUSTRY_PATTERN_MAP.md` — offline industry distillation
  (OpenAI Agents SDK / LangChain · LangGraph / Dify / Obsidian /
  Readwise · Cubox · Tana · Logseq · Notion AI · Mem · Anytype) +
  adopted / rejected / future + MindForge differentiation.
- `docs/LOCAL_FIRST_PRIVACY_CONTRACT.md` — canonical fake-default +
  real-opt-in privacy contract; cross-linked from
  `V0_13_DOGFOODING_READINESS.md` §5.
- `docs/PROPOSAL_REVIEWABLE_ARTIFACT.md` — docs-only sketch unifying
  `preview_packet` / `ai_draft_preview` / `readiness_report` /
  `real_smoke_result` / `recall_hit` / `weekly_review_packet` under one
  optional protocol; explicitly **NOT authorized for implementation**.
- `docs/V0_13_REAL_INGESTION_DEFERRED_GATES.md` — Cubox / Obsidian
  real-ingestion / real-write启用前置 (test-account-required /
  sample-folder-only / item-cap / no-persist / preview-only /
  `--allow-real` / `--allow-write`).
- `docs/V0_12_CAPABILITY_MATRIX.md` §8 — readiness rows added (fake /
  real-skeleton / real-opt-in / real-active / synthetic real smoke /
  Cubox / Obsidian); §6 "Excluded" semantics preserved.
- README + GETTING_STARTED §11 — pointers and verification recipe.
- 5 new test files (62 new tests):
  `test_v013_provider_readiness.py`, `test_v013_real_smoke_safety.py`,
  `test_v013_industry_pattern_map.py`, `test_v013_privacy_contract.py`,
  `test_v013_cli_provider_surface.py`. Includes AST import-boundary
  guards on the 3 new src files (no reverse imports of cli / approval /
  writer / cards / obsidian* / cubox* / scanner / dotenv / requests /
  httpx / subprocess).
- `tests/test_review_approval_boundary.py` allowed-set extended to
  cover the 3 new files (they reference the `human_approved` literal
  only as a reverse-direction safety claim, never as an automatic
  promotion path — same pattern as `strategies/custom.py`).

### Reaffirmed Non-Goals (deferred, with explicit gates)

- **Real Cubox real-API ingestion** — deferred;启用前置见
  `V0_13_REAL_INGESTION_DEFERRED_GATES.md` §3.
- **Real Obsidian vault 写入** — deferred; 启用前置见同文档 §4.
- **`ReviewableArtifact` protocol implementation** — proposal-only;
  启动 RFC 前置见 `PROPOSAL_REVIEWABLE_ARTIFACT.md` §4.
- **Custom strategy runtime / arbitrary plugin / shell strategy** —
  仍然禁止。
- **RAG / embedding / semantic merge** — 仍然不引入。
- **Auto-approval / `human_approved` 机器生成** — 永久禁止。
- **真实私人资料 dogfooding** — 在 Cubox + Obsidian 真实 gate 全部
  就绪前不进行。
- **真实 home 目录扫描** — 永久禁止。

### Quality Gates (local)

- `ruff check .`: clean.
- `pytest --no-header -q`: 1236 passed, 3 skipped.
- `git diff --check`: clean.
- Sensitive-token rg sweep on new src files: only docstring mentions
  of the ban list itself; no `Path.home()` / `requests.` / `httpx.` /
  `subprocess` / `dotenv` / `human_approved = True` etc.
