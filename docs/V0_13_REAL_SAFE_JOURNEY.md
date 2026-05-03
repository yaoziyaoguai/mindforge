# MindForge v0.13 Real-Safe User Journey

> Status: documentation. **No automation script behind this — every
> step is a manual command the user runs.** The whole point of this
> journey is that no step is silently auto-promoted.

## Audience

A new MindForge user who wants to verify, in roughly 10 minutes, that:

1. The default install is fake-safe;
2. Their real LLM provider is reachable when they explicitly opt in;
3. Their dogfood input path is classified safely before they spend
   tokens or attention on it;
4. No `human_approved` card is created without their hand on the
   `approve` command.

## Step 0 — Install and verify fake default

```bash
pip install mindforge   # or: pip install -e . from a clone
mindforge --version
mindforge doctor --paths
```

Expected:

- `doctor` reports `Python`, `Platform`, `config path`;
- No `.env` is read by `--version` or `doctor`;
- `active_profile` (visible via next step) is `fake`.

## Step 1 — Confirm fake default with `provider readiness`

```bash
mindforge provider readiness --config configs/mindforge.yaml
```

Expected:

- `active_profile: fake`
- `opt_in_state: fake_default` (or `env_only` if you happen to have
  one of MindForge's recognised env vars exported — that alone does
  **not** activate real)
- `can_run_real_smoke: False`

Optional JSON form for scripts / CI:

```bash
mindforge provider readiness --config configs/mindforge.yaml --format json
```

## Step 2 — Try real smoke without opt-in (must refuse)

```bash
mindforge provider smoke --config configs/mindforge.yaml
```

Expected:

- `ran: False`
- `blocker: ...` explaining why (no `--allow-real`, fake profile, etc.)
- Exit code 0 (refusal is not an error; it's a feature)

## Step 3 — Opt in to real smoke (only if you have a billed key)

> **Billing warning**: this step actually calls a real LLM endpoint.
> One synthetic prompt, ~hundreds of tokens. Confirm your account is
> what you expect before running.

```bash
# 1. Put your key in .env (gitignored). NEVER commit .env.
echo "MINDFORGE_LLM_API_KEY=sk-..." >> .env
chmod 600 .env

# 2. Confirm the env var name is recognised
mindforge provider readiness --config configs/mindforge.yaml

# 3. Run synthetic smoke against a non-fake profile
mindforge provider smoke --config configs/mindforge.yaml \
    --allow-real --profile anthropic_coding_plan
```

Expected:

- `ran: True`
- `provider_type`, `alias`, `tokens_in`, `tokens_out`, `latency_ms`
  populated
- `output_artifact: ai_draft_preview`
- `human_approved: False`
- `written: False`
- A short **scrubbed** output excerpt — never your API key, never
  truncation past 240 chars

If anything else appears (especially anything resembling your key),
stop and file an issue.

## Step 4 — Classify your dogfood input safely

```bash
# Synthetic path (always allowed)
mindforge dogfood preflight examples/demo-vault

# Your own non-sensitive local file (must declare)
mindforge dogfood preflight ./scratch/test.md --declare-non-sensitive

# A real Obsidian vault (must refuse)
mindforge dogfood preflight ~/MyVault/note.md
# → exit 2, classification=obsidian_vault_forbidden

# A path under your home (must refuse)
mindforge dogfood preflight ~/Documents/note.md
# → exit 2, classification=home_scan_forbidden
```

Preflight **never reads** your file contents. It only inspects path
shape + your declared intent + provider readiness.

## Step 5 — Run the actual fake dogfood checklist

```bash
mindforge dogfood plan --vault examples/demo-vault
```

This prints a manual checklist — copy each command, run it yourself,
review each output. There is no auto-runner; this is the design.

Notable fake-safe commands from the checklist:

```bash
mindforge process --profile fake --limit 1 --vault examples/demo-vault
mindforge approve list --vault examples/demo-vault
mindforge recall --query "agent" --vault examples/demo-vault
mindforge review weekly --vault examples/demo-vault
```

## Step 6 — Approve a card (the only path to `human_approved`)

```bash
mindforge approve list --vault examples/demo-vault
mindforge approve show --card <card-path> --vault examples/demo-vault
mindforge approve --card <card-path> --vault examples/demo-vault
```

This is the **only** code path that flips `human_approved=True`. No
preflight, no real smoke, no preview, no presenter writes this.

## Step 7 — What you have NOT done

By the end of this journey you have:

- ❌ NOT scanned your home directory
- ❌ NOT scanned your real Obsidian vault
- ❌ NOT pulled any Cubox content
- ❌ NOT written to your real Obsidian vault
- ❌ NOT auto-approved anything
- ❌ NOT printed your API key
- ❌ NOT committed `.env`
- ❌ NOT triggered RAG / embedding / semantic merge
- ❌ NOT executed any custom plugin / shell strategy

You **have** confirmed your install is safe-by-default and your real
provider is reachable when you ask for it.

## Cross-references

- [LOCAL_FIRST_PRIVACY_CONTRACT.md](./LOCAL_FIRST_PRIVACY_CONTRACT.md)
- [V0_13_DOGFOOD_PREFLIGHT.md](./V0_13_DOGFOOD_PREFLIGHT.md)
- [V0_13_REAL_LLM_SMOKE_SAFETY.md](./V0_13_REAL_LLM_SMOKE_SAFETY.md)
- [V0_13_CLOSURE_LEDGER.md](./V0_13_CLOSURE_LEDGER.md)
- [V0_13_RELEASE_READINESS_EVIDENCE.md](./V0_13_RELEASE_READINESS_EVIDENCE.md)
