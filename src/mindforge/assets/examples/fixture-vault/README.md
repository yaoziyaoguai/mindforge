# MindForge Fixture Vault

> 这是一份**完全虚构、无敏感数据**的示例 vault，用于：
> 1. 文档/截图；
> 2. 跑本地 smoke（`mindforge scan` / `recall` 等）；
> 3. 帮助新用户在 5 分钟内理解 MindForge 的产物形态。
>
> 任何文件**不得**包含：真实工作资料、个人隐私、API key、token、`.env`、
> 用户邮箱、未公开的项目代码。

## 目录结构

```
examples/fixture-vault/
├── 00-Inbox/
│   ├── Cubox/         · 1 篇虚构的 Cubox-style markdown
│   ├── WebClips/      · 1 篇虚构的 Web Clipper markdown
│   ├── ChatExports/   · 1 篇虚构的 ChatGPT 导出
│   └── ManualNotes/   · 1 篇虚构的手写笔记
├── 02-Knowledge/      · Obsidian-style 虚构 note（frontmatter/tags/wikilinks/headings）
├── 03-Projects/       · Obsidian-style 虚构项目 note
├── 20-Knowledge-Cards/
│   └── agent-runtime/ · 3 张已加工的示例卡片（含 ai_draft + human_approved）
├── 30-Projects/
│   └── my-first-agent.md  · 项目主笔记 + profile frontmatter
├── 40-Reviews/        · （空，由 review weekly 生成）
└── 90-Archive/        · （空）
```

## 用 fixture vault 跑一遍

```bash
# 1) 复制 configs（一次性）
cp configs/mindforge.yaml /tmp/mindforge-fixture.yaml
# 然后用 --vault 临时指向 fixture vault（不改 yaml）
export FIXTURE=$(pwd)/examples/fixture-vault

mindforge doctor --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge commands
mindforge next --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge scan --vault "$FIXTURE" --config configs/mindforge.yaml
# process 需要你在 configs/mindforge.yaml 配好 llm.models/default_model；
# 没有真实模型时可以跳过这一步，fixture vault 仍可用于 scan/recall/review。
# mindforge process --limit 1 --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge approve list --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge index rebuild --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge recall --query "checkpoint runtime" \
  --ranking hybrid --explain --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge review weekly --format markdown --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge review schedule --days 7 --format markdown --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge project context my-first-agent \
  --target claude-code --vault "$FIXTURE" --config configs/mindforge.yaml

# Obsidian Binding v0.5：只读扫描，不改正式 notes
mindforge obsidian doctor --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge obsidian scan --vault "$FIXTURE" --limit 5 --config configs/mindforge.yaml
mindforge obsidian links --vault "$FIXTURE" --config configs/mindforge.yaml
mindforge obsidian stage --vault "$FIXTURE" \
  --source 02-Knowledge/agent-runtime-observer.md \
  --dry-run --config configs/mindforge.yaml
```

`process` 会写本地产物。想反复 smoke 时，建议先复制 fixture vault 到
`/tmp`，再把 `FIXTURE` 指向副本。

## 安全契约

- **不含 secrets**：fixture 不包含 API key 或 token；
- **LLM opt-in**：fixture 不包含 API key；`process` 只在你显式配置
  `llm.models/default_model` 和 local secret store 后运行；
- **只读 inbox**：所有输入文件只读，pipeline 写产物到 `20-Knowledge-Cards/`；
- **只读 Obsidian notes**：`obsidian scan/links/doctor` 不修改正式笔记；
- **staging/review 隔离**：`obsidian stage` 默认 dry-run，写入需 `--write --confirm`；
- **只跑本地**：BM25/hybrid 索引、weekly、ical、project context 全部本地。
