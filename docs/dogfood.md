# MindForge Dogfood 指南

非敏感 dogfood 闭环：在完全不依赖真实 LLM、不读 `.env`、不接触私人资料的前提下，验证 MindForge 知识加工全链路能跑通。

## 前置条件

- Python >= 3.11
- 已 `pip install -e .`（开发模式安装）
- 不需要任何 API key
- 不需要网络连接

## 一键 Smoke

```bash
./scripts/dogfood_smoke.sh
```

脚本自动完成：创建临时 workspace → 写入 sample markdown → scan → process（fake provider）→ 验证 ai_draft → approve → index rebuild → recall/search。全部在 `/tmp` 下运行，不接触真实数据。

## 手动命令序列

如果不想用一键脚本，也可以逐步执行以下命令观察每一步的输出：

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

## 安全说明

- **Fake provider**：所有 LLM 调用使用 `[fake]` 确定性占位输出，不发起 HTTP 请求，不需要 API key。输出带有 `[fake]` 前缀以区别于真实 AI 生成内容。
- **不自动 approve**：`process` 只生成 `ai_draft`，必须 `mindforge approve <ref> --confirm` 才能提升为 `human_approved`。
- **不读 .env**：dogfood config 不引用任何环境变量或 secret store。
- **/tmp 隔离**：所有运行时状态、vault、index 都写入 `/tmp`，不接触真实 workspace。
- **BM25 检索**：纯本地词法检索，不是 RAG，不做 embedding，不调 LLM。

## 常见问题

| 现象 | 检查 |
|------|------|
| `mindforge: command not found` | 激活 venv 并运行 `pip install -e .` |
| 忘记传 `--config` | 默认 config 可能使用真实 provider，务必显式传 `--config` |
| 卡片状态不对 | 运行 `mindforge status --config "$DOGFOOD_CONFIG"` 检查 |
| `/tmp` 不可写 | 检查 `/tmp` 权限或换用其他临时目录 |
