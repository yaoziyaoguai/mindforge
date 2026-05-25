"""v2.5 U3 Dogfood Report tests — API endpoint + data aggregation 测试。

中文学习型说明：测试报告 API 结构和基本行为，使用合成数据不调用 LLM。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


class TestDogfoodReportResponse:
    """验证 DogfoodReportResponse schema 结构。"""

    def test_minimal_report_structure(self):
        """空知识库返回有效报告结构。"""
        from mindforge_web.schemas import DogfoodReportResponse

        report = DogfoodReportResponse(
            generated_at="2026-05-25T00:00:00+00:00",
            total_cards=0,
            approved_count=0,
            draft_count=0,
            approval_rate=0.0,
            source_count=0,
            graph_total_relations=0,
            graph_density=0.0,
            community_count=0,
            wiki_section_count=0,
            wiki_stale=False,
            search_index_exists=False,
            search_index_path="",
            imported_card_count=0,
            exported_count=0,
            import_error_count=0,
            health_issue_count=0,
            trend_summary="暂无卡片。",
            maintenance_suggestions=["知识库为空，导入资料或粘贴 Markdown 内容开始构建知识库。"],
        )
        assert report.total_cards == 0
        assert report.approval_rate == 0.0
        assert len(report.maintenance_suggestions) == 1

    def test_report_with_cards_calculates_approval_rate(self):
        """确认率的计算逻辑。"""
        from mindforge_web.schemas import DogfoodReportResponse

        report = DogfoodReportResponse(
            generated_at="2026-05-25T00:00:00+00:00",
            total_cards=10,
            approved_count=7,
            draft_count=3,
            approval_rate=0.7,
            source_count=2,
            graph_total_relations=5,
            graph_density=0.5,
            community_count=2,
            wiki_section_count=7,
            wiki_stale=False,
            search_index_exists=True,
            search_index_path="/tmp/test_index",
            imported_card_count=3,
            exported_count=7,
            import_error_count=0,
            health_issue_count=1,
            trend_summary="总卡片 10 张 · 确认率 70% · 3 张待审。",
            maintenance_suggestions=["审阅 3 张待确认草稿以提高知识库覆盖率。"],
        )
        assert report.approval_rate == 0.7
        assert report.total_cards == 10
        assert report.graph_density == 0.5
        assert len(report.maintenance_suggestions) > 0


class TestDogfoodApiEndpoint:
    """验证 dogfood report API 端点可访问。"""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """创建带临时 vault/config 的 TestClient。"""
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

    def test_dogfood_report_endpoint_returns_200(self):
        """GET /api/dogfood/report 返回 200。"""
        resp = self.client.get("/api/dogfood/report")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cards" in data
        assert "approval_rate" in data
        assert "trend_summary" in data
        assert "maintenance_suggestions" in data
        assert isinstance(data["maintenance_suggestions"], list)

    def test_dogfood_report_counts_are_non_negative(self):
        """空 vault 返回非负数。"""
        resp = self.client.get("/api/dogfood/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cards"] >= 0
        assert 0.0 <= data["approval_rate"] <= 1.0
        assert data["health_issue_count"] >= 0
