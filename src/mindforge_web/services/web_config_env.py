"""Dotenv detection utilities extracted from web_config_service.py.

中文学习型说明：env 文件检测逻辑自成一体 — 找到 .env 文件、解析其中的 key、
判断某个 env name 是否已配置。将这些纯函数从 WebConfigService 中提取出来，
减少 web_config_service.py 的职责范围，同时让 env 检测逻辑可以独立测试。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DotenvPresence:
    """.env 文件存在性及其中的 key 集合（仅 key 名，不含 value）。"""

    path: Path | None
    keys: frozenset[str]


def find_dotenv_file(start: Path) -> Path | None:
    """从 start 目录向上搜索 .env 文件，返回找到的第一个路径。"""
    cur = start.resolve()
    for path in (cur, *cur.parents):
        candidate = path / ".env"
        if candidate.is_file():
            return candidate
    return None


def parse_env_key(line: str) -> str | None:
    """从 .env 文件的一行中解析出 key 名称。

    跳过空行、注释行、不含 '=' 的行。
    支持 'export KEY=value' 格式。
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, _sep, _value = stripped.partition("=")
    key = key.removeprefix("export ").strip()
    return key if key.isidentifier() else None


def read_dotenv_presence(cwd: Path) -> DotenvPresence:
    """读取当前工作目录及其父目录中的 .env 文件。”

    返回 DotenvPresence，包含文件路径和解析出的 key 集合。
    不读取 key 的 value — 这保持了 secret-safe 语义。
    """
    path = find_dotenv_file(cwd)
    if path is None:
        return DotenvPresence(path=None, keys=frozenset())
    keys: set[str] = set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return DotenvPresence(path=path, keys=frozenset())
    for line in text.splitlines():
        parsed = parse_env_key(line)
        if parsed:
            keys.add(parsed)
    return DotenvPresence(path=path, keys=frozenset(keys))


def env_present(env_name: str | None, cwd: Path) -> bool:
    """判断给定的 env name 是否已在环境变量或 .env 文件中配置。"""
    if not env_name:
        return False
    dotenv = read_dotenv_presence(cwd)
    return env_name in os.environ or env_name in dotenv.keys
