"""Collections — 命名卡片分组的 JSON sidecar 存储。

存储在 vault/.mindforge/collections.json。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Collection:
    id: str
    name: str
    description: str = ""
    card_refs: tuple[str, ...] = ()
    rule_tags: tuple[str, ...] = ()
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "card_refs": list(self.card_refs),
            "rule_tags": list(self.rule_tags),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Collection:
        return cls(
            id=d["id"],
            name=d["name"],
            description=d.get("description", ""),
            card_refs=tuple(d.get("card_refs", [])),
            rule_tags=tuple(d.get("rule_tags", [])),
            created_at=d.get("created_at", ""),
        )


class CollectionStore:
    def __init__(self, vault_root: Path) -> None:
        self._dir = vault_root / ".mindforge"
        self._path = self._dir / "collections.json"

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            return []
        return []

    def _write_all(self, items: list[dict]) -> None:
        self._ensure_dir()
        self._path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_collections(self) -> list[Collection]:
        return [Collection.from_dict(d) for d in self._read_all()]

    def create_collection(self, col: Collection) -> Collection:
        now = datetime.now(timezone.utc).isoformat()
        items = self._read_all()
        entry = col.to_dict()
        entry["created_at"] = now
        items.append(entry)
        self._write_all(items)
        return Collection.from_dict(entry)

    def get_collection(self, col_id: str) -> Collection | None:
        for item in self._read_all():
            if item.get("id") == col_id:
                return Collection.from_dict(item)
        return None

    def add_cards(self, col_id: str, card_refs: list[str]) -> Collection | None:
        items = self._read_all()
        for item in items:
            if item.get("id") == col_id:
                existing = set(item.get("card_refs", []))
                existing.update(card_refs)
                item["card_refs"] = list(existing)
                self._write_all(items)
                return Collection.from_dict(item)
        return None

    def remove_cards(self, col_id: str, card_refs: list[str]) -> Collection | None:
        items = self._read_all()
        for item in items:
            if item.get("id") == col_id:
                to_remove = set(card_refs)
                existing = set(item.get("card_refs", []))
                item["card_refs"] = list(existing - to_remove)
                self._write_all(items)
                return Collection.from_dict(item)
        return None

    def delete_collection(self, col_id: str) -> bool:
        items = self._read_all()
        new_items = [i for i in items if i.get("id") != col_id]
        if len(new_items) == len(items):
            return False
        self._write_all(new_items)
        return True
