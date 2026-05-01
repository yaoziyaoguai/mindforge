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
