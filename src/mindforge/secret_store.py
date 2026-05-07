"""本地 secret store —— 将 API key 安全存储在 gitignored JSON 文件中。

中文学习型说明：SecretStore 是 API key 持久化的唯一入口，属于 core 层。
Web 层用它的 get/set/remove/masked；LLM provider 层用它的 get 来取 raw key
注入到 provider runtime。raw key 绝不出现在 API response、log、YAML、web dist。
路径 ``.mindforge/secrets.json`` 已被 .gitignore 中 ``.mindforge/`` 规则覆盖。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SecretStore:
    """按 model_id 索引的本地 API key 存储。

    调用方（WebConfigService / LLM provider）负责决定何时读/写/删除。
    本类不关心 config 语义，只保证安全读写。
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def get(self, model_id: str) -> str | None:
        """读取 raw API key；如果没有存储则返回 None。"""
        data = self._read()
        return data.get(model_id)

    def present(self, model_id: str) -> bool:
        """是否存在该 model_id 的 API key。"""
        return bool(self.get(model_id))

    def set(self, model_id: str, value: str) -> None:
        """写入 API key（覆盖已有 key）。"""
        data = self._read()
        data[model_id] = value
        self._write(data)

    def remove(self, model_id: str) -> None:
        """删除该 model_id 的 API key。"""
        data = self._read()
        data.pop(model_id, None)
        self._write(data)

    def masked(self, model_id: str) -> str | None:
        """返回脱敏后的 key，如 ``****abcd``；不存在则返回 None。

        Secret 安全边界：这是唯一允许返回给前端的 key 表示形式。
        """
        raw = self.get(model_id)
        if not raw:
            return None
        suffix = raw[-4:] if len(raw) >= 4 else raw
        prefix = "sk-" if raw.startswith("sk-") else ""
        return f"{prefix}****{suffix}"

    def all_ids(self) -> frozenset[str]:
        """返回所有已存储 model_id（用于清理 orphan key）。"""
        return frozenset(self._read().keys())

    # ------------------------------------------------------------------
    # 内部文件 I/O
    # ------------------------------------------------------------------

    def _read(self) -> dict[str, Any]:
        if not self._path.is_file():
            return {}
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(self._path)
