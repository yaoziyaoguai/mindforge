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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

PathType = Literal["file", "folder"]
WatchStatus = Literal["active", "missing", "error", "paused"]

REGISTRY_SCHEMA_VERSION = 1
DEFAULT_INBOX_ID = "default-inbox"
DEFAULT_FREQUENCY = "manual"


@dataclass(frozen=True)
class WatchFileSnapshot:
    relative_path: str
    path: Path
    content_hash: str
    size: int
    mtime: float
    last_seen_at: str
    last_processed_at: str | None = None
    status: str = "seen"
    skipped_reason: str | None = None


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
    strategy_id: str | None = None
    status: WatchStatus = "active"
    error: str | None = None
    recursive: bool = False
    frequency: str = DEFAULT_FREQUENCY
    last_scan_at: str | None = None
    next_scan_at: str | None = None
    baseline: dict[str, WatchFileSnapshot] = None  # type: ignore[assignment]
    diff_counts: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.baseline is None:
            object.__setattr__(self, "baseline", {})
        if self.diff_counts is None:
            object.__setattr__(self, "diff_counts", {})


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
        recursive=True,
    )


def registry_path_for_vault(vault_root: Path) -> Path:
    return vault_root / ".mindforge" / "watched_sources.json"


def list_watch_sources(vault_root: Path, registry_path: Path | None = None) -> tuple[WatchedSource, ...]:
    path = registry_path or registry_path_for_vault(vault_root)
    registry = WatchRegistry.load(path)
    return (default_inbox_watch(vault_root), *registry.sources)


def add_watch_source(
    vault_root: Path,
    registry_path: Path,
    source_path: Path,
    *,
    strategy_id: str | None = None,
    frequency: str = DEFAULT_FREQUENCY,
    recursive: bool | None = None,
) -> AddWatchResult:
    canonical = source_path.expanduser().resolve()
    normalized_frequency = normalize_frequency(frequency)
    registry = WatchRegistry.load(registry_path)
    for source in registry.sources:
        if source.path == canonical:
            return AddWatchResult(source=source, added=False, message="already registered")
    path_type = _path_type(canonical)
    watched = WatchedSource(
        id=_watch_id(canonical),
        path=canonical,
        path_type=path_type,
        is_default=False,
        added_at=_now(),
        last_seen_at=_now() if canonical.exists() else None,
        fingerprint=_fingerprint(canonical),
        strategy_id=strategy_id,
        status="active" if canonical.exists() else "missing",
        recursive=path_type == "folder" if recursive is None else bool(recursive),
        frequency=normalized_frequency,
        next_scan_at=next_scan_after(_now(), normalized_frequency),
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
    frequency: str | None = None,
    last_scan_at: str | None = None,
    next_scan_at: str | None = None,
    baseline: dict[str, WatchFileSnapshot] | None = None,
    diff_counts: dict[str, int] | None = None,
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
            strategy_id=source.strategy_id,
            status=status if status is not None else source.status,
            error=error,
            recursive=source.recursive,
            frequency=normalize_frequency(frequency) if frequency is not None else source.frequency,
            last_scan_at=last_scan_at if last_scan_at is not None else source.last_scan_at,
            next_scan_at=next_scan_at if next_scan_at is not None else source.next_scan_at,
            baseline=baseline if baseline is not None else source.baseline,
            diff_counts=diff_counts if diff_counts is not None else source.diff_counts,
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


def set_watch_status(vault_root: Path, registry_path: Path, ref: str, status: WatchStatus) -> WatchedSource | None:
    source = find_watch_source(vault_root, registry_path, ref)
    if source is None or source.is_default:
        return None
    return update_watch_source(vault_root, registry_path, source.id, status=status, error=None)


def find_watch_source(vault_root: Path, registry_path: Path, ref: str) -> WatchedSource | None:
    canonical = _try_resolve(ref)
    for source in list_watch_sources(vault_root, registry_path):
        if source.id == ref or str(source.path) == ref or (canonical is not None and source.path == canonical):
            return source
    return None


def normalize_frequency(value: str | None) -> str:
    text = (value or DEFAULT_FREQUENCY).strip().lower()
    aliases = {"1h": "every 1h", "6h": "every 6h", "12h": "every 12h", "24h": "every 24h"}
    text = aliases.get(text, text)
    if text in {"manual", "hourly", "daily", "weekly", "every 1h", "every 6h", "every 12h", "every 24h"}:
        return text
    raise ValueError(f"Unsupported watch frequency: {value}")


def is_due(source: WatchedSource, *, now: datetime | None = None) -> bool:
    if source.is_default or source.status == "paused":
        return False
    if source.frequency == "manual":
        return False
    if source.next_scan_at:
        try:
            due_at = datetime.fromisoformat(source.next_scan_at)
        except ValueError:
            return True
        return due_at <= (now or datetime.now(timezone.utc))
    if source.last_scan_at:
        try:
            last = datetime.fromisoformat(source.last_scan_at)
        except ValueError:
            return True
        return last + frequency_delta(source.frequency) <= (now or datetime.now(timezone.utc))
    return True


def next_scan_after(value: str | None, frequency: str) -> str | None:
    normalized = normalize_frequency(frequency)
    if normalized == "manual":
        return None
    try:
        base = datetime.fromisoformat(value or _now())
    except ValueError:
        base = datetime.now(timezone.utc)
    return (base + frequency_delta(normalized)).isoformat(timespec="seconds")


def frequency_delta(frequency: str) -> timedelta:
    normalized = normalize_frequency(frequency)
    if normalized in {"hourly", "every 1h"}:
        return timedelta(hours=1)
    if normalized == "every 6h":
        return timedelta(hours=6)
    if normalized == "every 12h":
        return timedelta(hours=12)
    if normalized in {"daily", "every 24h"}:
        return timedelta(days=1)
    if normalized == "weekly":
        return timedelta(days=7)
    return timedelta(0)


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
        "strategy_id": source.strategy_id,
        "status": source.status,
        "error": source.error,
        "recursive": source.recursive,
        "frequency": source.frequency,
        "last_scan_at": source.last_scan_at,
        "next_scan_at": source.next_scan_at,
        "baseline": {key: _snapshot_to_dict(item) for key, item in source.baseline.items()},
        "diff_counts": dict(source.diff_counts),
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
        strategy_id=data.get("strategy_id"),
        status=data.get("status", "active"),
        error=data.get("error"),
        recursive=bool(data.get("recursive", data.get("path_type") == "folder")),
        frequency=normalize_frequency(str(data.get("frequency") or DEFAULT_FREQUENCY)),
        last_scan_at=data.get("last_scan_at"),
        next_scan_at=data.get("next_scan_at"),
        baseline={
            str(key): _snapshot_from_dict(value)
            for key, value in (data.get("baseline") or {}).items()
            if isinstance(value, dict)
        },
        diff_counts={
            str(key): int(value)
            for key, value in (data.get("diff_counts") or {}).items()
            if isinstance(value, int)
        },
    )


def _snapshot_to_dict(item: WatchFileSnapshot) -> dict[str, Any]:
    return {
        "relative_path": item.relative_path,
        "path": str(item.path),
        "content_hash": item.content_hash,
        "size": item.size,
        "mtime": item.mtime,
        "last_seen_at": item.last_seen_at,
        "last_processed_at": item.last_processed_at,
        "status": item.status,
        "skipped_reason": item.skipped_reason,
    }


def _snapshot_from_dict(data: dict[str, Any]) -> WatchFileSnapshot:
    return WatchFileSnapshot(
        relative_path=str(data.get("relative_path") or ""),
        path=Path(str(data.get("path") or "")).expanduser().resolve(),
        content_hash=str(data.get("content_hash") or ""),
        size=int(data.get("size") or 0),
        mtime=float(data.get("mtime") or 0),
        last_seen_at=str(data.get("last_seen_at") or ""),
        last_processed_at=data.get("last_processed_at"),
        status=str(data.get("status") or "seen"),
        skipped_reason=data.get("skipped_reason"),
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
