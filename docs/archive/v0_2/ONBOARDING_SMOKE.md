# MindForge Onboarding Smoke

> 让一个**完全没用过 MindForge 的新用户**在 5 分钟内跑通"初始化 → 处理 →
> 批准 → 复习 → 召回 → 项目上下文"完整链路，**全程不调用真实 LLM、不读 .env、
> 不处理任何真实资料**。

## 0. 前置

- Python ≥ 3.11
- 在仓库根：`pip install -e .`（或 `pip install -e '.[dev]'`）
- 不需要任何 API key

为什么 onboarding smoke 必须使用 fake provider：
1. 我们不能假设新用户已经有 OpenAI / Anthropic key；
2. CI / 教学 / demo 环境必须能完全离线跑通；
3. fake provider 输出确定性结果，验证的是**链路通畅**，不是模型质量。

## 1. 初始化一个临时 vault

```bash
TMP=/tmp/mindforge-smoke
rm -rf $TMP && mkdir -p $TMP
cd $TMP

mindforge init --vault $TMP/vault --project-root $TMP --dry-run    # 先看 plan
mindforge init --vault $TMP/vault --project-root $TMP              # 真正执行
```

预期：
- `vault/00-Inbox/{Cubox,WebClips,ChatExports,PDFs,Docs,ManualNotes}` 创建
- `vault/{20-Knowledge-Cards,30-Projects,80-Reviews,90-System,_attachments}` 创建
- `configs/{mindforge.yaml,learning_tracks.yaml,llm.example.yaml}` 创建
- `.env.example` 创建（**不会**创建真实 `.env`）
- `mindforge.yaml` 中 `vault.root` 自动改写为 `$TMP/vault`

## 2. 放入一个非敏感样例 Markdown

```bash
cat > $TMP/vault/00-Inbox/ManualNotes/hello.md <<'EOF'
---
title: Hello MindForge
source_url: https://example.com/hello
created_at: 2025-01-01
tags: [demo, smoke]
---

# Hello

This is a non-sensitive smoke note about agent runtime checkpoints.
EOF
```

## 3. 自检

```bash
mindforge doctor --config $TMP/configs/mindforge.yaml
```

预期：vault 目录全 ok，optional deps 提示是否装 pdf/docx，**不**打印 .env 内容。

## 4. 扫描 + 处理（fake provider）

```bash
mindforge --config $TMP/configs/mindforge.yaml scan
mindforge --config $TMP/configs/mindforge.yaml process --profile fake --limit 1
```

> 默认 yaml 已经 `active_profile: fake`，但 `--profile fake` 写明意图。

## 5. 看看产出哪些 ai_draft

```bash
mindforge --config $TMP/configs/mindforge.yaml approve list
```

## 6. 显式 approve 一张卡片

```bash
CARD=$(ls $TMP/vault/20-Knowledge-Cards/**/*.md | head -1)
mindforge --config $TMP/configs/mindforge.yaml approve --card "$CARD"
```

为什么 approve 必须显式人工动作：见 `docs/M3_HUMAN_APPROVAL_PROTOCOL.md`。
**绝不**用 `approve --all --confirm` 跑 onboarding —— 那是危险动作的演示。

## 7. 复习 + 召回 + 项目上下文 + vault index

```bash
mindforge --config $TMP/configs/mindforge.yaml review due
mindforge --config $TMP/configs/mindforge.yaml recall agent
mindforge --config $TMP/configs/mindforge.yaml project context demo
mindforge --config $TMP/configs/mindforge.yaml vault index
mindforge --config $TMP/configs/mindforge.yaml vault links
```

## 8. 看本地 telemetry（**不**上传）

```bash
mindforge --config $TMP/configs/mindforge.yaml telemetry status
mindforge --config $TMP/configs/mindforge.yaml telemetry summary
```

## 9. 不要提交的产物

以下产物**绝不能**进 git；`.gitignore` 默认已包含：

- `.mindforge/`
- `.mindforge/telemetry.jsonl`
- `.env`
- `runs/`
- `state.json`
- 任何用户私人 vault 内容

## 10. 失败排查

| 现象 | 排查 |
|---|---|
| `mindforge: command not found` | 仓库根 `pip install -e .` |
| `config 文件不存在` | `--config` 路径不对，或 `mindforge init` 还没跑 |
| `approve list` 显示 `(no cards match)` | 还没 process 或 yaml `vault.root` 不对，跑 `mindforge doctor` |
| `OptionalDependencyError: mindforge[pdf]` | 你 PDF 文件被处理了；按提示装 `pip install 'mindforge[pdf]'` 或在 `sources.enabled` 移除 `pdf` |
| `--vault` 全局 flag 没生效 | 必须放在子命令前：`mindforge --vault X scan`，不是 `mindforge scan --vault X` |

## 11. smoke 之后清理

```bash
rm -rf $TMP
```

## 不做清单（任何 onboarding 都不会触发）

- ❌ 不读取 `.env` 内容
- ❌ 不发 HTTP（默认 fake provider）
- ❌ 不上传 telemetry
- ❌ 不批量 approve（必须显式 `--confirm`）
- ❌ 不修改原始 source 文件
- ❌ 不引入 RAG / embedding / OCR
