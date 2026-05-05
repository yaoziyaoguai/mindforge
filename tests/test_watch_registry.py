"""Simple watch registry contract tests.

watch registry 是用户级 ingestion 的轻量状态面：记录用户显式添加的 watched
source。default 00-Inbox 是系统内置 watched source，可以展示但不能删除。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.watch_registry import (
    WatchRegistry,
    add_watch_source,
    default_inbox_watch,
    delete_watch_source,
    list_watch_sources,
)


def test_default_inbox_watch_is_synthesized_and_not_persisted(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox"
    inbox.mkdir(parents=True)
    registry_path = vault / ".mindforge" / "watched_sources.json"

    watches = list_watch_sources(vault, registry_path)

    assert watches[0] == default_inbox_watch(vault)
    assert watches[0].id == "default-inbox"
    assert watches[0].path == inbox
    assert watches[0].is_default is True
    assert registry_path.exists() is False


def test_add_watch_source_is_idempotent_by_canonical_path(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    source = tmp_path / "source.md"
    source.write_text("# source\n", encoding="utf-8")
    registry_path = vault / ".mindforge" / "watched_sources.json"

    first = add_watch_source(vault, registry_path, source)
    second = add_watch_source(vault, registry_path, source)
    registry = WatchRegistry.load(registry_path)

    assert first.source.id == second.source.id
    assert first.added is True
    assert second.added is False
    assert len(registry.sources) == 1
    assert registry.sources[0].path == source.resolve()
    assert registry.sources[0].path_type == "file"


def test_delete_watch_source_only_removes_user_record(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    source = tmp_path / "source.md"
    source.write_text("# source\n", encoding="utf-8")
    registry_path = vault / ".mindforge" / "watched_sources.json"
    added = add_watch_source(vault, registry_path, source)

    deleted = delete_watch_source(vault, registry_path, added.source.id)
    missing = delete_watch_source(vault, registry_path, added.source.id)

    assert deleted.deleted is True
    assert source.exists(), "watch delete 只删 registry，不能删除原始 source"
    assert WatchRegistry.load(registry_path).sources == ()
    assert missing.deleted is False
    assert "not found" in missing.message


def test_delete_default_inbox_is_rejected(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    (vault / "00-Inbox").mkdir(parents=True)
    registry_path = vault / ".mindforge" / "watched_sources.json"

    result = delete_watch_source(vault, registry_path, "default-inbox")

    assert result.deleted is False
    assert "default 00-Inbox cannot be deleted" in result.message
    assert registry_path.exists() is False
