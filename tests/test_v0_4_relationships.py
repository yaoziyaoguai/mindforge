"""v0.4 Knowledge Relationship Experience — golden tests for U1-U5.

验证点：
- Health report 从已知卡片正确检出 orphan/low_quality/duplicates/missing_provenance
- Provenance trail 正确构建 source → sibling → wiki sections 链路
- Related cards 按原因分组并排序
- 所有 v0.4 API endpoints 返回正确结构
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from mindforge_web.app import create_app


# ──────────────────────────────────────────────────────────
# Fixture helpers
# ──────────────────────────────────────────────────────────

def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True, exist_ok=True)
    (vault / "30-Projects").mkdir(parents=True, exist_ok=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True, exist_ok=True)
    (vault / "30-Wiki").mkdir(parents=True, exist_ok=True)

    cfg = {
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
                },
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
    }
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return vault


def _write_card(cards_dir: Path, name: str, frontmatter: dict[str, object], body: str = "") -> Path:
    p = cards_dir / name
    lines = ["---"]
    for k, v in frontmatter.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    if body:
        lines.append("")
        lines.append(body)
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(config_path=(tmp_path / "mindforge.yaml"))
    return TestClient(app)


# ──────────────────────────────────────────────────────────
# U5: Health Report Golden Tests
# ──────────────────────────────────────────────────────────

class TestHealthReportGolden:
    """验证 health report 从已知卡片集合正确检测问题。"""

    def test_health_report_detects_orphan_cards(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        cards = vault / "20-Knowledge-Cards"
        # 一张被 wiki 引用和 related cards 支持的卡片
        _write_card(cards, "connected.md", {
            "id": "connected", "title": "Connected Card",
            "status": "human_approved", "source_id": "src-a",
        })
        # 一张孤立的卡片 — 无 wiki 引用，无 related cards
        _write_card(cards, "lonely.md", {
            "id": "lonely", "title": "Lonely Card",
            "status": "human_approved", "source_id": "src-x",
        })

        client = _make_client(tmp_path)
        resp = client.get("/api/knowledge/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "issues" in data
        codes = [i["code"] for i in data["issues"]]
        assert "orphans" in codes

    def test_health_report_detects_low_quality(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        cards = vault / "20-Knowledge-Cards"
        _write_card(cards, "thin.md", {
            "id": "thin", "title": "Thin Card",
            "status": "human_approved", "source_id": "src-1",
        }, body="short")

        client = _make_client(tmp_path)
        resp = client.get("/api/knowledge/health")
        assert resp.status_code == 200
        data = resp.json()
        codes = [i["code"] for i in data["issues"]]
        assert "low_quality" in codes

    def test_health_report_detects_missing_provenance(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        cards = vault / "20-Knowledge-Cards"
        _write_card(cards, "no-source.md", {
            "id": "no-source", "title": "No Source",
            "status": "human_approved",
        })

        client = _make_client(tmp_path)
        resp = client.get("/api/knowledge/health")
        assert resp.status_code == 200
        data = resp.json()
        codes = [i["code"] for i in data["issues"]]
        assert "missing_provenance" in codes

    def test_health_report_detects_duplicates(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        cards = vault / "20-Knowledge-Cards"
        _write_card(cards, "dup-a.md", {
            "id": "dup-a", "title": "Authentication Patterns Guide",
            "status": "human_approved", "source_id": "src-1",
        })
        _write_card(cards, "dup-b.md", {
            "id": "dup-b", "title": "Authentication Patterns Guidelines",
            "status": "human_approved", "source_id": "src-2",
        })

        client = _make_client(tmp_path)
        resp = client.get("/api/knowledge/health")
        assert resp.status_code == 200
        data = resp.json()
        codes = [i["code"] for i in data["issues"]]
        assert "duplicates" in codes

    def test_health_report_returns_stats(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        cards = vault / "20-Knowledge-Cards"
        _write_card(cards, "card-a.md", {
            "id": "card-a", "title": "Card A",
            "status": "human_approved", "source_id": "src-1",
        })

        client = _make_client(tmp_path)
        resp = client.get("/api/knowledge/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_cards"] == 1
        assert data["stats"]["approved"] == 1

    def test_health_report_empty_vault_is_clean(self, tmp_path: Path) -> None:
        _make_vault(tmp_path)
        client = _make_client(tmp_path)
        resp = client.get("/api/knowledge/health")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["issues"]) == 0


# ──────────────────────────────────────────────────────────
# U3: Provenance Trail Golden Tests
# ──────────────────────────────────────────────────────────

class TestProvenanceTrail:
    """验证 provenance trail 结构正确性。"""

    def test_trail_404_for_nonexistent_card(self, tmp_path: Path) -> None:
        _make_vault(tmp_path)
        client = _make_client(tmp_path)
        resp = client.get("/api/library/trail?ref=nonexistent")
        assert resp.status_code == 404

    def test_trail_returns_source_for_known_card(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        cards = vault / "20-Knowledge-Cards"
        _write_card(cards, "with-source.md", {
            "id": "with-source", "title": "Has Source",
            "status": "human_approved", "source_id": "my-source",
        })

        client = _make_client(tmp_path)
        resp = client.get("/api/library/trail?ref=with-source")
        assert resp.status_code == 200
        data = resp.json()
        assert data["card_id"] == "with-source"
        assert data["source"]["source_id"] == "my-source"

    def test_trail_returns_sibling_cards(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        cards = vault / "20-Knowledge-Cards"
        _write_card(cards, "center.md", {
            "id": "center", "title": "Center Card",
            "status": "human_approved", "source_id": "shared-src",
        })
        _write_card(cards, "sibling.md", {
            "id": "sibling", "title": "Sibling Card",
            "status": "human_approved", "source_id": "shared-src",
        })

        client = _make_client(tmp_path)
        resp = client.get("/api/library/trail?ref=center")
        assert resp.status_code == 200
        data = resp.json()
        siblings = data["sibling_cards"]
        assert len(siblings) >= 1
        sibling_ids = [s["card_id"] for s in siblings]
        assert "sibling" in sibling_ids


# ──────────────────────────────────────────────────────────
# U1: Library Card Detail with Local Graph
# ──────────────────────────────────────────────────────────

class TestLibraryCardDetail:
    """验证 card detail 返回 local graph 和 related cards。"""

    def test_card_detail_includes_local_graph(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        cards = vault / "20-Knowledge-Cards"
        _write_card(cards, "graph-card.md", {
            "id": "graph-card", "title": "Graph Card",
            "status": "human_approved", "source_id": "src-g",
            "tags": "['tag-a']",
        })

        client = _make_client(tmp_path)
        resp = client.get("/api/library/card?ref=graph-card")
        assert resp.status_code == 200
        data = resp.json()
        assert "local_graph" in data
        graph = data["local_graph"]
        assert graph is not None
        assert graph["center_id"] == "graph-card"
        assert len(graph["nodes"]) >= 1

    def test_card_detail_includes_related_cards(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        cards = vault / "20-Knowledge-Cards"
        _write_card(cards, "center.md", {
            "id": "center", "title": "Center",
            "status": "human_approved", "source_id": "shared",
            "tags": "['tag-x']",
        })
        _write_card(cards, "neighbor.md", {
            "id": "neighbor", "title": "Neighbor",
            "status": "human_approved", "source_id": "shared",
            "tags": "['tag-x']",
        })

        client = _make_client(tmp_path)
        resp = client.get("/api/library/card?ref=center")
        assert resp.status_code == 200
        data = resp.json()
        related = data["related_cards"]
        assert len(related) >= 1
        reasons = [r["reason"] for rc in related for r in rc["reasons"]]
        assert "same_source" in reasons or "same_tag" in reasons
