"""Cubox export adapter mapping contract tests — characterization slice.

本文件聚焦 ``CuboxApiAdapter.parse_export`` 的字段映射 / 边界场景，
将既有 production 行为以**测试**形式锁定，作为下一步 dogfood CLI 的
前置护栏。

设计原则：
- **零 production 改动**：任一测试失败必须停步并 Ask User，不擅改实现；
- 与 ``test_cubox_api_adapter.py`` 不重复：那里覆盖 fixture happy path
  + opt-in / credential / registry 边界；本文件覆盖 mapping 极端形态
  （空数组、缺失字段、null tags、空 highlight、duplicate item、
  无效时间、安全 metadata、不联网、不读 .env）；
- 不引入新 production 类型；只 import 既有 adapter 与 SourceDocument。
"""

from __future__ import annotations

import builtins
import json
import socket
from pathlib import Path
from typing import Any

import pytest

from mindforge.sources.cubox_api import CuboxApiAdapter


def _write_export(tmp_path: Path, items: list[dict[str, Any]]) -> Path:
    p = tmp_path / "export.json"
    p.write_text(json.dumps(items), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. Empty / malformed shape
# ---------------------------------------------------------------------------


def test_parse_export_empty_array_returns_empty_list(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [])
    assert CuboxApiAdapter().parse_export(p) == []


def test_parse_export_malformed_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        CuboxApiAdapter().parse_export(p)


# ---------------------------------------------------------------------------
# 2. Field mapping — optional / fallback
# ---------------------------------------------------------------------------


def test_parse_export_missing_optional_fields_stable(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [{"id": "only-id"}])
    docs = CuboxApiAdapter().parse_export(p)
    assert len(docs) == 1
    d = docs[0]
    assert d.source_url is None
    assert d.author is None
    assert d.created_at is None
    assert d.captured_at is None
    assert d.tags == []
    assert d.highlights == []
    assert d.raw_text == ""


def test_parse_export_empty_title_falls_back_to_item_id(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [{"id": "abc-123", "title": "   "}])
    d = CuboxApiAdapter().parse_export(p)[0]
    assert d.title == "abc-123"


def test_parse_export_uses_uuid_when_id_missing(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [{"uuid": "u-1", "title": "T"}])
    d = CuboxApiAdapter().parse_export(p)[0]
    assert "u-1" in d.metadata.get("cubox_item_id", "")


def test_parse_export_empty_url_becomes_none(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [{"id": "x", "url": "   "}])
    d = CuboxApiAdapter().parse_export(p)[0]
    assert d.source_url is None


def test_parse_export_null_tags_become_empty_list(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [{"id": "x", "tags": None}])
    d = CuboxApiAdapter().parse_export(p)[0]
    assert d.tags == []


def test_parse_export_invalid_timestamp_becomes_none(tmp_path: Path) -> None:
    p = _write_export(
        tmp_path, [{"id": "x", "created_at": "not-a-date", "saved_at": ""}]
    )
    d = CuboxApiAdapter().parse_export(p)[0]
    assert d.created_at is None
    assert d.captured_at is None


# ---------------------------------------------------------------------------
# 3. Highlights edge cases
# ---------------------------------------------------------------------------


def test_parse_export_skips_empty_highlight_text(tmp_path: Path) -> None:
    p = _write_export(
        tmp_path,
        [
            {
                "id": "x",
                "highlights": [
                    {"text": "  "},  # empty after strip → skip
                    {"text": "kept", "note": "  "},  # note空白 → None
                ],
            }
        ],
    )
    d = CuboxApiAdapter().parse_export(p)[0]
    assert len(d.highlights) == 1
    assert d.highlights[0].text == "kept"
    assert d.highlights[0].note is None


# ---------------------------------------------------------------------------
# 4. Determinism — duplicate item handled by SourceMux upstream
# ---------------------------------------------------------------------------


def test_parse_export_duplicate_item_id_yields_identical_source_id(
    tmp_path: Path,
) -> None:
    p = _write_export(
        tmp_path,
        [
            {"id": "dup", "title": "A", "content": "x"},
            {"id": "dup", "title": "A", "content": "x"},
        ],
    )
    docs = CuboxApiAdapter().parse_export(p)
    assert len(docs) == 2
    assert docs[0].source_id == docs[1].source_id


def test_parse_export_identical_payload_yields_identical_content_hash(
    tmp_path: Path,
) -> None:
    item = {
        "id": "h",
        "title": "T",
        "url": "https://e.com/a",
        "author": "Z",
        "content": "body",
    }
    p = _write_export(tmp_path, [item, dict(item)])
    docs = CuboxApiAdapter().parse_export(p)
    assert docs[0].content_hash == docs[1].content_hash


# ---------------------------------------------------------------------------
# 5. Safety — metadata cleanliness
# ---------------------------------------------------------------------------


_FORBIDDEN_META_KEY_FRAGMENTS = ("token", "auth", "cookie", "secret", "password")


def test_parse_export_metadata_excludes_credential_fields(tmp_path: Path) -> None:
    p = _write_export(
        tmp_path,
        [{"id": "x", "title": "T", "url": "https://e.com", "author": "A"}],
    )
    d = CuboxApiAdapter().parse_export(p)[0]
    for k in d.metadata:
        low = k.lower()
        for bad in _FORBIDDEN_META_KEY_FRAGMENTS:
            assert bad not in low, f"metadata key {k!r} 含敏感片段 {bad!r}"


# ---------------------------------------------------------------------------
# 6. Safety — no network, no .env
# ---------------------------------------------------------------------------


def test_parse_export_does_not_open_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("parse_export 不应建立网络连接")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)
    p = _write_export(tmp_path, [{"id": "x", "title": "T"}])
    docs = CuboxApiAdapter().parse_export(p)
    assert len(docs) == 1


def test_parse_export_does_not_read_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_open = builtins.open
    seen: list[str] = []

    def _spy(file: Any, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        s = str(file)
        if ".env" in s.lower():
            seen.append(s)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _spy)
    p = _write_export(tmp_path, [{"id": "x", "title": "T"}])
    CuboxApiAdapter().parse_export(p)
    assert seen == [], f"parse_export 不应读取 .env：{seen}"
