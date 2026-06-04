"""Topics API 集成测试。

用 tmp_path 加真实卡片文件验证 API contract。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from mindforge_web.app import create_app
from mindforge_web.deps import get_facade
from mindforge_web.services.web_facade import WebFacade


def _write_card(cards_dir: Path, filename: str, *, status: str = "human_approved",
                track: str = "React", knowledge_type: str = "concept",
                human_note: str | None = None, body: str = "", **extra) -> Path:
    """写入一张测试卡片，返回 card path。"""
    card = cards_dir / filename
    fm = {
        "id": filename.replace(".md", ""),
        "title": filename.replace(".md", "").replace("-", " ").title(),
        "status": status,
        "track": track,
        "tags": ["test"],
        "source_type": "plain_markdown",
        "source_title": "Test Source",
        "value_score": 5,
        "created_at": "2026-05-10T00:00:00",
        "knowledge_type": knowledge_type,
        **extra,
    }
    if human_note:
        fm["human_note"] = human_note
    yaml_lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    text = f"---\n{yaml_lines}\n---\n\n{body}"
    card.write_text(text, encoding="utf-8")
    return card


@pytest.fixture
def api(tmp_path: Path):
    """创建 TestClient + vault 路径。

    返回 (client, vault_root, cards_dir) 供测试使用。
    """
    vault = tmp_path / "test-vault"
    cards_dir = vault / "20-Knowledge-Cards"
    cards_dir.mkdir(parents=True)
    (vault / "30-Wiki").mkdir(parents=True, exist_ok=True)

    cfg_path = tmp_path / "mindforge.yaml"
    cfg = {
        "version": 0.7,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "llm": {
            "default_model": "test",
            "models": {"test": {"type": "fake", "base_url": "fake://", "model": "fake"}},
        },
    }
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    app = create_app()
    facade = WebFacade(config_path=cfg_path, vault_override=None, host="127.0.0.1")

    def override_get_facade():
        return facade

    app.dependency_overrides[get_facade] = override_get_facade
    client = TestClient(app)
    yield client, vault, cards_dir
    app.dependency_overrides.clear()


# ============================================================================
# GET /api/topics — list topics
# ============================================================================


def test_list_topics_empty(api):
    """无卡片时返回空列表。"""
    client, _, _ = api
    resp = client.get("/api/topics")
    assert resp.status_code == 200
    data = resp.json()
    assert "topics" in data
    assert data["topics"] == []


def test_list_topics_with_cards(api):
    """有 approved 卡片时列出唯一 topic 名称。"""
    client, _, cards_dir = api
    _write_card(cards_dir, "card-1.md", track="React")
    _write_card(cards_dir, "card-2.md", track="Python")
    _write_card(cards_dir, "card-3.md", track="React")

    resp = client.get("/api/topics")
    assert resp.status_code == 200
    data = resp.json()
    assert sorted(data["topics"]) == ["Python", "React"]


def test_list_topics_excludes_drafts(api):
    """只有 ai_draft 卡片的 topic 不出现在列表。"""
    client, _, cards_dir = api
    _write_card(cards_dir, "draft.md", track="OnlyDraft", status="ai_draft")
    _write_card(cards_dir, "approved.md", track="RealTopic", status="human_approved")

    resp = client.get("/api/topics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["topics"] == ["RealTopic"]


# ============================================================================
# GET /api/topics/{topic_name} — topic view
# ============================================================================


def test_get_topic_returns_stable_schema(api):
    """response 结构与 TopicViewResponse 一致。"""
    client, _, cards_dir = api
    _write_card(cards_dir, "card-1.md", track="React",
                body="## AI Summary\n\nReact hooks patterns summary.\n")

    resp = client.get("/api/topics/React")
    assert resp.status_code == 200
    data = resp.json()

    assert data["topic"] == "React"
    assert data["total_approved_cards"] == 1
    assert isinstance(data["type_counts"], dict)
    assert len(data["cards"]) == 1

    card = data["cards"][0]
    expected_keys = {
        "id", "title", "knowledge_type", "relations", "tags",
        "summary", "human_note", "approval_state", "value_score",
        "source_title", "source_type", "track", "created_at", "approved_at",
    }
    assert set(card.keys()) == expected_keys

    assert card["summary"] != ""
    assert "React hooks" in card["summary"]


def test_get_topic_unknown_returns_404(api):
    """不存在的 topic 返回 404。"""
    client, _, _ = api
    resp = client.get("/api/topics/NonExistent")
    assert resp.status_code == 404


def test_get_topic_no_approved_cards_returns_404(api):
    """topic 存在但无 approved 卡片时返回 404。"""
    client, _, cards_dir = api
    _write_card(cards_dir, "draft.md", track="React", status="ai_draft")

    resp = client.get("/api/topics/React")
    assert resp.status_code == 404


def test_get_topic_no_ai_draft_leakage(api):
    """ai_draft 卡片不出现在 approved view。"""
    client, _, cards_dir = api
    _write_card(cards_dir, "approved.md", track="React", status="human_approved",
                body="## AI Summary\n\nApproved content.\n")
    _write_card(cards_dir, "draft.md", track="React", status="ai_draft",
                body="## AI Summary\n\nDraft content — should NOT leak.\n")

    resp = client.get("/api/topics/React")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_approved_cards"] == 1

    for card in data["cards"]:
        assert card["approval_state"] == "human_approved"
        assert "Draft content" not in card["summary"]
        assert "should NOT leak" not in card["summary"]


def test_get_topic_human_note_transparency(api):
    """human_note 透出到 API。"""
    client, _, cards_dir = api
    _write_card(cards_dir, "c1.md", track="React", human_note="Approved with corrections",
                body="## AI Summary\n\nTest.\n")

    resp = client.get("/api/topics/React")
    assert resp.status_code == 200
    assert resp.json()["cards"][0]["human_note"] == "Approved with corrections"


def test_get_topic_path_special_characters(api):
    """带连字符和特殊字符的 topic name 正常工作。"""
    client, _, cards_dir = api
    _write_card(cards_dir, "c1.md", track="React-Components",
                body="## AI Summary\n\nSpecial topic.\n")

    resp = client.get("/api/topics/React-Components")
    assert resp.status_code == 200
    assert resp.json()["topic"] == "React-Components"


def test_get_topic_empty_topic_name(api):
    """空 topic name 的处理。"""
    client, _, _ = api
    resp = client.get("/api/topics/")
    # 可能 redirect 到 list 或 404
    assert resp.status_code in (200, 307, 404, 405)


# ============================================================================
# error behavior
# ============================================================================


def test_topic_response_404_has_detail(api):
    """404 响应包含 detail 信息。"""
    client, _, _ = api
    resp = client.get("/api/topics/DefinitelyNotExist")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data
