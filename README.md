# MindForge

MindForge is a local-first personal AI learning memory tool.

MindForge 帮你把本地资料整理成可以 review、recall、项目化使用的知识卡片。
真实 dogfood 主路径使用 `configs/mindforge.yaml` 里的 `llm.active`
选择默认 provider，但安全边界不变：
AI 只能生成 `ai_draft`；只有你显式确认后，卡片才会变成
`human_approved`。API key 只放在 shell env 或本地 `.env`，不要写进 YAML。

MindForge 是 single-user 的本地工具，不是 SaaS，不是多用户后台，not RAG，
not embedding，也不是 Obsidian plugin。

## Quick Start: First 10 Minutes

初始化你的本地工作区。你在哪里运行 `mindforge init`，哪里就是 MindForge
project root；默认会生成 `configs/mindforge.yaml`、`.env.example` 和
`vault/`：

```bash
mkdir -p /tmp/mindforge-first-run
cd /tmp/mindforge-first-run
mindforge init
```

MindForge 是 cwd-first / vault-first：程序安装目录只放程序，用户数据放在
project root 下的 `vault/`，或你显式选择的 vault 目录里。新 init 的
`vault.root` 默认是相对 project root 的 `vault`。

创建第一条 Markdown：

```bash
mkdir -p vault/00-Inbox/ManualNotes
cat > vault/00-Inbox/ManualNotes/first-note.md <<'EOF'
# 我的第一条 MindForge 笔记

今天我开始测试 MindForge。
我希望它能帮我把学习资料整理成可以复习和召回的知识卡片。
EOF
```

在 `configs/mindforge.yaml` 里选择默认 real provider：
`llm.active: openai_compatible` 或 `llm.active: anthropic`。可以用 shell
export，也可以放在当前项目或 vault 上级目录的本地 `.env`；不要写 API key
进 YAML。
OpenAI-compatible 需要：

- `MINDFORGE_OPENAI_API_KEY`
- `MINDFORGE_OPENAI_BASE_URL`
- `MINDFORGE_OPENAI_MODEL`

Anthropic-compatible / Claude 需要：

- `MINDFORGE_ANTHROPIC_API_KEY`
- `MINDFORGE_ANTHROPIC_BASE_URL`
- `MINDFORGE_ANTHROPIC_MODEL`

```bash
export MINDFORGE_OPENAI_API_KEY="<your-api-key>"
mindforge llm ping
```

跑通最小流程：

```bash
mindforge watch list
mindforge watch add vault/00-Inbox/ManualNotes/first-note.md
mindforge approve list
mindforge approve
mindforge approve 1 --confirm
mindforge recall --query "MindForge"
```

第一次可以先不要 approve。`approve` 是写入边界：它把 `ai_draft` 显式晋升
为 `human_approved`。`mindforge approve list` 会显示 `[1]` 这样的短编号、
short ref 和 source 摘要；`mindforge approve 1 --confirm` 是显式人工动作，
不是自动 approve。approve 成功后 MindForge 会默认刷新本地 recall index，
所以通常不需要手动运行 `mindforge index rebuild`。如果缺少
对应 provider 的 API key，真实 provider 会友好失败；MindForge 不会偷偷
fallback 到 fake。

`watch add` 的第一版不是后台监听：它会注册这个文件或文件夹，并立即处理当前
内容生成 `ai_draft`。未来的 polling / filesystem hook 会接在 watched source
registry 后面，本阶段没有 daemon、没有 `watch run/start/stop`。

如果你只是一次性导入一个文件或文件夹，不想持续关注它，用：

```bash
mindforge import /path/to/file-or-folder
```

`import` 会处理当前内容生成 `ai_draft`，但不会加入 watched sources。
MindForge 会先做 triage 来过滤低价值输入；如果被 skipped，输出会包含
`value_score`、threshold、`should_process` 和下一步提示。这不是 approve
边界，只是避免制造低质量草稿。你确认要强制生成草稿时可以用：

```bash
mindforge import /path/to/file-or-folder --force
```

`--force`（同 `--no-triage`）只覆盖 triage 低分拦截，不会绕过
`already_processed` / `already_approved` 去无限生成重复卡片。生成的
`ai_draft` 仍必须显式 `approve` 才会进入 `human_approved`。

`00-Inbox/` 是系统自带的 default watched source。它不是一个额外命令，也不
需要删除；`mindforge watch list` 会展示它。

Project root / vault path rules:

- project root 是运行 `mindforge init` 的目录，包含 `configs/mindforge.yaml`、
  `.env.example` / `.env` 和 `vault/`。
- `vault.root: vault` 按 project root 解析，不按任意 shell cwd 解析。
- `import` / `watch add` 支持 absolute path、cwd-relative、
  project-root-relative 和 active-vault-relative。
- 找不到路径时会明确报 `File not found`，并打印 cwd / project root /
  active vault / tried candidates。

例如这些都可以：

```bash
cd /tmp/mindforge-first-run
mindforge import vault/00-Inbox/ManualNotes/first-note.md

cd /tmp/mindforge-first-run/vault
mindforge import 00-Inbox/ManualNotes/first-note.md

mindforge import /tmp/mindforge-first-run/vault/00-Inbox/ManualNotes/first-note.md
```

Active vault resolution rule: explicit `--vault` wins first, then MindForge
detects a cwd/ancestor vault, then uses project root `configs/mindforge.yaml`
`vault.root`, then falls back to configured/bundled defaults. A fresh vault only
needs `00-Inbox/` to be detected, so this works:

```bash
mkdir -p /tmp/my-mindforge-vault/00-Inbox/ManualNotes
cd /tmp/my-mindforge-vault
mindforge watch list
```

If you run commands from the source repo or another non-vault directory, pass
`--vault <path>` or run `mindforge init`. When cwd vault and configured vault
differ, CLI output shows `project root`, `config path`, `active vault`, and
`configured vault is fallback candidate only: ...`.

## Three Concepts You Need First

1. **Vault**
   MindForge 的本地工作区。例子：
   `/Users/jinkun.wang/MindForgeVault`。

2. **Inbox**
   原始资料入口。第一天只需要用 `00-Inbox/ManualNotes`。

3. **Approve**
   MindForge 先生成 `ai_draft`。只有你显式 approve 后，才会变成
   `human_approved`。这是核心安全边界。

## What Init Creates

第一次看到很多目录是正常的。第一天只需要关注：

- `00-Inbox/ManualNotes`
- `20-Knowledge-Cards`
- `configs/mindforge.yaml`

其他目录先不用管：

- `00-Inbox/Cubox`: Cubox 导出内容；Cubox 只是数据源。
- `00-Inbox/WebClips`: 网页剪藏。
- `00-Inbox/ChatExports`: 聊天记录导出。
- `00-Inbox/PDFs` / `00-Inbox/Docs`: 高级或后续入口。
- `30-Projects`: 项目上下文，第一天不用管。
- `80-Reviews`: 复习，第一天不用管。
- `90-System`: 系统辅助，第一天不用管。
- `_attachments`: 附件，第一天不用管。

`00-Inbox/` 是原始资料入口。`00-Inbox/ManualNotes/` 最适合新手第一天使用，
直接放普通 Markdown。

`20-Knowledge-Cards/` 是知识卡片输出区，`ai_draft` 和 `human_approved` 都和
这里有关。新手不要手动乱改 generated 内容。

Source 和 Card 不是同一个东西：`00-Inbox/` 里的文件是原始证据，
`20-Knowledge-Cards/` 里的文件是加工后的知识卡片。`process` 阶段不会移动
source；生成 `ai_draft` 后 source 仍留在原始 Inbox。只有你显式 approve 成功
后，MindForge 才会把 vault 内的 source 移到
`00-Inbox/_processed/<adapter>/`，例如
`00-Inbox/_processed/ManualNotes/`。原始 source 不会被默认删除，card
frontmatter 会保留 `source_path` / `source_archive_path` / `source_id` /
`adapter_name` 等 provenance。

`20 / 30 / 80 / 90` 这些目录是后续完整知识工作流准备的，不是第一天必须
理解。不要随便删除即可。

## Config Files

### `configs/mindforge.yaml`

这是普通用户最重要的基础配置文件。第一天只需要关心：

- `vault.root`: vault 在哪里；新 init 默认写 `vault`，按 project root 解析。
- `llm.active`: 真实 dogfood 主路径可以选 `openai_compatible` 或
  `anthropic`。
- `llm.providers.openai_compatible` / `llm.providers.anthropic`: 只声明 env
  变量名映射和非 secret 默认值；真实 key/base_url/model 放 shell env 或 `.env`。
- `telemetry.local_only`: 只写本地，不上传。

新项目里的 YAML 是 user override，不是 MindForge internal full config dump。
`sources.registry`、state/index 路径、prompt versions、search 权重和 logging
细节由 package 内置 defaults 承担，运行时会做：

```text
internal defaults + configs/mindforge.yaml override = effective config
```

极简示例：

```yaml
version: 0.1
vault:
  root: vault
llm:
  active: openai_compatible
  providers:
    openai_compatible:
      type: openai_compatible
      api_key_env: MINDFORGE_OPENAI_API_KEY
      base_url_env: MINDFORGE_OPENAI_BASE_URL
      model_env: MINDFORGE_OPENAI_MODEL
      default_base_url: https://api.openai.com/v1
      default_model: gpt-4o-mini
    anthropic:
      type: anthropic
      api_key_env: MINDFORGE_ANTHROPIC_API_KEY
      base_url_env: MINDFORGE_ANTHROPIC_BASE_URL
      model_env: MINDFORGE_ANTHROPIC_MODEL
      default_base_url: https://api.anthropic.com
      default_model: claude-3-5-haiku-latest
    fake:
      type: fake
      purpose: offline_demo_ci_deterministic_tests
telemetry:
  enabled: true
  local_only: true
```

第一天只需要确认 `vault.root`、`llm.active` 和对应 provider 的 env
是否正确。`learning_tracks.yaml` 使用 package
内置默认值，不再由 init 默认生成。`llm.example.yaml` 不再是新用户项目里的
第二个配置入口；主配置入口就是 `configs/mindforge.yaml`。

Legacy configs with `llm.active_profile` / `llm.profiles` still load, but new
configs should use `llm.active` / `llm.providers`.

### `.env.example`

secret/API key 样例。真正使用时复制成 `.env`。`.env` 不能提交到 git。
MindForge 只显示 key 是否存在，不打印 secret 值。也可以不用 `.env`，直接
用 shell `export MINDFORGE_OPENAI_API_KEY=...`。

### Existing vault / old config

旧 vault 不会被自动迁移。新 `mindforge init` 只影响新项目；如果你的
`configs/mindforge.yaml` 是早期生成的 legacy full config，MindForge 仍会
支持它，但不会自动删除旧字段或覆盖正式 vault。

迁移建议：

- 先备份旧 `configs/mindforge.yaml`。
- 在临时空目录运行 `mindforge init`，查看新生成的极简模板。
- 手动把正式配置替换成新模板，并保留原来的 `vault.root`。
- API key、base_url、model 仍放 `.env` 或 shell env，不要写进 YAML。
- 如果不确定，不要直接覆盖正式 vault；先在临时 vault 验证。

## Markdown Sources Are Sources, Not Knowledge Types

Cubox Markdown、Plain Markdown、WebClip Markdown、ChatExport 不是不同知识
类型。

它们只是不同 source adapter：

- `ManualNotes`: 你手写的普通 Markdown。
- `Cubox`: 从 Cubox 导出的内容，可能带 URL、高亮、原文信息。
- `WebClips`: 网页剪藏。
- `ChatExports`: 聊天记录导出。

MindForge 内部会把它们统一成 `SourceDocument`。用户不需要记很多“知识类型”，
只需要知道这些是不同来源的资料入口。Cubox 只是一个数据源入口，不是
MindForge 的中心架构。

## Offline demo / CI / Testing

`fake provider` 没有被删除。它继续服务于 CI、offline demo 和 deterministic
tests。这个历史安全姿态也叫 `fake-default`，现在仅用于离线/demo/testing，
不是普通用户真实 dogfood 主路径：

```bash
mindforge demo
mindforge process --provider fake --limit 1
mindforge watch add /path/to/note.md --provider fake
mindforge import /path/to/note.md --provider fake
```

fake 不是普通用户真实 dogfood 主路径。真实路径缺 key 时会报错，不会 fallback
到 fake。需要离线验证时请显式使用 `--provider fake`。`--profile` 仍作为
legacy alias 保留，但不再是主路径文案。

## Safety Model

- 真实 LLM 只在你配置 `MINDFORGE_OPENAI_API_KEY` 并运行 watch/import/process
  时调用；`llm ping` 只检查 env presence，不发 HTTP。
- no real LLM call happens during init/config/status/readiness checks.
- `real-opt-in` / explicit opt-in 仍适用于 guarded smoke、custom strategy
  runtime 和任何可能产生费用或读取敏感资料的诊断路径。
- 不调用真实 Cubox API。
- does not call a real LLM。
- does not call the real Cubox API。
- no real Cubox。
- 不自动 approve。
- does not auto-approve。
- No automatic approve。
- 不自动写正式 Obsidian note。
- `.env` secret 不打印；只显示 key 是否存在。
- does not print `.env` secret values。
- no `.env` is read by default status/readiness paths。
- `approve` 必须显式 `--confirm`。
- `human_approved` 只能由 explicit approval / human decision gate 产生。
- Human Decision Gate Map: `ai_draft -> mindforge approve --confirm -> human_approved`。
- Recall 是 local lexical recall / BM25，本地词法检索，不是 RAG /
  embedding / semantic search / semantic merge。
- No RAG / embedding。
- No Obsidian plugin。
- 不自动整理真实 vault。
- does not automatically modify a real private vault。
- 不做 git tag、release automation、force push。
- 默认 dogfood 路径是 dry-run 或 read-only，真实写入必须明确确认。
- every dogfooding session must be a dry-run by default。
- no write occurs into a real obsidian vault unless a future human-authorized
  write gate is added。
- no human_approved card is generated by automation。
- no custom strategy is executed by discovery or preview。
- local-first privacy contract: local files stay local, secret values are not
  printed, and writes require an explicit human action。
- no tag, no force push。

Real ≠ Approved: real provider output is still review-only until a human uses
the human decision gate.

## Common Commands

### First Status Commands

| Command | Use |
|---|---|
| `mindforge demo` | 零配置演示 |
| `mindforge init --interactive` | 初始化本地工作区 |
| `mindforge status` | 查看整体状态 |
| `mindforge doctor` | 检查配置和安全状态 |
| `mindforge watch list` | 查看 default `00-Inbox` 和用户添加的 watched sources |
| `mindforge watch add <file-or-folder>` | 注册 watched source，并立即处理当前内容生成 `ai_draft` |
| `mindforge watch delete <file-or-folder-or-id>` | 只删除 watched source registry 记录，不删除 source 或 cards |
| `mindforge import <file-or-folder>` | 一次性导入当前内容，不加入 watched sources；默认尊重 triage |
| `mindforge import <file-or-folder> --force` | Advanced：覆盖 triage 低分拦截生成 `ai_draft`，不绕过重复/approved 边界 |
| `mindforge approve list` | 查看待确认 `ai_draft`，带短编号 / short ref |
| `mindforge approve show --card <path> --show-content` | 查看草稿内容 |
| `mindforge approve 1 --confirm` | 用短编号显式确认生成 `human_approved`，并默认刷新 recall index |
| `mindforge approve --card <path> --confirm` | 高级路径模式；仍然兼容长 card path |
| `mindforge recall --query "query"` | 本地词法召回，不是 RAG |
| `mindforge library stats` | Inspect：查看知识库总览、状态计数、index 状态 |
| `mindforge library list` | Inspect：列出卡片 metadata 和 source provenance |
| `mindforge library show <card-id-or-path>` | Inspect：查看单张卡片 metadata；`--show-content` 才显示 card body |
| `mindforge index rebuild` | Advanced：手动刷新本地 BM25 index |

### Advanced / Troubleshooting

`scan/process` 仍然保留，适合排障、脚本化或检查底层 pipeline：

```bash
mindforge scan
mindforge process --provider fake --limit 1
```

普通 first-run 用户优先使用 `watch add` 或 `import`，不用先理解
`state.json` / checkpoint / pipeline 的中间状态。

### Safe Real Dogfood

Dogfood helper:

```bash
mindforge dogfood init-demo --target /tmp/dogfood-vault
mindforge dogfood readiness --vault /tmp/dogfood-vault
mindforge dogfood quickstart --vault /tmp/dogfood-vault
```

The quickstart prints a manual runbook only. It does not execute the listed
commands, does not read `.env` contents, does not call a real LLM, does not
call the real Cubox API, does not write formal Obsidian notes, and does not
produce `human_approved`.

For Cubox JSON export dry-run:

```bash
mindforge cubox dry-run --export /path/to/cubox-export.json
mindforge cubox preview-ai-draft --export /path/to/cubox-export.json --limit 5
```

Start with `--limit 5`; do not exceed `--limit 20` during first runs. MindForge
does not support full Cubox account sync, has no `--all` ingestion, and does
not call the real Cubox API on this path.

Obsidian dogfood remains staged/dry-run only:

```bash
mindforge obsidian next --vault /path/to/project-vault
mindforge obsidian doctor --vault /path/to/project-vault
mindforge obsidian scan --vault /path/to/project-vault --limit 20
mindforge obsidian links --vault /path/to/project-vault
mindforge obsidian stage --vault /path/to/project-vault --source <note.md> --dry-run
mindforge obsidian preflight --vault /path/to/project-vault --manifest <export>.manifest.json
```

Use a disposable, non-sensitive vault copy. No formal Obsidian note writes.
No formal Obsidian notes are written. No default real LLM path. No telemetry upload.
No `.env`, real LLM, real Cubox API, or auto-approve. This is a
staged workflow: manifests, include/exclude filters, and diff preview are
review aids only.

Rollback rule: first dogfood runs should happen in a disposable or git-tracked
project vault. Use `git status`, `git restore`, or remove specific staged files
to roll back. Do not run broad destructive cleanup commands against a real vault.

### Real Provider Opt-In

Real Provider Setup: 真实 dogfood 主路径使用 `configs/mindforge.yaml` 里的
`llm.active: openai_compatible` 或 `llm.active: anthropic`。
只把 API key / base_url / model 放进 shell env 或本地 `.env`：

```bash
export MINDFORGE_OPENAI_API_KEY="<your-api-key>"
export MINDFORGE_OPENAI_MODEL="gpt-4o-mini"
mindforge llm ping
mindforge watch add /path/to/non-sensitive-note.md
```

`llm ping` 只检查 key 是否存在，不发 HTTP。`watch add` / `import` 会生成
`ai_draft`，不会自动 approve。缺 key 时命令会提示：
`real provider openai_compatible requires MINDFORGE_OPENAI_API_KEY` 或
`real provider anthropic requires MINDFORGE_ANTHROPIC_API_KEY`，并说明可以用
`--provider fake` 跑离线 demo/testing。

底层 synthetic provider smoke 仍需要显式 `--allow-real`；普通 Quick Start
不需要它。它只用于已经理解 billing/privacy 风险后的诊断，不替代
watch/import 主流程。

### Approval

Approval is the only supported `ai_draft -> human_approved` transition.
`mindforge approve list` is the main pending review queue. It shows short
numbers and refs so the usual write action is `mindforge approve 1 --confirm`.
`mindforge approve --card <path> --confirm` remains available as the advanced
path mode. After a successful approve, MindForge refreshes the local recall
index by default; use `--no-index` only for troubleshooting.

### Standard Quality Gate

Maintainers should run `git diff --check`, `ruff check .`, and `python -m
pytest` before landing documentation or behavior changes.

### Future Gate Notes

- sample folder / no-persist / dry-run modes are preferred for first real
  dogfood.
- diff preview and backup expectations are mandatory before any future formal
  vault write gate.
- G1 Real Cubox ingestion, G2 Real Obsidian formal-note write, G3 Approval UX,
  G4 Custom executable strategy runtime, G5 RAG / embedding / semantic merge,
  and G6 Public release / git tag remain future gates.

## Architecture In One Page

```text
SourceAdapter
  -> SourceDocument
  -> processing pipeline
  -> ai_draft
  -> explicit approval
  -> human_approved
  -> recall / review / project context
```

- AI 只能生成 `ai_draft`。
- `human_approved` 必须显式 approve。
- Source 是原始证据，Card 是加工结果；Card 不替代 Source。
- approve 成功后，vault 内 pending source 会移动到
  `00-Inbox/_processed/<adapter>/` 作为已处理证据保留。
- Processor / KnowledgeStrategy 只依赖 `SourceDocument`。
- Cubox 只是 `SourceAdapter`，不是架构中心。
- Obsidian / OPS 是人类知识工作台，不存机器 runtime/state/cache/index/logs/
  vector/graph 派生层。
- BM25/local lexical recall 是当前检索路径，不是 RAG。
- 当前不做 RAG / embedding / semantic merge。
- 当前不做 Obsidian plugin。
- 当前不自动整理真实 vault。
- Web first slice 是 localhost-only Local Console，默认绑定 `127.0.0.1`。
  当前 Web 增量提供 workflow / sources / drafts / library / recall 可见性：
  展示 source bucket、ai_draft、human_approved library、card provenance 和
  index guidance。Web 复用后端 service，不读取 source 正文，不显示 `.env`
  secret，也不重写 CLI 业务规则。

## Strategy Discovery

```bash
mindforge strategies list
```

Built-in strategies include `default_knowledge_card` and `five_stage`.
Strategy status has three meanings: `implemented` is ready to run, `preview` is
usable but still evolving, and `planned` is registered for visibility but is not
executed.

Custom strategies are declarative metadata definitions. Use explicit opt-in via
`--custom-path` to expose a local definition. Discovery is not execution;
loading is not execution. Custom definitions load from an explicit path only:
there is no implicit scan of your home directory, vault, or `.env`. A validation error
should be read as a schema/config problem, not as execution output.
MindForge does no arbitrary Python plugin loading, no arbitrary python runtime,
no shell strategy, and no executable strategy runtime.
Preview packets are review-only: not ai_draft, not human_approved, not
`ai_draft`, and not `human_approved`. Any future implementation still needs
explicit approval.

Preview to future implementation remains a gated path: a preview definition can
only become a future implementation after design review, tests, and explicit
human authorization. It must not introduce arbitrary Python, shell execution,
default real LLM usage, or automatic approval.

Review-only artifact kinds include preview packets, readiness checks, and real smoke output.
None of these artifacts is a Knowledge Card or an approval event.

## Implementation Map

Start reading code here:

- `src/mindforge/cli.py`: top-level Typer command registry.
- `src/mindforge/status_cli.py`: real-data status / doctor-style output.
- `src/mindforge/app_context.py`: local config/path context.
- `src/mindforge/sources/base.py`, `src/mindforge/sources/registry.py`,
  `src/mindforge/scanner.py`: SourceAdapter and SourceDocument path.
- `src/mindforge/provider_readiness.py`: provider readiness without real calls.
- `src/mindforge/cubox_readiness.py`: Cubox readiness without real API calls.
- `src/mindforge/approval_service.py`, `src/mindforge/approver.py`: approval
  boundary.
- `src/mindforge/library_service.py`, `src/mindforge/library_cli.py`: Knowledge
  Library inventory and card provenance.
- `src/mindforge/source_archive_service.py`: processed source archive after
  explicit approve.
- `src/mindforge/recall_service.py`, `src/mindforge/lexical_index.py`: local
  lexical recall.
- `src/mindforge/web_cli.py`, `src/mindforge_web/`, `web/src/`: local Web
  console.
- `tests/`: behavior tests and architecture boundary tests.

CLI and Web should stay thin adapters. Services hold business semantics;
presenters hold output shape. New behavior should not hide inside command
bodies or routers.

## Current Roadmap

Done:

- Web first slice.
- Real Data CLI Usability.
- Documentation cleanup.
- Product visibility and workflow support: CLI library inventory, processed
  source archive, Web workflow/library visibility.

Current:

- README-first onboarding.
- Local dogfood on non-sensitive or project-only data.

Next:

- Non-sensitive real vault dogfood.
- Onboarding polish.
- Packaging/install readiness.

Not current direction:

- RAG / embedding / semantic merge.
- Obsidian plugin.
- Real LLM enabled by default.
- Real Cubox API calls enabled by default.
- Hidden automatic approval.
- Automatic organization of a real vault.
- Cloud sync, accounts, OAuth, payments, hosting, or multi-user permissions.

Future gates remain explicit: Real Cubox ingestion, Real Obsidian formal-note
write, Approval UX polish, custom executable strategy runtime, RAG / embedding /
semantic merge, and public release / git tag all require fresh design review and
named human authorization. No automation may create a tag.

## FAQ

**我需要先配置真实 LLM 吗？**

不需要。默认 `fake` provider 就能安全跑通流程。

**为什么生成这么多目录？**

它们是为完整知识工作流准备的。第一次只关注
`00-Inbox/ManualNotes` 和 `20-Knowledge-Cards`。

**Cubox / WebClip / ManualNotes 都是 Markdown，为什么分目录？**

主要是为了保留来源语义和 adapter 处理差异，不代表知识类型不同。

**approve 会发生什么？**

`approve` 会把一张 `ai_draft` 显式晋升为 `human_approved`。不确定时先不要
approve。approve 成功后，MindForge 会把对应 vault Inbox source 移到
`00-Inbox/_processed/<adapter>/`，保留原始证据并让 Inbox 更像待处理队列。

**原始 source 会不会被删除？**

不会默认删除。Source 是证据，Card 是知识加工结果。vault 内 source 在
approve 后会移动到 `_processed` 归档区；vault 外部 source 默认不移动，只在
card metadata 里保留路径。

**会不会自动读我的 Obsidian vault？**

不会。只有你把路径指向某个 vault 并运行相应命令时，MindForge 才会处理
对应路径。Obsidian 路径默认是 read-only / staged。

**会不会打印 API key？**

不会。MindForge 只显示 key 是否存在，不打印 secret 值。

**recall 是不是 RAG？**

不是。当前 recall 是本地词法检索 / BM25，不是 RAG、embedding、semantic
search 或 semantic merge。

## For Maintainers

- [DESIGN.md](DESIGN.md): Web design-system discipline.
- [docs/TESTING.md](docs/TESTING.md): quality gates and smoke checks.
- [docs/LLM_PROVIDER_CONFIG.md](docs/LLM_PROVIDER_CONFIG.md): real provider opt-in.
- [docs/CUBOX_DRY_RUN.md](docs/CUBOX_DRY_RUN.md): Cubox JSON export dry-run.
- [docs/ROADMAP_COMPLETION_LEDGER.md](docs/ROADMAP_COMPLETION_LEDGER.md):
  compact future-gate guard ledger.
