# MindForge Real LLM Opt-in Dogfood Guide

> **Note (2026-05-24)**: 本文档已合并到统一的 [Dogfood Runbook](dogfood-runbook.md)。请以 runbook 为准。本文档保留作为参考。

使用真实 LLM 验证 MindForge 全链路行为的安全指南。**推荐路径是 Web-first setup**，适合新用户从 fresh clone 开始逐步验证。

## Recommended path: Web-first real LLM dogfood

这是新用户首选的真实 LLM dogfood 路径。你不需要手动编辑 YAML 或 export 环境变量 —— 所有模型配置通过 Web Setup 页面完成。

### 前提条件

- Python >= 3.11
- Node/npm（用于构建 Web 前端）
- 有效的 API key（OpenAI / Anthropic / compatible）
- 网络连接（能访问 LLM API endpoint）

### 1. Fresh clone 并安装

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

### 2. 初始化 workspace 并启动 Web

```bash
mkdir -p /tmp/mindforge-first-run
cd /tmp/mindforge-first-run
mindforge init

mindforge web --open
```

浏览器打开 `http://127.0.0.1:8765`。

### 3. 在 Web Setup 页面配置 provider

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

**API key 安全规则**：
- API key 存入 local secret store（`.mindforge/secrets.json`），**不写 YAML**
- **不要** 把 API key 写进 repo
- **不要** 把 API key 提交到 git
- **不要** 把 API key 发给 agent
- **不要** 把 API key 粘贴到聊天、issue、终端日志或 README

### 4. 确认 provider 已配置

保存后在 **Home** 页面或运行以下命令确认 provider readiness：

```bash
mindforge status
mindforge doctor
```

检查输出中 provider 状态显示为 `configured`（而非 `fake` 或 `model_setup_incomplete`）。

### 5. 导入非敏感样本

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

### 6. 触发 process

在 Web **Sources** 页面点击 **Process now**，或使用 CLI：

```bash
mindforge watch scan
```

查看处理进度：

```bash
mindforge runs list
mindforge runs show <run_id>
```

### 7. 确认只生成 ai_draft，不自动生成 human_approved

process 完成后：

```bash
mindforge approve list
```

应该列出 `ai_draft` 状态的卡片。

```bash
mindforge library list
```

应该显示"暂无卡片"（或为空）—— 这证明 `ai_draft` 没有被自动提升为 `human_approved`。

### 8. Review 页面人工审阅

打开 Web **Review** 页面，逐张查看 AI 生成的草稿卡片：

- 检查 summary 是否准确
- 检查 concepts 是否合理
- 检查 action_items 是否有意义
- 注意 `low-signal.md` 是否触发 `insufficient_content`

也可通过 CLI 查看：

```bash
mindforge approve show --card 1 --show-content
```

### 9. 显式 approve

**approve 必须带 `--confirm` 才能执行**。不带 `--confirm` 会报错退出。

在 Web **Review** 页面点击 **Approve** 按钮并确认，或使用 CLI：

```bash
# 逐张审批
mindforge approve 1 --confirm

# 或全部审批
mindforge approve --all --confirm
```

拒绝卡片：

```bash
mindforge reject <ref>
```

**reject / insufficient_content 的卡片不能进入 approved。**

### 10. Library 验证 human_approved

审批完成后：

```bash
mindforge library list
```

现在应该能看到已审批的卡片。在 Web **Library** 页面也可以浏览。

### 11. Recall 验证 BM25 lexical search

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

### 12. 记录 friction log

记录在 dogfood 过程中遇到的所有摩擦点（详见下方 [Friction Log](#friction-log) 章节）。

## How to confirm this is real LLM, not fake

以下信号共同确认当前使用的是真实 LLM 而非 fake provider：

1. **Provider readiness**：`mindforge doctor` 或 Home 页面显示 real provider configured，provider type 不是 `fake`
2. **不是 fake profile**：Web Setup 中 model type 为 `openai_compatible` 或 `anthropic_compatible`，而非 `fake`
3. **成本提示**：real-run 会有网络请求和延迟，process 期间可见出站 HTTPS 连接到 LLM API endpoint
4. **输出质量**：`ai_draft` 的 summary/concepts 是自然语言内容，不含 `[fake]` 前缀（fake provider 所有输出以 `[fake]` 开头）
5. **日志/status**：不显示 `fake://` 或 `[fake]` 标记；status 输出中能看到真实 provider 类型（但不会泄露 API key）

## How to confirm there is no auto approve

1. **process 后只有 ai_draft**：`mindforge library list` 应显示"暂无卡片"（或为空）—— `ai_draft` 未被自动提升
2. **human_approved 不自动出现**：除非你显式执行 `approve --confirm`，否则不会出现 `human_approved` 卡片
3. **approve 必须人工操作**：Web Review 页面需要点击 Approve 按钮并确认；CLI 需要显式执行 `mindforge approve`
4. **approve 必须显式 confirm**：CLI 的 `mindforge approve` 不带 `--confirm` 会报错退出，不能静默通过
5. **reject / insufficient_content 不进 approved**：被拒绝或标记为 insufficient_content 的卡片不会出现在 Library 中

## How to confirm recall is BM25 lexical

1. **当前不是 RAG**：MindForge 明确不做 RAG，不做 embedding，不做 semantic merge
2. **不使用 embedding**：配置中无 `embedding` 或 `vector` 配置段
3. **不做 semantic merge**：recall 只做本地词法匹配
4. **BM25 纯本地**：索引文件是 JSON 文本（TF-IDF 权重），不是向量二进制文件
5. **关键词验证**：用样本中出现的精确词搜索（如"Docker"、"PostgreSQL"），能匹配到对应卡片；用语义近义词（如搜"容器化"不会返回只含"Docker"的卡片，除非卡片内容中出现了"容器化"这个词）

## Friction Log

在 dogfood 过程中记录以下维度的摩擦点：

### 记录模板

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

### 评分锚定示例

**summary 准确性**：
- **5 分**（示例）：原文核心要点全部捕获，如"PostgreSQL 查询优化"→ summary 覆盖了索引优化、查询重写、表分区、连接池四个策略
- **3 分**（示例）：捕获了部分要点但有遗漏，如只提到了索引优化和查询重写，漏掉了表分区和监控指标
- **1 分**（示例）：summary 与原文内容几乎不相关，或存在事实错误

**concepts 提取**：
- **5 分**（示例）：`long-technical.md` 的 concepts 应包括 PostgreSQL、执行计划、B-tree索引、表分区、PgBouncer、查询优化等
- **3 分**（示例）：只提取了 PostgreSQL、查询优化，漏掉了具体的技术概念
- **1 分**（示例）：concepts 列表几乎为空或包含不相关的术语

**action_items 合理性**：
- **5 分**（示例）："为 orders 表在 created_at 列上建立索引"（具体、可执行）
- **3 分**（示例）："优化数据库性能"（方向正确但过于模糊）
- **1 分**（示例）："多喝热水"（与内容完全无关）

**insufficient_content 判断**：
- `low-signal.md`（~30 词，内容为"今天看到一个有意思的东西，改天再研究"）：理想情况应触发 insufficient_content 或生成空卡片
- 如果生成了正常 ai_draft，说明 insufficient_content 阈值可能过低

## Advanced path: CLI/YAML batch runner

以下 CLI/YAML 路径适合批量 E2E、CI-like 或开发者验证场景。**这不是新用户首选入口**，推荐新用户使用上方的 Web-first 路径。

### 前提条件

- 已 `pip install -e .`
- 有效的 API key
- 网络连接

### 配置步骤

#### 1. 复制配置模板

```bash
cp examples/dogfood/mindforge.real-llm.example.yaml /tmp/real-llm.yaml
```

#### 2. 编辑填入必要字段

编辑 `/tmp/real-llm.yaml`，在 `llm.models.real-main` 下填入：

```yaml
models:
  real-main:
    type: openai_compatible          # 或 anthropic_compatible
    provider: openai_compatible      # 或 anthropic_compatible
    base_url: "https://your-endpoint.example.com/v1"  # ← 填入
    model: "your-model-name"         # ← 填入
    api_key_env: "YOUR_ENV_VAR"      # ← 填入
```

模板中已包含 `anthropic_compatible` 的注释替代配置，取消注释并替换即可。

#### 3. 设置 API key 环境变量

```bash
export YOUR_ENV_VAR="sk-your-api-key-here"
```

**API key 只能由用户显式提供**。脚本不读取 `.env` 或 secret store。不要写入 `.env` 文件。

### Preflight 检查

运行 preflight 验证配置就绪（**不调用 LLM，不创建出站 HTTP 连接**）：

```bash
./scripts/real_llm_dogfood.sh
```

或指定自定义 config：

```bash
./scripts/real_llm_dogfood.sh --config /tmp/real-llm.yaml
```

Preflight 检查项：
- 环境就绪（python、mindforge 可用）
- Config 文件存在且可解析
- API key 环境变量已设置且非空
- Provider type 非 fake（验证 config 指向真实 LLM）
- 6 份 sample 文件存在且 YAML frontmatter 有效
- `/tmp` 可写

### Real-run Smoke

**必须显式传 `--real-llm` 和 `--confirm-cost` 双 flag**：

```bash
./scripts/real_llm_dogfood.sh --real-llm --confirm-cost
```

脚本自动完成：清理残留 → 创建工作区 → 复制 6 份样本 → scan → process（真实 LLM）→ 结构校验 → 安全边界验证 → 展示 review → **暂停等待手动 approve** → 轮询检测完成 → library 确认 → index rebuild → recall → 生成 friction log。

### 手动 approve

脚本执行到 [S9] 步骤时会暂停，**不会自动执行 approve**。此时你需要：

1. 打开**另一个终端**
2. 查看待审批卡片：
   ```bash
   mindforge approve list --config /tmp/real-llm.yaml
   ```
3. 审批所有卡片（**必须带 `--confirm`**）：
   ```bash
   mindforge approve --all --confirm --config /tmp/real-llm.yaml
   ```
4. 或逐张审批/拒绝：
   ```bash
   mindforge approve <ref> --confirm --config /tmp/real-llm.yaml
   mindforge reject <ref> --config /tmp/real-llm.yaml
   ```

脚本会每 5 秒轮询一次，检测到所有卡片审批完毕后自动继续。最多等待 5 分钟。

### 批量失败诊断

如果 `process` 步骤失败，脚本会自动打印逐样本隔离诊断命令，例如：

```bash
# 隔离测试 low-signal.md:
rm -rf /tmp/mindforge-dogfood-vault/00-Inbox/*
cp examples/dogfood/samples/low-signal.md /tmp/mindforge-dogfood-vault/00-Inbox/
mindforge scan --config /tmp/real-llm.yaml
mindforge process --config /tmp/real-llm.yaml
```

### 手动命令序列

如果不想用脚本，也可以逐步执行：

```bash
export CONFIG="/tmp/real-llm.yaml"
export SAMPLES="$(pwd)/examples/dogfood/samples"

# 0. 清理并创建工作区
rm -rf /tmp/mindforge-dogfood-vault /tmp/mindforge-dogfood-state
mkdir -p /tmp/mindforge-dogfood-vault/00-Inbox
mkdir -p /tmp/mindforge-dogfood-vault/20-Knowledge-Cards

# 1. 复制全部 6 份样本
cp "$SAMPLES"/*.md /tmp/mindforge-dogfood-vault/00-Inbox/

# 2. scan
mindforge scan --config "$CONFIG"

# 3. process — 真实 LLM 调用
mindforge process --config "$CONFIG"

# 4. 结构校验 — 验证 ai_draft 是合法 JSON
mindforge approve list --config "$CONFIG" --format json | python -m json.tool

# 5. 确认 ai_draft 未被自动提升
mindforge library list --config "$CONFIG"
# 应该显示"暂无卡片"（或为空）

# 6. 手动 approve（必须 --confirm）
mindforge approve --all --confirm --config "$CONFIG"

# 7. 索引
mindforge index rebuild --config "$CONFIG"

# 8. 检索验证 — BM25 词法检索，非 RAG
mindforge recall --query "Docker" --config "$CONFIG"
mindforge recall --query "PostgreSQL" --config "$CONFIG"
```

## Cleanup

所有产物保留在 `/tmp` 下供人工检查。需要清理时：

```bash
rm -rf /tmp/mindforge-dogfood-vault /tmp/mindforge-dogfood-state
rm -rf /tmp/mindforge-first-run
rm -f /tmp/real-llm.yaml
```

**注意**：这些命令只清理 `/tmp` 下的临时 dogfood 数据，不会影响你的真实 Obsidian vault 或个人资料。

## 常见问题

| 现象 | 检查 |
|------|------|
| `mindforge: command not found` | 激活 venv 并运行 `pip install -e .` |
| Web 页面空白 | 确认已构建前端：`cd web && npm run build` |
| Home 显示 provider 未配置 | 在 Web Setup 页面 Add model 并保存 |
| API key 未生效 | 检查 Setup 页面 model 的 key source 是否为 `local_secret` |
| 忘记传 `--config`（CLI 路径） | 默认 config 可能使用 fake provider，导致实际跑的是 fake |
| process 超时 | 检查网络连接和 API endpoint 可达性 |
| 轮询超时（5 分钟，CLI 路径） | 确认已在另一个终端执行 `approve --confirm` |
| recall 无结果 | 先确认 `mindforge library list` 是否有已审批卡片，再运行 `mindforge index rebuild` |
| `/tmp` 被清理（macOS 重启后） | 跨会话 dogfood 需重新复制 config 和样本 |
