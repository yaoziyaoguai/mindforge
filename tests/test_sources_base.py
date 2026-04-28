"""协议层单测：SourceDocument / Highlight / SourceAdapter / compute_content_hash。

测试目标：
1. 数据类的必填字段在缺失时正确报错；
2. ``compute_content_hash`` 是确定性的、对 metadata key 顺序不敏感；
3. ``SourceAdapter`` 是抽象类，子类必须实现 ``can_handle`` / ``load``；
4. 通过一个 ``FakeAdapter`` 验证子类合约能正常组合出一个 ``SourceDocument``。

注意：本测试**不读真实文件**、**不调 LLM**，只验证协议层契约。
"""

from __future__ import annotations

import pytest

from mindforge.sources.base import (
    Highlight,
    SourceAdapter,
    SourceDocument,
    compute_content_hash,
)

# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


def test_content_hash_is_deterministic() -> None:
    h1 = compute_content_hash("hello", {"url": "https://x", "author": "alice"})
    h2 = compute_content_hash("hello", {"author": "alice", "url": "https://x"})
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_content_hash_changes_with_text() -> None:
    assert compute_content_hash("hello") != compute_content_hash("hello!")


def test_content_hash_changes_with_metadata() -> None:
    h1 = compute_content_hash("hello", {"url": "https://a"})
    h2 = compute_content_hash("hello", {"url": "https://b"})
    assert h1 != h2


def test_content_hash_no_metadata_equiv_empty() -> None:
    assert compute_content_hash("hello") == compute_content_hash("hello", None)


# ---------------------------------------------------------------------------
# SourceDocument 必填校验
# ---------------------------------------------------------------------------


def _make_doc(**overrides) -> SourceDocument:
    """构造一个最小合法 SourceDocument，便于按字段覆盖测试边界。"""
    base = dict(
        source_id="sha1:abc",
        source_type="plain_markdown",
        source_path="00-Inbox/ManualNotes/x.md",
        raw_text="hello",
        content_hash=compute_content_hash("hello"),
    )
    base.update(overrides)
    return SourceDocument(**base)  # type: ignore[arg-type]


def test_source_document_minimum_valid() -> None:
    doc = _make_doc()
    assert doc.source_id == "sha1:abc"
    assert doc.source_type == "plain_markdown"
    assert doc.tags == []
    assert doc.highlights == []
    assert doc.metadata == {}


@pytest.mark.parametrize("missing", ["source_id", "source_path", "content_hash"])
def test_source_document_required_fields(missing: str) -> None:
    with pytest.raises(ValueError, match=missing):
        _make_doc(**{missing: ""})


def test_source_document_is_frozen() -> None:
    doc = _make_doc()
    with pytest.raises(Exception):
        doc.title = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Highlight
# ---------------------------------------------------------------------------


def test_highlight_minimal() -> None:
    h = Highlight(text="key sentence")
    assert h.text == "key sentence"
    assert h.note is None
    assert h.created_at is None


def test_highlight_is_frozen() -> None:
    h = Highlight(text="x")
    with pytest.raises(Exception):
        h.text = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SourceAdapter 抽象契约
# ---------------------------------------------------------------------------


def test_source_adapter_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        SourceAdapter()  # type: ignore[abstract]


class FakeAdapter(SourceAdapter):
    """仅用于测试：把"路径"当成 raw_text 直接构造 SourceDocument。

    展示后续真实 adapter（如 CuboxMarkdownAdapter）应当如何最小化实现：
    1. 类属性 name / source_type 必填；
    2. can_handle 返回快速判定；
    3. load 完成"读取 + 解析 + 计算 content_hash + 构造 SourceDocument"四步。
    """

    name = "FakeAdapter"
    source_type = "plain_markdown"  # type: ignore[assignment]

    def can_handle(self, path: str) -> bool:
        return path.endswith(".fake")

    def load(self, path: str) -> SourceDocument:
        raw = f"content-of:{path}"
        return SourceDocument(
            source_id=f"fake:{path}",
            source_type=self.source_type,
            source_path=path,
            raw_text=raw,
            content_hash=compute_content_hash(raw),
        )


def test_fake_adapter_roundtrip() -> None:
    adapter = FakeAdapter()
    assert adapter.can_handle("a.fake")
    assert not adapter.can_handle("a.md")

    doc = adapter.load("foo/bar.fake")
    assert doc.source_path == "foo/bar.fake"
    assert doc.source_type == "plain_markdown"
    assert doc.raw_text == "content-of:foo/bar.fake"
    assert doc.content_hash.startswith("sha256:")


def test_subclass_missing_methods_raises() -> None:
    class IncompleteAdapter(SourceAdapter):
        name = "Incomplete"

    with pytest.raises(TypeError):
        IncompleteAdapter()  # type: ignore[abstract]
