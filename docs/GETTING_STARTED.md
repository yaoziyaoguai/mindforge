# Getting Started — MindForge v0.5.0

> 目标：从零跑通 MindForge 的本地主链路，不调用真实 LLM、不接触私人数据。
> 全程使用 `fake` provider；**不读取 `.env`**。
>
> **想直接看效果？** 用仓库自带的 demo vault 一键跑：
> ```bash
> mindforge --vault examples/demo-vault doctor
> mindforge --vault examples/demo-vault next
> mindforge --vault examples/demo-vault scan
> mindforge --vault examples/demo-vault index rebuild
> mindforge --vault examples/demo-vault recall --query "checkpoint runtime" --ranking hybrid
> mindforge --vault examples/demo-vault project context my-first-agent --target claude-code
> mindforge obsidian doctor --vault examples/demo-vault
> mindforge obsidian scan --vault examples/demo-vault --limit 5
> mindforge obsidian links --vault examples/demo-vault
> mindforge obsidian stage --vault examples/demo-vault \
>   --source 02-Knowledge/agent-runtime-observer.md --dry-run
> ```
> （demo vault 完全虚构，详见 [`examples/demo-vault/README.md`](../examples/demo-vault/README.md)）
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

详见 [`USER_GUIDE.md`](./USER_GUIDE.md)、[`SECURITY.md`](./SECURITY.md)、
[`M5_7_TELEMETRY_PROTOCOL.md`](./M5_7_TELEMETRY_PROTOCOL.md)。
