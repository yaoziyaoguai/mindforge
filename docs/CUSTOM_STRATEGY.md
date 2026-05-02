# Custom Strategy (Declarative Only) — v0.12

> **Status:** v0.12 Slice 1 Green — declarative `StrategyDefinition` data
> contract + strict validation. **No** loading source, **no** runtime
> execution, **no** registry auto-registration yet. Those are scoped to
> later v0.12 slices and explicit Green commits.

## 0. TL;DR

MindForge supports user-defined strategies as **declarative data**
(YAML / JSON / dict). It does **not** support:

- arbitrary Python plugin modules,
- shell or script strategies,
- automatic provider activation,
- automatic approval,
- writing to your real Obsidian vault.

A custom strategy is a *description* of behavior — the runtime can choose
to execute it later under strict, project-controlled conditions. The
description itself is just data and cannot run anything on its own.

## 1. Why Declarative, Not Plugin Runtime

Any "plugin" that lets users supply code (Python callable, module path,
shell command, script path) immediately collapses MindForge's safety
chain:

- `no real LLM` by default,
- `no .env` reads,
- `no workspace writes`,
- `no auto-approve`,
- `ai_draft`-only outputs (no `human_approved` literal sneak-in),
- `no RAG / embedding / semantic merge`.

**Declarative-only** means: a custom strategy is parsed, validated, and
stored as an immutable dataclass. The parser executes nothing the user
provided, loads no module, runs no shell, and reads no environment file.
This is **no arbitrary python**, **no shell**, no network, no secrets.

## 2. The `StrategyDefinition` Contract

A valid custom strategy definition is a mapping containing **only** these
fields (everything else is rejected as `InvalidStrategyDefinitionError`):

| Field                       | Required | Notes                                                |
|-----------------------------|----------|------------------------------------------------------|
| `strategy_id`               | yes      | Stable identifier                                    |
| `strategy_version`          | yes      | Semver-ish string                                    |
| `display_name`              | yes      | UX label                                             |
| `description`               | yes      | Short prose                                          |
| `provider_mode`             | yes      | One of `fake_only` / `deterministic` / `real_opt_in` |
| `safety_policy`             | yes      | **Must** be `ai_draft_only`                          |
| `output_schema_id`          | yes      | `<strategy_id>@<schema_version>`                     |
| `status`                    | yes      | One of `planned` / `preview` (NOT `implemented`)     |
| `structured_payload_schema` | yes      | Mapping of field name → declared type                |
| `prompt_template`           | no       | Template string (data only, never executed at parse) |
| `real_provider_opt_in`      | no       | Required `True` iff `provider_mode == real_opt_in`   |

Anything else (e.g. `python_callable`, `python_path`, `module_path`,
`shell_command`, `script_path`, `exec`, `command`, `filesystem_write`,
`vault_write`, `auto_approve`) → **rejected**.

A `human_approved` key inside `structured_payload_schema` → **rejected**.
Approval state is owned by the approver, never produced by a strategy.

## 3. What v0.12 Slice 1 Green Does and Does Not Do

✅ Provides a stable parsing API in `mindforge.strategies.custom`:

```python
from mindforge.strategies.custom import (
    InvalidStrategyDefinitionError,
    StrategyDefinition,
    parse_strategy_definition,
)

definition: StrategyDefinition = parse_strategy_definition({
    "strategy_id": "user_concept_review",
    "strategy_version": "0.0.1",
    "display_name": "User Concept Review",
    "description": "用户自定义概念复习卡片策略（声明式）。",
    "provider_mode": "deterministic",
    "safety_policy": "ai_draft_only",
    "output_schema_id": "user_concept_review@1",
    "status": "preview",
    "structured_payload_schema": {"title": "string", "concepts": "list[string]"},
})

# Map to v0.11 StrategyMetadata for `mindforge strategies list` UX:
meta = definition.to_metadata()
```

✅ Provides `to_metadata()` to project a parsed definition onto v0.11
`StrategyMetadata` (UX consistency with built-ins).

✅ Forces every custom strategy to be `planned` or `preview` so v0.11
Slice 4's planned-execution guard automatically refuses to run them
once any future slice wires custom strategies into the registry.

❌ Does **not** load definitions from a file or directory. (Loading
source / safe config discovery is the v0.12 Slice 2 contract.)

❌ Does **not** register custom definitions in `StrategyRegistry`.
(Registry integration + safe runtime are later, deliberate slices.)

❌ Does **not** call any provider, read `.env`, or touch the filesystem.

❌ Does **not** activate the real LLM. `provider_mode == "real_opt_in"`
is metadata only — even with `real_provider_opt_in: True`, no provider
is invoked at parse time. Real-LLM activation remains a separate,
explicit opt-in at the project level (not a per-definition switch).

## 4. Failure Modes

`parse_strategy_definition` raises `InvalidStrategyDefinitionError`
(a `ValueError` subclass) with a human-readable message including the
offending field path or value. It never raises a raw Python repr or a
stack trace as primary UX.

## 5. Roadmap Beyond Slice 1

- **v0.12 Slice 2 (planned):** safe loading source — explicit path,
  no implicit home-directory or vault scanning, path-traversal /
  symlink defenses, malformed-file user-friendly validation errors.
  Loading is **not** execution.
- **v0.12 Slice 3+ (planned):** safe runtime that consumes
  `StrategyDefinition` via a strict prompt-template executor with
  schema-enforced output and `ai_draft`-only guarantees. No arbitrary
  Python plugin. No shell. No auto-approve.

Each of those slices will land as its own TDD Red → Green pair with
the same strict boundary contract.
