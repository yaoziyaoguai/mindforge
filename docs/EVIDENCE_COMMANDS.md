# MindForge Evidence Commands — Copy-Paste Cookbook

> Status: documentation. **Each command runs locally and prints
> evidence you can save / paste into a report.** No command in this
> cookbook writes to your real Obsidian vault, calls Cubox, prints
> secrets, or auto-approves anything.

## How to use

Run from the repo root with the venv activated:

```bash
cd /path/to/mindforge
source .venv/bin/activate
```

Each section produces evidence you can copy verbatim into a review
packet, an issue, or your own audit log.

---

## E1 — Quality gates

```bash
.venv/bin/ruff check .
.venv/bin/pytest --no-header -q
git diff --check
git status --short
git rev-list --left-right --count origin/main...HEAD
```

Expected baseline (v0.13 stage-complete):

- ruff: `All checks passed!`
- pytest: `1270 passed, 3 skipped`
- diff --check: empty
- ahead/behind: `0    0` (after Stage 5 push)

---

## E2 — Default-fake confirmation

```bash
.venv/bin/mindforge --version
.venv/bin/mindforge doctor --paths
.venv/bin/mindforge provider readiness --config configs/mindforge.yaml
.venv/bin/mindforge provider readiness --config configs/mindforge.yaml --format json | head -30
```

Look for: `active_profile: fake`, `opt_in_state: fake_default` (or
`env_only` if you happen to have a recognised env var exported), and
`can_run_real_smoke: false`.

---

## E3 — Real provider refusal (no opt-in)

```bash
.venv/bin/mindforge provider smoke --config configs/mindforge.yaml
```

Look for: `ran: False`, `blocker: <explicit reason>`, exit code 0.
This is the safe default and **must not** require any env var.

---

## E4 — Real provider opt-in (only if you have a billed key)

```bash
# 1. Confirm env loader sees your key (presence only — value never read)
.venv/bin/mindforge provider readiness --config configs/mindforge.yaml \
    --format json | python -c "import sys, json; r=json.load(sys.stdin); \
    print([a for a in r['provider']['aliases'] if a['api_key_present']])"

# 2. Run synthetic smoke with explicit opt-in
.venv/bin/mindforge provider smoke --config configs/mindforge.yaml \
    --allow-real --profile anthropic_coding_plan
```

Look for: `ran: True`, `output_artifact: ai_draft_preview`,
`human_approved: False`, `written: False`, `tokens_in/out` populated,
short scrubbed excerpt. **Never your API key.**

---

## E5 — Dogfood preflight (input safety)

```bash
# Synthetic — allowed
.venv/bin/mindforge dogfood preflight examples/demo-vault

# Local non-sensitive — allowed only with declaration
mkdir -p /tmp/mf-evidence && echo "synthetic" > /tmp/mf-evidence/test.md
.venv/bin/mindforge dogfood preflight /tmp/mf-evidence/test.md \
    --declare-non-sensitive

# Obsidian vault — refused (set up disposable demo)
mkdir -p /tmp/mf-evidence/v/.obsidian
echo "x" > /tmp/mf-evidence/v/n.md
.venv/bin/mindforge dogfood preflight /tmp/mf-evidence/v/n.md \
    --declare-non-sensitive
echo "exit=$?"   # expect 2

# Cleanup
rm -rf /tmp/mf-evidence
```

---

## E6 — Approval boundary check

```bash
# List currently-pending ai_draft cards in the demo vault
.venv/bin/mindforge approve list --vault examples/demo-vault

# Read-only show (does NOT promote)
.venv/bin/mindforge approve show --card <card-path> \
    --vault examples/demo-vault

# (Skip this in evidence runs — actually approves)
# .venv/bin/mindforge approve --card <card-path> --vault examples/demo-vault
```

Look for: `approve list` works without flipping anything, `approve
show` is read-only.

---

## E7 — Boundary regex sweep on tree

```bash
# Should produce ZERO non-comment, non-test hits:
rg -n 'human_approved\s*=\s*True' src/mindforge \
    --glob '!*_test.py' --glob '!test_*.py'

# Should produce ZERO hits:
git ls-files | grep -E '\.env$'
git log --all --source -- .env 2>&1 | head

# Should produce ZERO hits:
rg -n 'sk-[A-Za-z0-9]{16,}|Bearer [A-Za-z0-9]{16,}|AIza[A-Za-z0-9]{16,}' \
    src docs tests configs README.md
```

---

## E8 — Architecture boundary tests

```bash
.venv/bin/pytest tests/test_v013_cli_provider_surface.py \
                  tests/test_v013_real_smoke_safety.py \
                  tests/test_v013_provider_readiness.py \
                  tests/test_v013_stage4_dogfood_preflight.py \
                  tests/test_v013_stage5_closure_boundaries.py \
                  tests/test_v014_future_gates_spec.py \
                  tests/test_roadmap_completion_safety.py \
                  tests/test_review_approval_boundary.py \
                  tests/test_custom_strategy_import_boundaries.py \
                  -q --no-header
```

Look for: all green, no skips other than the documented 3.

`test_v014_future_gates_spec.py` pins the v0.14 gate-doc + cookbook
structure; `test_roadmap_completion_safety.py` is the repo-wide
forbidden-impl scan for G1–G6 (cubox HTTP / Obsidian write /
human_approved auto / subprocess in strategy layer / RAG-embedding-
semantic / git tag automation). Deleting either to "make CI green"
is a P0 violation by policy — see
[ROADMAP_COMPLETION_LEDGER.md](ROADMAP_COMPLETION_LEDGER.md) §How
a future contributor opens a gate.

---

## E9 — Roadmap state

```bash
ls docs/V0_13_*.md docs/V0_14_*.md docs/ROADMAP_COMPLETION_LEDGER.md
grep -E '^## v0\.13 Stage' docs/ROADMAP.md
grep -E '^## v0\.14|^## v1\.0' docs/ROADMAP.md
```

Look for: 5 Stage closure sections; v0.14 future-gate section;
ROADMAP_COMPLETION_LEDGER.md present (single-page status table).

---

## E10 — Push status

```bash
git log --oneline -5
git rev-list --left-right --count origin/main...HEAD
git tag --points-at HEAD
git tag --list | tail -10
```

Look for: ahead/behind = 0/0 if everything is pushed; no tag created.

---

## What this cookbook does NOT do

- ❌ Does not `cat .env`
- ❌ Does not print secrets
- ❌ Does not call Cubox
- ❌ Does not write to a real Obsidian vault
- ❌ Does not auto-approve any card
- ❌ Does not create a git tag
- ❌ Does not push to a remote you didn't ask for
