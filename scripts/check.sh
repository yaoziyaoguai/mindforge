#!/usr/bin/env bash
# MindForge 本地 push 前 safety gate。
#
# 中文学习型说明：
#
# 为什么需要这个脚本：
# - 之前 Agent 报告曾出现 "全部 passed" 但命令实际已 timeout / exit code 丢失的情况。
# - 手工逐条运行容易遗漏某一步，三条命令应该在一个入口里保证全部通过。
# - 这个脚本把所有验证整合成一个命令，exit code 明确，无法被误读。
#
# 为什么直接运行命令而不是 tail 截断输出：
# - tail / head 会吞掉 exit code，pytest 即使失败也可能被管道掩盖。
# - 直接运行命令让 shell 的原生错误传播（set -e）生效。
#
# 为什么 full pytest / ruff / diff check 都必须通过：
# - full pytest：覆盖所有测试文件，不只是某个子集。
# - ruff：确保代码风格和潜在 bug 被静态检查发现。
# - git diff --check：防止提交包含空白字符冲突（trailing whitespace、merge conflict markers）。
#
# 安全边界：
# - 本脚本不读取 .env 或 .mindforge/secrets.json。
# - 本脚本不调用真实 LLM / provider / 外部 API。
# - 所有测试默认使用 fake provider / safe local path。
# - 测试通过 tests/conftest.py 全局 autouse fixture 隔离 runtime state。
#
# 使用方式：
#   ./scripts/check.sh
#
# CI 中也运行相同的命令（见 .github/workflows/ci.yml），但本脚本是本地门禁。

set -euo pipefail

echo "=========================================="
echo " MindForge Local Push Gate"
echo "=========================================="
echo ""

# ---------------------------------------------------------------------------
# [1/3] pytest — 全量测试套件
# ---------------------------------------------------------------------------
echo "[1/3] Running pytest (full suite) ..."
python -m pytest -q
echo ""

# ---------------------------------------------------------------------------
# [2/3] ruff — 代码静态检查
# ---------------------------------------------------------------------------
echo "[2/3] Running ruff ..."
python -m ruff check src tests
echo ""

# ---------------------------------------------------------------------------
# [3/3] git diff --check — 空白字符/冲突标记检查
# ---------------------------------------------------------------------------
echo "[3/3] Running git diff --check ..."
git diff --check
echo ""

echo "=========================================="
echo " All local checks passed."
echo "=========================================="
