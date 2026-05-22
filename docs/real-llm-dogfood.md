# MindForge Real LLM Opt-in Dogfood 指南

批量、端到端、可重复的真实 LLM opt-in dogfood 路线。使用多份非敏感样本一次性验证 MindForge 在真实 LLM 下的全链路行为。

## 前提条件

- Python >= 3.11
- 已 `pip install -e .`（开发模式安装）
- 有效的 API key（OpenAI / Anthropic / compatible）
- 网络连接（能访问 LLM API endpoint）
- **不需要** 读取 `.env` 或 secret store

## 安全边界

在开始之前，理解以下安全契约：

| 边界 | 说明 |
|------|------|
| **显式 opt-in** | 真实 LLM 调用必须同时传 `--real-llm` 和 `--confirm-cost` 双 flag |
| **默认安全** | 脚本默认进入 preflight 模式，不调用 LLM，不创建出站 HTTP 连接 |
| **手动 approve** | 脚本绝不自动执行 `approve`，`human_approved` 必须人工 `approve --confirm` |
| **环境变量传 key** | API key 通过 shell `export` 传入，脚本不读 `.env` 或 secret store |
| **`/tmp` 隔离** | 所有数据写入 `/tmp`，不接触真实 Obsidian vault |
| **BM25 检索** | recall 使用纯本地词法检索，不是 RAG，不做 embedding |
| **非敏感样本** | 6 份样本均为合成数据，不含私人信息 |

## 配置步骤

### 1. 复制配置模板

```bash
cp examples/dogfood/mindforge.real-llm.example.yaml /tmp/real-llm.yaml
```

### 2. 编辑填入必要字段

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

### 3. 设置 API key 环境变量

```bash
export YOUR_ENV_VAR="sk-your-api-key-here"
```

**注意**：不要写入 `.env` 文件，脚本不会读取它。

## Preflight 检查

运行 preflight 验证配置就绪（不调用 LLM，不创建出站 HTTP 连接）：

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
- **API key 环境变量已设置且非空**
- Provider type 非 fake（验证 config 指向真实 LLM）
- 6 份 sample 文件存在且 YAML frontmatter 有效
- `/tmp` 可写

**如果 preflight 报告 `YOUR_API_KEY_ENV_VAR 未设置`**，说明你忘记 export 环境变量。

**如果 preflight 报告 `所有 model type 均为 fake`**，说明 config 中的 type 字段仍为 `fake`，需要改为 `openai_compatible` 或 `anthropic_compatible`。

## Real-run Smoke

### 一键执行

```bash
./scripts/real_llm_dogfood.sh --real-llm --confirm-cost
```

脚本自动完成：清理残留 → 创建工作区 → 复制 6 份样本 → scan → process（真实 LLM）→ 结构校验 → 安全边界验证 → 展示 review → **暂停等待手动 approve** → 轮询检测完成 → library 确认 → index rebuild → recall → 生成 friction log。

### 关键交互点：手动 approve

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

这样可以逐份定位是哪份样本触发了问题，无需重复处理全部 6 份。

## 手动命令序列

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

## 如何确认走的是真实 LLM？

以下信号共同确认当前使用的是真实 LLM 而非 fake provider：

1. **Config type 检查**：运行 `grep "type:" /tmp/real-llm.yaml | head -3`，应显示 `openai_compatible` 或 `anthropic_compatible`，而非 `fake`
2. **Preflight 验证**：preflight [P5] 输出 `has_real=True`，若为 `False` 则拒绝进入 real-run
3. **网络监控**：process 期间可见出站 HTTPS 连接到 LLM API endpoint
4. **输出内容**：ai_draft 的 summary/concepts 是自然语言内容，不含 `[fake]` 前缀（fake provider 所有输出以 `[fake]` 开头）
5. **process 日志**：不显示 `fake://` 或 `[fake]` 标记

## 如何确认没有自动 approve？

1. **[S7] 验证**：process 后 `mindforge library list` 应显示"暂无卡片"（或为空）—— 这意味着 ai_draft 未被自动提升
2. **脚本源码**：`grep "approve" scripts/real_llm_dogfood.sh` 不会找到脚本自动执行 approve 的命令
3. **state.json 检查**：`cat /tmp/mindforge-dogfood-state/state.json | python -m json.tool | grep status`，process 后所有卡片 status 应为 `ai_draft`
4. **approve 要求**：`mindforge approve` 不带 `--confirm` 会报错退出，不能静默通过

## 如何验证 recall 是 BM25（非 RAG/embedding）？

1. **Config 确认**：`search.bm25.enabled: true`，无 `embedding` 或 `vector` 配置段
2. **索引文件**：`file /tmp/mindforge-dogfood-state/index/bm25.json` 显示是 JSON 文本文件（TF-IDF 权重），不是向量二进制文件
3. **不需要 API key**：recall 在未 export API key 时仍可正常工作（BM25 纯本地计算）
4. **搜索行为**：只能匹配精确词干/词组，不会"理解"语义相似的词（例如搜"Docker"不会返回"容器化"相关卡片，除非卡片内容中包含"Docker"这个词）
5. **脚本确认**：脚本 [S12] 输出 `index rebuild 完成（BM25 纯本地，无 embedding/RAG）`

## Friction Log 使用

脚本在 `real-run` 完成后自动生成 friction log 模板到 `/tmp/mindforge-dogfood-state/friction-log.md`。

### 评分锚定示例

以下是每项维度的评分标准，填写 friction log 时参考：

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

## 清理

所有产物保留在 `/tmp` 下供人工检查。需要清理时：

```bash
rm -rf /tmp/mindforge-dogfood-vault /tmp/mindforge-dogfood-state
```

脚本在结束时也会打印清理命令。

## 常见问题

| 现象 | 检查 |
|------|------|
| `mindforge: command not found` | 激活 venv 并运行 `pip install -e .` |
| preflight P2a 报"未设置" | `export YOUR_ENV_VAR="sk-..."`（替换为你的环境变量名） |
| preflight P5 报"所有 type 为 fake" | 编辑 config 将 `type: fake` 改为 `type: openai_compatible` |
| 忘记传 `--config` | 默认 config 可能使用 fake provider，导致实际跑的是 fake |
| process 超时 | 检查网络连接和 API endpoint 可达性 |
| 轮询超时（5 分钟） | 确认已在另一个终端执行 `approve --confirm` |
| recall 无结果 | 先确认 `mindforge library list` 是否有已审批卡片 |
| `/tmp` 被清理（macOS 重启后） | 跨会话 dogfood 需重新复制 config 和样本 |
