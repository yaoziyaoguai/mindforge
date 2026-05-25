"""v0.6 Graph API tests — 图 API endpoint 集成测试。

中文学习型说明：测试 Graph API 的三端点（/node、/explore、/edge）和
Graph → GraphResponse 转换逻辑。使用临时 vault 和 TestClient。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from mindforge_web.app import create_app


# ── Helpers ────────────────────────────────────────


def _make_temp_vault(tmp_path: Path) -> tuple[Path, Path, Path]:
    """创建临时 vault，包含 approved cards 用于图测试。"""
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox"
    cards_dir = vault / "20-Knowledge-Cards"
    inbox.mkdir(parents=True)
    cards_dir.mkdir(parents=True)

    # 创建几张 approved cards
    _write_card(cards_dir, "card_1.md", {
        "id": "card_1",
        "title": "Card One",
        "status": "human_approved",
        "source_id": "src_1",
        "tags": ["ai", "llm"],
        "wiki_sections": ["Machine Learning"],
        "run_id": "run_1",
        "source_location_index": 0,
        "body": "Card one body about AI and LLM.",
    })
    _write_card(cards_dir, "card_2.md", {
        "id": "card_2",
        "title": "Card Two",
        "status": "human_approved",
        "source_id": "src_1",
        "tags": ["ai", "db"],
        "wiki_sections": ["Machine Learning"],
        "run_id": "run_1",
        "source_location_index": 1,
        "body": "Card two body about AI and databases.",
    })
    _write_card(cards_dir, "card_3.md", {
        "id": "card_3",
        "title": "Card Three",
        "status": "human_approved",
        "source_id": "src_2",
        "tags": ["db"],
        "wiki_sections": ["Database"],
        "run_id": "run_1",
        "source_location_index": 0,
        "body": "Card three body about databases.",
    })

    config: dict = {
        "version": 0.7,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {
            "enabled": ["plain_markdown"],
            "registry": {
                "plain_markdown": {
                    "adapter": "PlainMarkdownAdapter",
                    "inbox_subdir": ".",
                    "file_glob": "*.md",
                    "enabled": True,
                }
            },
        },
        "state": {
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
            "backup_state": True,
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "default_model": None,
            "models": {},
        },
        "approval": {
            "prompt_version_only": "v1.0",
        },
    }
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.dump(config))
    return cfg_path, vault, cards_dir


def _write_card(cards_dir: Path, filename: str, frontmatter: dict) -> None:
    import json
    lines = ["---"]
    for key, value in frontmatter.items():
        if key == "body":
            continue
        if isinstance(value, list):
            lines.append(f"{key}: {json.dumps(value)}")
        else:
            lines.append(f"{key}: {value!s}")
    lines.append("---")
    lines.append("")
    lines.append(frontmatter.get("body", ""))
    (cards_dir / filename).write_text("\n".join(lines))


# ── API Endpoint Tests ─────────────────────────────


class TestGraphNodeEndpoint:
    def test_graph_node_returns_200(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/node?ref=card_1&depth=1")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["center_id"] == "card_1"
        assert data["center_type"] == "card"
        assert data["depth"] == 1
        assert len(data["nodes"]) > 0
        assert len(data["edges"]) > 0

    def test_graph_node_2_hop(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/node?ref=card_1&depth=2")
        assert resp.status_code == 200, resp.text

    def test_graph_node_missing_card_returns_404(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/node?ref=nonexistent")
        assert resp.status_code == 404

    def test_every_edge_has_evidence(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/node?ref=card_1&depth=1")
        assert resp.status_code == 200
        for edge in resp.json()["edges"]:
            assert edge["evidence"]["reason"], "Edge missing reason"
            assert edge["evidence"]["evidence"], "Edge missing evidence text"
            assert edge["evidence"]["strength"] > 0, "Edge strength should be > 0"


class TestGraphExploreEndpoint:
    def test_explore_source(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/explore?node_type=source&node_id=src_1")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["center_type"] == "source"
        card_ids = {n["id"] for n in data["nodes"] if n["type"] == "card"}
        assert "card_1" in card_ids
        assert "card_2" in card_ids

    def test_explore_tag(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/explore?node_type=tag&node_id=ai")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        card_ids = {n["id"] for n in data["nodes"] if n["type"] == "card"}
        assert "card_1" in card_ids
        assert "card_2" in card_ids

    def test_explore_invalid_type_returns_404(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/explore?node_type=invalid&node_id=x")
        assert resp.status_code == 404

    def test_explore_unsupported_type_returns_422(self, tmp_path: Path):
        """v4.2 truth reset: community/topic/entity/concept_candidate 尚未实现，
        传入必须返回 422 UnsupportedNodeType，不得返回空图冒充成功。"""
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        unsupported_types = ["community", "topic", "entity", "concept_candidate"]
        for nt in unsupported_types:
            resp = client.get(f"/api/graph/explore?node_type={nt}&node_id=test")
            assert resp.status_code == 422, (
                f"不支持的 node_type={nt} 应返回 422，实际 {resp.status_code}: {resp.text}"
            )
            data = resp.json()
            assert "unsupported_node_type" in data.get("detail", {}).get("error", ""), (
                f"错误码应包含 unsupported_node_type: {data}"
            )


class TestGraphEdgeEndpoint:
    def test_edge_between_related_cards(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/edge?source=card_1&target=card_2")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["source_id"] == "card_1"
        assert data["target_id"] == "card_2"
        assert len(data["edges"]) > 0
        for edge in data["edges"]:
            assert edge["evidence"]["reason"]
            assert edge["evidence"]["strength"] > 0

    def test_edge_between_unrelated_cards_returns_404(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/edge?source=card_1&target=nonexistent")
        assert resp.status_code == 404


class TestGraphResponseSchema:
    def test_graph_response_matches_schema(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/node?ref=card_1&depth=1")
        assert resp.status_code == 200
        data = resp.json()
        # 验证顶层字段
        assert "center_id" in data
        assert "center_type" in data
        assert "depth" in data
        assert "nodes" in data
        assert "edges" in data
        # 验证 node 字段
        node = data["nodes"][0]
        assert "id" in node
        assert "type" in node
        assert "label" in node
        assert "card_count" in node
        # 验证 edge 字段
        edge = data["edges"][0]
        assert "source_id" in edge
        assert "target_id" in edge
        assert "edge_type" in edge
        assert "evidence" in edge
        ev = edge["evidence"]
        assert "reason" in ev
        assert "evidence" in ev
        assert "strength" in ev


# ── R6 Discovery Context API Tests ───────────────────


class TestDiscoveryContextEndpoint:
    def test_discovery_context_returns_200(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/discovery/context?ref=card_1")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["center_card_id"] == "card_1"
        assert data["center_card_title"] == "Card One"
        assert "direct_matches" in data
        assert "neighbor_cards" in data
        assert "wiki_sections" in data
        assert "shared_tags" in data
        assert "shared_sources" in data

    def test_discovery_context_has_direct_matches(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/discovery/context?ref=card_1")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["direct_matches"], list), "direct_matches 必须是 list"
        # 非空时验证字段
        for match in data["direct_matches"]:
            assert match["relation_reason"]
            assert match["relation_strength"] > 0
            assert match["evidence"]

    def test_discovery_context_missing_card_returns_404(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/discovery/context?ref=nonexistent")
        assert resp.status_code == 404

    def test_discovery_context_wiki_sections(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/discovery/context?ref=card_1")
        assert resp.status_code == 200
        data = resp.json()
        section_names = {s["section_title"] for s in data["wiki_sections"]}
        assert "Machine Learning" in section_names


class TestRecallWithGraphContext:
    def test_recall_graph_context_enriches_hits(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/recall?q=Card&context=graph")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["hits"]) > 0
        for hit in data["hits"]:
            assert "graph_neighbor_count" in hit
            assert "graph_shared_tag_count" in hit

    def test_recall_without_context_has_null_graph_fields(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/recall?q=Card")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for hit in data["hits"]:
            assert hit.get("graph_neighbor_count") is None
            assert hit.get("graph_shared_tag_count") is None


class TestGraphEvidenceQuality:
    """v0.7 U4：API response 中 evidence 文本和 detail 字段的质量验证。"""

    def test_edge_evidence_no_machine_format(self, tmp_path: Path):
        """API 返回的边 evidence 不应包含机器格式标记。"""
        cfg_path, _vault, _cards = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/node?ref=card_1&depth=1")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # card_1 和 card_2 共享 source_id=src_1，应有 related_by_source 边
        for edge in data.get("edges", []):
            ev = edge.get("evidence")
            assert ev is not None, f"Edge {edge} has no evidence"
            assert "↔" not in ev.get("evidence", ""), \
                f"Evidence should not contain machine ↔: {ev.get('evidence')}"
            assert ev.get("evidence"), "Evidence text should not be empty"

    def test_edge_evidence_detail_has_relation_reason(self, tmp_path: Path):
        """API 返回的边 evidence.detail 应包含 relation_reason。"""
        cfg_path, _vault, _cards = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/node?ref=card_1&depth=1")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for edge in data.get("edges", []):
            detail = edge.get("evidence", {}).get("detail", {})
            assert "relation_reason" in detail, \
                f"Edge evidence.detail should have relation_reason: {detail}"

    def test_graph_node_invalid_depth_clamped(self, tmp_path: Path):
        """验证 depth 参数超出范围时的行为（当前 clamp 到 1-3）。"""
        cfg_path, _vault, _cards = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        # depth=0 should still return a valid graph (clamped to 1)
        resp = client.get("/api/graph/node?ref=card_1&depth=0")
        assert resp.status_code in (200, 422), resp.text
        data = resp.json()
        assert "nodes" in data or "detail" in data
        # depth=10 should be clamped to 3 (max)
        resp = client.get("/api/graph/node?ref=card_1&depth=10")
        assert resp.status_code in (200, 422), resp.text


class TestKnowledgeCommunitiesEndpoint:
    """v1.2 U3: GET /api/knowledge/communities 端点测试。"""

    def test_returns_200(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/knowledge/communities")
        assert resp.status_code == 200, resp.text

    def test_response_has_communities_list(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/knowledge/communities")
        data = resp.json()
        assert "communities" in data, data
        assert isinstance(data["communities"], list)

    def test_community_has_required_fields(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/knowledge/communities")
        data = resp.json()
        for c in data["communities"]:
            assert "community_type" in c
            assert "shared_entity" in c
            assert "member_count" in c
            assert "member_card_ids" in c
            assert "description" in c
            assert c["member_count"] >= 2, f"community should have at least 2 members, got {c}"

    def test_communities_sorted_by_member_count_desc(self, tmp_path: Path):
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/knowledge/communities")
        data = resp.json()
        counts = [c["member_count"] for c in data["communities"]]
        assert counts == sorted(counts, reverse=True), \
            f"Expected descending order, got: {counts}"


# ── v4.2 Truth Reset Tests ─────────────────────────────


class TestGraphExposedNodeTypes:
    """v4.2 truth reset: 验证 Graph API/UI 暴露的 NodeType 与 backend 支持对齐。"""

    def test_explore_endpoint_only_supports_implemented_types(self, tmp_path: Path):
        """GET /api/graph/explore 只接受已实现的 4 种 NodeType。"""
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        supported = {"card", "source", "wiki_section", "tag"}
        unsupported = {"community", "topic", "entity", "concept_candidate"}

        for nt in supported:
            node_id = "card_1" if nt == "card" else "src_1" if nt == "source" else "ai" if nt == "tag" else "Machine Learning"
            resp = client.get(f"/api/graph/explore?node_type={nt}&node_id={node_id}")
            assert resp.status_code == 200, (
                f"已支持的 node_type={nt} 应返回 200，实际 {resp.status_code}"
            )

        for nt in unsupported:
            resp = client.get(f"/api/graph/explore?node_type={nt}&node_id=test")
            assert resp.status_code == 422, (
                f"未实现的 node_type={nt} 应返回 422，实际 {resp.status_code}"
            )

    def test_candidate_graph_not_exposed_as_fact(self, tmp_path: Path):
        """v4.2 truth reset: CONCEPT_CANDIDATE 属于 candidate graph，
        Graph API 不得将其当作 fact graph 节点暴露。"""
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        resp = client.get("/api/graph/explore?node_type=concept_candidate&node_id=test")
        assert resp.status_code == 422, (
            f"concept_candidate 属于 candidate graph，不得通过 fact graph API 暴露，"
            f"实际 {resp.status_code}"
        )
        data = resp.json()
        assert "unsupported" in data.get("detail", {}).get("error", ""), (
            f"错误码应指示 unsupported: {data}"
        )

    def test_node_endpoint_only_card_centered(self, tmp_path: Path):
        """GET /api/graph/node 只支持以 Card 为中心的查询。"""
        cfg_path, _, _ = _make_temp_vault(tmp_path)
        client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
        # card 查询应成功
        resp = client.get("/api/graph/node?ref=card_1&depth=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["center_type"] == "card"
