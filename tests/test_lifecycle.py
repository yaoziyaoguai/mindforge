"""v2.5 U2 Source-to-Card Lifecycle tests — API endpoint + data aggregation 测试。

中文学习型说明：测试 lifecycle API 结构和基本行为，使用合成数据不调用 LLM。
"""

from __future__ import annotations

import pytest


class TestLifecycleResponse:
    """验证 LifecycleResponse schema 结构。"""

    def test_empty_lifecycle_structure(self):
        """空知识库返回有效生命周期结构。"""
        from mindforge_web.schemas import LifecycleResponse

        resp = LifecycleResponse(
            sources=[],
            total_sources=0,
            total_cards=0,
            total_approved=0,
            total_drafts=0,
        )
        assert resp.total_sources == 0
        assert resp.total_cards == 0
        assert resp.sources == []

    def test_lifecycle_with_sources(self):
        """带 source 数据的生命周期统计。"""
        from mindforge_web.schemas import LifecycleResponse, SourceLifecycleItem

        sources = [
            SourceLifecycleItem(
                source_id="src/notes",
                source_title="学习笔记",
                total_cards=5,
                ai_draft_count=2,
                human_approved_count=3,
                imported_count=0,
                error_count=0,
            ),
        ]
        resp = LifecycleResponse(
            sources=sources,
            total_sources=1,
            total_cards=5,
            total_approved=3,
            total_drafts=2,
        )
        assert resp.total_sources == 1
        assert resp.total_approved == 3
        assert resp.total_drafts == 2
        assert resp.sources[0].source_title == "学习笔记"
        assert resp.sources[0].human_approved_count == 3
        assert resp.sources[0].ai_draft_count == 2


class TestLifecycleApiEndpoint:
    """验证 lifecycle API 端点可访问。"""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch: pytest.MonkeyPatch):
        """创建带临时 vault/config 的 TestClient。"""
        import yaml
        from fastapi.testclient import TestClient
        from mindforge_web.app import create_app

        vault = tmp_path / "vault"
        cards_dir = vault / "20-Knowledge-Cards"
        cards_dir.mkdir(parents=True)

        config: dict = {
            "version": 0.7,
            "vault": {
                "root": str(vault),
                "cards_dir": "20-Knowledge-Cards",
            },
            "state": {
                "workdir": str(tmp_path / ".mindforge"),
                "state_file": "state.json",
                "runs_dir": "runs",
                "index_file": "index.jsonl",
                "backup_state": True,
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
            "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
            "llm": {
                "default_model": None,
                "models": {},
                "routing": {},
            },
        }
        config_path = tmp_path / "mindforge.yaml"
        config_path.write_text(yaml.dump(config))

        app = create_app(config_path=config_path, host="127.0.0.1")
        with TestClient(app) as tc:
            self.client = tc

    def test_lifecycle_endpoint_returns_200(self):
        """GET /api/lifecycle 返回 200。"""
        resp = self.client.get("/api/lifecycle")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert "total_cards" in data
        assert "total_approved" in data
        assert "total_drafts" in data
        assert isinstance(data["sources"], list)

    def test_lifecycle_empty_vault(self):
        """空 vault 返回零值。"""
        resp = self.client.get("/api/lifecycle")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cards"] == 0
        assert data["total_sources"] == 0
        assert data["sources"] == []
