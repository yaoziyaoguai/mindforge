"""Checkpoint / state.json 单测。

覆盖：
- 空 state 加载；
- upsert 新条目 → status=raw；
- 同 hash 重复 upsert → 保留历史；
- hash 变化 → 重置 status；
- 原子写 + .bak 备份；
- 不兼容 schema version → 报错；
- count_by_status / count_by_source_type。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from mindforge.checkpoint import STATE_SCHEMA_VERSION, Checkpoint, CheckpointError
from mindforge.models import ItemState, StageRecord


def _make_state(
    *,
    source_type: str = "plain_markdown",
    source_path: str = "00-Inbox/ManualNotes/x.md",
    content_hash: str = "sha256:abc",
    source_id: str | None = None,
) -> ItemState:
    return ItemState(
        source_id=source_id or f"sha1:{source_path}",
        source_type=source_type,
        adapter_name="PlainMarkdownAdapter",
        source_path=source_path,
        content_hash=content_hash,
    )


def test_load_nonexistent_returns_empty(tmp_path: Path) -> None:
    cp = Checkpoint.load(tmp_path / "state.json")
    assert list(cp.all_items()) == []


def test_upsert_new_item(tmp_path: Path) -> None:
    cp = Checkpoint.load(tmp_path / "state.json")
    res = cp.upsert_seen(_make_state())
    assert res.status == "raw"
    assert res.first_seen_at is not None
    assert len(list(cp.all_items())) == 1


def test_upsert_same_hash_is_noop(tmp_path: Path) -> None:
    cp = Checkpoint.load(tmp_path / "state.json")
    first = cp.upsert_seen(_make_state())
    first.status = "processed"  # 模拟已加工
    again = cp.upsert_seen(_make_state())  # 同 hash
    assert again.status == "processed"     # 不被重置


def test_upsert_changed_hash_resets(tmp_path: Path) -> None:
    cp = Checkpoint.load(tmp_path / "state.json")
    first = cp.upsert_seen(_make_state(content_hash="sha256:v1"))
    first.status = "processed"
    new = cp.upsert_seen(_make_state(content_hash="sha256:v2"))
    assert new.status == "raw"            # 重置为 raw
    assert new.content_hash == "sha256:v2"
    assert new.first_seen_at == first.first_seen_at  # 保留首次见到时间


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    cp = Checkpoint.load(p)
    cp.upsert_seen(_make_state())
    cp.save(active_profile="default")

    cp2 = Checkpoint.load(p)
    assert len(list(cp2.all_items())) == 1
    item = next(iter(cp2.all_items()))
    assert item.status == "raw"
    assert item.adapter_name == "PlainMarkdownAdapter"


def test_save_writes_backup(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    cp = Checkpoint.load(p)
    cp.upsert_seen(_make_state(content_hash="sha256:v1"))
    cp.save()
    assert not p.with_suffix(".json.bak").exists()  # 第一次没备份

    # 第二次写入应生成 .bak
    cp.upsert_seen(_make_state(content_hash="sha256:v2"))
    cp.save()
    assert p.with_suffix(".json.bak").exists()


def test_save_atomic_no_tmp_left(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    cp = Checkpoint.load(p)
    cp.upsert_seen(_make_state())
    cp.save()
    leftovers = list(tmp_path.glob(".state.*"))
    assert leftovers == []


def test_load_unknown_schema_version_raises(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    p.write_text(
        json.dumps({"version": STATE_SCHEMA_VERSION + 99, "items": {}}),
        encoding="utf-8",
    )
    with pytest.raises(CheckpointError, match="schema 版本"):
        Checkpoint.load(p)


def test_load_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(CheckpointError, match="解析失败"):
        Checkpoint.load(p)


def test_count_by_status_and_source(tmp_path: Path) -> None:
    cp = Checkpoint.load(tmp_path / "state.json")
    cp.upsert_seen(_make_state(source_path="a.md"))
    cp.upsert_seen(_make_state(source_path="b.md"))
    cp.upsert_seen(_make_state(source_type="cubox_markdown", source_path="c.md"))
    by_status = cp.count_by_status()
    by_source = cp.count_by_source_type()
    assert by_status == {"raw": 3}
    assert by_source == {"plain_markdown": 2, "cubox_markdown": 1}


def test_stage_record_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    cp = Checkpoint.load(p)
    item = cp.upsert_seen(_make_state())
    item.stages["triage"] = StageRecord(
        stage="triage",
        model_alias="cheap_cloud",
        provider="cloud_openai_compatible",
        actual_model="cheap-model",
        prompt_version="triage@v1",
        status="ok",
        processed_at=datetime(2026, 4, 28, 13, 0, 0),
        tokens_in=100,
        tokens_out=20,
        latency_ms=850,
    )
    cp.save(active_profile="default")

    cp2 = Checkpoint.load(p)
    item2 = next(iter(cp2.all_items()))
    triage = item2.stages["triage"]
    assert triage.model_alias == "cheap_cloud"
    assert triage.tokens_in == 100
    assert triage.processed_at == datetime(2026, 4, 28, 13, 0, 0)
