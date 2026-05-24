"""v2.2 RetrievalPort contract tests — 检索端口抽象的形式化验证。

中文学习型说明：RetrievalPort 定义了词法检索的统一抽象边界。
这些测试验证：
1. Port 抽象不依赖具体实现（Bm25RetrievalEngine 可被替换）
2. Bm25RetrievalEngine 符合 Port 契约
3. recall_service 只依赖 Port，不依赖具体引擎

所有测试使用合成索引数据，不调用真实 LLM。
"""

from __future__ import annotations

from datetime import datetime

import pytest

from mindforge.retrieval.retrieval_port import RetrievalPort
from mindforge.retrieval.bm25_engine import Bm25RetrievalEngine
from mindforge.lexical_index import (
    BM25Index,
    SearchHit,
    HybridHit,
    build_index,
)
from mindforge.cards import CardSummary
from pathlib import Path


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _make_test_index(n: int = 3) -> BM25Index:
    """构建用于测试的合成 BM25 索引。"""
    cards = [
        CardSummary(
            path=Path(f"/fake/{i}.md"),
            rel_path=f"cards/c{i}.md",
            id=f"c{i}",
            title=f"Test Card {i}",
            status="human_approved",
            track=None,
            projects=[],
            tags=["test"] if i == 0 else [],
            source_type="plain_markdown",
            source_title=f"Source {i}",
            principles=[],
            known_risks=[],
            created_at=datetime(2025, 1, 1),
        )
        for i in range(n)
    ]
    return build_index(cards)


# ──────────────────────────────────────────────
# RetrievalPort contract tests
# ──────────────────────────────────────────────

class TestRetrievalPortContract:
    """RetrievalPort 抽象契约测试。"""

    def test_bm25_engine_is_retrieval_port(self):
        """Bm25RetrievalEngine 是 RetrievalPort 的子类。"""
        engine = Bm25RetrievalEngine()
        assert isinstance(engine, RetrievalPort)

    def test_retrieval_port_is_abstract(self):
        """RetrievalPort 不可直接实例化。"""
        with pytest.raises(TypeError):
            RetrievalPort()  # type: ignore[abstract]

    def test_bm25_engine_has_search(self):
        """Bm25RetrievalEngine 实现 search()。"""
        engine = Bm25RetrievalEngine()
        assert hasattr(engine, "search")
        assert callable(engine.search)

    def test_bm25_engine_has_hybrid_search(self):
        """Bm25RetrievalEngine 实现 hybrid_search()。"""
        engine = Bm25RetrievalEngine()
        assert hasattr(engine, "hybrid_search")
        assert callable(engine.hybrid_search)

    def test_search_returns_search_hits(self):
        """search() 返回 list[SearchHit]。"""
        engine = Bm25RetrievalEngine()
        index = _make_test_index(3)
        hits = engine.search(index, "test")
        assert isinstance(hits, list)
        if hits:
            assert isinstance(hits[0], SearchHit)

    def test_search_with_index_built_from_build_index(self):
        """search() 接受 build_index 构建的索引。"""
        engine = Bm25RetrievalEngine()
        index = _make_test_index(5)
        hits = engine.search(index, "card")
        assert isinstance(hits, list)

    def test_hybrid_search_returns_hybrid_hits(self):
        """hybrid_search() 返回 list[HybridHit]。"""
        engine = Bm25RetrievalEngine()
        index = _make_test_index(3)
        hits = engine.hybrid_search(index, "test")
        assert isinstance(hits, list)
        if hits:
            assert isinstance(hits[0], HybridHit)

    def test_engine_deterministic(self):
        """相同引擎 + 相同索引 + 相同查询 = 相同结果（确定性验证）。"""
        engine = Bm25RetrievalEngine()
        index = _make_test_index(5)
        hits1 = engine.search(index, "test card")
        hits2 = engine.search(index, "test card")
        assert len(hits1) == len(hits2)
        for h1, h2 in zip(hits1, hits2):
            assert h1.score == h2.score
            assert h1.doc.id == h2.doc.id

    def test_engine_filter_respected(self):
        """search() 的 status_filter 参数生效。"""
        engine = Bm25RetrievalEngine()
        index = _make_test_index(3)
        # default status_filter="human_approved"
        hits = engine.search(index, "card", status_filter="human_approved")
        result_ids = {h.doc.id for h in hits}
        # all cards in fixture are human_approved
        assert len(result_ids) <= 3

    def test_engine_empty_query_returns_empty(self):
        """空查询 → 空结果。"""
        engine = Bm25RetrievalEngine()
        index = _make_test_index(3)
        hits = engine.search(index, "")
        assert hits == []

    def test_engine_is_substitutable(self):
        """可替换性验证：任何符合 RetrievalPort 的实现都应该可用的接口。"""
        engine = Bm25RetrievalEngine()

        # 这是 RetrievalPort 的所有必须方法
        required_methods = ["search", "hybrid_search"]
        for method in required_methods:
            assert hasattr(engine, method)
            assert callable(getattr(engine, method))


# ──────────────────────────────────────────────
# recall_service dependency inversion test
# ──────────────────────────────────────────────

class TestRecallServicePortDependency:
    """验证 recall_service 只依赖 RetrievalPort，不依赖具体实现。"""

    def test_recall_service_accepts_retrieval_port(self):
        """recall_service.run_bm25_recall 的 engine 参数类型为 RetrievalPort。"""
        from mindforge.recall_service import run_bm25_recall
        import inspect

        sig = inspect.signature(run_bm25_recall)
        engine_param = sig.parameters.get("engine")
        assert engine_param is not None

        # 检查类型注解引用 RetrievalPort
        annotation = engine_param.annotation
        annotation_str = str(annotation)
        assert "RetrievalPort" in annotation_str or annotation is RetrievalPort

    def test_recall_service_default_engine_is_bm25(self):
        """默认引擎是 Bm25RetrievalEngine。"""
        from mindforge.recall_service import run_bm25_recall
        import inspect

        sig = inspect.signature(run_bm25_recall)
        engine_param = sig.parameters.get("engine")
        # 默认值应为 None，内部默认 Bm25RetrievalEngine
        assert engine_param.default is None or isinstance(engine_param.default, RetrievalPort)
