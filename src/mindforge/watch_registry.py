"""Watched source registry for simple ingestion.

中文学习型说明：watch registry 只记录用户显式添加的 watched source。系统内置
``00-Inbox`` 是 default watched source，用动态合成表达，避免把默认约定和用户
状态混在一个 JSON 文件里。registry 位于 active vault 的 ``.mindforge`` 区域，
不会写到源码 repo 或 home 固定目录。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

PathType = Literal["file", "folder"]
WatchStatus = Literal["active", "missing", "error"]

REGISTRY_SCHEMA_VERSION = 1
DEFAULT_INBOX_ID = "default-inbox"


@dataclass(frozen=True)
class WatchedSource:
    id: str
    path: Path
    path_type: PathType
    is_default: bool
    added_at: str
    last_seen_at: str | None = None
    last_processed_at: str | None = None
    fingerprint: str | None = None
    status: WatchStatus = "active"
    error: str | None = None


@dataclass(frozen=True)
class WatchRegistry:
    sources: tuple[WatchedSource, ...] = ()

    @classmethod
    def load(cls, path: Path) -> "WatchRegistry":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        if int(raw.get("version", 0)) != REGISTRY_SCHEMA_VERSION:
            raise ValueError(f"watched_sources.json schema mismatch: {path}")
        sources = tuple(_source_from_dict(item) for item in raw.get("sources", []))
        return cls(sources=sources)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": REGISTRY_SCHEMA_VERSION,
            "updated_at": _now(),
            "sources": [_source_to_dict(source) for source in self.sources],
        }
        fd, tmp_path = tempfile.mkstemp(
            prefix=".watched_sources.", suffix=".tmp", dir=str(path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise


@dataclass(frozen=True)
class AddWatchResult:
    source: WatchedSource
    added: bool
    message: str


@dataclass(frozen=True)
class DeleteWatchResult:
    deleted: bool
    message: str
    source: WatchedSource | None = None


def default_inbox_watch(vault_root: Path) -> WatchedSource:
    inbox = (vault_root / "00-Inbox").resolve()
    status: WatchStatus = "active" if inbox.exists() else "missing"
    return WatchedSource(
        id=DEFAULT_INBOX_ID,
        path=inbox,
        path_type="folder",
        is_default=True,
        added_at="system",
        status=status,
    )


def registry_path_for_vault(vault_root: Path) -> Path:
    return vault_root / ".mindforge" / "watched_sources.json"


def list_watch_sources(vault_root: Path, registry_path: Path | None = None) -> tuple[WatchedSource, ...]:
    path = registry_path or registry_path_for_vault(vault_root)
    registry = WatchRegistry.load(path)
    return (default_inbox_watch(vault_root), *registry.sources)


def add_watch_source(vault_root: Path, registry_path: Path, source_path: Path) -> AddWatchResult:
    canonical = source_path.expanduser().resolve()
    registry = WatchRegistry.load(registry_path)
    for source in registry.sources:
        if source.path == canonical:
            return AddWatchResult(source=source, added=False, message="already registered")
    watched = WatchedSource(
        id=_watch_id(canonical),
        path=canonical,
        path_type=_path_type(canonical),
        is_default=False,
        added_at=_now(),
        last_seen_at=_now() if canonical.exists() else None,
        fingerprint=_fingerprint(canonical),
        status="active" if canonical.exists() else "missing",
    )
    WatchRegistry(sources=(*registry.sources, watched)).save(registry_path)
    return AddWatchResult(source=watched, added=True, message="registered")


def update_watch_source(
    vault_root: Path,
    registry_path: Path,
    source_id: str,
    *,
    last_seen_at: str | None = None,
    last_processed_at: str | None = None,
    fingerprint: str | None = None,
    status: WatchStatus | None = None,
    error: str | None = None,
) -> WatchedSource | None:
    registry = WatchRegistry.load(registry_path)
    updated: list[WatchedSource] = []
    found: WatchedSource | None = None
    for source in registry.sources:
        if source.id != source_id:
            updated.append(source)
            continue
        found = WatchedSource(
            id=source.id,
            path=source.path,
            path_type=source.path_type,
            is_default=source.is_default,
            added_at=source.added_at,
            last_seen_at=last_seen_at if last_seen_at is not None else source.last_seen_at,
            last_processed_at=(
                last_processed_at if last_processed_at is not None else source.last_processed_at
            ),
            fingerprint=fingerprint if fingerprint is not None else source.fingerprint,
            status=status if status is not None else source.status,
            error=error,
        )
        updated.append(found)
    if found is not None:
        WatchRegistry(sources=tuple(updated)).save(registry_path)
    return found


def delete_watch_source(vault_root: Path, registry_path: Path, ref: str) -> DeleteWatchResult:
    if ref == DEFAULT_INBOX_ID or ref == str((vault_root / "00-Inbox").resolve()):
        return DeleteWatchResult(
            deleted=False,
            message="default 00-Inbox cannot be deleted",
        )
    canonical = _try_resolve(ref)
    registry = WatchRegistry.load(registry_path)
    kept: list[WatchedSource] = []
    deleted: WatchedSource | None = None
    for source in registry.sources:
        if source.id == ref or str(source.path) == ref or (canonical is not None and source.path == canonical):
            deleted = source
            continue
        kept.append(source)
    if deleted is None:
        return DeleteWatchResult(deleted=False, message=f"watch source not found: {ref}")
    WatchRegistry(sources=tuple(kept)).save(registry_path)
    return DeleteWatchResult(deleted=True, message="deleted", source=deleted)


def _source_to_dict(source: WatchedSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "path": str(source.path),
        "path_type": source.path_type,
        "is_default": source.is_default,
        "added_at": source.added_at,
        "last_seen_at": source.last_seen_at,
        "last_processed_at": source.last_processed_at,
        "fingerprint": source.fingerprint,
        "status": source.status,
        "error": source.error,
    }


def _source_from_dict(data: dict[str, Any]) -> WatchedSource:
    return WatchedSource(
        id=str(data["id"]),
        path=Path(str(data["path"])).expanduser().resolve(),
        path_type="folder" if data.get("path_type") == "folder" else "file",
        is_default=bool(data.get("is_default", False)),
        added_at=str(data.get("added_at") or ""),
        last_seen_at=data.get("last_seen_at"),
        last_processed_at=data.get("last_processed_at"),
        fingerprint=data.get("fingerprint"),
        status=data.get("status", "active"),
        error=data.get("error"),
    )


def _watch_id(path: Path) -> str:
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]
    return f"ws_{digest}"


def _path_type(path: Path) -> PathType:
    return "folder" if path.is_dir() else "file"


def _fingerprint(path: Path) -> str | None:
    if not path.exists():
        return None
    stat = path.stat()
    payload = f"{path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _try_resolve(ref: str) -> Path | None:
    try:
        return Path(ref).expanduser().resolve()
    except OSError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = [
    "AddWatchResult",
    "DeleteWatchResult",
    "DEFAULT_INBOX_ID",
    "WatchRegistry",
    "WatchedSource",
    "add_watch_source",
    "default_inbox_watch",
    "delete_watch_source",
    "list_watch_sources",
    "registry_path_for_vault",
    "update_watch_source",
]
