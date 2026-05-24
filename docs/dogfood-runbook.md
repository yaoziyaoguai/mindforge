# MindForge Dogfood Runbook

MindForge 狗粮操作手册，覆盖从零密钥的 fake provider 到真实 LLM opt-in 的完整路径。

---

## 目录

1. [快速开始 — Fake Provider（零密钥）](#1-快速开始--fake-provider零密钥)
2. [自动验证 — fake_dogfood.sh](#2-自动验证--fake_dogfoodsh)
3. [配置真实 LLM](#3-配置真实-llm)
4. [首次 Scan & Review](#4-首次-scan--review)
5. [审批 Approve & Wiki](#5-审批-approve--wiki)
6. [Recall 检索验证](#6-recall-检索验证)
7. [安全检查清单](#7-安全检查清单)
8. [Friction Log](#8-friction-log)
9. [清理](#9-清理)
10. [常见问题](#10-常见问题)

---

## 1. 快速开始 — Fake Provider（零密钥）

验证 MindForge 知识加工全链路能跑通，不依赖真实 LLM、不读 `.env`、不接触私人资料。

### 前置条件

- Python >= 3.11
- 已 `pip install -e .`（开发模式安装）
- 不需要 API key
- 不需要网络连接

### 一键 Smoke

```bash
./scripts/dogfood_smoke.sh
```

脚本自动完成：创建临时 workspace → 写入 sample markdown → scan → process（fake provider）→ 验证 ai_draft → approve → index rebuild → recall/search。全部在 `/tmp` 下运行。

### 手动命令序列

如果不使用脚本，可逐步执行：

```bash
# 0. 准备临时 workspace
export DOGFOOD_CONFIG="$(pwd)/examples/dogfood/mindforge.dogfood.yaml"
rm -rf /tmp/mindforge-dogfood-vault /tmp/mindforge-dogfood-state
mkdir -p /tmp/mindforge-dogfood-vault/00-Inbox
mkdir -p /tmp/mindforge-dogfood-vault/20-Knowledge-Cards

# 1. 验证配置
mindforge doctor --config "$DOGFOOD_CONFIG"

# 2. 写入非敏感 sample markdown
cat > /tmp/mindforge-dogfood-vault/00-Inbox/test-knowledge.md << 'MDEOF'
---
title: 非敏感测试知识片段
date: 2026-05-21
tags: [test, dogfood, smoke]
---

# checkpoint runtime 非敏感测试

这是一段用于验证 MindForge dogfood 闭环的非敏感测试内容。

## 核心概念

- checkpoint runtime 是模型推理时的中间状态快照
- 用于断点续训和推理回溯
- 不包含用户数据或模型权重

## 实践建议

1. 定期保存 checkpoint 防止意外中断
2. 过期 checkpoint 应及时清理以释放存储
3. checkpoint 命名应包含时间戳和 loss 值
MDEOF

# 3. 扫描 inbox
mindforge scan --config "$DOGFOOD_CONFIG"

# 4. 处理 — fake provider 生成 ai_draft，不发起 HTTP 请求
mindforge process --config "$DOGFOOD_CONFIG"

# 5. 检查卡片状态 — 必须是 ai_draft，不能是 human_approved
mindforge status --config "$DOGFOOD_CONFIG"

# 6. 查看待审批卡片
mindforge approve list --config "$DOGFOOD_CONFIG"

# 7. 审批 — 必须显式 --confirm
mindforge approve <ref> --confirm --config "$DOGFOOD_CONFIG"

# 8. 构建检索索引
mindforge index rebuild --config "$DOGFOOD_CONFIG"

# 9. 检索验证
mindforge recall --query "checkpoint runtime" --config "$DOGFOOD_CONFIG"
```

### Fake Provider 安全说明

- **Fake provider**：所有 LLM 调用使用 `[fake]` 确定性占位输出，不发起 HTTP 请求，不需要 API key。
- **不自动 approve**：`process` 只生成 `ai_draft`，必须 `approve --confirm` 才能提升为 `human_approved`。
- **不读 .env**：dogfood config 不引用任何环境变量或 secret store。
- **/tmp 隔离**：所有运行时状态、vault、index 都写入 `/tmp`，不接触真实 workspace。
- **BM25 检索**：纯本地词法检索，不是 RAG，不做 embedding。

---

## 2. 自动验证 — fake_dogfood.sh

除了上面的手动步骤，v0.5 新增的一键端到端验证脚本覆盖更完整的流程：

```bash
./scripts/fake_dogfood.sh
```

脚本步骤：

| 步骤 | 操作 | 验证点 |
|------|------|--------|
| S1 | 创建临时 dogfood workspace | `/tmp` 可写、config 可解析 |
| S2 | 导入全部 6 份 samples | 文件复制成功 |
| S3 | `mindforge scan` | 扫描无错误 |
| S4 | `mindforge process` | 生成 ai_draft |
| S5 | 验证 card 结构 | 每张 card 有 title/tags/summary |
| S6 | 验证 wiki rebuild | wiki 渲染非空 |
| S7 | `mindforge recall` | BM25 检索返回结果 |
| S8 | 安全边界验证 | 无 human_approved 自动提升 |
| S9 | 清理 | 移除临时文件 |

退出码 0 = 全部通过。不读取 `.env`，不调用真实 LLM。

---

## 3. 配置真实 LLM

当你准备好从 fake 切换到真实 LLM 时，推荐使用 **Web-first** 路径。

### 前提条件

- Python >= 3.11
- Node/npm（用于构建 Web 前端）
- 有效的 API key（OpenAI / Anthropic / 兼容）
- 网络连接（能访问 LLM API endpoint）

### 3.1 Fresh clone 并安装

```bash
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge

python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .

cd web
npm install
npm run build
cd ..
```

### 3.2 初始化 workspace 并启动 Web

```bash
mkdir -p /tmp/mindforge-first-run
cd /tmp/mindforge-first-run
mindforge init

mindforge web --open
```

浏览器打开 `http://127.0.0.1:8765`。

### 3.3 在 Web Setup 页面配置 provider

1. 打开 **Setup** 页面
2. 点击 **Add model**
3. 填写以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| **Model ID** | 自定义名称 | `main` |
| **Type** | `openai_compatible` 或 `anthropic_compatible` | `openai_compatible` |
| **Base URL** | LLM API endpoint | `https://api.openai.com/v1` |
| **Model** | 模型名称 | `gpt-4o` |
| **API Key** | 你的 API key | `sk-...` |

4. 点击 **Save**

### 3.4 API Key 安全规则

- API key 存入 local secret store（`.mindforge/secrets.json`），**不写 YAML**
- **不要** 把 API key 写进 repo
- **不要** 把 API key 提交到 git
- **不要** 把 API key 发给 agent
- **不要** 把 API key 粘贴到聊天、issue、终端日志或 README

### 3.5 确认 provider 已配置

保存后在 **Home** 页面或运行以下命令确认：

```bash
mindforge status
mindforge doctor
```

### 3.6 确认真实 LLM（非 fake）

以下信号共同确认使用的是真实 LLM：

1. **Provider readiness**：Home 页面显示 real provider configured，type 不是 `fake`
2. **不是 fake profile**：Setup 中 model type 为 `openai_compatible` 或 `anthropic_compatible`
3. **输出不含 `[fake]`**：fake provider 所有输出以 `[fake]` 开头，真实 LLM 输出不含此前缀
4. **网络延迟**：process 期间可见正常的 API 调用延迟

---

## 4. 首次 Scan & Review

### 4.1 导入非敏感样本

```bash
# 复制 samples 到 vault inbox
cp examples/dogfood/samples/*.md /tmp/mindforge-first-run/vault/00-Inbox/

# 导入并处理
mindforge import vault/00-Inbox/short-note.md
mindforge import vault/00-Inbox/long-technical.md
mindforge import vault/00-Inbox/bullet-notes.md
mindforge import vault/00-Inbox/tech-learning.md
mindforge import vault/00-Inbox/low-signal.md
mindforge import vault/00-Inbox/mixed-zh-en.md
```

或通过 Web **Sources** 页面逐个添加 source 并点击 **Process now**。

### 4.2 触发 process

Web **Sources** 页面点击 **Process now**，或 CLI：

```bash
mindforge watch scan
```

查看处理进度：

```bash
mindforge runs list
mindforge runs show <run_id>
```

### 4.3 确认不自动 approve

```bash
mindforge approve list     # 应列出 ai_draft 状态的卡片
mindforge library list     # 应显示为空 — ai_draft 未被自动提升
```

---

## 5. 审批 Approve & Wiki

### 5.1 人工审阅

打开 Web **Review** 页面，逐张查看 AI 生成的草稿卡片：

- 检查 summary 是否准确
- 检查 concepts 是否合理
- 检查 action_items 是否有意义
- 注意 `low-signal.md` 是否触发 `insufficient_content`

CLI 查看：

```bash
mindforge approve show --card 1 --show-content
```

### 5.2 显式 Approve

**approve 必须带 `--confirm` 才能执行**。不带 `--confirm` 会报错退出。

Web **Review** 页面点击 **Approve** 按钮并确认，或 CLI：

```bash
mindforge approve <ref> --confirm     # 逐张审批
mindforge approve --all --confirm     # 全部审批
```

拒绝卡片：

```bash
mindforge reject <ref>
```

### 5.3 Library 验证

审批完成后：

```bash
mindforge library list     # 应看到已审批卡片
```

### 5.4 Wiki Rebuild

审批后 Wiki 自动重建（如已开启 auto-rebuild），或手动触发。在 Web **Wiki** 页面验证 section 内容和 provenance 正确。

---

## 6. Recall 检索验证

```bash
# 重建索引
mindforge index rebuild

# BM25 词法检索
mindforge recall --query "Docker"
mindforge recall --query "PostgreSQL"
mindforge recall --query "Kubernetes"
```

确认：
- 检索结果来自已审批卡片
- 匹配的是词法/词组，不是语义相似
- 不需要 API key 即可执行（纯本地计算）
- 用精确词搜索能匹配；用语义近义词不返回纯词法不匹配的内容

---

## 7. 安全检查清单

在真实 LLM dogfood 前，逐项确认：

### 配置安全

- [ ] API key 仅通过 Web Setup 页面填入，从未写入 YAML 文件
- [ ] `.mindforge/secrets.json` 不在 git 跟踪中（`.gitignore` 已包含）
- [ ] 未在任何 `.md`、`.yaml`、`.py` 文件中硬编码 API key
- [ ] 未在终端日志、聊天、issue 中粘贴 API key

### 审批安全

- [ ] `process` 后卡片状态为 `ai_draft`，未被自动提升为 `human_approved`
- [ ] `approve` 必须显式传 `--confirm` 或 Web 端点击确认按钮
- [ ] `reject` / `insufficient_content` 的卡片不在 Library 中

### 检索安全

- [ ] Recall 使用 BM25 本地词法检索，不调用外部 API
- [ ] 没有 embedding / vector DB / RAG 参与检索链路

### 沙箱隔离

- [ ] Dogfood 数据全部在 `/tmp` 下，不接触真实 Obsidian vault
- [ ] 未使用 `~/Documents`、`~/Obsidian`、`~/Library` 等路径

### 网络与隐私

- [ ] 仅 process 阶段有出站 HTTPS 连接到 LLM API endpoint
- [ ] Scan、triage、approve、recall 均为本地操作
- [ ] 未上传任何 source 文件内容到第三方服务（除 LLM API 正常调用外）

---

## 8. Friction Log

在 dogfood 过程中记录以下维度的摩擦点：

| 维度 | 摩擦点 | 严重程度 |
|------|--------|----------|
| 安装摩擦 | | |
| Web 启动摩擦 | | |
| provider 配置摩擦 | | |
| process 摩擦 | | |
| review / approve 摩擦 | | |
| recall 摩擦 | | |
| 文档不清楚的地方 | | |
| 是否需要改产品逻辑 | | |

### 评分锚定

**summary 准确性**：
- **5 分**：原文核心要点全部捕获
- **3 分**：捕获了部分要点但有遗漏
- **1 分**：summary 与原文内容几乎不相关或存在事实错误

**action_items 合理性**：
- **5 分**：具体、可执行（如"为 orders 表在 created_at 列上建立索引"）
- **3 分**：方向正确但过于模糊（如"优化数据库性能"）
- **1 分**：与内容完全无关

**insufficient_content 判断**：
- `low-signal.md`（~30 词，内容为"今天看到一个有意思的东西，改天再研究"）：理想情况应触发 insufficient_content

---

## 9. 清理

所有产物保留在 `/tmp` 下供人工检查。需要清理时：

```bash
rm -rf /tmp/mindforge-dogfood-vault /tmp/mindforge-dogfood-state
rm -rf /tmp/mindforge-first-run
rm -f /tmp/real-llm.yaml
```

**注意**：这些命令只清理 `/tmp` 下的临时 dogfood 数据，不会影响真实 Obsidian vault 或个人资料。

---

## 10. 常见问题

| 现象 | 检查 |
|------|------|
| `mindforge: command not found` | 激活 venv 并运行 `pip install -e .` |
| Web 页面空白 | 确认已构建前端：`cd web && npm run build` |
| Home 显示 provider 未配置 | 在 Web Setup 页面 Add model 并保存 |
| API key 未生效 | 检查 Setup 页面 model 的 key source 是否为 `local_secret` |
| 忘记传 `--config`（CLI 路径） | 默认 config 可能使用 fake provider |
| process 超时 | 检查网络连接和 API endpoint 可达性 |
| recall 无结果 | 先确认 `library list` 有已审批卡片，再 `index rebuild` |
| `/tmp` 被清理（macOS 重启后） | 跨会话 dogfood 需重新复制 config 和样本 |
| 卡片状态不对 | 运行 `mindforge status --config <config>` 检查 |
| `/tmp` 不可写 | 检查 `/tmp` 权限或换用其他临时目录 |

---

## 参考

- 零密钥快速指南（原始）：`docs/dogfood.md`
- 真实 LLM 指南（原始）：`docs/real-llm-dogfood.md`
- 一键 fake smoke 脚本：`scripts/dogfood_smoke.sh`
- v0.5 Dogfood Spec：`docs/specs/2026-05-24-011-v0_5-dogfood-readiness-spec.md`
