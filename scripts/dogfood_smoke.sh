#!/usr/bin/env bash
# MindForge 非敏感 dogfood smoke 脚本。
#
# 中文学习型说明：
#
# 为什么需要这个脚本：
# - 验证 MindForge 在完全不依赖真实 LLM、不读 .env、不接触私人资料的前提下
#   能跑通完整知识加工闭环：import → process → ai_draft → approve → recall。
# - 每次修改管线后，开发者可以快速手动验证核心链路没有断裂。
# - 与 pytest test_onboarding_smoke.py 互补：pytest 覆盖自动化测试，
#   本脚本面向开发者手动快速验证。
#
# 安全边界：
# - 所有步骤使用 fake provider（确定性、零网络、零密钥），输出 [fake] 前缀内容。
# - 不读取 .env 或 .mindforge/secrets.json。
# - 不调用真实 LLM / provider / 外部 API。
# - 所有数据写入 /tmp，不接触真实 Obsidian vault 或私人资料。
# - ai_draft 不会被自动提升为 human_approved（本脚本显式验证这一点）。
# - 不做 RAG / embedding / vector DB。
#
# 使用方式：
#   ./scripts/dogfood_smoke.sh
#
# 注意：忘记 --config 会回退到默认 config（可能使用真实 provider）。
# 本脚本通过 DOGFOOD_CONFIG 变量强制使用 dogfood config。
#
# 清理：本脚本不在结束后清理 /tmp 下的临时文件，方便手动检查产出。
# 下次运行会自动 rm -rf 清理上次残留。
#
# 退出码：任何一步失败则非零退出，不会被管道掩盖。

set -euo pipefail

DOGFOOD_CONFIG="$(cd "$(dirname "$0")/.." && pwd)/examples/dogfood/mindforge.dogfood.yaml"
VAULT="/tmp/mindforge-dogfood-vault"
STATE="/tmp/mindforge-dogfood-state"
INBOX="$VAULT/00-Inbox"
CARDS="$VAULT/20-Knowledge-Cards"

# 辅助函数：打印步骤标题
step() {
  echo ""
  echo "=========================================="
  echo " $1"
  echo "=========================================="
}

# 辅助函数：确认输出包含预期字符串
assert_contains() {
  local output="$1"
  local expected="$2"
  local description="$3"
  if echo "$output" | grep -q "$expected"; then
    echo "  ✓ $description"
  else
    echo "  ✗ FAIL: $description — 输出中未找到 '$expected'"
    echo "  实际输出:"
    echo "$output"
    exit 1
  fi
}

# =============================================================================
# [0/9] 环境检查
# =============================================================================
step "[0/9] 环境检查"

if ! command -v python &> /dev/null; then
  echo "错误：未找到 python 命令。请激活 venv。"
  exit 1
fi

if ! python -m mindforge --help &> /dev/null; then
  echo "错误：mindforge 未安装。请运行: pip install -e ."
  exit 1
fi

if [[ ! -f "$DOGFOOD_CONFIG" ]]; then
  echo "错误：dogfood config 不存在: $DOGFOOD_CONFIG"
  exit 1
fi

echo "  ✓ python 可用"
echo "  ✓ mindforge 可用"
echo "  ✓ dogfood config 存在: $DOGFOOD_CONFIG"

# =============================================================================
# [1/9] 清理上次残留
# =============================================================================
step "[1/9] 清理上次残留"

rm -rf "$VAULT" "$STATE"
echo "  ✓ 已清理 $VAULT"
echo "  ✓ 已清理 $STATE"

# =============================================================================
# [2/9] 创建 workspace 目录结构
# =============================================================================
step "[2/9] 创建 workspace 目录结构"

mkdir -p "$INBOX"
mkdir -p "$CARDS"
echo "  ✓ $INBOX"
echo "  ✓ $CARDS"

# =============================================================================
# [3/9] 写入非敏感 sample markdown
# =============================================================================
step "[3/9] 写入非敏感 sample markdown"

cat > "$INBOX/test-knowledge.md" << 'MDEOF'
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

echo "  ✓ 已写入: $INBOX/test-knowledge.md"

# =============================================================================
# [4/9] scan — 扫描 inbox
# =============================================================================
step "[4/9] scan — 扫描 inbox"

scan_output=$(python -m mindforge scan --config "$DOGFOOD_CONFIG" 2>&1)
echo "$scan_output"
echo "  ✓ scan 完成"

# =============================================================================
# [5/9] process — fake provider 生成 ai_draft
# =============================================================================
step "[5/9] process — fake provider 生成 ai_draft（不发起 HTTP 请求）"

process_output=$(python -m mindforge process --config "$DOGFOOD_CONFIG" 2>&1)
echo "$process_output"
assert_contains "$process_output" "ai_draft" "卡片 status 为 ai_draft"
echo "  ✓ process 完成，ai_draft 已生成"

# =============================================================================
# [6/9] 验证 R4：ai_draft 未被自动提升为 human_approved
# =============================================================================
step "[6/9] 验证 R4 安全边界：ai_draft 未被自动提升"

# approve list 默认只显示 ai_draft 状态的卡片
draft_list=$(python -m mindforge approve list --config "$DOGFOOD_CONFIG" --format json 2>&1)
echo "$draft_list"

# 确认有 ai_draft 卡片
draft_count=$(echo "$draft_list" | python -c "import sys,json; data=json.load(sys.stdin); print(data.get('count', 0))" 2>&1)
if [[ "$draft_count" -gt 0 ]]; then
  echo "  [OK] ai_draft card count: $draft_count (not auto-promoted to human_approved)"
else
  echo "  ✗ FAIL: 未找到 ai_draft 卡片"
  exit 1
fi

# 确认 library 中还没有已审批卡片（process 不应自动 approve）
library_output=$(python -m mindforge library list --config "$DOGFOOD_CONFIG" 2>&1)
echo "$library_output"
if echo "$library_output" | grep -q "暂无"; then
  echo "  ✓ library 中暂无已审批卡片（确认 process 没有自动 approve）"
else
  # 尝试统计行数来估算卡片数，如果没有"暂无"就认为可能有卡片
  echo "  ✗ FAIL: library 中已有卡片 — process 可能自动 approve 了"
  exit 1
fi

# =============================================================================
# [7/9] approve — 显式人工确认
# =============================================================================
step "[7/9] approve --confirm — 显式人工确认（必须 --confirm）"

approve_output=$(python -m mindforge approve --all --confirm --config "$DOGFOOD_CONFIG" 2>&1)
echo "$approve_output"
assert_contains "$approve_output" "human_approved" "卡片已晋升为 human_approved"
echo "  ✓ approve 完成"

# =============================================================================
# [8/9] 确认卡片已进入 library
# =============================================================================
step "[8/9] 确认卡片已进入 library（human_approved）"

library_output=$(python -m mindforge library list --config "$DOGFOOD_CONFIG" 2>&1)
echo "$library_output"
# library list 没有 --format json；存在已审批卡片时不输出"暂无"
if echo "$library_output" | grep -q "暂无"; then
  echo "  ✗ FAIL: approve 后 library 仍为空"
  exit 1
else
  echo "  ✓ library 中已有已审批卡片（human_approved 确认）"
fi

# =============================================================================
# [9/9] index rebuild → recall 检索
# =============================================================================
step "[9/9] index rebuild → recall 检索"

echo "--- index rebuild ---"
rebuild_output=$(python -m mindforge index rebuild --config "$DOGFOOD_CONFIG" 2>&1)
echo "$rebuild_output"
echo "  ✓ index rebuild 完成"

echo ""
echo "--- recall --query 'checkpoint runtime' ---"
recall_output=$(python -m mindforge recall --query "checkpoint runtime" --config "$DOGFOOD_CONFIG" 2>&1)
echo "$recall_output"

# 验证 recall 返回了结果（非空）
if echo "$recall_output" | grep -q "没有匹配的卡片"; then
  echo "  ✗ FAIL: recall 返回 0 条结果"
  exit 1
else
  echo "  ✓ recall 返回了匹配结果（检索正常）"
fi

# =============================================================================
# 完成
# =============================================================================
echo ""
echo "=========================================="
echo " Dogfood smoke 全部通过"
echo "=========================================="
echo ""
echo " 覆盖步骤："
echo "   ✓ 环境检查"
echo "   ✓ 清理残留 → 创建 workspace → 写入 sample markdown"
echo "   ✓ scan → process（fake provider, ai_draft）"
echo "   ✓ R4 验证：ai_draft 未被自动提升"
echo "   ✓ approve --confirm（human_approved）"
echo "   ✓ library 确认"
echo "   ✓ index rebuild → recall"
echo ""
echo " 安全确认："
echo "   - 零网络请求"
echo "   - 零 API key"
echo "   - 零 .env 读取"
echo "   - 零真实私人资料"
echo "   - 零真实 Obsidian vault 写入"
echo ""
echo " 临时文件保留在 /tmp 下，可手动检查："
echo "   vault: $VAULT"
echo "   state: $STATE"
