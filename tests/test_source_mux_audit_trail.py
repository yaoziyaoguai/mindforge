"""Source Plugin Slice 3 — SourceMux dedup audit-trail 契约 (TDD Red 阶段)。

为什么有这个文件
================

v0.9 Source ingestion milestone 的 Slice 3 目标：把 ``SourceMux`` 的
"丢了哪一份" 决策**显式记录到 audit trail**。当前 ``MuxStats`` 只暴露
``yielded`` / ``deduped`` / ``by_source`` 三个**计数**，无法回答
"为什么我的某条 Cubox 文章在 OPS 里没出现"。

Slice 3 契约要求 ``MuxStats`` 携带一个**可读、可序列化、不可变**的
audit list，每条记录至少含：
- ``dropped_source_id``：被丢弃的 SourceDocument.source_id；
- ``dropped_source_type``：被丢弃的 source_type；
- ``dropped_adapter_name``：被丢弃的 adapter_name；
- ``kept_source_id``：先到达并被保留的同 key SourceDocument.source_id；
- ``dedup_key``：用来比较的 key（默认即 ``content_hash``）。

同时静态守卫：``SourceMux`` 永远不能滑向 semantic merge / embedding /
vector dedupe / LLM 调用 / .env 读取 / Obsidian 写入。

设计边界
========

- 本文件**只动 tests**，不动 production code；
- 仅 import ``mindforge.source_mux`` / ``mindforge.scanner`` /
  ``mindforge.sources.base``；
- 不构造真实 IO；用 in-memory fixture 即可。

Red / Green 期望
================

- **预期 Red**（production 契约缺口）：
  1. ``test_mux_stats_exposes_audit_trail_attribute`` ——
     ``MuxStats`` 没有 ``audit_trail`` 字段。
  2. ``test_audit_trail_records_dropped_documents`` —— 即使存在字段，
     当前 mux 也不会写入 audit 记录。
  3. ``test_audit_trail_entries_are_immutable`` —— audit 记录本身必须
     是 frozen dataclass 或 tuple，禁止外界修改。

- **Green 守卫**（今天就应通过）：
  - ``test_mux_module_does_not_import_embedding_or_vector`` —— AST
    扫 ``source_mux.py`` 不得 import ``numpy`` / ``embedding`` /
    ``vector`` / ``transformer`` / ``faiss`` / 任何 LLM provider。
  - ``test_mux_module_does_not_import_strategy_or_approval`` —— mux
    不能耦合到下游领域。
  - ``test_default_dedup_key_is_content_hash`` —— 锁定 Slice 3 Stop
    条件："禁止把默认 key 改为非 content_hash"。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from mindforge.scanner import ScanResult
from mindforge.source_mux import MuxStats, SourceMux, _default_key
from mindforge.sources.base import SourceDocument, compute_content_hash


# ---------------------------------------------------------------------------
# fixture 工厂
# ---------------------------------------------------------------------------


def _doc(text: str, *, source_type: str = "cubox_markdown",
         adapter_name: str = "FakeAdapter") -> SourceDocument:
    """构造最小合法 SourceDocument；content_hash 由 raw_text 决定。"""
    h = compute_content_hash(text)
    return SourceDocument(
        source_id=f"id:{h}:{source_type}",
        source_type=source_type,  # type: ignore[arg-type]
        source_path=f"/tmp/{source_type}/{h}.md",
        raw_text=text,
        content_hash=h,
        adapter_name=adapter_name,
    )


def _result(doc: SourceDocument, *, source_type: str | None = None,
            adapter: str = "FakeAdapter") -> ScanResult:
    return ScanResult(
        path=Path(doc.source_path),
        source_type=source_type or doc.source_type,
        adapter_name=adapter,
        document=doc,
        error=None,
    )


# ---------------------------------------------------------------------------
# 1. MuxStats 必须暴露 audit_trail 字段（**预期 Red**）
# ---------------------------------------------------------------------------


def test_mux_stats_exposes_audit_trail_attribute() -> None:
    """MuxStats 必须有 ``audit_trail`` 字段。

    Slice 3 契约：mux 决策必须是**可解释的**——每个被丢弃的 ScanResult
    必须留下一条审计记录，告诉用户"它被丢，是因为同 key 的另一份先到了"。

    **预期 Red**：当前 ``MuxStats`` 只有 yielded / deduped / by_source
    三个字段，没有 audit_trail。
    """
    stats = MuxStats()
    assert hasattr(stats, "audit_trail"), (
        "MuxStats 必须有 audit_trail 字段（用于记录 kept/dropped/key）"
    )


# ---------------------------------------------------------------------------
# 2. audit_trail 必须真的写入条目（**预期 Red**）
# ---------------------------------------------------------------------------


def test_audit_trail_records_dropped_documents() -> None:
    """喂入两份相同 content_hash 的 ScanResult，第二份必须出现在 audit_trail。

    Slice 3 契约：audit 记录必须包含 dropped_source_id / kept_source_id /
    dedup_key 三项最小信息，让用户从单一 stats 对象就能溯源 dedup 决策。

    **预期 Red**：当前 mux 不写 audit。
    """
    mux = SourceMux()
    a = _doc("same body", adapter_name="CuboxMarkdownAdapter")
    b = _doc("same body", source_type="cubox_api", adapter_name="CuboxApiAdapter")
    # 两者 raw_text 完全一致 → content_hash 一致 → 第二个被 dedupe。
    list(mux.iter_deduped([_result(a), _result(b)]))

    audit = mux.stats.audit_trail  # type: ignore[attr-defined]
    assert len(audit) == 1, f"应有 1 条 audit 记录，实际 {len(audit)} 条"
    entry = audit[0]
    # 用属性或下标访问以容纳 dataclass / namedtuple / dict 实现。
    dropped_id = getattr(entry, "dropped_source_id", None) or entry.get("dropped_source_id")  # type: ignore[union-attr]
    kept_id = getattr(entry, "kept_source_id", None) or entry.get("kept_source_id")  # type: ignore[union-attr]
    dedup_key = getattr(entry, "dedup_key", None) or entry.get("dedup_key")  # type: ignore[union-attr]
    assert dropped_id == b.source_id, f"dropped_source_id 不匹配：{dropped_id}"
    assert kept_id == a.source_id, f"kept_source_id 不匹配：{kept_id}"
    assert dedup_key == a.content_hash, "dedup_key 默认应为 content_hash"


# ---------------------------------------------------------------------------
# 3. audit_trail 条目必须不可变（**预期 Red**）
# ---------------------------------------------------------------------------


def test_audit_trail_entries_are_immutable() -> None:
    """audit 记录是审计证据，禁止外界修改。"""
    mux = SourceMux()
    a = _doc("X")
    b = _doc("X", source_type="cubox_api", adapter_name="CuboxApiAdapter")
    list(mux.iter_deduped([_result(a), _result(b)]))
    entry = mux.stats.audit_trail[0]  # type: ignore[attr-defined]
    # 尝试改字段；应该抛错（FrozenInstanceError 或 AttributeError）。
    with pytest.raises(Exception):
        entry.dropped_source_id = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 4. Green 守卫：默认 key 必须是 content_hash
# ---------------------------------------------------------------------------


def test_default_dedup_key_is_content_hash() -> None:
    """``_default_key`` 必须返回 doc.content_hash —— Slice 3 Stop 条件。"""
    doc = _doc("hello")
    assert _default_key(doc) == doc.content_hash


# ---------------------------------------------------------------------------
# 5. Green 守卫：source_mux 不得 import embedding / vector / LLM 任何符号
# ---------------------------------------------------------------------------


def _module_imports(path: Path) -> set[str]:
    """返回模块的所有 import 名（顶层 import 与 from-import 的根模块）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def test_mux_module_does_not_import_embedding_or_vector() -> None:
    """source_mux.py 不得 import 任何 embedding / vector / LLM 模块。

    Slice 3 Stop 条件：mux 永远是 deterministic content-hash dedup，
    不滑向 semantic merge。本测试用 AST 直接扫 import 表。
    """
    import mindforge.source_mux as mux_mod

    src_path = Path(mux_mod.__file__)
    imports = _module_imports(src_path)
    forbidden = {
        "numpy",
        "scipy",
        "torch",
        "transformers",
        "sentence_transformers",
        "faiss",
        "chromadb",
        "pinecone",
        "openai",
        "anthropic",
        "embedding",
        "embeddings",
    }
    leaked = imports & forbidden
    assert not leaked, f"source_mux 不得 import {leaked}"


def test_mux_module_does_not_import_strategy_or_approval() -> None:
    """source_mux.py 不得 import strategy / approval / cli / pipeline。"""
    import mindforge.source_mux as mux_mod

    src_path = Path(mux_mod.__file__)
    imports = _module_imports(src_path)
    # source_mux 顶层只允许：collections / dataclasses / typing /
    # mindforge.scanner / mindforge.sources（含 sources.base）。
    forbidden_prefixes = (
        "approval",
        "approve",
        "review",
        "recall",
        "cli",
        "processors",
        "strategies",
        "obsidian",
    )
    leaked = {
        n
        for n in imports
        if any(n.startswith(p) for p in forbidden_prefixes)
    }
    assert not leaked, f"source_mux 不得 import 下游领域：{leaked}"
