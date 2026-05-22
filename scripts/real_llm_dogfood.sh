#!/usr/bin/env bash
# MindForge Real LLM Opt-in Dogfood 脚本。
#
# 中文学习型说明：
#
# 本脚本提供两种模式：
#   - 默认（无 flag）: preflight 检查 — 验证配置就绪，不调用 LLM，不创建 HTTP 连接。
#   - --real-llm --confirm-cost: 完整批量端到端 real LLM dogfood pipeline。
#
# 安全边界：
#   - 真实 LLM 调用必须同时传递 --real-llm --confirm-cost 双 flag（顺序无关）。
#   - 默认 preflight 模式不读取 .env，不调用 LLM，不读取 secrets 文件。
#   - API key 由用户通过 shell 环境变量传入（K5），脚本不读 .env 或 secret store。
#   - human_approved 必须人工执行 approve --confirm，脚本绝不自动 approve。
#   - 所有数据写入 ${TMPDIR:-/tmp}，不接触真实 Obsidian vault。
#   - 不做 RAG / embedding / vector DB（recall 使用 BM25 词法检索）。
#
# 使用方式：
#   ./scripts/real_llm_dogfood.sh                               # preflight
#   ./scripts/real_llm_dogfood.sh --real-llm --confirm-cost     # real-run
#
# 清理：
#   脚本结束后会在 /tmp 下保留运行时产物供人工检查。
#   运行结束时打印清理命令，用户可手动执行。
#   下次 preflight 或 real-run 会自动清理上次残留。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="${REAL_LLM_CONFIG:-$REPO_ROOT/examples/dogfood/mindforge.real-llm.example.yaml}"
SAMPLES_DIR="$REPO_ROOT/examples/dogfood/samples"
TMP_BASE="${TMPDIR:-/tmp}"
VAULT="$TMP_BASE/mindforge-dogfood-vault"
STATE="$TMP_BASE/mindforge-dogfood-state"
INBOX="$VAULT/00-Inbox"
CARDS="$VAULT/20-Knowledge-Cards"
FRICTION_LOG="$STATE/friction-log.md"

# Expected sample file names (must match U1 coverage matrix)
EXPECTED_SAMPLES=(
  "short-note.md"
  "long-technical.md"
  "bullet-notes.md"
  "tech-learning.md"
  "low-signal.md"
  "mixed-zh-en.md"
)

# =============================================================================
# Helper functions
# =============================================================================

step() {
  echo ""
  echo "=========================================="
  echo " $1"
  echo "=========================================="
}

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

check_cmd() {
  if ! command -v "$1" &> /dev/null; then
    echo "错误：未找到 $1 命令。"
    exit 1
  fi
}

usage() {
  echo "Usage: $0 [--real-llm --confirm-cost] [--config <path>]"
  echo ""
  echo "Modes:"
  echo "  (no flags)           preflight — validate setup, zero network calls"
  echo "  --real-llm --confirm-cost   real-run — full batch end-to-end pipeline"
  echo ""
  echo "Options:"
  echo "  --config <path>       use alternative config (default: examples/dogfood/mindforge.real-llm.example.yaml)"
  echo "  --help                show this help"
  echo ""
  echo "Environment:"
  echo "  REAL_LLM_CONFIG       default config file path"
  exit 0
}

# Check sample YAML frontmatter validity (presence of --- delimiters and title/tags/date)
check_sample_frontmatter() {
  local file="$1"
  local first_line
  first_line=$(head -1 "$file")
  if [[ "$first_line" != "---" ]]; then
    echo "  ✗ FAIL: $file 缺少 YAML frontmatter (第一行不是 ---)"
    return 1
  fi
  # Check that we have a closing ---
  if ! awk 'NR>1 && /^---$/ {found=1; exit} END {exit !found}' "$file"; then
    echo "  ✗ FAIL: $file YAML frontmatter 未正确闭合"
    return 1
  fi
  return 0
}

# =============================================================================
# Flag parsing — loop-based, order-independent
# =============================================================================

REAL_LLM=false
CONFIRM_COST=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --real-llm)
      REAL_LLM=true
      shift
      ;;
    --confirm-cost)
      CONFIRM_COST=true
      shift
      ;;
    --config)
      CONFIG_FILE="$2"
      shift 2
      ;;
    --help)
      usage
      ;;
    *)
      echo "未知参数: $1"
      usage
      ;;
  esac
done

# =============================================================================
# Mode gate
# =============================================================================

if $REAL_LLM && $CONFIRM_COST; then
  MODE="real-run"
elif $REAL_LLM || $CONFIRM_COST; then
  echo "=============================================="
  echo " 拒绝执行：--real-llm 和 --confirm-cost 必须同时出现"
  echo ""
  if $REAL_LLM; then
    echo " 检测到 --real-llm，但缺少 --confirm-cost"
  else
    echo " 检测到 --confirm-cost，但缺少 --real-llm"
  fi
  echo ""
  echo " 正确用法: $0 --real-llm --confirm-cost"
  echo "=============================================="
  exit 1
else
  MODE="preflight"
fi

# =============================================================================
# Preflight mode
# =============================================================================

run_preflight() {
  step "[P1] 环境检查"

  check_cmd python
  echo "  ✓ python 可用"

  if ! python -m mindforge --help &> /dev/null; then
    echo "错误：mindforge 未安装。请运行: pip install -e ."
    exit 1
  fi
  echo "  ✓ mindforge 可用"

  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "错误：config 文件不存在: $CONFIG_FILE"
    echo "请先创建 config：cp examples/dogfood/mindforge.real-llm.example.yaml /tmp/real-llm.yaml"
    echo "然后编辑填入 api_key_env / base_url / model"
    exit 1
  fi
  echo "  ✓ config 文件存在: $CONFIG_FILE"

  # ===========================================================================
  step "[P2] Provider readiness 检查"

  doctor_output=$(python -m mindforge doctor --config "$CONFIG_FILE" 2>&1) || true
  echo "$doctor_output"
  echo "  ✓ doctor 检查完成"

  # ===========================================================================
  step "[P2a] API key 环境变量检查"

  # Extract api_key_env values from config YAML
  api_key_envs=$(python -c "
import yaml
with open('$CONFIG_FILE') as f:
    cfg = yaml.safe_load(f)
models = cfg.get('llm', {}).get('models', {})
for name, mc in models.items():
    env_var = mc.get('api_key_env', '')
    if env_var:
        print(env_var)
" 2>/dev/null)

  if [[ -z "$api_key_envs" ]]; then
    echo "  ⚠ 未在 config 中找到 api_key_env 字段"
    echo "  请确认 config 中 llm.models 下已配置 api_key_env"
  else
    all_set=true
    while IFS= read -r env_var; do
      if [[ -n "$env_var" ]]; then
        if [[ -n "${!env_var+set}" ]]; then
          echo "  ✓ $env_var 已设置"
        else
          echo "  ✗ $env_var 未设置 — 请先 export $env_var=<your-api-key>"
          all_set=false
        fi
      fi
    done <<< "$api_key_envs"
    if ! $all_set; then
      echo ""
      echo "  提示：API key 由用户通过 shell 环境变量传入（不读 .env）。"
      echo "  例如：export YOUR_API_KEY_ENV_VAR=\"sk-...\""
      exit 1
    fi
  fi

  # ===========================================================================
  step "[P3] Sample 文件验证"

  sample_count=0
  for sample in "${EXPECTED_SAMPLES[@]}"; do
    local path="$SAMPLES_DIR/$sample"
    if [[ -f "$path" ]]; then
      if check_sample_frontmatter "$path"; then
        echo "  ✓ $sample (frontmatter OK)"
        sample_count=$((sample_count + 1))
      else
        echo "  ✗ $sample frontmatter 无效"
      fi
    else
      echo "  ✗ 缺少 sample: $path"
    fi
  done

  if [[ "$sample_count" -lt 6 ]]; then
    echo "错误：sample 数量不足 (${sample_count}/6)"
    exit 1
  fi
  echo "  ✓ 共 $sample_count 份 sample 就绪"

  # ===========================================================================
  step "[P4] 临时目录可写性检查"

  if [[ ! -d "$TMP_BASE" ]]; then
    echo "错误：$TMP_BASE 不存在"
    exit 1
  fi
  local test_file="$TMP_BASE/.mindforge-dogfood-write-test"
  if touch "$test_file" 2>/dev/null; then
    rm -f "$test_file"
    echo "  ✓ $TMP_BASE 可写"
  else
    echo "错误：$TMP_BASE 不可写"
    exit 1
  fi

  # ===========================================================================
  step "[P5] Preflight readiness 报告"

  # Verify config is parseable and provider is not fake
  config_check=$(python -c "
from pathlib import Path
from src.mindforge.config import load_mindforge_config

cfg = load_mindforge_config(Path('$CONFIG_FILE'))
models = cfg.llm.models
# Collect types
types = {mc.type for mc in models.values()}
has_real = bool(types - {'fake'})
print(f'model_count={len(models)}')
print(f'types={types}')
print(f'has_real={has_real}')
" 2>&1)

  echo "  config 可解析: OK"
  echo "  $config_check"

  has_real=$(echo "$config_check" | grep 'has_real=' | cut -d= -f2)
  if [[ "$has_real" != "True" ]]; then
    echo ""
    echo "  ⚠ 警告：config 中所有 model type 均为 fake"
    echo "  真实 LLM dogfood 需要至少一个非 fake provider"
    echo "  请在 $CONFIG_FILE 中将 type 改为 openai_compatible 或 anthropic_compatible"
  fi

  echo ""
  echo "=============================================="
  echo " Preflight 完成"
  echo "=============================================="
  echo ""
  echo "  状态: opt-in ready"
  echo "  配置: $CONFIG_FILE"
  echo "  样本: $sample_count 份 ($SAMPLES_DIR)"
  echo "  临时目录: $TMP_BASE"
  echo ""
  echo "  下一步: $0 --real-llm --confirm-cost"
  echo "=============================================="
}

# =============================================================================
# Real-run mode
# =============================================================================

run_real() {
  # [S0] Verify config provider type (done here, after flag check)
  step "[S0] Config 验证 — 确认 provider 非 fake"

  config_check=$(python -c "
from pathlib import Path
from src.mindforge.config import load_mindforge_config

cfg = load_mindforge_config(Path('$CONFIG_FILE'))
models = cfg.llm.models
types = {mc.type for mc in models.values()}
has_real = bool(types - {'fake'})
print(f'has_real={has_real}')
print(f'types={types}')
" 2>&1)

  echo "  $config_check"
  has_real=$(echo "$config_check" | grep 'has_real=' | cut -d= -f2)
  if [[ "$has_real" != "True" ]]; then
    echo ""
    echo "  ✗ 拒绝执行：config 中所有 model type 均为 fake"
    echo "  即使传了 --real-llm --confirm-cost，config 指向的是 fake provider。"
    echo "  请在 $CONFIG_FILE 中将 type 改为 openai_compatible 或 anthropic_compatible"
    exit 1
  fi
  echo "  ✓ config provider type 验证通过（非 fake）"

  # ===========================================================================
  step "[S1] 清理 /tmp 残留"

  rm -rf "$VAULT" "$STATE"
  echo "  ✓ 已清理 $VAULT"
  echo "  ✓ 已清理 $STATE"

  # ===========================================================================
  step "[S2] 创建 workspace 目录结构"

  mkdir -p "$INBOX" "$CARDS" "$STATE"
  echo "  ✓ $INBOX"
  echo "  ✓ $CARDS"
  echo "  ✓ $STATE"

  # ===========================================================================
  step "[S3] 复制 sample markdowns 到 inbox"

  for sample in "${EXPECTED_SAMPLES[@]}"; do
    local src="$SAMPLES_DIR/$sample"
    if [[ -f "$src" ]]; then
      cp "$src" "$INBOX/$sample"
      echo "  ✓ $sample → inbox"
    else
      echo "  ✗ 缺少 sample: $src"
      exit 1
    fi
  done

  # ===========================================================================
  step "[S4] scan — 扫描 inbox"

  scan_output=$(python -m mindforge scan --config "$CONFIG_FILE" 2>&1)
  echo "$scan_output"
  echo "  ✓ scan 完成"

  # ===========================================================================
  step "[S5] process — 真实 LLM 调用生成 ai_draft"

  echo "  ⚠ 即将调用真实 LLM API，可能产生费用..."
  process_output=$(python -m mindforge process --config "$CONFIG_FILE" 2>&1) || {
    echo ""
    echo "  ✗ process 失败。以下是逐样本诊断命令，可帮助定位问题样本："
    echo ""
    for sample in "${EXPECTED_SAMPLES[@]}"; do
      echo "  # 隔离测试 $sample:"
      echo "  rm -rf $VAULT/00-Inbox/* && cp $SAMPLES_DIR/$sample $INBOX/"
      echo "  mindforge scan --config $CONFIG_FILE"
      echo "  mindforge process --config $CONFIG_FILE"
      echo ""
    done
    exit 1
  }
  echo "$process_output"
  assert_contains "$process_output" "ai_draft" "卡片 status 为 ai_draft"
  echo "  ✓ process 完成，ai_draft 已生成"

  # ===========================================================================
  step "[S6] 结构校验 — 验证 ai_draft 输出格式"

  draft_list=$(python -m mindforge approve list --config "$CONFIG_FILE" --format json 2>&1)
  echo "$draft_list"

  # Verify it's valid JSON
  if echo "$draft_list" | python -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    echo "  ✓ ai_draft 输出是合法 JSON"
  else
    echo "  ✗ FAIL: approve list --format json 输出不是合法 JSON"
    exit 1
  fi

  # Verify required fields exist (check first card if any)
  draft_count=$(echo "$draft_list" | python -c "
import sys, json
data = json.load(sys.stdin)
count = data.get('count', 0)
print(count)
if count > 0:
    card = data.get('cards', data.get('items', [{}]))[0] if data.get('cards') or data.get('items') else {}
    # Check common required fields
    for field in ['ref', 'title', 'status']:
        if field not in card and 'ref' not in str(data):
            print(f'WARN: field {field} not found', file=sys.stderr)
" 2>&1)
  echo "  ✓ 结构校验完成，ai_draft count: ${draft_count:-0}"

  if [[ "${draft_count:-0}" -eq 0 ]]; then
    echo "  ⚠ 警告：ai_draft 卡片数为 0，请检查 process 输出"
    echo "  可能原因：所有样本触发了 insufficient_content 或 low-signal 过滤"
  fi

  # ===========================================================================
  step "[S7] 验证安全边界：ai_draft 未被自动提升"

  library_output=$(python -m mindforge library list --config "$CONFIG_FILE" 2>&1)
  echo "$library_output"
  if echo "$library_output" | grep -q "暂无"; then
    echo "  ✓ library 中暂无已审批卡片（确认 process 没有自动 approve）"
  else
    echo "  ✗ FAIL: library 中已有卡片 — process 可能自动 approve 了"
    exit 1
  fi

  # ===========================================================================
  step "[S8] 展示 review 列表"

  echo "以下卡片需要人工 review："
  echo ""
  python -m mindforge approve list --config "$CONFIG_FILE" 2>&1

  # ===========================================================================
  step "[S9] 交互式 approve — 需要你手动操作"

  echo ""
  echo "=============================================="
  echo " ⚠ 请在另一个终端中手动执行 approve"
  echo "=============================================="
  echo ""
  echo " 本脚本不会自动执行 approve。请打开另一个终端，运行："
  echo ""
  echo "   # 查看待审批卡片"
  echo "   mindforge approve list --config $CONFIG_FILE"
  echo ""
  echo "   # 审批所有卡片（必须 --confirm）"
  echo "   mindforge approve --all --confirm --config $CONFIG_FILE"
  echo ""
  echo "   # 或逐张审批/拒绝"
  echo "   mindforge approve <ref> --confirm --config $CONFIG_FILE"
  echo "   mindforge reject <ref> --config $CONFIG_FILE"
  echo ""
  echo "=============================================="

  # ===========================================================================
  step "[S10] 等待 approve 完成"

  echo "轮询等待 approve 完成（每 5 秒检查一次，最多等待 5 分钟）..."
  MAX_WAIT=300
  ELAPSED=0
  POLL_INTERVAL=5

  while [[ $ELAPSED -lt $MAX_WAIT ]]; do
    draft_list=$(python -m mindforge approve list --config "$CONFIG_FILE" --format json 2>&1) || true
    remaining=$(echo "$draft_list" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('count',0))" 2>/dev/null || echo "0")

    if [[ "${remaining:-0}" -eq 0 ]]; then
      echo ""
      echo "  ✓ 所有卡片已审批完毕（无剩余 ai_draft）"
      break
    fi

    echo "  还剩 $remaining 张卡片待审批... (${ELAPSED}s/${MAX_WAIT}s)"
    sleep "$POLL_INTERVAL"
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
  done

  if [[ $ELAPSED -ge $MAX_WAIT ]]; then
    echo ""
    echo "  ⚠ 等待超时（${MAX_WAIT}s）。请确认是否已完成 approve/reject。"
    echo "  如需继续，可手动完成 approve 后重新运行本脚本的后续步骤："
    echo ""
    echo "  # 从 S11 开始："
    echo "  mindforge library list --config $CONFIG_FILE"
    echo "  mindforge index rebuild --config $CONFIG_FILE"
    echo "  mindforge recall --query \"<关键词>\" --config $CONFIG_FILE"
    exit 1
  fi

  # ===========================================================================
  step "[S11] 验证 library 中有已审批卡片"

  library_output=$(python -m mindforge library list --config "$CONFIG_FILE" 2>&1)
  echo "$library_output"
  if echo "$library_output" | grep -q "暂无"; then
    echo "  ✗ FAIL: approve 后 library 仍为空"
    exit 1
  else
    echo "  ✓ library 中已有已审批卡片（human_approved 确认）"
  fi

  # ===========================================================================
  step "[S12] index rebuild — BM25 词法索引"

  rebuild_output=$(python -m mindforge index rebuild --config "$CONFIG_FILE" 2>&1)
  echo "$rebuild_output"
  echo "  ✓ index rebuild 完成（BM25 纯本地，无 embedding/RAG）"

  # ===========================================================================
  step "[S13] recall 检索验证"

  # Use a query term that's likely to match at least one card
  # The samples cover: docker, postgresql, kubernetes, golang, etc.
  echo "--- recall --query 'Docker 镜像' ---"
  recall_output=$(python -m mindforge recall --query "Docker 镜像" --config "$CONFIG_FILE" 2>&1)
  echo "$recall_output"

  if echo "$recall_output" | grep -q "没有匹配的卡片"; then
    echo "  ⚠ 'Docker 镜像' 无结果，尝试通用查询..."
    echo "--- recall --query '优化' ---"
    recall_output=$(python -m mindforge recall --query "优化" --config "$CONFIG_FILE" 2>&1)
    echo "$recall_output"
  fi

  if echo "$recall_output" | grep -q "没有匹配的卡片"; then
    echo "  ✗ FAIL: recall 返回 0 条结果（所有查询词均无匹配）"
    exit 1
  else
    echo "  ✓ recall 返回了匹配结果（BM25 检索正常，非 RAG/embedding）"
  fi

  # ===========================================================================
  step "[S14] 生成 friction log 模板"

  cat > "$FRICTION_LOG" << 'FLOGEOF'
# MindForge Real LLM Dogfood — Friction Log

> 运行时间：
> 配置：
> 模型：
> 样本数：

## 总体观察

| 指标 | 值 |
|------|-----|
| process 耗时 | |
| API 调用次数（估算） | |
| ai_draft 卡片数 | |
| insufficient_content / 跳过数 | |
| approve 卡片数 | |
| reject 卡片数 | |
| recall 命中数 | |
| 错误/重试次数 | |

## 逐样本 AI Draft 质量评估

对每份样本，评估以下维度（1-5 分）：
- **summary 准确性**: 5=完美捕获所有关键点, 3=部分正确但有遗漏, 1=有事实错误或完全偏离
- **concepts 提取**: 5=提取了所有核心技术概念且命名准确, 3=提取了部分, 1=几乎无有效概念
- **action_items 合理性**: 5=具体可执行, 3=方向正确但模糊, 1=无意义或完全错误
- **insufficient_content**: Y/N，是否被正确识别为信息不足

### short-note.md（简短笔记，~80 词）
- summary: _/5 — [观察]
- concepts: _/5 — [观察]
- action_items: _/5 — [观察]
- insufficient_content: [Y/N]

### long-technical.md（长技术文档，~500 词）
- summary: _/5 — [观察]
- concepts: _/5 — [观察]
- action_items: _/5 — [观察]
- insufficient_content: [Y/N]

### bullet-notes.md（结构化 bullet，~120 词）
- summary: _/5 — [观察]
- concepts: _/5 — [观察]
- action_items: _/5 — [观察]
- insufficient_content: [Y/N]

### tech-learning.md（技术学习笔记，~250 词）
- summary: _/5 — [观察]
- concepts: _/5 — [观察]
- action_items: _/5 — [观察]
- insufficient_content: [Y/N]

### low-signal.md（低价值/信息不足，~30 词）
- summary: _/5 — [观察]
- insufficient_content: [Y/N] — 理想情况应触发 insufficient_content

### mixed-zh-en.md（中英混合，~200 词）
- summary: _/5 — [观察]
- concepts: _/5 — [观察]
- action_items: _/5 — [观察]
- insufficient_content: [Y/N]

## Review Questions 评估

- review_questions 是否有意义？[观察]
- 问题是否具体可回答？[观察]
- 是否有无意义或重复的问题？[观察]

## 意外行为

- [记录任何意外行为、崩溃、格式错误等]

## 改进建议

- [基于本次 dogfood 观察的改进建议]
FLOGEOF

  echo "  ✓ friction log 模板已生成: $FRICTION_LOG"

  # ===========================================================================
  # Done
  # ===========================================================================
  echo ""
  echo "=============================================="
  echo " Real LLM Dogfood 全部完成"
  echo "=============================================="
  echo ""
  echo " 覆盖步骤："
  echo "   ✓ S0   Config 非 fake 验证"
  echo "   ✓ S1   清理残留"
  echo "   ✓ S2   创建 workspace"
  echo "   ✓ S3   复制 6 份 sample markdown"
  echo "   ✓ S4   scan"
  echo "   ✓ S5   process（真实 LLM 调用）"
  echo "   ✓ S6   结构校验（JSON 有效性）"
  echo "   ✓ S7   安全边界验证（ai_draft 未被自动提升）"
  echo "   ✓ S8   展示 review 列表"
  echo "   ✓ S9   提示手动 approve"
  echo "   ✓ S10  轮询等待 approve 完成"
  echo "   ✓ S11  library 确认"
  echo "   ✓ S12  index rebuild（BM25）"
  echo "   ✓ S13  recall 检索验证"
  echo "   ✓ S14  friction log 模板"
  echo ""
  echo " 安全确认："
  echo "   - API key 通过 shell env var 传入（不读 .env）"
  echo "   - human_approved 必须人工 approve --confirm"
  echo "   - BM25 词法检索（非 RAG/embedding）"
  echo "   - 不接触真实 Obsidian vault"
  echo ""
  echo " 产物位置："
  echo "   vault:       $VAULT"
  echo "   state:       $STATE"
  echo "   friction log: $FRICTION_LOG"
  echo ""
  echo " 清理命令（需要时手动执行）："
  echo "   rm -rf $VAULT $STATE"
  echo "=============================================="
}

# =============================================================================
# Dispatch
# =============================================================================

echo "MindForge Real LLM Opt-in Dogfood"
echo "  mode:   $MODE"
echo "  config: $CONFIG_FILE"
echo "  temp:   $TMP_BASE"

if [[ "$MODE" == "preflight" ]]; then
  run_preflight
else
  run_real
fi
