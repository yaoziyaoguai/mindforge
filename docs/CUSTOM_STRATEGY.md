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

- **v0.12 Slice 2 (✅ Green):** safe loading source (this section).
- **v0.12 Slice 3+ (planned):** safe runtime that consumes
  `StrategyDefinition` via a strict prompt-template executor with
  schema-enforced output and `ai_draft`-only guarantees. No arbitrary
  Python plugin. No shell. No auto-approve.

Each of those slices will land as its own TDD Red → Green pair with
the same strict boundary contract.

## 6. Loading Source (v0.12 Slice 2)

`mindforge.strategies.custom_loader` lets you read a declarative
strategy definition from a file you point at explicitly. **Loading is
not execution** — loading is not execution, period. A loaded definition
is still subject to v0.11 Slice 4's planned-execution guard until a
future slice opts it into a safe runtime.

### 6.1 Explicit path only — no implicit scanning

The loader **only** opens paths the caller passes in. It does **not**:

- scan your home directory,
- scan an Obsidian vault,
- scan any private workspace,
- read `.env`,
- recurse into subdirectories.

There is no `~/.config/mindforge/strategies/`-style auto-discovery.
Implicit discovery would mean reading user files without explicit
consent — that is a privacy and safety regression we refuse to ship.

### 6.2 Whitelist file extensions

Only `.yaml`, `.yml`, and `.json` are accepted. Anything else
(`.py`, `.sh`, `.txt`, `.bin`, no extension at all) is rejected before
the file is opened. This makes "execute Python under
`/strategies/`" impossible by design, not by audit.

### 6.3 Path-traversal and symlink defense

- Paths containing `..` segments are rejected at the loader entry,
  even if the resolved file exists and would otherwise pass validation.
- Inside a directory load, any symlink that resolves *outside* the
  explicit base directory is rejected, so a hostile symlink to
  `~/.ssh/config` or `~/.env` cannot be smuggled into the load set.

### 6.4 User-friendly errors

All failures raise `StrategyDefinitionFileError` (a subclass of
`InvalidStrategyDefinitionError`). The message always includes the
offending file path and a short reason. The loader never lets a raw
`FileNotFoundError`, `OSError`, `yaml.YAMLError`, or `json.JSONDecodeError`
bubble up as primary UX, and the message never contains a Python repr
or stack-trace fragment.

### 6.5 API

```python
from pathlib import Path
from mindforge.strategies.custom_loader import (
    StrategyDefinitionFileError,
    load_strategy_definition_from_file,
    load_strategy_definitions_from_directory,
)

definition = load_strategy_definition_from_file(Path("./my_strategy.yaml"))
all_defs   = load_strategy_definitions_from_directory(Path("./strategies/"))
```

Both functions delegate validation to `parse_strategy_definition`, so
all Slice 1 guarantees (whitelist fields, `ai_draft_only`, status ∈
{`planned`, `preview`}, no `human_approved` schema field, no arbitrary
Python / shell / FS-write fields) still apply uniformly to both
hand-built dicts and file-loaded definitions.

### 6.6 What loading still does **not** do

- Loaded definitions are **not** registered in `StrategyRegistry`
  automatically. `mindforge strategies list` will show them only after
  a later, explicit slice wires the registry surface.
- Loaded definitions are **not** executable. Even if registered, v0.11
  Slice 4's planned-execution guard refuses to run them because their
  status is forced to `planned` or `preview`.
- Loading does not call any provider, read `.env`, write to a vault,
  or generate `human_approved`. Approval remains owned by the
  approver chain.

## 7. Discovery UX (v0.12 Slice 3 Green)

Slice 3 wires the loaded definitions into the **discovery surface** —
i.e. `mindforge strategies list`. This is purely a presentation slice:
discovery is not execution.

### 7.1 The `--custom-path` opt-in flag

```
mindforge strategies list                       # built-ins only
mindforge strategies list --custom-path ./defs  # built-ins + custom
```

`--custom-path` is the **only** way the CLI is allowed to look at user
definitions. There is no implicit scan of `~`, `~/.config`,
`~/.mindforge`, an Obsidian vault, or any "magic" directory. If you
do not pass the flag, the output is byte-identical to v0.11 — exactly
the four built-ins.

### 7.2 Custom entries are clearly marked

For every definition under `--custom-path` the CLI prints an extra
`(custom) not executable` badge alongside the built-in metadata
(`status` is always `preview` or `planned` for custom definitions).
The intent is that a user reading the terminal can never confuse a
custom preview with a project-shipped, runnable strategy.

### 7.3 Discovery is not execution

Loading a definition only parses + validates data; it does not invoke
any provider, never reads `.env`, never writes to a vault, never
generates `human_approved`, never auto-approves anything. There is
no arbitrary python plugin entry point. There is no shell strategy,
no script strategy, no subprocess. A custom definition stays a static
description until a future slice — explicitly opted into per call —
wires real execution behind a separate flag.

### 7.4 Validation error UX

If any file under `--custom-path` fails validation the CLI prints a
single human-readable `validation error` line containing the file
name plus the underlying field/value problem. It never prints a raw
Python `Traceback`, object repr (`<object …>`), or class repr
(`<class …>`). Other valid files in the same directory continue to be
listed; the built-in list is always shown first and is never affected
by a custom-side validation error.

A custom definition that failed validation is **not** registered into
`available_strategies()`. That is, a name only appears in the listing
when the definition fully passed `parse_strategy_definition` —
preventing the trap of "name visible → user runs `process` → only
then learns the file was malformed".

### 7.5 Public discovery API

```python
from pathlib import Path
from mindforge.strategies import discover_strategies

builtin_only = discover_strategies()
combined     = discover_strategies(custom_path=Path("./defs"))
```

`discover_strategies()` returns `tuple[StrategyMetadata, ...]` and is
the single source the CLI list command consumes. It never constructs
an `LLMClient`, never calls a provider, never reads `.env`, never
writes anywhere; it merely combines built-in metadata with the
custom-path metadata produced by Slice 2's loader.

## 8. From Preview to Future Implementation (v0.12 Slice 4 Green)

A custom declarative definition is registered as **metadata only**.
Its `status` is forced to `preview` or `planned` at parse time, and
`build_strategy(name, ctx, custom_path=DIR)` refuses to instantiate
it with a `NotYetImplementedStrategyError` whose message contains
both the literals `preview` and `discovery is not execution`. This
prevents two failure modes at once: (a) a confusing
`UnknownStrategyError` when the user *can clearly see* the name in
`mindforge strategies list --custom-path DIR`; (b) a custom
definition silently activating a real or default strategy under a
familiar id.

### 8.1 The path from preview to implementation

There is exactly one safe route from "discovered preview" to "really
runnable":

1. The declarative definition stays the source of truth for
   metadata (`strategy_id`, `provider_mode`, `safety_policy`,
   `output_schema_id`, `description`, `structured_payload_schema`,
   `prompt_template`).
2. A future, project-shipped, **explicitly opted-in** Python module
   provides a deterministic factory bound to that `strategy_id`. The
   factory is reviewed and merged into the project source tree —
   never auto-loaded from disk, never imported from the user's
   `--custom-path`.
3. The factory is registered in `strategies/registry.py`'s
   `_FACTORIES` dict by an explicit code change (visible in PRs and
   git blame). The `status` field on the corresponding metadata
   module is then promoted from `preview` to `implemented`.

Steps 2 and 3 are deliberately code changes, not user actions. The
project will never:

- accept a Python entry point or callable from a `--custom-path`
  YAML/JSON file;
- accept a shell or script field in a custom definition;
- import or `exec`/`eval` user-supplied code based on a declarative
  field;
- enable real LLM calls without an additional explicit opt-in
  switch beyond `--custom-path`.

This means a custom preview can never become executable through the
discovery surface alone — which is exactly the property that lets
users safely point `--custom-path` at any directory.

### 8.2 What remains forbidden

- **No arbitrary python**: declarative custom strategies cannot
  reference Python callables, modules, entry points, or import
  paths. Loading is parse + validate only.
- **No shell** strategy, no subprocess, no `os.system`, no script
  execution.
- **No real LLM by default**: even after a strategy moves from
  preview to implementation, real-LLM calls remain off unless the
  caller passes a separate, documented opt-in flag (`UPSTAGE_API_KEY`
  is never read implicitly).
- **No auto-approval**: `human_approved` is owned by the explicit
  approver chain. A custom (or built-in) strategy can only emit
  `ai_draft`. The schema validator rejects any `human_approved` key
  inside `structured_payload_schema`.
- **No registry mutation from discovery**: `discover_strategies()`
  never writes into `_FACTORIES` or `available_strategies()`.
  Custom previews are a metadata view; built-in factories remain
  the single source of "what is executable today".

## 9. Review-Only Preview Packet (v0.12 Slice 5 Green)

到 Slice 4 为止，custom strategy 已经能被安全 *parse / load / discover*，
``build_strategy`` 也能在 registry 边界友好地拒绝执行。但用户写完
YAML 后仍缺最后一段桥梁：**用户在终端到底应该看到什么样的"review
卡片"，才能既看清自己写了什么、又绝不会误以为这是已批准的知识卡？**

Slice 5 Green 给出答案 —— ``mindforge.strategies.preview_packet``
模块，提供一个稳定、只读、纯数据的 **preview packet** 与配套渲染。

### 9.1 What the preview packet *is*

- 一份纯 ``dict``（11 个字段，valid 形态；5 个字段，invalid 形态）；
- 通过 ``build_custom_preview_packet(definition)`` 或
  ``build_invalid_preview_packet(path, error)`` 构造；
- 通过 ``render_custom_preview_packet(packet)`` 渲染成纯文本，可直接
  print 或写入日志；
- 始终包含 ``kind="preview_only"`` 与 ``executable=False`` 两个稳定
  discriminator，便于下游消费方判别。

### 9.2 What the preview packet *is not*

| 维度 | preview packet | ai_draft KnowledgeCard | human_approved card |
| --- | --- | --- | --- |
| 是策略数据吗 | 是（定义元数据） | 否 | 否 |
| 是知识卡吗 | **否** | 是（草稿） | 是（已批准） |
| 由 LLM 生成吗 | 否（声明 + 校验产物） | 是 | 是 + 人工 |
| 会进入 ApprovalService 吗 | **永远不会** | 进入待审 | 已审 |
| 会进入 CardWriter 吗 | **永远不会** | 写 staging | 写 vault |
| 字段含 `human_approved` 吗 | **永远不含** | 否 | 是 |
| 是否可执行 | **executable=false** | 取决于策略 | 已生效 |

> Preview packet 是 review-only。它显式地 not ai_draft，显式地
> not human_approved。任何把 preview packet 当作 ai_draft 或
> approved card 消费的下游路径，都属于安全契约违反。

### 9.3 Explicit approval is still required

- preview packet 出现 ≠ 用户接受这个策略；
- 即便未来 v0.13+ 真正实现 custom strategy execution，**explicit
  approval** 仍是必须步骤，preview 只承担"展示给人看"的职责；
- preview packet 永远不写入 vault、不调用 provider、不读取 ``.env``。

### 9.4 Public API

```python
from mindforge.strategies.preview_packet import (
    build_custom_preview_packet,
    build_invalid_preview_packet,
    render_custom_preview_packet,
)
```

- ``build_custom_preview_packet(definition: StrategyDefinition) -> dict``
- ``build_invalid_preview_packet(source_path, error: InvalidStrategyDefinitionError) -> dict``
- ``render_custom_preview_packet(packet) -> str``

### 9.5 Boundary tests

``tests/test_custom_preview_packet_contract.py`` 用 5 个 family
（packet shape / no-execution / presenter UX / boundary docs / sanity
baselines）固化上述契约。源码 source-scan 同时覆盖：preview_packet.py
不允许出现 subprocess / eval / LLMClient( / load_dotenv / .obsidian /
CardWriter( / ApprovalService( / human_approved 等 17 个越界 token。
