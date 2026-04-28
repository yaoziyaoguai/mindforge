"""轻量 .env 加载器 — 静默、安全、无依赖泄漏。

设计原则
========

1. **静默**
   - 不打印任何变量名或值；只返回加载条数。
   - 不抛任何异常给上层（除非 .env 本身格式严重错乱），保证 CLI 启动鲁棒。

2. **不覆盖**
   - 已存在的环境变量（用户 ``export`` 的）优先级**高于** .env，
     避免 CI / 临时 shell 注入被 .env 覆盖。
   - 这是 12-factor 的标准约定：env > dotfile。

3. **无第三方依赖**
   - v0.1 不引入 ``python-dotenv``。.env 语法只支持最常见的：
       ``KEY=VALUE``
       ``KEY="quoted"``
       ``KEY='single'``
       ``# 注释行``
   - 不支持变量内插值 ``${OTHER}``、不支持 ``export`` 前缀、不支持多行字符串。
     v0.1 用户 .env 都是简单 ``KEY=VALUE``，足够。

4. **路径发现**
   - 默认从 ``cwd`` 向上查找最近的 ``.env``；找不到就什么也不做。
   - 永远不读 ``~/.env``、永远不读其他用户目录，避免污染。

5. **once-only guard**
   - 模块级哨兵 ``_LOADED``，多次调用只生效一次（避免在测试或多命令会话里重复加载）。
"""

from __future__ import annotations

from pathlib import Path

# 模块级哨兵：进程内只加载一次
_LOADED: bool = False


def _find_dotenv(start: Path) -> Path | None:
    """从 ``start`` 向上查找 ``.env``；返回找到的绝对路径或 ``None``。"""
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        candidate = p / ".env"
        if candidate.is_file():
            return candidate
    return None


def _parse_line(line: str) -> tuple[str, str] | None:
    """解析一行 ``.env``。注释 / 空行返回 ``None``。"""
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if "=" not in s:
        return None
    key, _, val = s.partition("=")
    key = key.strip()
    val = val.strip()
    # 去引号
    if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
        val = val[1:-1]
    if not key.isidentifier():
        return None
    return key, val


def load_dotenv_silently(
    start: Path | None = None,
    *,
    override: bool = False,
) -> int:
    """加载 .env 到 ``os.environ``。

    返回成功设置（或跳过）的条数；**永远不返回值本身、不打印任何 value**。
    多次调用只生效一次。

    Args:
        start: 起点目录（默认 cwd）。
        override: 是否允许覆盖已存在的环境变量；默认 False（env > dotfile）。
    """
    global _LOADED
    if _LOADED:
        return 0
    _LOADED = True

    import os

    base = start or Path.cwd()
    path = _find_dotenv(base)
    if path is None:
        return 0

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0

    count = 0
    for raw_line in text.splitlines():
        parsed = _parse_line(raw_line)
        if parsed is None:
            continue
        key, val = parsed
        if not override and key in os.environ:
            continue
        os.environ[key] = val
        count += 1
    return count


def reset_for_tests() -> None:
    """仅供测试用：重置 once-only guard。"""
    global _LOADED
    _LOADED = False


__all__ = ["load_dotenv_silently", "reset_for_tests"]
