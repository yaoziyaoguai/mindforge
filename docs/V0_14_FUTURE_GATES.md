# MindForge v0.14 / v1.0 Future Gate Specifications

> Status: **specification only**. Nothing here is implemented in v0.13.
> Each capability listed must clear its named gate **before** any code
> is written. This document is the contract between current safety
> boundaries and future capability landings.

## Why explicit gates?

v0.13 deliberately kept several capabilities un-implemented because
their design impacts privacy / billing / vault integrity in ways that
cannot be made safe by tooling alone. Listing them as "TODO" without
gates would invite a future contributor to silently land them. Each
gate below specifies the *minimum* additional design work required.

## Gate template

Each gate has six required sections:

1. **Capability** — what we want to enable
2. **Why deferred** — what concrete risk drove deferral
3. **Pre-conditions** — what must be true before implementation starts
4. **Boundary contract** — what the implementation may NEVER do
5. **Closure criteria** — when can we say the gate is cleared
6. **Test surface** — what tests must exist to ratify closure

---

## Gate G1 — Real Cubox Ingestion

1. **Capability**: Read items from a real Cubox account into MindForge
   `SourceDocument`s.
2. **Why deferred**: Cubox accounts hold private articles. A naive
   "fetch everything" would dump real personal content into the
   pipeline before the user has any chance to review.
3. **Pre-conditions**:
   - `--sample-folder <folder>` flag forces scoping to a single named
     folder (no whole-account fetches).
   - `--item-cap N` (default 10, hard ceiling 50) limits per-run.
   - `--dry-run-first` mandatory on first invocation per session;
     prints titles only, no body.
   - `--no-persist` is the default; persistence requires a separate
     explicit flag.
   - Existing `cubox_dryrun_presenter.py` keeps preview-only role.
4. **Boundary contract**:
   - Never auto-poll on a timer.
   - Never write Cubox content directly to vault — must go through
     the same `ai_draft → human approval → human_approved` path.
   - Never log Cubox raw bodies.
   - Cubox API key follows the same `.env` + presence-only rules as
     LLM keys.
5. **Closure criteria**:
   - Test stub of Cubox API returns synthetic items only.
   - Real-account smoke is run by user once, recorded as evidence,
     never automated in CI.
   - `dogfood preflight` adds a `cubox_real_forbidden` classification
     for paths that look like Cubox dumps without the explicit gate.
6. **Test surface**:
   - `test_cubox_real_ingestion_requires_sample_folder`
   - `test_cubox_real_ingestion_requires_dry_run_first`
   - `test_cubox_real_ingestion_does_not_persist_by_default`
   - `test_cubox_real_ingestion_does_not_create_human_approved`

---

## Gate G2 — Real Obsidian Formal-Note Write

1. **Capability**: Write produced cards into a real Obsidian vault as
   formal notes (not just `00-Inbox` previews).
2. **Why deferred**: Real Obsidian vaults are user-owned source-of-
   truth. Silent writes can corrupt years of personal notes.
3. **Pre-conditions**:
   - `--target <vault>` must be explicit and must NOT match
     `dogfood_safety._REFUSING_CLASSES` patterns.
   - `--dry-run` is default; actual write requires `--commit-write`.
   - `--diff-preview` is the default before any write; user must
     confirm interactively.
   - Per-write confirmation prompt (no `--yes-to-all` flag — by
     design).
   - Existing `obsidian_stage` flow keeps preview-only role.
4. **Boundary contract**:
   - Never overwrite an existing file without showing diff and asking
     for confirmation.
   - Never write files outside the user-named target subdirectory.
   - Never write files with names that collide with existing
     `.obsidian/` config files.
   - Always create a backup snapshot under `.mindforge/backups/`
     before the first write of a session.
5. **Closure criteria**:
   - 100% test coverage of write-path branches.
   - Manual smoke against a *disposable* vault recorded as evidence.
   - Rollback procedure documented and tested.
6. **Test surface**:
   - `test_obsidian_write_requires_explicit_commit_flag`
   - `test_obsidian_write_creates_backup_before_first_write`
   - `test_obsidian_write_refuses_overwrite_without_confirmation`
   - `test_obsidian_write_refuses_outside_target_subdirectory`

---

## Gate G3 — `human_approved` Production UX

1. **Capability**: A more ergonomic approval flow (batch review,
   inline diff, keyboard navigation) — *not* auto-approve.
2. **Why deferred**: Better UX must not weaken the approval boundary.
3. **Pre-conditions**:
   - `approver.approve_card` remains the only function that flips
     `human_approved=True`.
   - All UX surfaces must call `approve_card`; none may set the field
     directly.
   - No batch flag may approve more than one card per keystroke
     without a confirmation prompt that names every card.
4. **Boundary contract**:
   - No timer-based auto-approval.
   - No "approve based on similarity to past approvals."
   - No model-driven approval.
   - No silent `human_approved=True` from any presenter / writer /
     CLI helper.
5. **Closure criteria**:
   - Existing `human_approved` literal allowlist test still passes.
   - New UX surface added to allowlist with explicit reason.
   - Manual smoke recorded.
6. **Test surface**:
   - Existing `test_human_approved_promotion_requires_explicit_approve_card_call` still passes.
   - `test_batch_approve_requires_per_card_confirmation`
   - `test_no_approval_via_similarity_inference`

---

## Gate G4 — Custom Executable Strategy Runtime

1. **Capability**: Allow users to provide a Python entry-point that
   actually runs in-process (not just declarative preview).
2. **Why deferred**: Arbitrary user code runs with full process
   privileges; would obliterate every other safety gate.
3. **Pre-conditions**:
   - Sandbox design first (subprocess + capability-based environment
     restriction at minimum).
   - Out-of-process execution; the strategy never sees the parent
     process's `os.environ`.
   - All file I/O goes through a single capability handle the parent
     grants.
   - No network unless the strategy declares `requires_network: true`
     in its yaml AND user passes `--allow-network-strategy`.
4. **Boundary contract**:
   - Strategy runtime never imports MindForge internals (no
     approval/writer/Obsidian/Cubox).
   - Strategy can produce `ai_draft` only; cannot produce
     `human_approved`.
   - Strategy timeout enforced (default 30s, hard cap 5min).
5. **Closure criteria**:
   - Sandbox design RFC accepted.
   - Reference implementation passes adversarial test suite.
   - Existing declarative preview stays unchanged and is recommended
     as the default.
6. **Test surface**:
   - `test_custom_strategy_runtime_runs_out_of_process`
   - `test_custom_strategy_runtime_cannot_read_parent_env`
   - `test_custom_strategy_runtime_cannot_produce_human_approved`
   - `test_custom_strategy_runtime_enforces_timeout`

---

## Gate G5 — RAG / Embedding / Semantic Merge

1. **Capability**: Vector-index user cards for semantic recall and
   cross-card merge suggestions.
2. **Why deferred**: Embedding APIs ship card content to remote
   services; semantic merge can silently mutate `human_approved`
   cards.
3. **Pre-conditions**:
   - Privacy-impact assessment documented.
   - Local-only embedding option (e.g., Ollama / sentence-transformers)
     supported as the *default* path.
   - Remote embedding requires its own opt-in flag analogous to
     `--allow-real`.
   - Semantic merge only produces *suggestions* — never modifies
     `human_approved` cards.
4. **Boundary contract**:
   - No silent re-embedding on file change.
   - No suggestion auto-application.
   - Clear visual distinction between user content and AI suggestion.
5. **Closure criteria**:
   - Local embedding default works end-to-end on demo vault.
   - Remote embedding gated as above.
   - Suggestion → approval flow has its own approval boundary.
6. **Test surface**:
   - `test_default_embedding_path_is_local`
   - `test_remote_embedding_requires_explicit_opt_in`
   - `test_semantic_merge_does_not_modify_human_approved`

---

## Gate G6 — Public Release / Git Tag

1. **Capability**: Cut a `vX.Y` tag and publish to PyPI.
2. **Why deferred**: A tag is a public commitment; once a version
   number is out, support obligations follow.
3. **Pre-conditions**:
   - Human authorizer named explicitly (not "the team").
   - CHANGELOG.md frozen for the version.
   - `V0_X_RELEASE_READINESS_EVIDENCE.md` reviewed by authorizer.
   - Clean working tree, ahead/behind 0/0.
   - No `*-rc*` artifacts in tree.
4. **Boundary contract**:
   - No automation may create a tag.
   - No CI may publish to PyPI without an authorizer-signed marker
     file in the repo.
5. **Closure criteria**:
   - Authorizer sign-off recorded in commit message.
   - Tag created manually with `git tag -s vX.Y -m "..."`.
   - Push tag is a separate explicit operation.
6. **Test surface**:
   - `test_no_v013_doc_promises_a_tag` (already exists in Stage 5)
   - Future: `test_release_marker_required_for_publish`

---

## Cross-cutting invariants (apply to every gate)

- Fake remains the default for any opt-in path.
- `.env` value is never printed, never committed.
- `human_approved` only via `approver.approve_card`.
- AST guards stay in place for new modules.
- Each gate gets its own `docs/V0_X_GATE_GN.md` doc when work begins.
