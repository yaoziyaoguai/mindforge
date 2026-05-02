"""SourceMux contract tests — TDD Red phase 先行。

SourceMux 是 Scanner 输出的薄包装层，作用是跨源去重（cross-source
dedup）。引入动机：``cubox_markdown``（插件离线同步）与 ``cubox_api``
（JSON export）可能对**同一 Cubox 文章**各产出一份 SourceDocument，
不去重就会让 ai_draft 重复生成。

边界（由测试守护）：
- mux 不感知任何具体 adapter / source_type；
- mux 不修改任何已有 SourceDocument；
- mux 不强制接入 CLI 默认路径（opt-in）。
"""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from mindforge.scanner import ScanResult
from mindforge.source_mux import MuxStats, SourceMux
from mindforge.sources.base import SourceDocument


# ---------------------------------------------------------------------------
# 测试用 SourceDocument 工厂
# ---------------------------------------------------------------------------


def _doc(content_hash: str, *, title: str = "T", source_type: str = "cubox_markdown",
         source_url: str | None = None) -> SourceDocument:
    return SourceDocument(
        source_id=f"id:{content_hash}",
        source_type=source_type,  # type: ignore[arg-type]
        source_path=f"/tmp/{content_hash}.md",
        title=title,
        author=None,
        source_url=source_url,
        created_at=None,
        captured_at=None,
        tags=[],
        highlights=[],
        raw_text="",
        metadata={},
        content_hash=content_hash,
    )


def _result(doc: SourceDocument | None, *, source_type: str | None = None,
            adapter: str = "Adapter", error: str | None = None) -> ScanResult:
    return ScanResult(
        source_type=source_type or (doc.source_type if doc else "unknown"),
        adapter_name=adapter,
        path=Path("/tmp/x"),
        document=doc,
        error=error,
    )


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


def test_mux_passes_through_unique_documents() -> None:
    mux = SourceMux()
    results = [_result(_doc("h1")), _result(_doc("h2")), _result(_doc("h3"))]
    out = list(mux.iter_deduped(results))
    assert [r.document.content_hash for r in out] == ["h1", "h2", "h3"]
    assert mux.stats.yielded == 3
    assert mux.stats.deduped == 0


def test_mux_dedupes_by_content_hash_across_sources() -> None:
    """同一 content_hash 来自不同 source_type 时，只保留首次。"""
    mux = SourceMux()
    md = _result(_doc("same_hash", source_type="cubox_markdown"))
    api = _result(_doc("same_hash", source_type="cubox_api"))
    out = list(mux.iter_deduped([md, api]))
    assert len(out) == 1
    assert out[0].source_type == "cubox_markdown"  # first-seen 保留
    assert mux.stats.yielded == 1
    assert mux.stats.deduped == 1
    assert mux.stats.by_source.get("cubox_api") == 1


def test_mux_first_seen_wins_preserves_order() -> None:
    mux = SourceMux()
    a = _result(_doc("h1", source_type="plain_markdown"))
    b = _result(_doc("h2", source_type="cubox_api"))
    a_dup = _result(_doc("h1", source_type="cubox_api"))
    out = list(mux.iter_deduped([a, b, a_dup]))
    assert [r.source_type for r in out] == ["plain_markdown", "cubox_api"]
    assert mux.stats.deduped == 1


def test_mux_failed_results_pass_through_without_dedup() -> None:
    """document=None 的失败结果不参与去重，逐条透传（错误本身就是观测信号）。"""
    mux = SourceMux()
    err1 = _result(None, source_type="cubox_api", error="ParseError: x")
    err2 = _result(None, source_type="cubox_api", error="ParseError: y")
    out = list(mux.iter_deduped([err1, err2]))
    assert len(out) == 2
    assert all(r.error for r in out)
    assert mux.stats.deduped == 0


def test_mux_empty_input() -> None:
    mux = SourceMux()
    assert list(mux.iter_deduped([])) == []
    assert mux.stats == MuxStats(yielded=0, deduped=0, by_source={})


def test_mux_custom_key_fn_dedupes_by_source_url() -> None:
    """支持注入自定义 key 函数（如按 source_url 去重）。"""
    mux = SourceMux(key_fn=lambda d: d.source_url or d.content_hash)
    a = _result(_doc("h1", source_url="https://x.com/a"))
    b = _result(_doc("h2", source_url="https://x.com/a"))  # 不同 hash 但同 url
    out = list(mux.iter_deduped([a, b]))
    assert len(out) == 1
    assert mux.stats.deduped == 1


def test_mux_feed_returns_none_for_duplicate() -> None:
    """单条 feed 接口：新值返回原 result，重复返回 None。"""
    mux = SourceMux()
    first = _result(_doc("h1"))
    dup = _result(_doc("h1", source_type="cubox_api"))
    assert mux.feed(first) is first
    assert mux.feed(dup) is None
    assert mux.stats.yielded == 1
    assert mux.stats.deduped == 1


def test_mux_does_not_mutate_documents() -> None:
    mux = SourceMux()
    doc = _doc("h1")
    snap = replace(doc)  # frozen 拷贝
    list(mux.iter_deduped([_result(doc)]))
    assert doc == snap


# ---------------------------------------------------------------------------
# Architecture boundaries
# ---------------------------------------------------------------------------

_REPO = Path(__file__).resolve().parent.parent
_MUX_PATH = _REPO / "src" / "mindforge" / "source_mux.py"


def test_mux_does_not_import_any_specific_adapter() -> None:
    """mux 必须对所有 source_type 中立 —— 不能 import cubox/plain/pdf/docx 等。"""
    forbidden = {"cubox_markdown", "cubox_api", "plain_markdown", "webclip_markdown",
                 "pdf", "docx", "chat_export", "obsidian_vault"}
    tree = ast.parse(_MUX_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for f in forbidden:
                assert f not in node.module, (
                    f"source_mux.py 不应 import 具体 adapter 模块 {node.module!r}"
                )
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    assert f not in alias.name, (
                        f"source_mux.py 不应 import 具体 adapter {alias.name!r}"
                    )


def test_scanner_does_not_import_mux() -> None:
    """Scanner 不感知 mux —— mux 是 opt-in 的上层组合，不能侵入既有 scan 路径。"""
    scanner_src = (_REPO / "src" / "mindforge" / "scanner.py").read_text(encoding="utf-8")
    assert "source_mux" not in scanner_src


def test_cli_does_not_import_mux_in_default_path() -> None:
    """CLI 默认路径不引入 mux（保持向后兼容；mux 是 opt-in 增强）。

    这条边界确保引入 mux 后，所有既有命令的输出 / 行为字节级不变。
    """
    cli_src = (_REPO / "src" / "mindforge" / "cli.py").read_text(encoding="utf-8")
    assert "source_mux" not in cli_src


def test_mux_module_only_depends_on_scanner_and_sources_base() -> None:
    """mux 只能依赖 ScanResult 和 SourceDocument 两个稳定符号，不依赖业务层。"""
    forbidden = {"cli", "processor", "pipeline", "approver", "approval_service",
                 "review_service", "recall_service", "writer", "presenter"}
    tree = ast.parse(_MUX_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            last = node.module.split(".")[-1]
            assert last not in forbidden, (
                f"source_mux.py 禁止依赖 {node.module!r}（应只用 scanner + sources.base）"
            )
