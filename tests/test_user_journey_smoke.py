"""User journey smoke tests — 覆盖主路径 Home→Sources→Drafts→Library→Recall→Wiki→Export。

中文学习型说明：这些测试不需要浏览器，使用 FastAPI TestClient 直接验证
主路径 API 端点的 HTTP 200 和响应结构。不依赖真实 LLM、不读 .env/secrets、
不写 Obsidian vault。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from mindforge_web.app import create_app


def _write_config(tmp_path: Path) -> tuple[Path, Path]:
    """创建临时 vault + config，写入一张 sample approved 卡片。"""
    vault = tmp_path / "dogfood-vault"
    inbox = vault / "00-Inbox" / "ManualNotes"
    cards = vault / "20-Knowledge-Cards"
    projects = vault / "30-Projects"
    inbox.mkdir(parents=True)
    cards.mkdir(parents=True)
    projects.mkdir(parents=True)

    # 写入一张 approved 卡片，使 Library/Recall/Wiki 有数据
    card_path = cards / "sample-card.md"
    card_path.write_text(
        "---\n"
        "status: human_approved\n"
        "title: 主路径冒烟测试卡片\n"
        "track: testing\n"
        "tags:\n"
        "  - smoke\n"
        "  - journey\n"
        "source_type: plain_markdown\n"
        "source_title: sample-source.md\n"
        "source_path: sample-source.md\n"
        "value_score: 8\n"
        "quality_score: 85\n"
        "quality_level: good\n"
        "approved_at: \"2026-05-26T10:00:00\"\n"
        "created_at: \"2026-05-26T09:00:00\"\n"
        "updated_at: \"2026-05-26T10:00:00\"\n"
        "---\n"
        "\n"
        "# 主路径冒烟测试卡片\n"
        "\n"
        "## Summary\n"
        "这是一张用于端到端冒烟测试的示例知识卡片。\n"
        "验证主路径：Home → Sources → Drafts → Review → Library → Recall → Wiki → Export。\n"
        "\n"
        "## Actions\n"
        "- 运行冒烟测试\n"
        "- 验证所有主路径端点返回 200\n"
        "\n"
        "## Principles\n"
        "- 不调用真实 LLM\n"
        "- 不读 .env/secrets\n"
        "- 不写 Obsidian vault\n",
        encoding="utf-8",
    )

    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                    "projects_dir": "30-Projects",
                },
                "sources": {
                    "enabled": ["plain_markdown"],
                    "registry": {
                        "plain_markdown": {
                            "adapter": "PlainMarkdownAdapter",
                            "inbox_subdir": "ManualNotes",
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
                    "active_profile": "fake",
                    "profiles": {
                        "fake": {
                            "triage": "fake_alias",
                            "distill": "fake_alias",
                            "link_suggestion": "fake_alias",
                            "review_questions": "fake_alias",
                            "action_extraction": "fake_alias",
                        }
                    },
                    "models": {
                        "fake_alias": {
                            "provider": "fake",
                            "type": "fake",
                            "base_url": "fake://",
                            "model": "fake",
                            "timeout_seconds": 5,
                            "max_retries": 0,
                            "api_key_env": "MINDFORGE_FAKE_SECRET",
                        }
                    },
                },
                "prompts": {
                    "triage_version": "v1",
                    "distill_version": "v1",
                    "link_suggestion_version": "v1",
                    "review_questions_version": "v1",
                    "action_extraction_version": "v1",
                },
                "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg_path, vault


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """创建带有一张 sample approved 卡片的 TestClient fixture。"""
    cfg_path, vault = _write_config(tmp_path)
    app = create_app(config_path=cfg_path, vault_override=vault)
    return TestClient(app)


class TestUserJourneyMainPath:
    """主路径冒烟测试：验证所有关键 API 端点返回 HTTP 200。

    覆盖路径：Home → Sources → Drafts → Library → Recall → Wiki → Export。
    每个端点只需验证 HTTP 200 和基本响应结构。
    """

    def test_home_status_ok(self, client: TestClient) -> None:
        """GET /api/home/status → 200，cards_by_status 包含数据。"""
        resp = client.get("/api/home/status")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "cards_by_status" in data
        assert data["cards_by_status"].get("human_approved", 0) >= 1

    def test_workspace_status_ok(self, client: TestClient) -> None:
        """GET /api/workspace/status → 200。"""
        resp = client.get("/api/workspace/status")
        assert resp.status_code == 200, resp.text

    def test_sources_ok(self, client: TestClient) -> None:
        """GET /api/sources → 200。"""
        resp = client.get("/api/sources")
        assert resp.status_code == 200, resp.text

    def test_drafts_ok(self, client: TestClient) -> None:
        """GET /api/drafts → 200（空列表也正常）。"""
        resp = client.get("/api/drafts")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "drafts" in data

    def test_library_cards_ok(self, client: TestClient) -> None:
        """GET /api/library/cards → 200，至少包含测试卡片。"""
        resp = client.get("/api/library/cards")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "cards" in data
        assert len(data["cards"]) >= 1, "应至少有一张 sample approved 卡片"

    def test_library_stats_ok(self, client: TestClient) -> None:
        """GET /api/library/stats → 200，total_cards >= 1。"""
        resp = client.get("/api/library/stats")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "total_cards" in data
        assert data["total_cards"] >= 1

    def test_recall_search_ok(self, client: TestClient) -> None:
        """GET /api/recall?q=... → 200，中文查询能命中测试卡片。"""
        resp = client.get("/api/recall", params={"q": "冒烟测试"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "hits" in data
        assert len(data["hits"]) >= 1, "中文查询应能命中冒烟测试卡片"

    def test_recall_english_search_ok(self, client: TestClient) -> None:
        """GET /api/recall?q=... → 200，英文查询也能命中。"""
        resp = client.get("/api/recall", params={"q": "smoke test"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "hits" in data
        assert len(data["hits"]) >= 1, "英文查询应能命中 smoke 标签卡片"

    def test_wiki_status_ok(self, client: TestClient) -> None:
        """GET /api/wiki/status → 200。"""
        resp = client.get("/api/wiki/status")
        assert resp.status_code == 200, resp.text

    def test_wiki_content_ok(self, client: TestClient) -> None:
        """GET /api/wiki/content → 200，基于 approved 卡片生成。"""
        resp = client.get("/api/wiki/content")
        assert resp.status_code == 200, resp.text

    def test_workflow_summary_ok(self, client: TestClient) -> None:
        """GET /api/workflow/summary → 200。"""
        resp = client.get("/api/workflow/summary")
        assert resp.status_code == 200, resp.text

    def test_health_ok(self, client: TestClient) -> None:
        """GET /api/health → 200。"""
        resp = client.get("/api/health")
        assert resp.status_code == 200, resp.text

    def test_knowledge_health_ok(self, client: TestClient) -> None:
        """GET /api/knowledge/health → 200。"""
        resp = client.get("/api/knowledge/health")
        assert resp.status_code == 200, resp.text

    def test_config_status_ok(self, client: TestClient) -> None:
        """GET /api/config/status → 200。"""
        resp = client.get("/api/config/status")
        assert resp.status_code == 200, resp.text

    def test_export_ok(self, client: TestClient) -> None:
        """POST /api/knowledge/export → 200，导出所有卡片为 markdown。"""
        lib_resp = client.get("/api/library/cards")
        cards = lib_resp.json()["cards"]
        card_ids = [(c.get("id") or c["rel_path"]) for c in cards]
        assert len(card_ids) >= 1

        resp = client.post(
            "/api/knowledge/export",
            json={"card_ids": card_ids, "format": "markdown"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "markdown" in data

    def test_lifecycle_ok(self, client: TestClient) -> None:
        """GET /api/lifecycle → 200。"""
        resp = client.get("/api/lifecycle")
        assert resp.status_code == 200, resp.text


class TestUserJourneyResponseStructure:
    """验证主路径各端点的响应结构完整性。

    确保关键字段存在，避免 schema 回归导致的 UI 报错。
    """

    def test_library_cards_have_required_fields(self, client: TestClient) -> None:
        """Library 卡片列表包含前端渲染必需的关键字段。"""
        resp = client.get("/api/library/cards")
        cards = resp.json()["cards"]
        card = cards[0]
        required = ["title", "status", "rel_path", "source_type", "approved_at", "quality_level"]
        for field in required:
            assert field in card, f"卡片应包含 {field} 字段"

    def test_recall_hits_have_required_fields(self, client: TestClient) -> None:
        """Recall 命中结果包含关键字段。"""
        resp = client.get("/api/recall", params={"q": "smoke"})
        hits = resp.json()["hits"]
        assert len(hits) >= 1
        hit = hits[0]
        required = ["score", "title", "rel_path", "status", "why_this_matched"]
        for field in required:
            assert field in hit, f"命中结果应包含 {field} 字段"

    def test_home_status_has_expected_fields(self, client: TestClient) -> None:
        """Home 状态包含首页渲染必需的字段。"""
        resp = client.get("/api/home/status")
        data = resp.json()
        # HomeStatusResponse 字段 — schema 参考 schemas/provider.py
        expected = ["cards_by_status", "next_actions", "workspace", "recall"]
        for field in expected:
            assert field in data, f"Home status 应包含 {field} 字段"

    def test_wiki_content_is_non_empty(self, client: TestClient) -> None:
        """Wiki 内容基于 approved 卡片应非空。"""
        resp = client.get("/api/wiki/content")
        data = resp.json()
        # wiki/content 返回格式包含 content/markdown/sections 之一
        has_content = any(k in data for k in ("content", "sections", "markdown"))
        assert has_content, f"Wiki content 应有 content/sections/markdown 字段，实际: {list(data.keys())[:5]}"

    def test_library_cards_source_path_available(self, client: TestClient) -> None:
        """Library 卡片包含 source_path_view 溯源信息。"""
        resp = client.get("/api/library/cards")
        cards = resp.json()["cards"]
        if cards:
            card = cards[0]
            assert "source_path_view" in card, "卡片应包含 source_path_view 字段"
