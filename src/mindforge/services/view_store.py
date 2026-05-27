"""Saved Views — 命名筛选+排序组合的持久化存储。

存储在 vault/.mindforge/views.json，纯 JSON sidecar，不依赖数据库。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SavedView:
    id: str
    name: str
    status_filter: str = "all"
    track_filter: str = "all"
    source_type_filter: str = "all"
    quality_filter: str = "all"
    sort_by: str = "newest"
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status_filter": self.status_filter,
            "track_filter": self.track_filter,
            "source_type_filter": self.source_type_filter,
            "quality_filter": self.quality_filter,
            "sort_by": self.sort_by,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SavedView:
        return cls(
            id=d["id"],
            name=d["name"],
            status_filter=d.get("status_filter", "all"),
            track_filter=d.get("track_filter", "all"),
            source_type_filter=d.get("source_type_filter", "all"),
            quality_filter=d.get("quality_filter", "all"),
            sort_by=d.get("sort_by", "newest"),
            created_at=d.get("created_at", ""),
        )


class ViewStore:
    """管理 saved views 的 JSON sidecar 文件。"""

    def __init__(self, vault_root: Path) -> None:
        self._views_dir = vault_root / ".mindforge"
        self._views_path = self._views_dir / "views.json"

    def _ensure_dir(self) -> None:
        self._views_dir.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> list[dict]:
        if not self._views_path.exists():
            return []
        try:
            data = json.loads(self._views_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            return []
        return []

    def _write_all(self, views: list[dict]) -> None:
        self._ensure_dir()
        self._views_path.write_text(
            json.dumps(views, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_views(self) -> list[SavedView]:
        return [SavedView.from_dict(d) for d in self._read_all()]

    def save_view(self, view: SavedView) -> SavedView:
        now = datetime.now(timezone.utc).isoformat()
        views = self._read_all()
        for i, existing in enumerate(views):
            if existing.get("id") == view.id:
                updated = view.to_dict()
                updated["created_at"] = existing.get("created_at", now)
                views[i] = updated
                self._write_all(views)
                return SavedView.from_dict(updated)
        new_view = view.to_dict()
        new_view["created_at"] = now
        views.append(new_view)
        self._write_all(views)
        return SavedView.from_dict(new_view)

    def delete_view(self, view_id: str) -> bool:
        views = self._read_all()
        new_views = [v for v in views if v.get("id") != view_id]
        if len(new_views) == len(views):
            return False
        self._write_all(new_views)
        return True
