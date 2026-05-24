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
