# Real Dogfood Quickstart

> **Haven't tried MindForge yet?** Run `mindforge demo` first — a
> zero-token / zero-network 60-second tour on bundled fixtures.
> Then come back here for the real-data path.
>
> **For new MindForge users.** 10 minutes from `pip install` to a real
> end-to-end dogfood loop using your own non-sensitive Cubox export
> and a project-only Obsidian vault. **Stays fake-default + dry-run
> at every step.** No real LLM call. No real Cubox HTTP call. No
> formal vault write. No `human_approved` record produced.
>
> Companion docs:
> [USAGE.md](USAGE.md) (canonical usage guide) ·
> [LOCAL_FIRST_PRIVACY_CONTRACT.md](LOCAL_FIRST_PRIVACY_CONTRACT.md) ·
> [CUBOX_DRY_RUN.md](CUBOX_DRY_RUN.md) ·
> [V0_14_FUTURE_GATES.md](V0_14_FUTURE_GATES.md) (G1–G6 gates) ·
> [RFC_G1_CUBOX_REAL_INGESTION.md](RFC_G1_CUBOX_REAL_INGESTION.md)
> (the future HTTP path; not yet open).

## What you need

1. A working Python venv with MindForge installed (`pip install -e .`).
2. **Optional**: a Cubox account where you can do
   `Settings → Export → JSON`. Pick **non-sensitive** items only;
   any item you wouldn't paste into a public gist should not be in
   the export.
3. **Optional**: a **project-only** Obsidian vault — a directory you
   created **specifically for MindForge dogfooding**. Do **not** point
   commands at your real personal Obsidian vault.

If you only want the packaged demo vault, create a disposable copy first:

```
mindforge dogfood init-demo --target /tmp/dogfood-vault
```

This works from an installed CLI and does not require a repository checkout.

## The runbook (single command)

Before printing the runbook, check that your target is still safe:

```
mindforge dogfood readiness --vault /path/to/project-vault \
  --cubox-export /path/to/cubox-export.json
```

This reads neither `.env` nor the Cubox export content. It only checks:
the vault path classification, provider fake-default state, and whether
the optional export path exists.

```
mindforge dogfood quickstart --vault /path/to/project-vault \
  --cubox-export /path/to/cubox-export.json
```

This **prints** the 11-step runbook. It does **not** execute anything.
Each step is a copy-paste command you run yourself. If you skip
`--cubox-export`, the Cubox steps will still print but with
`<file.json>` placeholder text.

## What the runbook covers

| # | Command | What it does |
|---|---|---|
| 1 | `mindforge dogfood readiness --vault <project-vault>` | One-screen safety summary before copying the runbook |
| 2 | `mindforge doctor --vault <project-vault> --paths` | Confirm local paths + safety boundaries |
| 3 | `mindforge provider readiness ...` | Confirm `active_profile=fake` (no real LLM) |
| 4 | `mindforge dogfood cubox-readiness ...` | Confirm Cubox real-path readiness (no network) |
| 5 | `mindforge cubox dry-run --export <file.json>` | Cubox JSON-export offline preview (real data, zero network) |
| 6 | `mindforge cubox preview-ai-draft --export <file.json> --limit 5` | First 5 items → ai_draft via fake provider |
| 7 | `mindforge dogfood preflight <project-vault> --declare-non-sensitive` | Static dogfood path classification |
| 8 | `mindforge obsidian doctor --vault <project-vault>` | Confirm project vault safety (no home scan) |
| 9 | `mindforge obsidian scan --vault <project-vault> --limit 5` | Scan project vault for Markdown |
| 10 | `mindforge obsidian stage --vault <project-vault> --source <note.md> --dry-run` | Project-vault staging dry-run |
| 11 | `mindforge approve list --vault <project-vault>` | List ai_drafts awaiting human approval |

## Safety boundaries you can verify yourself

After running the steps above, verify:

- `mindforge dogfood cubox-readiness` output contains
  `token value not printed` (never the token itself).
- `mindforge provider readiness` output never contains your `api_key`
  value.
- `mindforge cubox dry-run` does **not** make a network call (you
  can confirm by running with the network disabled).
- `mindforge obsidian stage --dry-run` does **not** write to the
  vault (verify with `git status` if your project vault is git-
  tracked).
- No command produces a `human_approved` record. The only path that
  promotes an `ai_draft` to `human_approved` is `approver.approve_card`,
  invoked explicitly by you per item.

## What this guide intentionally does not cover

- **Real Cubox HTTP API ingestion** (`fetch_inbox`). This path is
  future-gated (G1, see `V0_14_FUTURE_GATES.md` and
  `RFC_G1_CUBOX_REAL_INGESTION.md`). Today, the JSON-export path
  (steps 4–5) gives you a real-data dogfood loop without needing to
  open G1.
- **Obsidian formal-note write** (`commit_write_card` etc.).
  Future-gated (G2). Use `--dry-run` to preview.
- **Auto-approval** of `ai_draft → human_approved`. Forbidden by
  design; G3 RFC required even for UX changes around the gesture.
- **Background indexing / RAG / embedding**. Out of scope (G5).
- **`git tag` / public release**. Out of scope (G6).

## Common errors and what to do

- *"Cubox export 文件不存在"* — run `Settings → Export` from Cubox
  web and pass the resulting `.json` file path.
- *"token_present: False"* in `cubox-readiness` — that's expected
  when you have not configured `MINDFORGE_CUBOX_TOKEN`. The JSON-
  export path (steps 4–5) does not need a token.
- *"Obsidian vault not found"* — pass `--vault <abs-path>` to
  `mindforge obsidian doctor` and confirm the directory exists. Do
  not pass your real personal vault.

## When you outgrow this quickstart

Open an RFC for the future gate you want to cross. RFC = design
review only; not implementation, not authorization, not release.
The current open RFC is
[`RFC_G1_CUBOX_REAL_INGESTION.md`](RFC_G1_CUBOX_REAL_INGESTION.md).

---

## Explicit limit guidance (read this before you run anything Cubox-related)

MindForge **does not support full Cubox account sync**. Today the only
real-Cubox-data path is the JSON-export route; there is no automatic
"pull everything" command.

For your **first** dogfood run we strongly recommend:

- **`--limit 5`** for `mindforge cubox preview-ai-draft`. Five items
  is enough to see the loop end-to-end without burning attention.
- **Do not exceed `--limit 20`** on your first 2–3 runs. The fake
  provider is fast, but reviewing 20+ ai_draft items by hand at once
  is exhausting and tends to short-circuit careful review.
- **Never** target a non-curated, full export. If your Cubox account
  has hundreds of items, do `Settings → Export` of a *specific
  folder* (or hand-trim the JSON to the 5–20 items you actually want
  to dogfood). The whole point of the JSON-export route is that
  *you* control which items enter MindForge.
- **There is no `--all` flag.** If you find yourself asking "how do I
  process everything", that is a signal you are at the boundary of
  what this quickstart is designed for. Stop and read
  [`RFC_G1_CUBOX_REAL_INGESTION.md`](RFC_G1_CUBOX_REAL_INGESTION.md)
  before going further.

`mindforge cubox dry-run` has its own `--limit` flag (default 3) but
that one only controls *how many sample titles are printed* — the
underlying scan is whole-file. Use `dry-run` first to confirm the
file is well-formed; then use `preview-ai-draft --limit 5` for the
ai_draft loop.

## Rollback and cleanup guidance

Every step in the runbook above is **safe by default**:

| Step | Writes anything? | How to roll back |
|---|---|---|
| `doctor`, `provider readiness`, `cubox-readiness`, `readiness`, `quickstart` | No | Nothing to roll back |
| `cubox dry-run`, `cubox preview-ai-draft` | **In-memory only.** No Cubox state changes, no vault writes. | Nothing to roll back |
| `dogfood preflight` | No | Nothing to roll back |
| `obsidian doctor`, `obsidian scan`, `obsidian links` | Read-only | Nothing to roll back |
| `obsidian stage --dry-run` | **No** (this is what `--dry-run` means) | Nothing to roll back |
| `obsidian stage --write` | **Yes — writes to staging/ inside the vault** | See below |
| `approve list` | Read-only | Nothing to roll back |

**If you accidentally ran `obsidian stage --write` on a vault you did
not mean to write to:**

1. **Stop.** Do not run any further `mindforge` commands until you
   have cleaned up.
2. The write target is a `staging/` directory inside the vault you
   passed to `--vault`. List what was created:
   ```bash
   ls -la <your-vault>/staging/
   ```
3. If the vault is git-tracked (recommended for project vaults),
   `git status` and `git restore .` / `git clean -fd staging/` will
   undo the write.
4. If the vault is not git-tracked, delete the specific files
   listed in step 2. **Do not** `rm -rf` the whole vault.
5. MindForge **does not** modify your `.obsidian/` directory,
   existing notes, or links. The blast radius is confined to
   `staging/` plus any new Markdown files MindForge created.

**Strong recommendations to make rollback trivial:**

- Use a **disposable** project vault for your first runs (e.g.,
  `mindforge dogfood init-demo --target /tmp/dogfood-vault` and pass
  `--vault /tmp/dogfood-vault`).
- Keep your project vault **under git** so any unwanted write is one
  `git restore` away.
- **Do not** use your real personal Obsidian vault until after at
  least 5 successful project-vault dry-runs.

## Token safety guidance

Your Cubox API token (and any future LLM API key) is a **secret**.
MindForge enforces this in code via `cubox_readiness` (presence-only
check, never reads the value) and via test-pinned literals
(`token value not printed`). You must enforce it on your side too.

**Never:**

- Paste your token into a chat with any AI agent (including this
  one).
- Commit a token to git, even temporarily, even in a branch you
  "plan to delete".
- Put a token in a docs file, README, USAGE, runbook,
  comment, commit message, or test fixture.
- Print a token via `echo $MINDFORGE_CUBOX_TOKEN`, `printenv`, or
  `env | grep CUBOX` in a recorded session.
- Paste a `mindforge` log line that *might* contain a token into a
  GitHub issue, gist, or screenshot.

**Always:**

- Set the token via your shell's environment (e.g., a `.env` file
  read by your shell startup, or `export MINDFORGE_CUBOX_TOKEN=...`
  typed by hand). MindForge **does not** read `.env` content; it
  only checks env-var presence.
- Treat `mindforge dogfood cubox-readiness` as the *only* sanctioned
  way to ask "is my token wired up?" — it returns `token_present:
  True/False` and a literal `token value not printed`, never the
  value.
- If you suspect a leak (you pasted it somewhere by mistake, or
  it ended up in shell history that was synced), **rotate it
  immediately** in Cubox web (`Settings → API`) and update the env
  var. The leaked token must be considered burned.

## Boundary guidance — what this quickstart guarantees and what it does NOT do

**This quickstart guarantees** (verified by tests):

- Default `provider readiness` shows `fake-default` (no real LLM).
- `cubox-readiness` returns `g1_gate_open: False` always.
- `cubox dry-run` and `preview-ai-draft` run on a local JSON file
  only; **no Cubox HTTP API call is made**.
- `obsidian stage` defaults to `--dry-run`; `--write` is opt-in and
  only ever writes to `staging/` inside the `--vault` you pass.
- All ai_draft outputs are **review-only**. They cannot become
  `human_approved` automatically.
- No background indexing, no RAG, no embedding, no semantic merge.
- No data ever leaves your machine via this quickstart.

**This quickstart does NOT and cannot:**

- Bulk-sync your full Cubox account. (No such command exists.)
- Write to your real personal Obsidian vault. (Only the path you
  pass to `--vault` is touched, and only `staging/` within it.)
- Auto-approve any item. (`approver.approve_card` requires explicit
  per-item invocation by you.)
- Produce a `human_approved` record. (Forbidden by design across
  every code path in this quickstart.)
- Scan your `$HOME` directory or any path you did not pass on the
  command line.
- Read or print the *value* of any env var, including your Cubox
  token and any LLM api_key.
- Tag a release, push to origin, or modify the remote. (MindForge
  itself never runs `git tag` or `git push`; you do.)
- Constitute a release. There is **no v1.0 tag**, no PyPI publish,
  no "stable" promise yet. This is dogfood readiness — you are an
  early user, not a v1.0 customer.

If any of the above appear to be happening, **stop immediately** and
file an issue: that would be a hard-boundary violation, not a UX
question.
