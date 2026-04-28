# MindForge Demo Vault

> 这是一份**完全虚构、无敏感数据**的示例 vault，用于：
> 1. 文档/截图/演示；
> 2. 跑 smoke（`mindforge scan` / `process --profile fake` / `recall` 等）；
> 3. 帮助新用户在 5 分钟内理解 MindForge 的产物形态。
>
> 任何文件**不得**包含：真实工作资料、个人隐私、API key、token、`.env`、
> 用户邮箱、未公开的项目代码。

## 目录结构

```
examples/demo-vault/
├── 00-Inbox/
│   ├── Cubox/         · 1 篇虚构的 Cubox-style markdown
│   ├── WebClips/      · 1 篇虚构的 Web Clipper markdown
│   ├── ChatExports/   · 1 篇虚构的 ChatGPT 导出
│   └── ManualNotes/   · 1 篇虚构的手写笔记
├── 20-Knowledge-Cards/
│   └── agent-runtime/ · 3 张已加工的示例卡片（含 ai_draft + human_approved）
├── 30-Projects/
│   └── my-first-agent.md  · 项目主笔记 + profile frontmatter
├── 40-Reviews/        · （空，由 review weekly 生成）
└── 90-Archive/        · （空）
```

## 用 demo vault 跑一遍

```bash
# 1) 复制 configs（一次性）
cp configs/mindforge.yaml /tmp/demo.yaml
# 然后用 --vault 临时指向 demo vault（不改 yaml）
export DEMO=$(pwd)/examples/demo-vault

mindforge --vault "$DEMO" doctor --config configs/mindforge.yaml
mindforge --vault "$DEMO" next   --config configs/mindforge.yaml
mindforge --vault "$DEMO" scan   --config configs/mindforge.yaml
mindforge --vault "$DEMO" process --config configs/mindforge.yaml --limit 5
mindforge --vault "$DEMO" approve list --config configs/mindforge.yaml
mindforge --vault "$DEMO" index rebuild --config configs/mindforge.yaml
mindforge --vault "$DEMO" recall --query "checkpoint runtime" \
  --ranking hybrid --explain --config configs/mindforge.yaml
mindforge --vault "$DEMO" review weekly --config configs/mindforge.yaml
mindforge --vault "$DEMO" project context my-first-agent \
  --target claude-code --config configs/mindforge.yaml
```

## 安全契约

- **不含 .env**：`mindforge[doctor|next]` 仅检查 `.env` 是否在 `.gitignore`，
  绝不读取 `.env` 内容；
- **fake provider**：默认 `active_profile=fake`，`process` 不会真的调 LLM；
- **只读 inbox**：所有输入文件只读，pipeline 写产物到 `20-Knowledge-Cards/`；
- **只跑本地**：BM25/hybrid 索引、weekly、ical、project context 全部本地。
