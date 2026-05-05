# Getting Started — MindForge v0.5.2

> **⚡ 60 秒看到效果（零 token / 零网络 / 零 vault 写入）:**
> ```bash
> mindforge demo
> ```
> 4-step tour: Cubox JSON parse → dogfood path classification →
> Obsidian vault read-only probe → in-memory review packet. Uses
> bundled fixtures only; never reads `.env`, never writes any vault,
> never produces `human_approved`. Add `--json` for machine-readable
> output. Run this before anything else if you just installed MindForge.

> **🚀 Real-data dogfood quickstart (10 min, 0 sensitive data, 0 network):**
> ```bash
> mindforge dogfood readiness --vault /path/to/disposable-project-vault
> mindforge dogfood quickstart --vault /path/to/disposable-project-vault
> ```
> `readiness` first confirms the vault/provider/export state is still
> fake-default + dry-run safe. `quickstart` then prints an 11-step
> copy-paste runbook that takes you from install →
> Cubox JSON-export preview → ai_draft → project-vault dry-run, **all
> on the fake-default + dry-run path**. No real LLM. No real Cubox API.
> No formal vault write. No `human_approved` produced. **No release / no
> tag / no v1.0.** Recommended first-run limit is **`--limit 5`**; never
> exceed `--limit 20` on early runs; there is **no full-Cubox-sync**
> command. Use a disposable project vault (e.g.,
> `mindforge dogfood init-demo --target /tmp/dogfood-vault`) so rollback = delete
> the directory. Full guide, including rollback / token-safety /
> boundary-guarantee sections, in
> [`REAL_DOGFOOD_QUICKSTART.md`](REAL_DOGFOOD_QUICKSTART.md).

> 目标：从零跑通 MindForge 的本地主链路，不调用真实 LLM、不接触私人数据。
> 全程使用 `fake` provider；**不读取 `.env`**。
>
> **想直接看效果？** 用仓库自带的 demo vault 一键跑：
> ```bash
> mindforge dogfood init-demo --target /tmp/dogfood-vault
> mindforge doctor --vault /tmp/dogfood-vault
> mindforge dogfood readiness --vault /tmp/dogfood-vault
> mindforge commands
> mindforge next --vault /tmp/dogfood-vault
> mindforge scan --vault /tmp/dogfood-vault
> mindforge process --profile fake --limit 1 --vault /tmp/dogfood-vault
> mindforge approve list --vault /tmp/dogfood-vault
> mindforge index rebuild --vault /tmp/dogfood-vault
> mindforge recall --query "checkpoint runtime" --ranking hybrid --explain --vault /tmp/dogfood-vault
> mindforge review weekly --format markdown --vault /tmp/dogfood-vault
> mindforge review schedule --days 7 --format markdown --vault /tmp/dogfood-vault
> mindforge project context my-first-agent --target claude-code --vault /tmp/dogfood-vault
> mindforge obsidian doctor --vault /tmp/dogfood-vault
> mindforge obsidian scan --vault /tmp/dogfood-vault --limit 5
> mindforge obsidian links --vault /tmp/dogfood-vault
> mindforge obsidian stage --vault /tmp/dogfood-vault \
>   --source 02-Knowledge/agent-runtime-observer.md --dry-run
> rm -rf /tmp/dogfood-vault
> ```
> （demo vault 完全虚构，详见 [`examples/demo-vault/README.md`](../examples/demo-vault/README.md)）
>
> 提示：`process` 会写一张本地 `ai_draft` demo 卡，所以推荐用
> `dogfood init-demo` 创建 `/tmp/dogfood-vault`。想重置 demo 状态时，
> 删除这个 disposable 副本即可。这个命令从安装态 CLI 也可用，不依赖仓库根。
>
> 不知道下一步该敲哪条命令？随时跑 **`mindforge next`** 看建议，
> 或 **`mindforge commands`** 看按场景分组的命令地图。完整文档地图见
> [`DOCS_INDEX.md`](./DOCS_INDEX.md)。

## 1. 安装

```bash
# 推荐用 venv 隔离
python -m venv .venv && source .venv/bin/activate
pip install -e .
# 可选 PDF/Docx 支持（不做 OCR）
pip install -e '.[pdf,docx]'
```

v0.5.2 packages the default prompts, Knowledge Card template, and default
configs inside the `mindforge` package. That means the default fake-provider
path works from a vault directory or `/tmp`, not only from the repository root.
If you pass `--prompts-dir`, `--tracks`, or `--template`, your explicit paths
still take priority.

## 2. 一键铺骨架

```bash
mindforge init --vault ~/MindForgeVault
```

也可以使用交互式向导：

```bash
mindforge init --interactive
```

它会依次询问 vault 路径、本地 telemetry 是否启用、`active_profile`。默认仍是
`fake`，不会读取 `.env`，不会调用真实 LLM。

这会：
- 创建 `00-Inbox/{Cubox,ManualNotes,WebClips,ChatExports,PDFs,Docs}/`、
  `20-Knowledge-Cards/`、`30-Projects/`、`40-Reviews/`、`90-Archive/`；
- 复制 `configs/mindforge.yaml`（`active_profile=fake`）+ `learning_tracks.yaml`；
- 写 `.env.example`（**不写真实 secret**）；
- 自动改写新 yaml 中的 `vault.root`。

`mindforge init --dry-run` 可预览将创建的文件。

## 3. 健康检查

```bash
mindforge doctor
```

这一步会指出：vault 缺什么目录、是否需要 init、`.env` 是否在 `.gitignore`、
optional 依赖是否安装、有没有 `ai_draft` 待审核、索引是否 stale、
是否有 overdue 复习。**不读取 `.env` 内容**。

## 4. 放入 Markdown，跑 fake pipeline

```bash
echo '# 我的第一篇笔记\n\n这是关于 agent runtime 的初步思考。' \
  > ~/MindForgeVault/00-Inbox/ManualNotes/note-1.md

mindforge scan
mindforge process --limit 5    # active_profile=fake 不调真实 LLM
```

每个产出会落到 `20-Knowledge-Cards/<track>/` 下，`status: ai_draft`。

## 5. 人工 approve（晋升长期记忆）

```bash
mindforge approve list
mindforge approve --card 20-Knowledge-Cards/agent-runtime/...md
# 或批量：
mindforge approve --all --confirm
```

## 6. 建立本地索引并搜索

```bash
mindforge index rebuild
mindforge index info --json | head -20

# 默认 BM25
mindforge recall --query "checkpoint runtime"
# 多路混合，并打开权重解释
mindforge recall --query "checkpoint runtime" --ranking hybrid --explain
# 临时压制 review_due 通道
mindforge recall --query "..." --ranking hybrid \
  --weight-bm25 1.0 --weight-value-score 0.0 --weight-review-due 0.0
```

## 7. 复习计划

```bash
mindforge review schedule --days 7                       # 默认 markdown
mindforge review schedule --days 7 --format json
mindforge review schedule --days 7 --format ical \
  --output /tmp/mindforge-review.ics                    # 本地 .ics（不接系统日历）

mindforge review backlog                                 # overdue/today/upcoming/missing
mindforge review stats --json
mindforge review weekly --output /tmp/weekly.md          # 周报，纯结构化汇总
mindforge review mark --card <path> --result remembered  # 真写
mindforge review mark --card <path> --result partial \
  --note "卡在 ReAct 步骤 3" --dry-run                  # 预览
```

## 8. 项目上下文包

```bash
mindforge project list
mindforge project context my-first-agent --target claude-code
mindforge project context my-first-agent agent-tool-harness \
  --format markdown -o /tmp/context.md
mindforge project update-evidence my-first-agent --dry-run
```

## 9. 安全核心（默认就守住的边界）

- **绝不**调用真实 LLM —— 默认 `active_profile=fake`；
- **绝不**读取 `.env` 内容 —— `doctor` 只检查文件是否在 `.gitignore`；
- **绝不**联网 —— 所有 BM25 / hybrid / iCal / weekly 都是本地纯计算；
- **绝不**修改 raw source；
- **绝不**自动 approve；
- telemetry **本地 only**，10 字段白名单，`.gitignore` 已防泄漏。
- Obsidian binding 默认只读；staging 写入必须显式 `--write --confirm`，且不改正式 notes。
- v0.5.1 Local Usability 不进入 RAG / embedding，不做 Obsidian plugin。

详见 [`USER_GUIDE.md`](./USER_GUIDE.md)、[`SECURITY.md`](./SECURITY.md)、
[`M5_7_TELEMETRY_PROTOCOL.md`](./M5_7_TELEMETRY_PROTOCOL.md)。

## 10. Cubox 本地 export 预检（dogfood）

想用本地 Cubox JSON export 文件做一次只读预检（不联网、不调真实 API、
不写 vault、不调 LLM、不生成 `human_approved`），见
[`CUBOX_DRY_RUN.md`](./CUBOX_DRY_RUN.md)。

## 11. 验证你的安装是 fake-default + 安全的真实 opt-in (v0.13)

v0.13 Stage 1 引入 `mindforge provider` 子命令, 让你**不调网络、不读
secret value** 就能确认本地路径仍然是 fake-default, 并在显式 opt-in
时跑一次最小 synthetic real-LLM smoke。

```bash
# 报告当前 provider 状态 (active_profile / 各 alias api_key 是否存在)
# 输出包含 fake-default / real provider opt-in / human approval required 等固定 token,
# 永远不会打印 api_key value。
mindforge provider readiness --config configs/mindforge.yaml

# 默认拒绝触发真实 LLM (无 --allow-real)
mindforge provider smoke --config configs/mindforge.yaml

# 显式 opt-in 触发 synthetic real-LLM smoke (仅当你已切换 active_profile 且 api_key 存在)
# 输入是硬编码 synthetic prompt, 输出仅落 ai_draft_preview, 永不写 vault/cards,
# 永远不会成为 human_approved。
mindforge provider smoke --config configs/mindforge.yaml --allow-real
```

完整的安全契约见
[`LOCAL_FIRST_PRIVACY_CONTRACT.md`](./LOCAL_FIRST_PRIVACY_CONTRACT.md);
推迟项 (Cubox 真实 ingestion / Obsidian 真实写入) 的启用前置见
[`V0_13_REAL_INGESTION_DEFERRED_GATES.md`](./V0_13_REAL_INGESTION_DEFERRED_GATES.md)
和 v0.14/v1.0 的统一 future-gate 规格
[`V0_14_FUTURE_GATES.md`](./V0_14_FUTURE_GATES.md)。整个 Roadmap 的
当前状态 (已 push / future-gated / release-gated / forbidden) 在
[`ROADMAP_COMPLETION_LEDGER.md`](./ROADMAP_COMPLETION_LEDGER.md);
要给审计员/团队成员一份可复制的取证命令, 见
[`EVIDENCE_COMMANDS.md`](./EVIDENCE_COMMANDS.md)。
