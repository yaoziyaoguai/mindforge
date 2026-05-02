# Example Custom Strategies — synthetic, preview-only

This directory holds **synthetic, non-sensitive** declarative custom
strategy fixtures. They exist to:

- Document the v0.12 declarative custom-strategy shape with a real,
  loadable file.
- Power `tests/test_custom_preview_packet_contract.py` Family E baseline
  asserts (Slice 4 discovery + Slice 5 preview-only refusal).
- Give downstream contributors a copy-paste-able starting point that
  they can adapt to their own (still synthetic) experiments.

## Safety contract

Per `docs/V0_13_DOGFOODING_READINESS.md` and the v0.12 capability matrix
(`docs/V0_12_CAPABILITY_MATRIX.md`), any file in this directory:

- is **review-only** — `mindforge` will refuse to execute it;
- never causes a real LLM provider call;
- never reads `.env`;
- never writes any Obsidian vault;
- never produces an `ai_draft` and never produces an approved card;
- never auto-approves anything.

Loading happens only when the user passes the explicit
`--custom-path examples/custom-strategies/` flag to
`mindforge strategies list`. Nothing in MindForge implicitly scans this
directory.

## Files

- `user_concept_review.yaml` — minimal synthetic example, status
  `preview`, `safety_policy: ai_draft_only`. Same shape that Slice 5
  preview-packet tests pin as the canonical valid sample.

## How to inspect

```bash
.venv/bin/mindforge strategies list \
  --custom-path examples/custom-strategies/
```

The command will list this synthetic strategy alongside built-ins and
clearly mark it as `(custom)` and as preview-only. Asking
`mindforge` to actually run it will fail loudly with
`NotYetImplementedStrategyError("preview" + "discovery is not execution")`
— that is the intended, documented behaviour.
