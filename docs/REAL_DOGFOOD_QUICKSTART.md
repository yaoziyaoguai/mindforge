# Real Dogfood Quickstart

> **For new MindForge users.** 10 minutes from `pip install` to a real
> end-to-end dogfood loop using your own non-sensitive Cubox export
> and a project-only Obsidian vault. **Stays fake-default + dry-run
> at every step.** No real LLM call. No real Cubox HTTP call. No
> formal vault write. No `human_approved` record produced.
>
> Companion docs:
> [GETTING_STARTED.md](GETTING_STARTED.md) (full install guide) ·
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

## The runbook (single command)

```
mindforge dogfood quickstart --vault /path/to/project-vault \
  --cubox-export /path/to/cubox-export.json
```

This **prints** the 10-step runbook. It does **not** execute anything.
Each step is a copy-paste command you run yourself. If you skip
`--cubox-export`, the Cubox steps will still print but with
`<file.json>` placeholder text.

## What the runbook covers

| # | Command | What it does |
|---|---|---|
| 1 | `mindforge doctor --paths` | Confirm local paths + safety boundaries |
| 2 | `mindforge provider readiness ...` | Confirm `active_profile=fake` (no real LLM) |
| 3 | `mindforge dogfood cubox-readiness ...` | Confirm Cubox real-path readiness (no network) |
| 4 | `mindforge cubox dry-run --export <file.json>` | Cubox JSON-export offline preview (real data, zero network) |
| 5 | `mindforge cubox preview-ai-draft --export <file.json> --limit 3` | First 3 items → ai_draft via fake provider |
| 6 | `mindforge dogfood preflight examples/demo-vault --declare-non-sensitive` | Static dogfood path classification |
| 7 | `mindforge obsidian doctor --vault <project-vault>` | Confirm project vault safety (no home scan) |
| 8 | `mindforge obsidian scan --vault <project-vault> --limit 5` | Scan project vault for Markdown |
| 9 | `mindforge obsidian stage --vault <project-vault> --source <note.md> --dry-run` | Project-vault staging dry-run |
| 10 | `mindforge approve list` | List ai_drafts awaiting human approval |

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
