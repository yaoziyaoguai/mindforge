"""MindForge Local Console API tests.

中文学习型说明：这些测试使用临时 vault/config 验证 Web adapter 边界：
API 可以读取真实本地状态，但不能泄露 secret；approve 必须二次确认，且
最终仍走现有 approval_service 写入单张 ai_draft。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from mindforge_web.app import create_app


def _write_config(tmp_path: Path) -> tuple[Path, Path, Path]:
    vault = tmp_path / "dogfood-vault"
    inbox = vault / "00-Inbox" / "ManualNotes"
    cards = vault / "20-Knowledge-Cards"
    projects = vault / "30-Projects"
    inbox.mkdir(parents=True)
    cards.mkdir(parents=True)
    projects.mkdir(parents=True)
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
    return cfg_path, vault, cards


def _write_draft(cards: Path) -> Path:
    card = cards / "draft.md"
    card.write_text(
        """---
id: draft-1
title: Test Draft
status: ai_draft
track: agent-runtime
projects:
  - local-console
tags:
  - web
source_type: manual_note
adapter_name: PlainMarkdownAdapter
source_path: 00-Inbox/ManualNotes/source-note.md
source_archive_path: ""
source_missing: false
source_title: Safe source
value_score: 8
profile: fake
stage_models:
  distill: { alias: fake_alias, provider: fake, model: fake }
---

## Distilled Note

This is safe draft body.
""",
        encoding="utf-8",
    )
    return card


def _client(tmp_path: Path, monkeypatch) -> tuple[TestClient, Path]:
    cfg_path, _vault, cards = _write_config(tmp_path)
    (tmp_path / ".env").write_text(
        "MINDFORGE_FAKE_SECRET=do-not-leak\nMINDFORGE_CUBOX_TOKEN=cubox-secret\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    app = create_app(config_path=cfg_path, host="127.0.0.1")
    return TestClient(app), cards


def test_web_workflow_library_and_source_visibility_are_metadata_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, cards = _client(tmp_path, monkeypatch)
    card = _write_draft(cards)
    source = tmp_path / "dogfood-vault" / "00-Inbox" / "ManualNotes" / "source-note.md"
    source.write_text("SOURCE_BODY_MUST_NOT_LEAK", encoding="utf-8")
    processed = (
        tmp_path
        / "dogfood-vault"
        / "00-Inbox"
        / "_processed"
        / "ManualNotes"
        / "done.md"
    )
    processed.parent.mkdir(parents=True)
    processed.write_text("PROCESSED_BODY_MUST_NOT_LEAK", encoding="utf-8")

    workflow = client.get("/api/workflow/summary").json()
    library = client.get("/api/library/cards").json()
    detail = client.get("/api/library/card", params={"ref": "draft-1"}).json()
    sources = client.get("/api/sources").json()
    combined = f"{workflow} {library} {detail} {sources}"

    assert workflow["vault_root"].endswith("dogfood-vault")
    assert workflow["ai_draft_count"] == 1
    assert workflow["human_approved_count"] == 0
    assert workflow["source_bucket_counts"]["pending"]["ManualNotes"] == 1
    assert workflow["source_bucket_counts"]["processed"]["ManualNotes"] == 1
    assert library["cards"][0]["source_path"] == "00-Inbox/ManualNotes/source-note.md"
    assert library["cards"][0]["source_missing"] is False
    assert detail["card"]["id"] == "draft-1"
    assert detail["card"]["fake_provider_note"]
    assert "body" not in detail
    assert "SOURCE_BODY_MUST_NOT_LEAK" not in combined
    assert "PROCESSED_BODY_MUST_NOT_LEAK" not in combined
    assert card.exists()


def test_web_health_home_config_do_not_expose_secret_values(tmp_path: Path, monkeypatch) -> None:
    client, _cards = _client(tmp_path, monkeypatch)

    assert client.get("/api/health").json()["ok"] is True
    home = client.get("/api/home/status").json()
    config = client.get("/api/config/status").json()
    combined = f"{home} {config}"

    assert "do-not-leak" not in combined
    assert "cubox-secret" not in combined
    assert "MINDFORGE_FAKE_SECRET" in combined
    assert home["safety"]["local_only"] is True
    assert config["provider"]["active_profile"] == "fake"


def test_web_drafts_detail_and_approve_confirmation_boundary(tmp_path: Path, monkeypatch) -> None:
    client, cards = _client(tmp_path, monkeypatch)
    card = _write_draft(cards)

    drafts = client.get("/api/drafts").json()
    assert [draft["id"] for draft in drafts["drafts"]] == ["draft-1"]
    detail = client.get("/api/drafts/draft-1").json()
    assert "safe draft body" in detail["body"].lower()

    refused = client.post(
        "/api/drafts/draft-1/approve",
        json={"confirm": False, "reviewed_source": True},
    ).json()
    assert refused["ok"] is False
    assert "status: ai_draft" in card.read_text(encoding="utf-8")

    approved = client.post(
        "/api/drafts/draft-1/approve",
        json={"confirm": True, "reviewed_source": True},
    ).json()
    assert approved["ok"] is True
    assert approved["new_status"] == "human_approved"
    assert "status: human_approved" in card.read_text(encoding="utf-8")


def test_web_reject_and_imports_are_honest_unavailable(tmp_path: Path, monkeypatch) -> None:
    client, cards = _client(tmp_path, monkeypatch)
    _write_draft(cards)

    reject = client.post("/api/drafts/draft-1/reject", json={"reason": "not useful"}).json()
    import_local = client.post("/api/sources/import-local").json()
    import_cubox = client.post("/api/sources/import-cubox-json").json()

    assert reject["available"] is False
    assert import_local["available"] is False
    assert import_cubox["available"] is False
