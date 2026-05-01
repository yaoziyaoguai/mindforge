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

After the v0.7.20–v0.7.23 Architecture Quality Milestone completes, return to
validating real local-product usability on small, non-sensitive disposable
vault copies before adding new feature classes.

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
