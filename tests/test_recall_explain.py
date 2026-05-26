"""v4.9 Direction C — Query Explain 测试。

验证 explain_zero_hits() 和 explain_hits() 的逻辑正确性。
纯 deterministic，不调用 LLM/embedding/vector DB。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.recall_service import (
    RecallIndexInfo,
    explain_hits,
    explain_zero_hits,
    run_bm25_recall,
)
from tests.test_recall_benchmark import _make_benchmark_config, _make_query
from tests.fixtures.recall_benchmark import build_recall_benchmark
from mindforge.config import load_mindforge_config


class TestExplainZeroHits:
    """验证 explain_zero_hits() 诊断逻辑。"""

    def test_diagnoses_empty_index(self):
        """空索引应提示'没有任何卡片'。"""
        index = RecallIndexInfo(
            source="memory-temp",
            used_disk=False,
            path=Path("/tmp/bm25.json"),
            vault_root=Path("/tmp"),
            cards_dir="20-Knowledge-Cards",
            stale=False,
            suggest_rebuild=True,
            card_counts={"total": 0, "human_approved": 0, "ai_draft": 0, "other": 0},
        )
        result = explain_zero_hits(_make_query("test"), index)

        assert result.is_zero_hits is True
        assert result.total_hits == 0
        assert "卡片" in result.miss_reason or "card" in str(result.miss_reason).lower()
        assert result.token_count > 0

    def test_diagnoses_no_approved_cards(self):
        """无已审批卡片时应提示先审批。"""
        index = RecallIndexInfo(
            source="disk",
            used_disk=True,
            path=Path("/tmp/bm25.json"),
            vault_root=Path("/tmp"),
            cards_dir="20-Knowledge-Cards",
            stale=False,
            suggest_rebuild=False,
            card_counts={"total": 10, "human_approved": 0, "ai_draft": 10, "other": 0},
        )
        result = explain_zero_hits(_make_query("test"), index)

        assert "human_approved" in result.miss_reason.lower() or "审批" in result.miss_reason

    def test_diagnoses_stale_index(self):
        """过期索引应提示 rebuild。"""
        index = RecallIndexInfo(
            source="memory-rebuilt-stale",
            used_disk=False,
            path=Path("/tmp/bm25.json"),
            vault_root=Path("/tmp"),
            cards_dir="20-Knowledge-Cards",
            stale=True,
            suggest_rebuild=True,
            card_counts={"total": 10, "human_approved": 5, "ai_draft": 5, "other": 0},
        )
        result = explain_zero_hits(_make_query("test"), index)

        assert "rebuild" in result.miss_reason.lower() or "重建" in result.miss_reason

    def test_diagnoses_track_filter(self):
        """按 track 过滤时可提示过于严格。"""
        index = RecallIndexInfo(
            source="disk",
            used_disk=True,
            path=Path("/tmp/bm25.json"),
            vault_root=Path("/tmp"),
            cards_dir="20-Knowledge-Cards",
            stale=False,
            suggest_rebuild=False,
            card_counts={"total": 10, "human_approved": 5, "ai_draft": 5, "other": 0},
        )
        result = explain_zero_hits(_make_query("test", track="engineering"), index)

        assert "track" in result.miss_reason.lower()

    def test_diagnoses_tag_filter(self):
        """按 tag 过滤时可提示过于严格。"""
        index = RecallIndexInfo(
            source="disk",
            used_disk=True,
            path=Path("/tmp/bm25.json"),
            vault_root=Path("/tmp"),
            cards_dir="20-Knowledge-Cards",
            stale=False,
            suggest_rebuild=False,
            card_counts={"total": 10, "human_approved": 5, "ai_draft": 5, "other": 0},
        )
        result = explain_zero_hits(_make_query("test", tags=("python",)), index)

        assert "tag" in result.miss_reason.lower()

    def test_include_boundary_note(self):
        """所有 explain 都应包含 BM25 边界说明。"""
        index = RecallIndexInfo(
            source="disk",
            used_disk=True,
            path=Path("/tmp/bm25.json"),
            vault_root=Path("/tmp"),
            cards_dir="20-Knowledge-Cards",
            stale=False,
            suggest_rebuild=False,
            card_counts={"total": 5, "human_approved": 3, "ai_draft": 2, "other": 0},
        )
        result = explain_zero_hits(_make_query("nonexistent_term_xyz"), index)

        assert result.boundary_note
        assert "BM25" in result.boundary_note


class TestExplainHits:
    """验证 explain_hits() 汇总逻辑。"""

    def test_explain_hits_with_golden_data(self, tmp_path: Path):
        """使用 golden benchmark 数据验证 explain_hits 输出的正确性。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("architecture"))
        explain = explain_hits(result)

        assert explain.is_zero_hits is False
        assert explain.total_hits > 0
        assert len(explain.matched_fields_summary) > 0, (
            "至少应有一个字段命中"
        )
        assert len(explain.top_contributing_terms) > 0, (
            "至少应有一个 contributing term"
        )
        assert "architecture" in explain.top_contributing_terms, (
            f"查询词 'architecture' 应出现在 top terms 中，"
            f"实际: {explain.top_contributing_terms}"
        )
        assert explain.boundary_note
        assert "BM25" in explain.boundary_note
        assert str(explain.total_hits) in explain.boundary_note

    def test_explain_hits_aggregates_fields(self, tmp_path: Path):
        """explain_hits 应正确汇总各字段的命中数。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("security"))
        explain = explain_hits(result)

        # 'security' 应主要在 tags 和 body 中命中
        all_fields = set(explain.matched_fields_summary.keys())
        relevant_fields = {"tags", "body_summary", "title", "body_risks"}
        assert all_fields & relevant_fields, (
            f"应至少命中 tags/body/title 之一，实际: {all_fields}"
        )

    def test_explain_hits_top_terms_sorted(self, tmp_path: Path):
        """top_contributing_terms 应按 contribution 降序排列。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("architecture design python"))
        explain = explain_hits(result)

        # 查询词应按相关性排序，'architecture' 应在最前面
        assert len(explain.top_contributing_terms) >= 2
        # 'architecture' 在 tags 中权重 3.0，应排第一
        assert explain.top_contributing_terms[0] == "architecture", (
            f"'architecture' 应为 top term，实际: {explain.top_contributing_terms[0]}"
        )

    def test_explain_safe_no_internal_paths(self, tmp_path: Path):
        """explain 输出不应包含内部路径或 secrets。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("architecture"))
        explain = explain_hits(result)

        # 检查安全边界
        explain_str = str(explain.miss_reason or "") + explain.boundary_note
        assert ".env" not in explain_str
        assert "secrets" not in explain_str.lower()
        assert "/tmp" not in explain.boundary_note  # 不应暴露临时路径
