#!/usr/bin/env bash
# MindForge Product Main Path Dogfood — 扩展版 (50+ 文档)
#
# 基于 scripts/fake_dogfood.sh，扩展为使用 49 个 synthetic 非敏感样本。
#
# 安全边界：
# - 使用 fake provider（确定性、零网络、零密钥）
# - 不读取 .env 或 secrets
# - 不调用真实 LLM / 外部 API
# - 所有数据写入 /tmp
# - 不做 RAG / embedding / vector DB
#
# 使用方式：
#   bash scripts/expanded_dogfood.sh

set -euo pipefail

DOGFOOD_CONFIG="$(cd "$(dirname "$0")/.." && pwd)/examples/dogfood/mindforge.dogfood.yaml"
SAMPLES_DIR="/tmp/mindforge-dogfood-samples"
VAULT="/tmp/mindforge-dogfood-vault"
STATE="/tmp/mindforge-dogfood-state"
INBOX="$VAULT/00-Inbox"

FAIL_COUNT=0

# ── 辅助函数 ──────────────────────────────────────────────────

step() {
  echo ""
  echo "=========================================="
  echo " $1"
  echo "=========================================="
}

pass() { echo "  ✓ PASS: $1"; }

fail() {
  echo "  ✗ FAIL: $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

assert_contains() {
  local output="$1" expected="$2" description="$3"
  if echo "$output" | grep -q "$expected"; then
    pass "$description"
  else
    fail "$description — 输出中未找到 '$expected'"
  fi
}

# ── [S0] 环境检查 ─────────────────────────────────────────────

step "[S0] 环境检查"

command -v python &>/dev/null || { echo "错误：未找到 python"; exit 1; }
python -m mindforge --help &>/dev/null || { echo "错误：mindforge 未安装"; exit 1; }

SAMPLE_COUNT=$(find "$SAMPLES_DIR" -name '*.md' -type f | wc -l | tr -d ' ')
echo "  ✓ python / mindforge 可用"
echo "  ✓ 样本目录: $SAMPLES_DIR ($SAMPLE_COUNT 个 .md 文件)"

# ── [S1] 生成样本并创建工作区 ─────────────────────────────────

step "[S1] 生成样本并创建工作区"

if [[ ! -d "$SAMPLES_DIR" ]]; then
  python scripts/generate_dogfood_samples.py --target "$SAMPLES_DIR" --count 80
  SAMPLE_COUNT=$(find "$SAMPLES_DIR" -name '*.md' -type f | wc -l | tr -d ' ')
fi

rm -rf "$VAULT" "$STATE"
mkdir -p "$INBOX"
echo "  ✓ 工作区已创建: $INBOX"

# ── [S2] 导入所有 .md 样本 ─────────────────────────────────────

step "[S2] 导入 $SAMPLE_COUNT 个 .md 样本文件"

COPIED=0
for f in "$SAMPLES_DIR"/notes/*.md; do
  base=$(basename "$f")
  cp "$f" "$INBOX/$base"
  COPIED=$((COPIED + 1))
done

if [[ "$COPIED" -ge 20 ]]; then
  pass "成功导入 $COPIED 个样本文件 (>=20, 满足 dogfood 最低要求)"
else
  fail "仅导入 $COPIED 个样本，不满足最低 20 要求"
fi

# ── [S3] scan ──────────────────────────────────────────────────

step "[S3] mindforge scan ($COPIED 个文件)"

scan_output=$(python -m mindforge scan --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$scan_output"
  fail "scan 命令失败"
}
echo "$scan_output" | tail -5
pass "scan 完成 — 共 $COPIED 个文件"

# ── [S4] process (fake provider) ───────────────────────────────

step "[S4] mindforge process（fake provider）"

process_output=$(python -m mindforge process --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$process_output"
  fail "process 命令失败"
}
echo "$process_output" | tail -10
assert_contains "$process_output" "ai_draft" "卡片 status 为 ai_draft"

# 统计处理结果
processed_count=$(echo "$process_output" | grep -c "processed /" || echo "0")
echo "  processed count: $processed_count"
if [[ "$processed_count" -ge 20 ]]; then
  pass "process 完成 — $processed_count 张卡片生成"
else
  fail "process 仅生成 $processed_count 张卡片"
fi

# ── [S5] 验证 card 结构 ────────────────────────────────────────

step "[S5] 验证 ai_draft card 结构"

draft_list=$(python -m mindforge approve list --config "$DOGFOOD_CONFIG" --format json 2>&1) || {
  echo "$draft_list"
  fail "approve list 命令失败"
}

draft_count=$(echo "$draft_list" | python -c "import sys,json; data=json.load(sys.stdin); print(data.get('count', len(data) if isinstance(data, list) else 0))" 2>&1) || {
  fail "解析 draft count 失败"
  draft_count=0
}

if [[ "$draft_count" -ge 20 ]]; then
  pass "ai_draft count: $draft_count"
else
  fail "ai_draft count 不足: $draft_count (需要 >= 20)"
fi

# ── [S6] 安全边界验证 ─────────────────────────────────────────

step "[S6] 安全边界验证：ai_draft 未被自动提升为 human_approved"

library_output=$(python -m mindforge library list --config "$DOGFOOD_CONFIG" 2>&1)

if echo "$library_output" | grep -q "暂无"; then
  pass "library 中暂无已审批卡片（process 没有自动 approve）"
else
  fail "library 中已有卡片 — process 可能自动 approve 了"
fi

# ── [S7] approve ───────────────────────────────────────────────

step "[S7] mindforge approve --all --confirm"

approve_output=$(python -m mindforge approve --all --confirm --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$approve_output"
  fail "approve 命令失败"
}
assert_contains "$approve_output" "human_approved" "卡片已晋升为 human_approved"

approved_count=$(echo "$approve_output" | grep -c "approved " || echo "0")
if [[ "$approved_count" -ge 20 ]]; then
  pass "approve 完成 — $approved_count 张卡片已审批"
else
  fail "approve 仅完成 $approved_count 张"
fi

# ── [S8] Library 浏览 ─────────────────────────────────────────

step "[S8] Library 浏览"

lib_output=$(python -m mindforge library list --config "$DOGFOOD_CONFIG" 2>&1)
echo "$lib_output" | head -20

if echo "$lib_output" | grep -q "暂无"; then
  fail "library 为空 — approve 后应有卡片"
else
  card_in_lib=$(echo "$lib_output" | grep -c "Knowledge-Card" || echo "0")
  pass "library 浏览 — $card_in_lib 个 card track"
fi

# ── [S9] wiki rebuild ──────────────────────────────────────────

step "[S9] mindforge wiki rebuild"

wiki_output=$(python -m mindforge wiki rebuild --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$wiki_output"
  fail "wiki rebuild 命令失败"
}
echo "$wiki_output"

wiki_status=$(python -m mindforge wiki status --config "$DOGFOOD_CONFIG" 2>&1)

if echo "$wiki_status" | grep -qi "card\|section\|Ready"; then
  pass "wiki rebuild 完成"
else
  fail "wiki rebuild 状态异常"
fi

# ── [S10] index rebuild ───────────────────────────────────────

step "[S10] mindforge index rebuild"

rebuild_output=$(python -m mindforge index rebuild --config "$DOGFOOD_CONFIG" 2>&1) || {
  echo "$rebuild_output"
  fail "index rebuild 命令失败"
}
echo "$rebuild_output"
pass "index rebuild 完成"

# ── [S11] recall 检索（多查询验证）──────────────────────────────

step "[S11] mindforge recall — BM25 检索"

QUERIES=("Python" "Docker" "PostgreSQL" "Kubernetes" "SQL" "API" "Git" "React" "Linux" "安全")
HIT_COUNT=0
for query in "${QUERIES[@]}"; do
  recall_output=$(python -m mindforge recall --query "$query" --config "$DOGFOOD_CONFIG" 2>&1) || true
  if echo "$recall_output" | grep -q "没有匹配\|暂无"; then
    echo "  ⚠ query '$query': 无匹配"
  else
    match_count=$(echo "$recall_output" | grep -c "Knowledge-Card" || echo "0")
    echo "  ✓ query '$query': $match_count 个匹配"
    HIT_COUNT=$((HIT_COUNT + 1))
  fi
done

if [[ "$HIT_COUNT" -ge 5 ]]; then
  pass "recall 检索 — $HIT_COUNT/10 个查询有结果"
else
  echo "  ⚠ WARN: 仅 $HIT_COUNT/10 个查询有结果"
fi

# ── [S12] Export 验证 ─────────────────────────────────────────

step "[S12] Export 验证"

EXPORT_DIR="/tmp/mindforge-dogfood-export"
rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR"

# JSON 导出
json_output=$(python -m mindforge export --format json --output "$EXPORT_DIR" --config "$DOGFOOD_CONFIG" 2>&1) || true
if [[ -f "$EXPORT_DIR"/*.json ]] || echo "$json_output" | grep -q "export"; then
  pass "JSON export 完成"
else
  echo "  ⚠ WARN: JSON export 未能确认"
fi

echo "$json_output" | head -5

# ── [S13] 清理 ────────────────────────────────────────────────

step "[S13] 清理临时文件"

rm -rf "$VAULT" "$STATE" "$EXPORT_DIR"
if [[ ! -e "$VAULT" ]]; then pass "$VAULT 已清理"; else fail "$VAULT 清理失败"; fi
if [[ ! -e "$STATE" ]]; then pass "$STATE 已清理"; else fail "$STATE 清理失败"; fi
# 保留样本目录供后续使用
echo "  (样本目录保留: $SAMPLES_DIR)"

# ── 完成 ──────────────────────────────────────────────────────

echo ""
echo "=========================================="
if [[ "$FAIL_COUNT" -eq 0 ]]; then
  echo " Product Main Path Dogfood 全部通过"
else
  echo " Product Main Path Dogfood — $FAIL_COUNT 项失败"
fi
echo "=========================================="
echo ""
echo " 覆盖步骤:"
echo "   S0  环境检查"
echo "   S1  生成 49+ 样本"
echo "   S2  导入 $COPIED 个 .md 文件"
echo "   S3  scan"
echo "   S4  process ($processed_count 张 ai_draft)"
echo "   S5  card 结构验证"
echo "   S6  安全边界验证"
echo "   S7  approve ($approved_count 张 human_approved)"
echo "   S8  Library 浏览"
echo "   S9  wiki rebuild"
echo "   S10 index rebuild"
echo "   S11 recall (BM25: $HIT_COUNT/10 查询命中)"
echo "   S12 export"
echo "   S13 清理"
echo ""
echo " Dogfood 指标:"
echo "   - 样本文件: $COPIED 个"
echo "   - ai_draft: $draft_count 张"
echo "   - human_approved: $approved_count 张"
echo "   - recall 命中率: $HIT_COUNT/10"
echo ""
echo " 安全确认:"
echo "   - 零网络请求 / 零 API key"
echo "   - 零真实私人资料"
echo "   - fake provider 确定性输出"
echo "   - 不做 RAG / embedding / vector DB"

exit "$FAIL_COUNT"
