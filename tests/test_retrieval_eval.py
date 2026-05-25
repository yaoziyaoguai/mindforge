"""v3.2 — 检索质量评估测试。

验证 eval_metrics 的正确性和 benchmark fixture 的完整性。
纯 deterministic 测试，不调用 LLM/embedding/vector DB。
"""

from __future__ import annotations


from mindforge.retrieval.eval_metrics import RelationPair, evaluate
from tests.fixtures.retrieval_benchmark import (
    build_benchmark,
    cards_to_relation_records,
)


class TestBenchmarkFixture:
    """验证 benchmark 数据的正确性。"""

    def test_benchmark_card_count(self):
        bm = build_benchmark()
        assert len(bm.cards) == 9, "benchmark 应有 9 张卡片"

    def test_ground_truth_not_empty(self):
        bm = build_benchmark()
        assert len(bm.ground_truth) > 0, "ground truth 不能为空"

    def test_unrelated_pairs_exist(self):
        bm = build_benchmark()
        assert len(bm.unrelated_pairs) > 0, "负例不能为空"

    def test_all_card_ids_unique(self):
        bm = build_benchmark()
        ids = [c.card_id for c in bm.cards]
        assert len(ids) == len(set(ids)), "卡片 ID 必须唯一"

    def test_ground_truth_refs_existing_cards(self):
        bm = build_benchmark()
        card_ids = {c.card_id for c in bm.cards}
        for gt in bm.ground_truth:
            assert gt.source_id in card_ids, f"source {gt.source_id} 不在 benchmark 中"
            assert gt.target_id in card_ids, f"target {gt.target_id} 不在 benchmark 中"

    def test_unrelated_pairs_do_not_share_attributes(self):
        """确保负例卡片对确实不共享任何可产生关系的属性。"""
        bm = build_benchmark()
        card_map = {c.card_id: c for c in bm.cards}
        for s_id, t_id in bm.unrelated_pairs:
            s = card_map[s_id]
            t = card_map[t_id]
            # 不共享 source_id
            assert s.source_id != t.source_id or s.source_id is None, (
                f"负例 {s_id}<->{t_id} 共享 source_id"
            )
            # 不共享 tags
            shared_tags = set(s.tags) & set(t.tags)
            assert len(shared_tags) == 0, f"负例 {s_id}<->{t_id} 共享 tags: {shared_tags}"
            # 不共享 wiki_sections
            shared_wiki = set(s.wiki_sections) & set(t.wiki_sections)
            assert len(shared_wiki) == 0, f"负例 {s_id}<->{t_id} 共享 wiki_sections: {shared_wiki}"

    def test_can_convert_cards_to_records(self):
        bm = build_benchmark()
        records = cards_to_relation_records(bm.cards)
        assert len(records) == len(bm.cards)
        for rec in records:
            assert "id" in rec
            assert "title" in rec
            assert "tags" in rec
            assert "wiki_sections" in rec


class TestEvalMetrics:
    """验证 eval_metrics 核心逻辑。"""

    def test_perfect_precision_recall(self):
        """完美匹配场景：检索结果 == ground truth。"""
        gt = [("a", "b", "same_tag"), ("b", "c", "same_tag")]
        retrieved = [
            RelationPair("a", "b", "same_tag", has_evidence=True),
            RelationPair("b", "c", "same_tag", has_evidence=True),
        ]
        report = evaluate(retrieved, gt, total_cards=3, cards_with_provenance=3)
        assert report.precision == 1.0
        assert report.recall == 1.0
        assert report.f1 == 1.0
        assert report.explainability_coverage == 1.0
        assert report.false_positive_count == 0

    def test_zero_precision_all_wrong(self):
        """全错场景：所有检索结果都不在 ground truth 中。"""
        gt = [("a", "b", "same_tag")]
        retrieved = [RelationPair("c", "d", "same_tag")]
        report = evaluate(retrieved, gt)
        assert report.precision == 0.0
        assert report.recall == 0.0
        assert report.f1 == 0.0
        assert report.false_positive_count == 1

    def test_zero_retrieved(self):
        """未检索到任何关系：precision=0, recall=0。"""
        gt = [("a", "b", "same_tag")]
        report = evaluate([], gt)
        assert report.precision == 0.0
        assert report.recall == 0.0
        assert report.total_retrieved == 0

    def test_empty_ground_truth(self):
        """空 ground truth 且无检索结果：precision=0, recall=0。"""
        report = evaluate([], [])
        assert report.precision == 0.0
        assert report.recall == 0.0

    def test_explainability_partial(self):
        """只有部分关系有 evidence。"""
        gt = [("a", "b", "same_tag")]
        retrieved = [
            RelationPair("a", "b", "same_tag", has_evidence=True),
            RelationPair("b", "c", "same_tag", has_evidence=False),
        ]
        report = evaluate(retrieved, gt)
        assert report.explainability_coverage == 0.5

    def test_negative_pair_violations(self):
        """负例检测：不应有关系却被检出的情况。"""
        gt: list[tuple[str, str, str]] = []
        retrieved = [RelationPair("x", "y", "same_tag")]
        negative = [("x", "y")]
        report = evaluate(retrieved, gt, negative_pairs=negative)
        assert report.negative_pair_violations == 1

    def test_no_violations_on_valid_pairs(self):
        """正例不应被记为违规。"""
        gt = [("a", "b", "same_tag")]
        retrieved = [RelationPair("a", "b", "same_tag")]
        negative = [("x", "y")]  # 不同对
        report = evaluate(retrieved, gt, negative_pairs=negative)
        assert report.negative_pair_violations == 0

    def test_provenance_coverage(self):
        """溯源覆盖计算。"""
        gt = [("a", "b", "same_tag")]
        retrieved = [RelationPair("a", "b", "same_tag")]
        report = evaluate(retrieved, gt, total_cards=10, cards_with_provenance=7)
        assert report.provenance_coverage == 0.7

    def test_summary_includes_key_metrics(self):
        gt = [("a", "b", "same_tag")]
        retrieved = [RelationPair("a", "b", "same_tag")]
        report = evaluate(retrieved, gt, total_cards=2, cards_with_provenance=2)
        assert "Precision=100.00%" in report.summary
        assert "Recall=100.00%" in report.summary
        assert "F1=100.00%" in report.summary

    def test_pair_normalization(self):
        """无序对规范化：(a,b) 和 (b,a) 应被视为同一关系。"""
        gt = [("a", "b", "same_tag")]
        retrieved = [RelationPair("b", "a", "same_tag")]  # 反向
        report = evaluate(retrieved, gt)
        assert report.total_correct == 1
        assert report.precision == 1.0
        assert report.recall == 1.0


class TestE2EIntegration:
    """端到端集成测试：benchmark → graph engine → eval。"""

    def test_graph_engine_on_benchmark(self):
        """使用 DeterministicGraphBuilder 在 benchmark 数据上运行并评估。"""
        from mindforge.relations.graph_builder import DeterministicGraphBuilder, NodeType

        bm = build_benchmark()
        records = cards_to_relation_records(bm.cards)
        builder = DeterministicGraphBuilder(records)

        card_ids = {c.card_id for c in bm.cards}

        # 为每张卡片检索关系（仅保留 card-to-card 边）
        all_retrieved: list[RelationPair] = []
        for card in bm.cards:
            graph = builder.get_graph(card.card_id, NodeType.CARD, depth=1)
            for edge in graph.edges:
                # 过滤非 card-to-card 的边（如 card-to-tag, card-to-wiki_section 等）
                if edge.source_id not in card_ids or edge.target_id not in card_ids:
                    continue
                has_ev = bool(edge.evidence and (edge.evidence.reason or edge.evidence.evidence))
                all_retrieved.append(RelationPair(
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    relation_type=edge.edge_type.value if edge.edge_type else "unknown",
                    has_evidence=has_ev,
                ))

        # 构建 ground truth
        gt = [(gt.source_id, gt.target_id, gt.relation_type) for gt in bm.ground_truth]

        # 溯源统计
        cards_with_prov = sum(1 for c in bm.cards if c.source_id is not None)

        report = evaluate(
            all_retrieved, gt,
            negative_pairs=list(bm.unrelated_pairs),
            total_cards=len(bm.cards),
            cards_with_provenance=cards_with_prov,
        )

        # 核心断言：benchmark 上的检索质量应满足最低标准
        assert report.total_retrieved > 0, "应至少检索到一些关系"
        assert report.recall >= 0.8, (
            f"recall ({report.recall:.2%}) 应 ≥ 80%：关系引擎应找回大部分 ground truth 关系"
        )
        assert report.negative_pair_violations == 0, (
            "负例卡片对之间不应错误检出关系（hallucinated relations）"
        )
