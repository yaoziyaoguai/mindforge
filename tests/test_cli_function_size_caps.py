"""cli.py 函数体大小上限的架构契约。

为什么需要这个测试：
- src/mindforge/cli.py 历史上是单文件 4500+ LOC 的 Typer 命令聚合点；
  即使经过多轮 service / presenter / use-case 抽取，命令体仍可能再次膨胀。
- 我们不打算把 cli.py 拆成多个 Typer module（会破坏现有 entrypoint），
  但要防止单个函数体重新长成 300+ LOC 的 god-function。
- 这个 cap 只针对 cli.py 内部函数；不约束 service / presenter / 其他模块。

边界 / 例外：
- Typer 命令体的 ``def`` 行数被 Option 默认值占用很多，因此放宽到 200 LOC。
- 已知 borderline 函数列在 ALLOWLIST 中并附原因；新增 borderline 必须改测试，
  这就强制了一次 code review，避免静默膨胀。
"""

from __future__ import annotations

import ast
from pathlib import Path

CLI_PATH = Path(__file__).resolve().parents[1] / "src" / "mindforge" / "cli.py"

# 单函数 LOC 硬上限。超过即视为新的 god-function 必须再次拆解。
HARD_CAP = 200

# 允许略微超过 HARD_CAP 的函数 + 原因。新增条目必须显式 code review。
ALLOWLIST: dict[str, str] = {
    # 主入口；体内大量 typer.Option 默认值占行，已经把 per-item 处理抽出到
    # _process_one_result，把收尾抽出到 _finalize_process_run。
    # 主体逻辑只剩 1 个 for 循环 + 早退分支。
}


def _function_loc(node: ast.AST) -> int:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return 0
    end = getattr(node, "end_lineno", None)
    if end is None:
        return 0
    return end - node.lineno + 1


def test_cli_no_function_exceeds_hard_cap() -> None:
    src = CLI_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    offenders: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        loc = _function_loc(node)
        if loc > HARD_CAP and node.name not in ALLOWLIST:
            offenders.append((node.name, loc))

    assert not offenders, (
        "cli.py 出现 LOC 超过硬上限的函数；请抽取或显式列入 ALLOWLIST 并解释原因：\n"
        + "\n".join(f"  - {name}: {loc} LOC (cap={HARD_CAP})" for name, loc in offenders)
    )
