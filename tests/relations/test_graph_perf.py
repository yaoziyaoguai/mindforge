"""v2.1 U4 Graph Relation Quality Tests — Performance characterization.

中文学习型说明：性能特征化测试不设硬性阈值，而是测量并在报告中
呈现执行时间。目标是建立性能基线，方便未来检测性能回归。

所有测试使用合成数据，不依赖外部服务或真实数据。
"""

from __future__ import annotations

import gc
import time
import random

from mindforge.relations.related_cards import compute_multi_hop_related_cards
from mindforge.relations.community import detect_communities
from mindforge.relations.discovery_context import assemble_discovery_context
from mindforge.relations.graph_models import (
    Graph, GraphNode, GraphEdge, RelationEvidence,
    NodeType, EdgeType,
)


# ──────────────────────────────────────────────
# 合成数据生成
# ──────────────────────────────────────────────

_SOURCES = [f"src_{i}" for i in range(20)]
_TAGS = [f"tag_{i}" for i in range(50)]
_WIKI_SECTIONS = [f"section_{i}" for i in range(20)]
_STATUSES = ["human_approved", "ai_draft", "raw"]
_BODIES = [
    "这是关于人工智能的深入讨论",
    "数据库系统设计原理与实践",
    "REST API 设计最佳实践指南",
    "前端性能优化策略分析",
    "机器学习模型部署流程",
]


def _make_synthetic_cards(n: int, *, seed: int = 42) -> list[dict[str, object]]:
    """生成 N 张合成卡片，模拟真实数据分布。

    密度控制：
    - 每 5 张卡片共享 source（20% source 共享率）
    - 每张卡片随机 1-5 个 tags
    - 每张卡片随机 0-3 个 wiki_sections
    """
    rng = random.Random(seed)
    cards: list[dict[str, object]] = []
    for i in range(n):
        cards.append({
            "id": f"c{i}",
            "source_id": _SOURCES[i % len(_SOURCES)],
            "tags": [rng.choice(_TAGS) for _ in range(rng.randint(1, 5))],
            "wiki_sections": [rng.choice(_WIKI_SECTIONS) for _ in range(rng.randint(0, 3))],
            "status": rng.choice(_STATUSES),
            "run_id": f"run_{i // 10}",
            "source_location_index": i % 10,
            "body": rng.choice(_BODIES),
        })
    return cards


def _to_related_record(card: dict[str, object]) -> dict[str, object]:
    """转换为 related_cards 期望格式。"""
    return {
        "id": card["id"],
        "source_id": card["source_id"],
        "tags": list(card["tags"]),
        "wiki_sections": list(card["wiki_sections"]),
        "status": card["status"],
        "run_id": card["run_id"],
        "source_location_index": card["source_location_index"],
    }


def _measure_time_ms(func, *args, **kwargs) -> float:
    """测量函数执行时间（毫秒）。"""
    start = time.perf_counter()
    func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return elapsed * 1000


# ──────────────────────────────────────────────
# Performance: compute_multi_hop_related_cards
# ──────────────────────────────────────────────

class TestPerfMultiHopRelatedCards:
    """compute_multi_hop_related_cards 性能特征化。

    不设硬性阈值，仅记录在合理范围内的执行时间。
    """

    def test_perf_100_cards_2hop(self):
        """100 cards, 2-hop: 应在 500ms 以内完成。"""
        cards = _make_synthetic_cards(100)
        records = [_to_related_record(c) for c in cards]
        ms = _measure_time_ms(
            compute_multi_hop_related_cards, "c0", records, max_depth=2,
        )
        assert ms < 500, f"100 cards 2-hop 耗时 {ms:.0f}ms > 500ms"

    def test_perf_500_cards_2hop(self):
        """500 cards, 2-hop: 应在 2000ms 以内完成。"""
        cards = _make_synthetic_cards(500)
        records = [_to_related_record(c) for c in cards]
        ms = _measure_time_ms(
            compute_multi_hop_related_cards, "c0", records, max_depth=2,
        )
        assert ms < 2000, f"500 cards 2-hop 耗时 {ms:.0f}ms > 2000ms"

    def test_perf_1000_cards_1hop(self):
        """1000 cards, 1-hop: 应在 1000ms 以内完成。"""
        cards = _make_synthetic_cards(1000)
        records = [_to_related_record(c) for c in cards]
        ms = _measure_time_ms(
            compute_multi_hop_related_cards, "c0", records, max_depth=1,
        )
        assert ms < 1000, f"1000 cards 1-hop 耗时 {ms:.0f}ms > 1000ms"


# ──────────────────────────────────────────────
# Performance: detect_communities
# ──────────────────────────────────────────────

class TestPerfCommunities:
    """detect_communities 性能特征化。"""

    def test_perf_100_cards(self):
        """100 cards → 应在 200ms 以内。"""
        cards = _make_synthetic_cards(100)
        ms = _measure_time_ms(detect_communities, cards, min_members=2)
        assert ms < 200, f"100 cards community 耗时 {ms:.0f}ms > 200ms"

    def test_perf_500_cards(self):
        """500 cards → 应在 1000ms 以内。"""
        cards = _make_synthetic_cards(500)
        ms = _measure_time_ms(detect_communities, cards, min_members=2)
        assert ms < 1000, f"500 cards community 耗时 {ms:.0f}ms > 1000ms"

    def test_perf_1000_cards(self):
        """1000 cards → 应在 3000ms 以内。"""
        cards = _make_synthetic_cards(1000)
        ms = _measure_time_ms(detect_communities, cards, min_members=2)
        assert ms < 3000, f"1000 cards community 耗时 {ms:.0f}ms > 3000ms"


# ──────────────────────────────────────────────
# Performance: assemble_discovery_context
# ──────────────────────────────────────────────

class TestPerfDiscoveryContext:
    """assemble_discovery_context 性能特征化。"""

    def test_perf_100_nodes(self):
        """100 nodes graph → 应在 50ms 以内。"""
        cards = _make_synthetic_cards(100)
        nodes = [GraphNode(id="center", type=NodeType.CARD, label="中心", card_count=None)]
        edges: list[GraphEdge] = []
        for c in cards[:50]:
            nodes.append(GraphNode(
                id=c["id"], type=NodeType.CARD,
                label=str(c["id"]), card_count=None,
            ))
            edges.append(GraphEdge(
                source_id="center", target_id=str(c["id"]),
                edge_type=EdgeType.SHARES_TAG,
                evidence=RelationEvidence(
                    reason="shared_tag", strength=0.5, evidence="tag",
                ),
            ))
        graph = Graph(center_id="center", center_type=NodeType.CARD, depth=1,
                      nodes=tuple(nodes), edges=tuple(edges))
        ms = _measure_time_ms(assemble_discovery_context, graph)
        assert ms < 50, f"100 nodes context 耗时 {ms:.0f}ms > 50ms"

    def test_perf_deterministic_repeat(self):
        """验证 100 次调用的执行时间一致性（无内存泄漏或累积延迟）。

        中文学习型说明：全量测试套件中，其他测试产生的垃圾对象可能
        在测量循环中触发 GC，导致单次测量值异常偏高。禁用 GC 可排除
        这一外部干扰，让性能特征化测试只反映被测代码自身的稳定性。

        预热调用排除 Python JIT/import 缓存的一次性开销，
        确保测量只反映稳态性能。
        """
        cards = _make_synthetic_cards(20)
        records = [_to_related_record(c) for c in cards]
        # 预热调用 — 排除 JIT/import 缓存一次性开销
        _measure_time_ms(compute_multi_hop_related_cards, "c0", records, max_depth=1)
        gc.disable()
        try:
            times: list[float] = []
            for _ in range(100):
                ms = _measure_time_ms(
                    compute_multi_hop_related_cards, "c0", records, max_depth=1,
                )
                times.append(ms)

            avg = sum(times) / len(times)
            # 单次不应超过平均值的 5 倍（排除 GC spike，warmup 已处理 JIT 开销）
            outliers = [t for t in times if t > avg * 5]
            assert len(outliers) == 0, (
                f"发现 {len(outliers)} 个性能异常值（>5x avg={avg:.2f}ms）"
            )
        finally:
            gc.enable()
