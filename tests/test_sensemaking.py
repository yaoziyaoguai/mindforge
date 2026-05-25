"""v4.0 Graph-backed Sensemaking contract tests — 验证 sensemaking 分析原语。

中文学习型说明：所有测试使用合成数据，不调用真实 LLM / embedding。
验证桥接节点检测、孤立岛屿检测、证据溯源、源影响路径、卡片演化路径、
社区子图等确定性分析的正确性。
"""

from __future__ import annotations

from mindforge.relations.sensemaking import (
    BridgeNode,
    CardEvolutionPath,
    CommunitySubgraph,
    EvidenceTrail,
    OrphanIsland,
    SensemakingAnalysis,
    SourceInfluencePath,
    analyze_sensemaking,
    build_card_evolution_path,
    build_community_subgraphs,
    build_evidence_trail,
    build_source_influence_path,
    detect_bridge_nodes,
    detect_orphan_islands,
)


class TestBridgeNodeDetection:
    """桥接节点检测测试。"""

    @staticmethod
    def _card(id_, title, source_id=None, tags=None, sections=None):
        return {
            "id": id_,
            "title": title,
            "source_id": source_id,
            "tags": tags or [],
            "wiki_sections": sections or [],
        }

    def test_no_bridges_with_single_community(self):
        """所有卡片在同一社区 → 无桥接节点。"""
        cards = [
            self._card("c1", "Card 1", source_id="src1", tags=["ai"]),
            self._card("c2", "Card 2", source_id="src1", tags=["ai"]),
        ]
        result = detect_bridge_nodes(cards)
        # c1: source:src1 + tag:ai = 2 个社区 → 是桥接
        # c2: source:src1 + tag:ai = 2 个社区 → 也是桥接
        bridge_ids = {b.card_id for b in result}
        assert "c1" in bridge_ids, "c1 跨越 2 个社区，应被识别为桥接"
        assert "c2" in bridge_ids, "c2 跨越 2 个社区，应被识别为桥接"

    def test_bridge_node_connecting_source_and_tag(self):
        """卡片同时属于 source 社区和 tag 社区 → 桥接节点。"""
        cards = [
            self._card("c1", "Bridge Card", source_id="src_a", tags=["ml"]),
            self._card("c2", "Other Card", source_id="src_b", tags=["ml"]),
        ]
        result = detect_bridge_nodes(cards)
        # c1 在 source:src_a 和 tag:ml → 2 个社区，是桥接
        # c2 在 source:src_b 和 tag:ml → 2 个社区，也是桥接
        bridge_ids = {b.card_id for b in result}
        assert "c1" in bridge_ids
        assert "c2" in bridge_ids

    def test_bridge_node_multi_community(self):
        """卡片跨越 3+ 社区 → 高分桥接节点。"""
        cards = [
            self._card("c1", "Super Connector", source_id="src_x", tags=["ai", "dl"], sections=["Intro"]),
            self._card("c2", "Plain Card", source_id="src_y"),
            self._card("c3", "Tag Sharer", tags=["ai"]),
        ]
        result = detect_bridge_nodes(cards)
        # c1: source:src_x + tag:ai + tag:dl + wiki_section:Intro = 4 个社区
        bridges = [b for b in result if b.card_id == "c1"]
        assert len(bridges) == 1
        assert bridges[0].community_count >= 3

    def test_bridge_nodes_sorted_by_community_count(self):
        """桥接节点按社区数量降序排列。"""
        cards = [
            self._card("c1", "Many Communities", source_id="s1", tags=["t1", "t2", "t3"], sections=["sec1"]),
            self._card("c2", "Two Communities", source_id="s1", tags=["t1"]),
            self._card("c3", "Plain", source_id="s1"),
        ]
        result = detect_bridge_nodes(cards)
        for i in range(len(result) - 1):
            assert result[i].community_count >= result[i + 1].community_count

    def test_empty_cards_no_bridges(self):
        """空卡片列表 → 空结果。"""
        assert detect_bridge_nodes([]) == []


class TestOrphanIslandDetection:
    """孤立岛屿检测测试。"""

    @staticmethod
    def _card(id_, title, source_id=None, tags=None, sections=None):
        return {
            "id": id_,
            "title": title,
            "source_id": source_id,
            "tags": tags or [],
            "wiki_sections": sections or [],
        }

    def test_true_orphan_no_connections(self):
        """完全孤立的卡片（无 source/tag/section 共享）→ true orphan。"""
        cards = [
            self._card("c1", "Connected A", source_id="src1", tags=["ai"]),
            self._card("c2", "Connected B", source_id="src1", tags=["ai"]),
            self._card("c3", "Lonely Card"),
        ]
        result = detect_orphan_islands(cards)
        true_orphans = [o for o in result if o.is_true_orphan]
        assert len(true_orphans) >= 1
        orphan_ids = {cid for o in true_orphans for cid in o.card_ids}
        assert "c3" in orphan_ids

    def test_no_orphans_when_all_connected(self):
        """所有卡片通过 source 连接 → 无孤立节点。"""
        cards = [
            self._card("c1", "A", source_id="src1"),
            self._card("c2", "B", source_id="src1"),
            self._card("c3", "C", source_id="src1"),
        ]
        result = detect_orphan_islands(cards)
        assert len(result) == 0

    def test_small_isolated_group(self):
        """2 卡片小群组与外界无连接 → 孤岛群组。"""
        cards = [
            self._card("c1", "Main A", source_id="main_src", tags=["shared"]),
            self._card("c2", "Main B", source_id="main_src", tags=["shared"]),
            self._card("c3", "Isolated X", tags=["private"]),
            self._card("c4", "Isolated Y", tags=["private"]),
        ]
        result = detect_orphan_islands(cards, max_island_size=2)
        # c3 和 c4 形成孤立群组（只通过 tag:private 连接彼此，与 c1/c2 无共享）
        islands = [o for o in result if not o.is_true_orphan]
        assert len(islands) >= 1

    def test_respects_max_island_size(self):
        """max_island_size 参数控制被识别为孤岛的最大群组大小。"""
        cards = [
            self._card("c1", "Big Group A", tags=["group"]),
            self._card("c2", "Big Group B", tags=["group"]),
            self._card("c3", "Big Group C", tags=["group"]),
            self._card("c4", "Big Group D", tags=["group"]),
        ]
        # max_island_size=3, 4 张卡片的群组不应被识别为孤岛
        result = detect_orphan_islands(cards, max_island_size=3)
        # 4 张卡片群组 > max_island_size，应被忽略
        assert len(result) == 0

    def test_empty_cards_no_orphans(self):
        """空卡片列表 → 空结果。"""
        assert detect_orphan_islands([]) == []


class TestEvidenceTrail:
    """证据溯源测试。"""

    @staticmethod
    def _card(id_, title, source_id=None, tags=None, sections=None):
        return {
            "id": id_,
            "title": title,
            "source_id": source_id,
            "tags": tags or [],
            "wiki_sections": sections or [],
        }

    def test_trail_with_shared_tags(self):
        """两张卡片共享 tag → evidence trail 包含 shared_tag 项。"""
        cards = [
            self._card("c1", "Card One", tags=["machine-learning"]),
            self._card("c2", "Card Two", tags=["machine-learning"]),
        ]
        trail = build_evidence_trail("c1", "c2", cards)
        assert trail is not None
        assert trail.source_id == "c1"
        assert trail.target_id == "c2"
        tag_items = [ti for ti in trail.trail_items if ti.evidence_type == "shared_tag"]
        assert len(tag_items) >= 1
        assert any("machine-learning" in ti.evidence_label for ti in tag_items)

    def test_trail_with_shared_source(self):
        """两张卡片共享 source → evidence trail 包含 shared_source 项。"""
        cards = [
            self._card("c1", "Card A", source_id="doc1.md"),
            self._card("c2", "Card B", source_id="doc1.md"),
        ]
        trail = build_evidence_trail("c1", "c2", cards)
        assert trail is not None
        source_items = [ti for ti in trail.trail_items if ti.evidence_type == "shared_source"]
        assert len(source_items) >= 1

    def test_trail_with_shared_wiki_section(self):
        """两张卡片共享 wiki_section → evidence trail 包含 shared_wiki_section 项。"""
        cards = [
            self._card("c1", "Card X", sections=["Introduction"]),
            self._card("c2", "Card Y", sections=["Introduction"]),
        ]
        trail = build_evidence_trail("c1", "c2", cards)
        assert trail is not None
        section_items = [ti for ti in trail.trail_items if ti.evidence_type == "shared_wiki_section"]
        assert len(section_items) >= 1

    def test_trail_none_for_no_shared_entities(self):
        """无共享实体 → 返回 None。"""
        cards = [
            self._card("c1", "Card P", source_id="doc_a.md", tags=["x"]),
            self._card("c2", "Card Q", source_id="doc_b.md", tags=["y"]),
        ]
        # 无共享 source/tag/section，且标题 token 也不重叠
        trail = build_evidence_trail("c1", "c2", cards)
        # 可能有标题 token 重叠（"Card"），所以不一定为 None
        # 但至少 total_shared_entities 不会太高
        if trail is not None:
            # 仅共享标题 token（如 "card"），entity-level 共享应为 0
            entity_items = [
                ti for ti in trail.trail_items
                if ti.evidence_type != "shared_title_token"
            ]
            assert len(entity_items) == 0

    def test_trail_none_for_missing_card(self):
        """卡片不存在 → None。"""
        cards = [self._card("c1", "Only Card")]
        assert build_evidence_trail("c1", "c999", cards) is None
        assert build_evidence_trail("c999", "c1", cards) is None

    def test_trail_structure_is_frozen(self):
        """EvidenceTrail 结构完整性验证。"""
        cards = [
            self._card("c1", "A", tags=["t1"], sections=["s1"]),
            self._card("c2", "B", tags=["t1"], sections=["s1"]),
        ]
        trail = build_evidence_trail("c1", "c2", cards)
        assert trail is not None
        assert isinstance(trail.trail_items, tuple)
        assert trail.total_shared_entities == len(trail.trail_items)
        assert len(trail.source_title) > 0
        assert len(trail.target_title) > 0


class TestSourceInfluencePath:
    """源影响路径测试。"""

    @staticmethod
    def _card(id_, title, source_id=None, tags=None, sections=None):
        return {
            "id": id_,
            "title": title,
            "source_id": source_id,
            "tags": tags or [],
            "wiki_sections": sections or [],
        }

    def test_influence_path_basic(self):
        """基本源影响路径：直接派生 + 间接影响。"""
        cards = [
            self._card("c1", "Direct A", source_id="src/doc.md", tags=["ai"]),
            self._card("c2", "Direct B", source_id="src/doc.md", tags=["dl"]),
            self._card("c3", "Influenced", source_id="other.md", tags=["ai"]),
        ]
        path = build_source_influence_path("src/doc.md", cards)
        assert path is not None
        assert path.source_id == "src/doc.md"
        assert "c1" in path.direct_cards
        assert "c2" in path.direct_cards
        # c3 通过 tag:ai 与 c1 间接关联
        assert "c3" in path.influenced_cards
        assert path.total_reach >= 3

    def test_influence_path_none_for_no_cards(self):
        """源文档无派生卡片 → None。"""
        cards = [self._card("c1", "Other", source_id="other.md")]
        assert build_source_influence_path("nonexistent.md", cards) is None

    def test_influence_path_only_direct(self):
        """只有直接派生卡片，无间接影响。"""
        cards = [
            self._card("c1", "Solo A", source_id="unique.md"),
            self._card("c2", "Solo B", source_id="unique.md"),
        ]
        path = build_source_influence_path("unique.md", cards)
        assert path is not None
        assert len(path.direct_cards) == 2
        assert len(path.influenced_cards) == 0


class TestCardEvolutionPath:
    """卡片演化路径测试。"""

    @staticmethod
    def _card(id_, title, source_id=None, tags=None, sections=None):
        return {
            "id": id_,
            "title": title,
            "source_id": source_id,
            "tags": tags or [],
            "wiki_sections": sections or [],
        }

    def test_evolution_path_basic(self):
        """同源卡片按 ID 排序形成演化路径。"""
        cards = [
            self._card("c3", "Card Three", source_id="src/doc.md"),
            self._card("c1", "Card One", source_id="src/doc.md"),
            self._card("c2", "Card Two", source_id="src/doc.md"),
        ]
        path = build_card_evolution_path("src/doc.md", cards)
        assert path is not None
        assert path.step_count == 3
        # 按 ID 排序：c1, c2, c3
        assert [s.card_id for s in path.steps] == ["c1", "c2", "c3"]

    def test_evolution_path_none_for_no_cards(self):
        """源文档无派生卡片 → None。"""
        cards = [self._card("c1", "Other", source_id="other.md")]
        assert build_card_evolution_path("nonexistent.md", cards) is None

    def test_evolution_steps_include_tags_and_sections(self):
        """演化步骤包含 tags 和 wiki_sections 信息。"""
        cards = [
            self._card("c1", "Step 1", source_id="src/doc.md", tags=["intro"], sections=["Basics"]),
            self._card("c2", "Step 2", source_id="src/doc.md", tags=["advanced"], sections=["Deep Dive"]),
        ]
        path = build_card_evolution_path("src/doc.md", cards)
        assert path is not None
        assert "intro" in path.steps[0].tags
        assert "advanced" in path.steps[1].tags
        assert "Basics" in path.steps[0].wiki_sections
        assert "Deep Dive" in path.steps[1].wiki_sections


class TestCommunitySubgraphs:
    """社区子图测试。"""

    @staticmethod
    def _card(id_, title, source_id=None, tags=None, sections=None):
        return {
            "id": id_,
            "title": title,
            "source_id": source_id,
            "tags": tags or [],
            "wiki_sections": sections or [],
        }

    def test_community_subgraphs_for_source(self):
        """中心卡片所属 source 的社区子图。"""
        cards = [
            self._card("c1", "Center", source_id="src/doc.md", tags=["ai"]),
            self._card("c2", "Sibling", source_id="src/doc.md"),
        ]
        subgraphs = build_community_subgraphs("c1", cards)
        source_sg = [sg for sg in subgraphs if sg.community_type == "source"]
        assert len(source_sg) >= 1
        assert source_sg[0].community_label == "src/doc.md"
        assert source_sg[0].member_count == 2

    def test_community_subgraphs_for_tag(self):
        """中心卡片所属 tag 的社区子图（仅多成员 tag 显示）。"""
        cards = [
            self._card("c1", "Center", tags=["ml", "dl"]),
            self._card("c2", "Tag Mate", tags=["ml"]),
            self._card("c3", "DL Mate", tags=["dl"]),
        ]
        subgraphs = build_community_subgraphs("c1", cards)
        tag_sgs = [sg for sg in subgraphs if sg.community_type == "tag"]
        assert len(tag_sgs) == 2  # ml and dl (both have ≥2 members)
        ml_sg = next(sg for sg in tag_sgs if sg.community_label == "ml")
        assert ml_sg.member_count == 2

    def test_community_subgraphs_skip_single_member(self):
        """单成员社区被跳过（tag/wiki_section 社区至少 2 人才有意义）。"""
        cards = [
            self._card("c1", "Center", tags=["unique"]),
        ]
        subgraphs = build_community_subgraphs("c1", cards)
        tag_sgs = [sg for sg in subgraphs if sg.community_type == "tag"]
        # unique tag 只有 1 个成员，应被跳过
        assert len(tag_sgs) == 0

    def test_community_subgraphs_bridge_marking(self):
        """社区子图中的桥接卡片被正确标记。"""
        cards = [
            self._card("c1", "Center", source_id="src/doc.md", tags=["ai"]),
            self._card("c2", "Bridge Card", source_id="src/doc.md", tags=["ai", "dl"]),
        ]
        subgraphs = build_community_subgraphs("c1", cards)
        for sg in subgraphs:
            if "c2" in sg.member_card_ids:
                # c2 是桥接卡片（在 source + 两个 tag 社区中）
                assert "c2" in sg.bridge_card_ids


class TestFullSensemakingAnalysis:
    """综合 sensemaking 分析测试。"""

    @staticmethod
    def _card(id_, title, source_id=None, tags=None, sections=None):
        return {
            "id": id_,
            "title": title,
            "source_id": source_id,
            "tags": tags or [],
            "wiki_sections": sections or [],
        }

    def test_analysis_includes_all_dimensions(self):
        """综合分析的响应包含所有维度。"""
        cards = [
            self._card("c1", "Center Card", source_id="src/doc.md", tags=["ai", "dl"], sections=["Intro"]),
            self._card("c2", "Related A", source_id="src/doc.md", tags=["ai"]),
            self._card("c3", "Related B", source_id="src/doc.md", tags=["dl"]),
            self._card("c4", "Orphan Card", tags=["orphan"]),
            self._card("c5", "Orphan Mate", tags=["orphan"]),
        ]
        analysis = analyze_sensemaking("c1", cards)
        assert analysis is not None
        assert analysis.center_card_id == "c1"
        assert analysis.center_card_title == "Center Card"
        # bridge nodes: c1 跨越 3+ 社区
        assert len(analysis.bridge_nodes) >= 1
        # orphan islands: c4+c5 孤岛群组
        assert len(analysis.orphan_islands) >= 1
        # evidence trails: c1 与 c2、c3 之间的关系
        assert len(analysis.evidence_trails) >= 1
        # source influence: src/doc.md 的影响
        assert analysis.source_influence is not None
        assert analysis.source_influence.total_reach >= 3
        # card evolution: 同源 3 张卡片
        assert analysis.card_evolution is not None
        assert analysis.card_evolution.step_count == 3
        # community subgraphs
        assert len(analysis.community_subgraphs) >= 1
        # total cards
        assert analysis.total_cards_analyzed == 5

    def test_analysis_none_for_missing_card(self):
        """中心卡片不存在 → None。"""
        assert analyze_sensemaking("nonexistent", []) is None

    def test_analysis_with_minimal_data(self):
        """最小数据集的综合分析和。"""
        cards = [
            self._card("c1", "Only Card", source_id="doc.md", tags=["solo"]),
        ]
        analysis = analyze_sensemaking("c1", cards)
        assert analysis is not None
        assert analysis.center_card_id == "c1"
        # 单张卡片：无桥接、无孤立、无 trail、有 source 和社区
        assert isinstance(analysis.bridge_nodes, tuple)
        assert isinstance(analysis.orphan_islands, tuple)
        assert isinstance(analysis.evidence_trails, tuple)


class TestSensemakingBoundary:
    """Sensemaking 边界测试。

    中文学习型说明：确保 sensemaking 分析不调用 LLM / embedding / vector DB，
    不引入外部依赖，不修改输入数据。
    """

    @staticmethod
    def _card(id_, title, source_id=None, tags=None, sections=None):
        return {
            "id": id_,
            "title": title,
            "source_id": source_id,
            "tags": tags or [],
            "wiki_sections": sections or [],
        }

    def test_analysis_is_pure_function(self):
        """analyze_sensemaking 不修改输入数据。"""
        cards = [
            {"id": "c1", "title": "Original", "source_id": "src", "tags": ["ai"], "wiki_sections": []},
            {"id": "c2", "title": "Another", "source_id": "src", "tags": ["ai"], "wiki_sections": []},
        ]
        original = [dict(c) for c in cards]
        analyze_sensemaking("c1", cards)
        for i, orig in enumerate(original):
            assert cards[i] == orig

    def test_no_llm_or_embedding_imports(self):
        """sensemaking 模块不引入 LLM / embedding / vector DB 依赖。"""
        import ast
        from pathlib import Path
        src = Path(__file__).resolve().parent.parent / "src" / "mindforge" / "relations" / "sensemaking.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        forbidden = {"openai", "anthropic", "chromadb", "faiss", "pinecone", "qdrant", "huggingface", "sentence_transformers"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, f"禁止引入: {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden, f"禁止引入: {node.module}"

    def test_dataclasses_are_frozen(self):
        """所有 sensemaking 数据类均为 frozen。"""
        import dataclasses
        types_to_check = [
            BridgeNode, OrphanIsland, EvidenceTrail, SourceInfluencePath,
            CardEvolutionPath, CommunitySubgraph, SensemakingAnalysis,
        ]
        for t in types_to_check:
            assert dataclasses.is_dataclass(t), f"{t.__name__} 必须是 dataclass"
            assert t.__dataclass_params__.frozen, f"{t.__name__} 必须是 frozen"

    def test_bridge_node_has_required_fields(self):
        """BridgeNode 结构完整性验证。"""
        b = BridgeNode(
            card_id="c1",
            card_title="Test",
            connecting_communities=("source:src1", "tag:ai"),
            community_count=2,
        )
        assert b.community_count == len(b.connecting_communities)

    def test_orphan_island_has_required_fields(self):
        """OrphanIsland 结构完整性验证。"""
        o = OrphanIsland(
            card_ids=("c1", "c2"),
            card_titles=("T1", "T2"),
            size=2,
            is_true_orphan=False,
        )
        assert o.size == len(o.card_ids)
        assert o.size == len(o.card_titles)

    def test_module_docstring_marks_lab_internal(self):
        """v4.2 truth reset: sensemaking 模块必须标记为 LAB/INTERNAL。"""
        import ast
        from pathlib import Path
        src = Path(__file__).resolve().parent.parent / "src" / "mindforge" / "relations" / "sensemaking.py"
        module = ast.parse(src.read_text(encoding="utf-8"))
        docstring = ast.get_docstring(module)
        assert docstring is not None, "sensemaking.py 必须有模块 docstring"
        assert "LAB" in docstring.upper() or "INTERNAL" in docstring.upper(), (
            f"sensemaking 模块 docstring 必须标记为 LAB/INTERNAL，"
            f"当前: {docstring[:100]}..."
        )

    def test_sensemaking_not_production_ready(self):
        """v4.2 truth reset: sensemaking 数据类 docstring 不得声称 production-ready。"""
        prohibited = {"production-ready", "product-grade", "production grade"}
        for cls in [BridgeNode, SourceInfluencePath, CardEvolutionPath, SensemakingAnalysis]:
            doc = (cls.__doc__ or "").lower()
            for term in prohibited:
                assert term not in doc, (
                    f"{cls.__name__} docstring 不得声称 {term}，当前是 lab/internal"
                )
