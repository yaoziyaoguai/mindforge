# RFC — G1 Real Cubox Ingestion (Dogfood Plan)

> **Status: RFC only.** This document is a design-review request and a
> phased dogfooding plan. It is **not** an authorization to call the
> real Cubox API, **not** an implementation, **not** a release. The G1
> gate in [V0_14_FUTURE_GATES.md](V0_14_FUTURE_GATES.md) remains
> closed until the user explicitly authorizes Phase 1 below in a
> follow-up Ask User.
>
> Companion docs:
> [V0_14_FUTURE_GATES.md §G1](V0_14_FUTURE_GATES.md) (capability spec) ·
> [CUBOX_DRY_RUN.md](CUBOX_DRY_RUN.md) (existing local-JSON path) ·
> [LOCAL_FIRST_PRIVACY_CONTRACT.md](LOCAL_FIRST_PRIVACY_CONTRACT.md) ·
> [SOURCE_ADAPTER_PROTOCOL.md](SOURCE_ADAPTER_PROTOCOL.md).

## 1. User context (input fact)

The user has confirmed that **his** Cubox account and Obsidian vault
are dedicated, **non-sensitive, project-only dogfooding stores**
prepared specifically for MindForge. They are **not** personal
secrets and **not** work-confidential material.

This unlocks the *possibility* of writing this RFC. It does **not**
remove the Cubox API token / link from the secret class: tokens
remain `.env`-managed, never printed, never committed, never logged.
"Non-sensitive content" is not "non-sensitive credential".

## 2. Why open G1 now

1. The capture leg of MindForge's loop (capture → process → review
   → approve → recall) is currently driven only by local JSON
   exports (`docs/CUBOX_DRY_RUN.md`). Without a real-API path, the
   loop cannot be exercised end-to-end.
2. The user has prepared a non-sensitive Cubox account that lets us
   test the real path without violating privacy invariants.
3. Real-API evidence is needed before the related G2 (Obsidian
   write) RFC can be motivated by anything other than speculation.

## 3. Scope

### In-scope (this RFC and its eventual implementation)

- Fetching items from a real Cubox account into in-memory
  `SourceDocument` previews.
- Producing `ai_draft` previews for human review.
- Producing a structured per-run report containing only counts,
  titles, and `SourceDocument.id` references.

### Out-of-scope (this RFC)

- Whole-account synchronisation.
- Auto-polling / scheduling / background jobs.
- Persisting Cubox content beyond the in-process run unless the user
  explicitly invokes a future `--persist` flag (which itself would be
  a separate RFC).
- Writing to Obsidian — that is **G2**, gated separately.
- Generating `human_approved` records — only `approver.approve_card`
  with a human in the loop can do that, and this RFC does not change
  that.
- RAG / embedding / semantic merge.

### Permanently forbidden (does not become legal even after G1 opens)

- Printing the Cubox API token / link in any output, log, or commit.
- Reading `.env` outside the existing `env_loader` (which already
  silently no-ops on missing file).
- Defaulting `active_profile` to anything that triggers real Cubox.
- Producing `human_approved=True` from any non-human path.
- Bypassing item-cap or sample-folder constraints.

## 4. Architecture invariants

These predate this RFC and **must remain true** after G1 opens.

| # | Invariant |
|---|---|
| 1 | Cubox is a **`SourceAdapter`** — never a processor, never a writer. |
| 2 | `Processor` / `KnowledgeStrategy` consume only `SourceDocument`. |
| 3 | `CuboxAdapter` does **not** import `cards.py`, `workspace*`, `obsidian*`, `approval_service`, or `recall_service`. |
| 4 | CLI is a thin Typer adapter; orchestration lives in services. |
| 5 | Presenter renders preview text only; never mutates state. |
| 6 | `ai_draft` and `human_approved` are distinct artifact classes; only `approver.approve_card` produces the latter. |
| 7 | `active_profile: fake` remains the safe default. |
| 8 | Real Cubox is reachable only via explicit opt-in flag **plus** secret presence check. |
| 9 | Tests pin the boundary; deleting a guard test = P0 violation. |

## 5. Phased dogfooding execution plan

Each phase ends with an **Ask User checkpoint**. No phase auto-runs
the next.

### Phase 0 — Preparation (user-side; no agent action)

- User configures Cubox token in a local `.env` (already
  `.gitignore`-protected).
- User chooses a single sample folder name **or** an item-cap
  starting at **5–20 items** (hard ceiling: 50).
- User does **not** paste the token to the agent.
- User confirms the chosen sample folder contains only non-sensitive
  dogfooding items.

### Phase 1 — Connection diagnostic

- New (or extended) `mindforge cubox readiness --config <path>`
  command:
  - Reads token *presence only* via existing `env_loader`.
  - Reports `{token_present: bool, sample_folder_set: bool,
    item_cap: N, base_url_present: bool}`.
  - **Never** prints the token; never prints the base URL value.
  - Exits 0 in all branches; failure paths emit masked diagnostics
    (e.g., `"token not present — run with --profile fake to stay
    safe"`).
- Implementation reuses the `provider_readiness.py` pattern.
- Does **not** make a network call.

### Phase 2 — Small-scope fetch (the actual G1 trigger)

- Extended command (working title): `mindforge cubox fetch
  --sample-folder <name> --item-cap N --dry-run --allow-real`.
- All four flags required; **no defaults activate the real path**.
- Calls `CuboxAdapter.fetch_inbox` (currently
  `NotImplementedError`) implementation.
- Returns at most `N` items, scoped to `<name>`.
- Output:
  - Per-item: `title`, `cubox_id`, `created_at`, `byte_length`,
    `source_document_id`.
  - **Never** raw bodies in the default output.
  - **Never** the token in any error path.
- Persistence: **none** by default. With `--dry-run` the run leaves
  no on-disk artifact other than an audit log line containing only
  counts and ids (no titles, no bodies).

### Phase 3 — `ai_draft` generation (review-only)

- Feed Phase-2 `SourceDocument`s through the existing fake provider
  (default) or, if user explicitly switches `active_profile`, the
  real LLM provider (which is itself gated by existing
  `provider_readiness` rules).
- Output is `ai_draft` only. **No `human_approved` is produced.**
- Display via existing `recall` / `review` presenters.

### Phase 4 — Human review

- User reads each `ai_draft`, marks subjective value.
- Notes recorded out-of-band (a personal log file, not in the repo).
- Particular attention to: extraction quality, field-mapping bugs,
  presenter wording, false positives, false negatives.

### Phase 5 — Decision gate (Ask User)

Three legitimate forks:

1. **Quality good** → motivate G2 Obsidian write RFC; G2 itself
   remains a separate gate.
2. **Quality mediocre** → improve `KnowledgeStrategy` / extraction
   first; G2 deferred.
3. **Field instability** → fix `CuboxAdapter` field mapping first;
   re-run Phase 2 with same sample folder.

## 6. Safety boundaries (recap)

- ❌ no token print, no token log, no token commit, no token in error
  message text
- ❌ no auto-polling / no background fetch / no scheduling
- ❌ no Obsidian write
- ❌ no `human_approved` generation
- ❌ no RAG / embedding / semantic merge
- ❌ no persistence beyond in-process run unless explicit follow-up
  RFC opens it
- ❌ no expansion beyond `--item-cap` / `--sample-folder` without a
  fresh Ask User
- ✅ `active_profile: fake` remains the default
- ✅ Cubox real is reachable only with `--allow-real` plus secret
  presence

## 7. Implementation prerequisites (before any Phase 2 code lands)

1. The **test surface** in §8 is written first (test-driven).
2. `dogfood_safety.py` extended with a `cubox_real_forbidden`
   classification for paths that look like Cubox dumps but lack the
   explicit flags.
3. `LOCAL_FIRST_PRIVACY_CONTRACT.md` updated to add the line
   "non-sensitive Cubox content does not promote a Cubox token to
   non-secret".
4. `ROADMAP_COMPLETION_LEDGER.md` adds a row "G1 Phase 1 readiness"
   in the `local-complete` bucket once the readiness command lands;
   "G1 Phase 2 fetch" stays `future-gated` until the user explicitly
   opens it.
5. No CLI restructuring; all new code lands as small additions to
   the existing `cubox_*.py` and `provider_readiness.py` neighbours.

## 8. Test surface to add (before any Phase 2 code lands)

Pinned by future `tests/test_g1_cubox_real_ingestion.py`:

1. `test_cubox_token_never_printed` — runs readiness + fetch with
   monkeypatched env, asserts token literal is absent from every
   captured stdout/stderr/log line.
2. `test_env_file_never_committed` — repo-level `git ls-files`
   assertion that `.env` is not tracked.
3. `test_env_presence_alone_does_not_enable_real_cubox` — token set
   but no `--allow-real` → command refuses with structured blocker.
4. `test_missing_token_emits_masked_diagnostic` — token absent →
   readiness reports `token_present: false`, never prints the empty
   string back out as a value.
5. `test_item_cap_is_enforced` — request `N+1`, receive ≤ `N`.
6. `test_sample_folder_is_enforced` — items outside the named folder
   are filtered before they enter the pipeline.
7. `test_fetch_returns_only_source_documents` — output type
   assertion.
8. `test_source_document_to_ai_draft_does_not_import_cubox_adapter`
   — AST guard on `KnowledgeStrategy` source.
9. `test_phase_2_does_not_create_human_approved` — runs Phase 2 +
   Phase 3 stub, asserts `human_approved=False` on every artifact.
10. `test_phase_2_does_not_write_obsidian` — monkeypatched
    file-system assertion.
11. `test_phase_2_does_not_enable_rag_embedding` — AST guard on
    cubox modules.
12. `test_failure_path_does_not_leak_token` — inject a fake API
    error, capture all output, assert no token literal.
13. `test_dry_run_output_contains_no_secret` — regex sweep.
14. `test_docs_do_not_promise_full_sync` — docs assertion: the
    string "whole account" does not appear in any G1-related doc as
    an offered capability.
15. `test_g1_default_closed` — simulating no `--allow-real` keeps
    G1 forbidden; deleting this test is a P0 violation.

## 9. Open questions

1. **Token storage**: stay with `.env` or move to OS keyring? RFC
   default is `.env` (lowest-friction, already supported). Keyring
   could be a Phase-2.5 follow-up.
2. **Audit log**: Phase 2 should emit one structured line per run
   with counts + ids. Where does it live? Proposal: `runs/cubox-
   YYYYMMDD-HHMMSS.jsonl`, `.gitignore`-protected.
3. **Folder naming convention**: should the RFC require the sample
   folder to start with a known prefix (e.g., `mindforge-`) so the
   adapter can refuse non-prefixed folders by default? Open.
4. **Rate-limit posture**: Cubox API limits unknown to MindForge.
   Conservative default: no concurrency, sleep 1 s between requests
   for the first 100 lifetime requests.
5. **Token rotation**: out-of-scope for G1; document as user
   responsibility.

## 10. What this RFC does **not** commit to

- It does not commit to building Phase 2 code.
- It does not commit to a timeline.
- It does not promise stability of Cubox API field shapes.
- It does not promote Cubox real ingestion to a default path under
  any condition.
- It does not weaken any G1–G6 guard test.

## 11. Decision required from the user

Before any code change:

- Approve / reject this RFC as a design.
- If approved, separately authorize **Phase 1 only** (readiness
  diagnostic; no network call).
- Phase 2 (the actual fetch with `--allow-real`) requires a **second
  separate Ask User** after Phase 1 evidence is on disk.
