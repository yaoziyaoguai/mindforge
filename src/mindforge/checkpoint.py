"""state.json 读写 — MindForge v0.1 的 checkpoint 层。

设计要点
========

1. **state.json 是 v0.1 的 checkpoint，不是缓存**
   - 决定下一次 ``process`` 跳过哪些文件、回放哪些文件、回填哪些状态。
   - 写入必须**原子**：先写 ``.tmp`` 再 ``rename``，避免中途崩溃半写。
   - 可选保留 ``.bak``：每次成功写入前备份上一份。

2. **复合 key**
   - ``"<source_type>::<source_path>"``，把多源情况下"同名 plain.md vs cubox/plain.md"
     这种冲突直接消灭在 key 层。

3. **本模块不做业务判断**
   - 不决定"什么时候算 skipped"、"value_score 多少算低"——这些由 Triager 决定。
   - 它只是个"安全的 KV 存储 + 序列化"。
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .models import ItemState, StageRecord

STATE_SCHEMA_VERSION = 1


class CheckpointError(RuntimeError):
    """checkpoint 读写失败。"""


class Checkpoint:
    """state.json 的高层封装。

    用法（M1 仅会用到 ``upsert_seen`` / ``get`` / ``all_items``）::

        cp = Checkpoint.load(state_path)
        cp.upsert_seen(item_state)
        cp.save(active_profile="default")
    """

    def __init__(
        self,
        path: Path,
        items: dict[str, ItemState],
        active_profile: str | None = None,
        provider_mode: str = "fake",
        backup: bool = True,
    ) -> None:
        self.path = path
        self.items = items
        self.active_profile = active_profile
        self.provider_mode = provider_mode
        self.backup = backup

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, path: str | Path, *, backup: bool = True) -> "Checkpoint":
        """从磁盘加载 state.json；不存在时返回空 checkpoint。"""
        p = Path(path)
        if not p.exists():
            return cls(path=p, items={}, backup=backup)

        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CheckpointError(f"state.json 解析失败：{p}: {e}") from e

        version = int(raw.get("version", 0))
        if version != STATE_SCHEMA_VERSION:
            # v0.1 不做迁移，直接报错让人决定
            raise CheckpointError(
                f"state.json schema 版本 {version} 与代码期望 {STATE_SCHEMA_VERSION} 不一致；"
                "v0.1 不做自动迁移，请人工处理"
            )

        items_raw = raw.get("items") or {}
        items: dict[str, ItemState] = {}
        for key, value in items_raw.items():
            items[key] = _item_from_dict(value)

        return cls(
            path=p,
            items=items,
            active_profile=raw.get("active_profile"),
            provider_mode=raw.get("provider_mode", "fake"),
            backup=backup,
        )

    # ----------------------------------------------------------------- save
    def save(self, *, active_profile: str | None = None, provider_mode: str | None = None) -> None:
        """原子保存。先写 .tmp 再 rename；可选写 .bak。"""
        if active_profile is not None:
            self.active_profile = active_profile
        if provider_mode is not None:
            self.provider_mode = provider_mode

        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.backup and self.path.exists():
            shutil.copy2(self.path, self.path.with_suffix(self.path.suffix + ".bak"))

        payload = {
            "version": STATE_SCHEMA_VERSION,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "active_profile": self.active_profile,
            "provider_mode": self.provider_mode,
            "items": {k: _item_to_dict(v) for k, v in self.items.items()},
        }

        # 用 NamedTemporaryFile 同目录写，再 os.replace 原子替换
        fd, tmp_path = tempfile.mkstemp(
            prefix=".state.", suffix=".tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        except Exception:
            # 写失败时清理 tmp，避免污染目录
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise

    # --------------------------------------------------------- 业务便捷接口
    def get(self, source_type: str, source_path: str) -> ItemState | None:
        return self.items.get(_compose_key(source_type, source_path))

    def upsert_seen(self, state: ItemState) -> ItemState:
        """登记 / 更新一条 item，返回最终保留的 ItemState。

        合并规则：
        - 若已存在且 ``content_hash`` 未变 → 保留旧记录的 status/track/...，
          只刷新 ``last_run_id``（如有）和 ``processed_at`` 不动；
        - 若 ``content_hash`` 变化 → 视为新版本，``status`` 重置为 ``raw``，
          清掉 stage 历史，强制下次 process 重新加工；
        - 若不存在 → 写入并把 ``status`` 置 ``raw``，``first_seen_at`` 设为 now。
        """
        key = state.state_key
        existing = self.items.get(key)
        if existing is None:
            new_state = ItemState(
                source_id=state.source_id,
                source_type=state.source_type,
                adapter_name=state.adapter_name,
                source_path=state.source_path,
                content_hash=state.content_hash,
                status="raw",
                first_seen_at=state.first_seen_at or datetime.now(),
            )
            self.items[key] = new_state
            return new_state

        if existing.content_hash == state.content_hash:
            # 没变化，保留所有历史；只可能更新 adapter_name（极少）
            if existing.adapter_name != state.adapter_name:
                existing.adapter_name = state.adapter_name
            return existing

        # 内容变化：重置加工状态，但保留 first_seen_at
        new_state = ItemState(
            source_id=state.source_id,
            source_type=state.source_type,
            adapter_name=state.adapter_name,
            source_path=state.source_path,
            content_hash=state.content_hash,
            status="raw",
            first_seen_at=existing.first_seen_at,
        )
        self.items[key] = new_state
        return new_state

    def all_items(self) -> Iterable[ItemState]:
        return self.items.values()

    def count_by_status(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for item in self.items.values():
            result[item.status] = result.get(item.status, 0) + 1
        return result

    def count_by_source_type(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for item in self.items.values():
            result[item.source_type] = result.get(item.source_type, 0) + 1
        return result


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------


def _compose_key(source_type: str, source_path: str) -> str:
    return f"{source_type}::{source_path}"


def _item_to_dict(item: ItemState) -> dict[str, Any]:
    """ItemState → JSON 可序列化 dict（datetime 转 ISO 字符串）。"""
    data = _dataclass_asdict_iso(item)
    # stages 是 dict[str, StageRecord]，asdict 会递归转 dict，但为了清晰再走一次
    stages = data.get("stages") or {}
    data["stages"] = {k: _normalize_stage(v) for k, v in stages.items()}
    return data


def _item_from_dict(data: dict[str, Any]) -> ItemState:
    stages_raw = data.get("stages") or {}
    stages: dict[str, StageRecord] = {}
    for sk, sv in stages_raw.items():
        stages[sk] = StageRecord(
            stage=sv["stage"],
            model_alias=sv["model_alias"],
            provider=sv["provider"],
            actual_model=sv["actual_model"],
            prompt_version=sv["prompt_version"],
            status=sv["status"],
            processed_at=_parse_iso(sv["processed_at"]),
            error_message=sv.get("error_message"),
            tokens_in=sv.get("tokens_in"),
            tokens_out=sv.get("tokens_out"),
            latency_ms=sv.get("latency_ms"),
        )

    return ItemState(
        source_id=data["source_id"],
        source_type=data["source_type"],
        adapter_name=data["adapter_name"],
        source_path=data["source_path"],
        content_hash=data["content_hash"],
        status=data.get("status", "raw"),
        track=data.get("track"),
        value_score=data.get("value_score"),
        card_path=data.get("card_path"),
        last_run_id=data.get("last_run_id"),
        first_seen_at=_parse_iso(data.get("first_seen_at")),
        processed_at=_parse_iso(data.get("processed_at")),
        error_message=data.get("error_message"),
        stages=stages,
        approved_at=_parse_iso(data.get("approved_at")),
        approval_method=data.get("approval_method"),
    )


def _normalize_stage(v: Any) -> dict[str, Any]:
    if isinstance(v, StageRecord):
        return _dataclass_asdict_iso(v)
    if isinstance(v, dict):
        # 已经是 dict（来自 asdict），仅把 datetime 字段转 ISO
        out = dict(v)
        if isinstance(out.get("processed_at"), datetime):
            out["processed_at"] = out["processed_at"].isoformat()
        return out
    raise CheckpointError(f"无法序列化 stage 记录：{type(v).__name__}")


def _dataclass_asdict_iso(obj: Any) -> dict[str, Any]:
    """dataclass → dict，并把所有 datetime 字段转 ISO 字符串。"""
    if not is_dataclass(obj):
        raise CheckpointError(f"期望 dataclass，得到 {type(obj).__name__}")
    raw = asdict(obj)
    for f in fields(obj):
        v = raw.get(f.name)
        if isinstance(v, datetime):
            raw[f.name] = v.isoformat()
    return raw


def _parse_iso(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except ValueError as e:
            raise CheckpointError(f"datetime 字符串解析失败：{v!r}: {e}") from e
    raise CheckpointError(f"datetime 字段类型异常：{type(v).__name__}")


__all__ = [
    "STATE_SCHEMA_VERSION",
    "CheckpointError",
    "Checkpoint",
]
