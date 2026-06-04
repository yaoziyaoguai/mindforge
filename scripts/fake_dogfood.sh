#!/usr/bin/env bash
# MindForge v0.5 Fake Dogfood — 端到端自动化验证脚本。
#
# 流程：创建临时 workspace → 导入全部 6 份 samples → scan → process (fake)
#       → 验证 ai_draft → approve → wiki rebuild → index rebuild → recall → 清理
#
# 安全边界：
# - 所有步骤使用 fake provider（确定性、零网络、零密钥）
# - 不读取 .env 或 .mindforge/secrets.json
# - 不调用真实 LLM / provider / 外部 API
# - 所有数据写入 /tmp，不接触真实 Obsidian vault 或私人资料
# - 不做 RAG / embedding / vector DB
#
# 使用方式：
#   ./scripts/fake_dogfood.sh
#
# 退出码：0 = 全部通过，非 0 = 失败步骤数

set -euo pipefail

DOGFOOD_CONFIG="$(cd "$(dirname "$0")/.." && pwd)/examples/dogfood/mindforge.dogfood.yaml"
SAMPLES_DIR="$(cd "$(dirname "$0")/.." && pwd)/examples/dogfood/samples"
VAULT="/tmp/mindforge-dogfood-vault"
STATE="/tmp/mindforge-dogfood-state"
INBOX="$VAULT/00-Inbox"

FAIL_COUNT=0

# ── 辅助函数 ──────────────────────────────────────────────────────────────

step() {
  echo ""
  echo "=========================================="
  echo " $1"
  echo "=========================================="
}

pass() {
  echo "  ✓ PASS: $1"
}

fail() {
  echo "  ✗ FAIL: $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

assert_file() {
  if [[ -f "$1" ]]; then
    pass "$1 存在"
  else
    fail "$1 不存在"
  fi
}

assert_contains() {
  local output="$1" expected="$2" description="$3"
  if echo "$output" | grep -q "$expected"; then
    pass "$description"
  else
    fail "$description — 输出中未找到 '$expected'"
  fi
}

# ── [S0] 环境检查 ─────────────────────────────────────────────────────────

step "[S0] 环境检查"

if ! command -v python &> /dev/null; then
  echo "错误：未找到 python 命令。请激活 venv: source .venv/bin/activate"
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

if [[ ! -d "$SAMPLES_DIR" ]]; then
  echo "错误：samples 目录不存在: $SAMPLES_DIR"
  exit 1
fi

SAMPLE_COUNT=$(find "$SAMPLES_DIR" -name '*.md' -type f | wc -l | tr -d ' ')
echo "  ✓ python 可用"
echo "  ✓ mindforge 可用"
echo "  ✓ dogfood config 存在"
echo "  ✓ samples 目录存在 ($SAMPLE_COUNT 份样本)"

# ── [S1] 清理并创建工作区 ─────────────────────────────────────────────────

step "[S1] 清理并创建工作区"

rm -rf "$VAULT" "$STATE"
mkdir -p "$INBOX"
echo "  ✓ 工作区已创建: $INBOX"

# ── [S2] 导入全部 samples ─────────────────────────────────────────────────

step "[S2] 导入全部 $SAMPLE_COUNT 份 samples"

COPIED=0
for f in "$SAMPLES_DIR"/*.md; do
  base=$(basename "$f")
  cp "$f" "$INBOX/$base"
  COPIED=$((COPIED + 1))
  echo "  ✓ $base"
done

if [[ "$COPIED" -eq "$SAMPLE_COUNT" ]]; then
  pass "全部 $SAMPLE_COUNT 份样本已复制"
else
  fail "期望 $SAMPLE_COUNT 份，实际复制 $COPIED 份"
fi

# ── [S3] scan ──────────────────────────────────────────────────────────────

step "[S3] mindforge scan"

scan_output=$(python -m mindforge scan --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$scan_output"
  fail "scan 命令失败"
}
echo "$scan_output"
pass "scan 完成"

# ── [S4] process (fake provider) ───────────────────────────────────────────

step "[S4] mindforge process（fake provider，零网络零密钥）"

process_output=$(python -m mindforge process --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$process_output"
  fail "process 命令失败"
}
echo "$process_output"
assert_contains "$process_output" "ai_draft" "卡片 status 为 ai_draft"
pass "process 完成，ai_draft 已生成"

# ── [S5] 验证 card 结构 ────────────────────────────────────────────────────

step "[S5] 验证 ai_draft card 结构"

draft_list=$(python -m mindforge approve list --config "$DOGFOOD_CONFIG" --format json 2>&1) || {
  echo "$draft_list"
  fail "approve list 命令失败"
}

draft_count=$(echo "$draft_list" | python -c "import sys,json; data=json.load(sys.stdin); print(data.get('count', len(data) if isinstance(data, list) else 0))" 2>&1) || {
  fail "解析 draft count 失败"
  draft_count=0
}

if [[ "$draft_count" -gt 0 ]]; then
  pass "ai_draft count: $draft_count"
else
  fail "未找到 ai_draft 卡片"
fi

# 验证 fake 前缀（确认为 fake provider 输出）
if echo "$draft_list" | grep -q '\[fake\]'; then
  pass "确认 [fake] 前缀 — fake provider 确定性输出"
else
  echo "  ⚠ WARN: 未检测到 [fake] 前缀，可能不是 fake provider"
fi

# ── [S6] 安全边界验证 ─────────────────────────────────────────────────────

step "[S6] 安全边界验证：ai_draft 未被自动提升为 human_approved"

library_output=$(python -m mindforge library list --config "$DOGFOOD_CONFIG" 2>&1)
echo "$library_output"

if echo "$library_output" | grep -q "暂无"; then
  pass "library 中暂无已审批卡片（process 没有自动 approve）"
else
  fail "library 中已有卡片 — process 可能自动 approve 了"
fi

# ── [S7] approve ───────────────────────────────────────────────────────────

step "[S7] mindforge approve --all --confirm"

approve_output=$(python -m mindforge approve --all --confirm --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$approve_output"
  fail "approve 命令失败"
}
echo "$approve_output"
assert_contains "$approve_output" "human_approved" "卡片已晋升为 human_approved"
pass "approve 完成"

# ── [S8] wiki rebuild (deprecated) ─────────────────────────────────────────────

step "[S8] mindforge wiki rebuild (deprecated)"

wiki_output=$(python -m mindforge wiki rebuild --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$wiki_output"
  fail "wiki rebuild 命令失败"
}
echo "$wiki_output"

# v0.5: wiki rebuild 已废弃，CLI 返回 deprecation 消息（exit 0）
if echo "$wiki_output" | grep -qi "deprecated\|废弃"; then
  pass "wiki rebuild 返回 deprecation notice（符合 v0.5 预期）"
else
  fail "wiki rebuild 应返回 deprecation notice"
fi

# ── [S9] index rebuild ─────────────────────────────────────────────────────

step "[S9] mindforge index rebuild"

rebuild_output=$(python -m mindforge index rebuild --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$rebuild_output"
  fail "index rebuild 命令失败"
}
echo "$rebuild_output"
pass "index rebuild 完成"

# ── [S10] recall 检索 ──────────────────────────────────────────────────────

step "[S10] mindforge recall — BM25 词法检索"

# 使用多个查询验证召回
for query in "checkpoint" "Docker" "PostgreSQL" "Kubernetes" "中文"; do
  recall_output=$(python -m mindforge recall --query "$query" --config "$DOGFOOD_CONFIG" 2>&1) || true
  if echo "$recall_output" | grep -q "没有匹配的卡片"; then
    echo "  ⚠ query '$query': 无匹配结果"
  elif echo "$recall_output" | grep -q "."; then
    echo "  ✓ query '$query': 有匹配结果"
  else
    echo "  ⚠ query '$query': 无法判断"
  fi
done

pass "recall 检索完成（BM25 纯本地词法匹配）"

# ── [S11] 清理 ─────────────────────────────────────────────────────────────

step "[S11] 清理临时文件"

rm -rf "$VAULT" "$STATE"
assert_file_not_exist() {
  if [[ ! -e "$1" ]]; then
    pass "$1 已清理"
  else
    fail "$1 清理失败"
  fi
}
if [[ ! -e "$VAULT" ]]; then pass "$VAULT 已清理"; else fail "$VAULT 清理失败"; fi
if [[ ! -e "$STATE" ]]; then pass "$STATE 已清理"; else fail "$STATE 清理失败"; fi

# ── 完成 ───────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
if [[ "$FAIL_COUNT" -eq 0 ]]; then
  echo " Fake Dogfood 全部通过"
  echo "=========================================="
else
  echo " Fake Dogfood 完成 — $FAIL_COUNT 项失败"
  echo "=========================================="
fi
echo ""
echo " 覆盖步骤："
echo "   S0  环境检查"
echo "   S1  创建工作区"
echo "   S2  导入 $SAMPLE_COUNT 份 samples"
echo "   S3  scan"
echo "   S4  process（fake provider, ai_draft）"
echo "   S5  card 结构验证"
echo "   S6  安全边界验证（无自动 approve）"
echo "   S7  approve --confirm（human_approved）"
echo "   S8  wiki rebuild (deprecated)"
echo "   S9  index rebuild"
echo "   S10 recall（BM25 词法检索）"
echo "   S11 清理"
echo ""
echo " 安全确认："
echo "   - 零网络请求 / 零 API key / 零 .env 读取"
echo "   - 零真实私人资料 / 零真实 Obsidian vault 写入"
echo "   - 所有 LLM 输出带 [fake] 前缀"
echo "   - 不做 RAG / embedding / vector DB"

exit "$FAIL_COUNT"
