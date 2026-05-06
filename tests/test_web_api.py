"""MindForge Local Console API tests.

中文学习型说明：这些测试使用临时 vault/config 验证 Web adapter 边界：
API 可以读取真实本地状态，但不能泄露 secret；approve 必须二次确认，且
最终仍走现有 approval_service 写入单张 ai_draft。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from mindforge.watch_registry import WatchRegistry
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
source_id: src_draft_1
adapter_name: PlainMarkdownAdapter
source_path: 00-Inbox/ManualNotes/source-note.md
source_content_hash: sha256:provenancehash
source_archive_path: ""
source_missing: false
source_title: Safe source
value_score: 8
strategy_id: five_stage
strategy_version: 0.10.0
schema_version: "1"
prompt_version: distill@v1
prompt_versions:
  triage: v1
  distill: v1
  link_suggestion: v1
  review_questions: v1
  action_extraction: v1
profile: fake
stage_models:
  distill: { alias: fake_alias, provider: fake, model: fake }
run_id: run-web-provenance
---

## Distilled Note

This is safe draft body.
""",
        encoding="utf-8",
    )
    return card


def _write_approved(cards: Path) -> Path:
    card = cards / "approved.md"
    card.write_text(
        """---
id: approved-1
title: Approved Card
status: human_approved
track: product
projects:
  - local-console
tags:
  - library
source_type: manual_note
source_id: src_approved_1
adapter_name: PlainMarkdownAdapter
source_path: 00-Inbox/_processed/ManualNotes/source-note.md
source_content_hash: sha256:approvedhash
source_archive_path: 90-Archive/Processed/source-note.md
source_missing: false
source_title: Approved source
value_score: 7
strategy_id: knowledge_card
strategy_version: 0.10.0
schema_version: "1"
prompt_versions:
  triage: v1
  distill: v1
profile: real-profile
stage_models:
  distill: { alias: real_alias, provider: openai_compatible, model: gpt-test }
run_id: run-approved
---

## Source Excerpt

SOURCE_EXCERPT_VISIBLE_BUT_NOT_RAW_FILE

## AI Summary

Approved summary alpha workspace.

## AI Inference

Approved inference beta.

## Review Questions

- What should be reviewed?

## Action Items

- Maintain the card.

## Human Note

HUMAN_NOTE_MUST_NOT_BE_RECALLABLE
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


def test_web_workflow_library_and_source_visibility_return_card_content_not_source_raw(
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
    assert library["cards"][0]["source_id"] == "src_draft_1"
    assert library["cards"][0]["source_content_hash"] == "sha256:provenancehash"
    assert library["cards"][0]["strategy_id"] == "five_stage"
    assert library["cards"][0]["prompt_versions"]["distill"] == "v1"
    assert library["cards"][0]["run_id"] == "run-web-provenance"
    assert library["cards"][0]["source_missing"] is False
    assert detail["card"]["id"] == "draft-1"
    assert detail["card"]["strategy_version"] == "0.10.0"
    assert detail["card"]["schema_version"] == "1"
    assert detail["card"]["fake_provider_note"]
    assert "safe draft body" in detail["body"].lower()
    assert "SOURCE_BODY_MUST_NOT_LEAK" not in combined
    assert "PROCESSED_BODY_MUST_NOT_LEAK" not in combined
    assert card.exists()


def test_sources_api_exposes_frequency_due_and_baseline_counts(tmp_path: Path, monkeypatch) -> None:
    client, _cards = _client(tmp_path, monkeypatch)
    source = tmp_path / "watched.md"
    source.write_text("# Watched\n\nbody\n", encoding="utf-8")

    added = client.post("/api/sources/watch", json={"path": str(source), "frequency": "daily"})
    sources = client.get("/api/sources").json()

    assert added.status_code == 200
    watched = [item for item in sources["watched_sources"] if item["path"] == str(source.resolve())][0]
    assert watched["frequency"] == "daily"
    assert watched["last_scan_at"]
    assert watched["next_scan_at"]
    assert watched["due_status"] in {"Due", "Not due", "Manual"}
    assert "added" in watched["diff_counts"]


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


def test_setup_editor_saves_allowed_non_secret_fields_and_refreshes_status(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["custom_unrelated"] = {"keep": "unchanged"}
    raw["llm"]["profiles"]["real"] = {
        "triage": "real_alias",
        "distill": "real_alias",
        "link_suggestion": "real_alias",
        "review_questions": "real_alias",
        "action_extraction": "real_alias",
    }
    raw["llm"]["models"]["real_alias"] = {
        "provider": "openai_compatible",
        "type": "openai_compatible",
        "base_url": "https://old.example.invalid/v1",
        "model": "old-model",
        "timeout_seconds": 30,
        "max_retries": 1,
        "api_key_env": "MINDFORGE_REAL_SECRET",
        "base_url_env": "MINDFORGE_OLD_BASE_URL",
        "model_env": "MINDFORGE_OLD_MODEL",
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    (tmp_path / ".env").write_text("MINDFORGE_REAL_SECRET=never-return-this\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    editable = client.get("/api/config/editable").json()

    assert editable["vault"]["root"].endswith("dogfood-vault")
    assert editable["llm"]["active_provider"] == "fake"
    assert editable["llm"]["providers"]["real"]["api_key_env_configured"] is True
    assert editable["llm"]["providers"]["real"]["api_key_secret_present"] is False
    assert "never-return-this" not in f"{editable}"

    new_vault = tmp_path / "new-vault"
    saved = client.patch(
        "/api/config/editable",
        json={
            "vault_root": str(new_vault),
            "create_vault": True,
            "active_provider": "real",
            "providers": {
                "real": {
                    "default_base_url": "https://new.example.invalid/v1",
                    "default_model": "new-model",
                    "api_key_env": "MINDFORGE_REAL_SECRET_RENAMED",
                    "base_url_env": "MINDFORGE_NEW_BASE_URL",
                    "model_env": "MINDFORGE_NEW_MODEL",
                }
            },
        },
    ).json()
    after_raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    combined = f"{saved} {cfg_path.read_text(encoding='utf-8')} {capsys.readouterr()}"

    assert saved["ok"] is True
    assert saved["status"]["vault"]["path"] == str(new_vault.resolve())
    assert saved["status"]["provider"]["active_profile"] == "real"
    assert (new_vault / "00-Inbox").is_dir()
    assert after_raw["custom_unrelated"] == {"keep": "unchanged"}
    assert after_raw["triage"]["default_track"] == "unrouted"
    assert after_raw["llm"]["active_profile"] == "real"
    assert after_raw["llm"]["models"]["real_alias"]["model"] == "new-model"
    assert after_raw["llm"]["models"]["real_alias"]["base_url"] == "https://new.example.invalid/v1"
    assert after_raw["llm"]["models"]["real_alias"]["api_key_env"] == "MINDFORGE_REAL_SECRET_RENAMED"
    assert "never-return-this" not in combined


def test_setup_editor_validates_paths_and_never_writes_api_key_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    (tmp_path / ".env").write_text("MINDFORGE_FAKE_SECRET=hidden-secret\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    invalid = client.post("/api/config/validate", json={"vault_root": "/"}).json()
    refused = client.patch(
        "/api/config/editable",
        json={
            "vault_root": str(tmp_path / "missing-vault"),
            "create_vault": False,
            "providers": {"fake": {"api_key_value": "must-not-be-written"}},
        },
    )

    config_text = cfg_path.read_text(encoding="utf-8")
    assert invalid["ok"] is False
    assert any("dangerous" in error.lower() for error in invalid["errors"])
    assert refused.status_code == 400
    assert "hidden-secret" not in refused.text
    assert "must-not-be-written" not in config_text


def test_setup_effective_provider_config_distinguishes_env_names_defaults_and_masked_secret(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    secret_value = "sk-ant-" + "test-secret-value-" + "abcd"
    raw["llm"] = {
        "active": "anthropic",
        "providers": {
            "anthropic": {
                "type": "anthropic",
                "api_key_env": "MINDFORGE_ANTHROPIC_API_KEY",
                "base_url_env": "MINDFORGE_ANTHROPIC_BASE_URL",
                "model_env": "MINDFORGE_ANTHROPIC_MODEL",
                "default_base_url": "https://api.anthropic.com",
                "default_model": "claude-3-5-haiku-latest",
            },
            "fake": {"type": "fake"},
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_MODEL", raising=False)
    monkeypatch.setenv("MINDFORGE_ANTHROPIC_API_KEY", secret_value)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    editable = client.get("/api/config/editable").json()
    provider = editable["llm"]["providers"]["anthropic"]
    combined = f"{editable} {capsys.readouterr()}"

    assert editable["llm"]["active_provider"] == "anthropic"
    assert provider["api_key_env"] == "MINDFORGE_ANTHROPIC_API_KEY"
    assert provider["api_key_env_configured"] is True
    assert provider["api_key_secret_present"] is True
    assert provider["api_key_masked_value"] == "sk-****abcd"
    assert provider["api_key_status_label"] == "present (sk-****abcd)"
    assert provider["base_url_env"] == "MINDFORGE_ANTHROPIC_BASE_URL"
    assert provider["base_url_env_status"] == "missing"
    assert provider["effective_base_url"] == "https://api.anthropic.com"
    assert provider["base_url_source"] == "config_default"
    assert provider["model_env"] == "MINDFORGE_ANTHROPIC_MODEL"
    assert provider["model_env_status"] == "missing"
    assert provider["effective_model"] == "claude-3-5-haiku-latest"
    assert provider["model_source"] == "config_default"
    assert secret_value not in combined


def test_setup_effective_provider_config_reports_configured_secret_name_when_value_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "active": "anthropic",
        "providers": {
            "anthropic": {
                "type": "anthropic",
                "api_key_env": "MINDFORGE_ANTHROPIC_API_KEY",
                "base_url_env": "MINDFORGE_ANTHROPIC_BASE_URL",
                "model_env": "MINDFORGE_ANTHROPIC_MODEL",
                "default_base_url": "https://api.anthropic.com",
                "default_model": "claude-3-5-haiku-latest",
            }
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    provider = client.get("/api/config/editable").json()["llm"]["providers"]["anthropic"]

    assert provider["api_key_env_configured"] is True
    assert provider["api_key_secret_present"] is False
    assert provider["api_key_masked_value"] is None
    assert provider["api_key_status_label"] == "env name configured, value missing"
    assert provider["effective_base_url"] == "https://api.anthropic.com"
    assert provider["effective_model"] == "claude-3-5-haiku-latest"


def test_web_drafts_detail_and_approve_confirmation_boundary(tmp_path: Path, monkeypatch) -> None:
    client, cards = _client(tmp_path, monkeypatch)
    card = _write_draft(cards)

    drafts = client.get("/api/drafts").json()
    assert [draft["id"] for draft in drafts["drafts"]] == ["draft-1"]
    assert drafts["drafts"][0]["strategy_id"] == "five_stage"
    assert drafts["drafts"][0]["source_id"] == "src_draft_1"
    assert drafts["drafts"][0]["prompt_versions"]["triage"] == "v1"
    detail = client.get("/api/drafts/draft-1").json()
    assert "safe draft body" in detail["body"].lower()
    assert detail["draft"]["source_content_hash"] == "sha256:provenancehash"
    assert detail["frontmatter"]["run_id"] == "run-web-provenance"

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
    assert approved["index_updated"] is True
    assert approved["index_path"]
    assert Path(approved["index_path"]).exists()
    assert "status: human_approved" in card.read_text(encoding="utf-8")
    approved_fm = yaml.safe_load(card.read_text(encoding="utf-8").split("---", 2)[1])
    assert approved_fm["strategy_id"] == "five_stage"
    assert approved_fm["prompt_versions"]["distill"] == "v1"


def test_web_workspace_can_save_draft_without_approving_or_losing_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Web 编辑的是 Knowledge Card 正文，不是 source，也不能绕过显式 approve。

    大模型和 source 都不参与这个测试；它只验证 Web API 是否复用卡片持久化边界：
    保存 draft 只替换 body，frontmatter 的 status/provenance 必须原样保留。
    """

    client, cards = _client(tmp_path, monkeypatch)
    card = _write_draft(cards)
    source = tmp_path / "dogfood-vault" / "00-Inbox" / "ManualNotes" / "source-note.md"
    source.write_text("SOURCE_BODY_MUST_NOT_LEAK_AFTER_SAVE", encoding="utf-8")

    saved = client.patch(
        "/api/drafts/draft-1",
        json={"body": "## AI Summary\n\nEdited draft workspace summary.\n"},
    ).json()
    detail = client.get("/api/drafts/draft-1").json()
    combined = f"{saved} {detail}"
    fm = yaml.safe_load(card.read_text(encoding="utf-8").split("---", 2)[1])

    assert saved["ok"] is True
    assert saved["status"] == "ai_draft"
    assert saved["index_updated"] is False
    assert "Edited draft workspace summary" in detail["body"]
    assert "status: ai_draft" in card.read_text(encoding="utf-8")
    assert fm["strategy_id"] == "five_stage"
    assert fm["source_content_hash"] == "sha256:provenancehash"
    assert fm["prompt_versions"]["triage"] == "v1"
    assert "SOURCE_BODY_MUST_NOT_LEAK_AFTER_SAVE" not in combined


def test_web_workspace_can_read_and_save_approved_card_and_refresh_recall(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Library 是正式知识工作台：approved card 可阅读、可编辑，保存后刷新 BM25。

    中文学习型说明：这里 intentionally 用 approved card body 中的 AI Summary 命中
    recall，证明 Web save 后调用的是本地 lexical index rebuild，而不是只改文件。
    """

    client, cards = _client(tmp_path, monkeypatch)
    card = _write_approved(cards)
    source = tmp_path / "dogfood-vault" / "00-Inbox" / "_processed" / "ManualNotes" / "source-note.md"
    source.parent.mkdir(parents=True)
    source.write_text("APPROVED_SOURCE_RAW_MUST_NOT_LEAK", encoding="utf-8")

    detail = client.get("/api/library/card", params={"ref": "approved-1"}).json()
    assert "Approved summary alpha workspace" in detail["body"]
    assert detail["card"]["strategy_label"] == "Knowledge Card Strategy"

    saved = client.patch(
        "/api/library/card",
        params={"ref": "approved-1"},
        json={"body": "## AI Summary\n\nEdited approved gamma workspace.\n"},
    ).json()
    after = client.get("/api/library/card", params={"ref": "approved-1"}).json()
    recall = client.get("/api/recall", params={"q": "gamma workspace"}).json()
    combined = f"{detail} {saved} {after} {recall}"
    fm = yaml.safe_load(card.read_text(encoding="utf-8").split("---", 2)[1])

    assert saved["ok"] is True
    assert saved["status"] == "human_approved"
    assert saved["index_updated"] is True
    assert Path(saved["index_path"]).exists()
    assert "Edited approved gamma workspace" in after["body"]
    assert "status: human_approved" in card.read_text(encoding="utf-8")
    assert fm["source_archive_path"] == "90-Archive/Processed/source-note.md"
    assert fm["run_id"] == "run-approved"
    assert recall["hits"][0]["rel_path"].endswith("approved.md")
    assert recall["hits"][0]["card_ref"] == "approved-1"
    assert recall["hits"][0]["detail_href"].startswith("/library?")
    assert "APPROVED_SOURCE_RAW_MUST_NOT_LEAK" not in combined
    assert "HUMAN_NOTE_MUST_NOT_BE_RECALLABLE" not in recall["hits"][0]["why_this_matched"]


def test_web_reject_and_imports_are_honest_unavailable(tmp_path: Path, monkeypatch) -> None:
    client, cards = _client(tmp_path, monkeypatch)
    _write_draft(cards)

    reject = client.post("/api/drafts/draft-1/reject", json={"reason": "not useful"}).json()
    import_local = client.post("/api/sources/import-local").json()
    import_cubox = client.post("/api/sources/import-cubox-json").json()

    assert reject["available"] is False
    assert import_local["available"] is False
    assert import_cubox["available"] is False


def test_web_watch_list_add_delete_and_import_align_with_cli_ingestion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Web ingestion 必须复用 watch/import 语义，而不是暴露 scan/process 主流程。

    这些动作使用临时 source；断言重点是 registry/card/source 的状态边界：
    watch delete 只删 registry，import 不进 registry，所有自动化只生成 ai_draft。
    """

    client, cards = _client(tmp_path, monkeypatch)
    vault = tmp_path / "dogfood-vault"
    watch_file = tmp_path / "watch-file.md"
    watch_folder = tmp_path / "watch-folder"
    import_file = tmp_path / "import-file.md"
    registered_only_file = tmp_path / "registered-only.md"
    watch_file.write_text("# Watch File\n\nWATCH_BODY_MUST_NOT_LEAK\n", encoding="utf-8")
    watch_folder.mkdir()
    (watch_folder / "watch-folder-note.md").write_text("# Watch Folder\n\nbody\n", encoding="utf-8")
    import_file.write_text("# Import File\n\nIMPORT_BODY_MUST_NOT_LEAK\n", encoding="utf-8")
    registered_only_file.write_text("# Registered Only\n\nbody\n", encoding="utf-8")

    listed = client.get("/api/sources/watch").json()
    assert listed["watched_sources"][0]["id"] == "default-inbox"
    assert listed["watched_sources"][0]["is_default"] is True
    assert listed["watched_sources"][0]["can_delete"] is False

    added_file = client.post("/api/sources/watch", json={"path": str(watch_file)}).json()
    added_folder = client.post("/api/sources/watch", json={"path": str(watch_folder)}).json()
    registered_only = client.post(
        "/api/sources/watch",
        json={"path": str(registered_only_file), "process_now": False},
    ).json()

    assert added_file["ok"] is True
    assert added_file["mode"] == "watch_add"
    assert added_file["counts"]["processed"] == 1
    assert added_file["added_to_registry"] is True
    assert added_folder["counts"]["processed"] == 1
    assert registered_only["added_to_registry"] is True
    assert registered_only["counts"]["processed"] == 0

    frequency_update = client.patch(
        f"/api/sources/watch/{registered_only['watch_id']}/frequency",
        json={"frequency": "daily"},
    ).json()
    assert frequency_update["ok"] is True
    assert "top-level source only" in frequency_update["message"]

    registry = WatchRegistry.load(vault / ".mindforge" / "watched_sources.json")
    assert {source.path for source in registry.sources} == {
        watch_file.resolve(),
        watch_folder.resolve(),
        registered_only_file.resolve(),
    }
    assert next(source for source in registry.sources if source.path == registered_only_file.resolve()).frequency == "daily"

    deleted = client.delete(f"/api/sources/watch/{registry.sources[0].id}").json()
    assert deleted["ok"] is True
    assert deleted["source_deleted"] is False
    assert deleted["cards_deleted"] is False
    assert watch_file.exists()
    assert len(list(cards.rglob("*.md"))) == 2

    imported = client.post("/api/sources/import", json={"path": str(import_file)}).json()

    assert imported["ok"] is True
    assert imported["mode"] == "import"
    assert imported["counts"]["processed"] == 1
    assert imported["added_to_registry"] is False
    assert len(WatchRegistry.load(vault / ".mindforge" / "watched_sources.json").sources) == 2
    assert len(list(cards.rglob("*.md"))) == 3
    assert all("status: ai_draft" in card.read_text(encoding="utf-8") for card in cards.rglob("*.md"))

    after = client.get("/api/sources").json()
    combined = f"{listed} {added_file} {imported} {after}"
    assert "WATCH_BODY_MUST_NOT_LEAK" not in combined
    assert "IMPORT_BODY_MUST_NOT_LEAK" not in combined
    assert "human_approved 必须显式确认" in combined
    assert after["ingestion"]["primary_entry"] == "watch/import"
    assert "advanced" in after["ingestion"]["advanced_note"].lower()


def test_sources_api_returns_recursive_folder_watch_diagnostics(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, cards = _client(tmp_path, monkeypatch)
    watch_folder = tmp_path / "watch-folder"
    supported = watch_folder / "nested" / "supported.md"
    unsupported = watch_folder / "nested" / "unsupported.csv"
    temp_file = watch_folder / "~$draft.md"
    hidden = watch_folder / ".hidden.md"
    generated = watch_folder / "20-Knowledge-Cards" / "generated.md"
    supported.parent.mkdir(parents=True)
    for path, body in (
        (supported, "# Supported\n\nSUPPORTED_BODY_MUST_NOT_LEAK\n"),
        (unsupported, "UNSUPPORTED_BODY_MUST_NOT_LEAK\n"),
        (temp_file, "# Temp\n\nTEMP_BODY_MUST_NOT_LEAK\n"),
        (hidden, "# Hidden\n\nHIDDEN_BODY_MUST_NOT_LEAK\n"),
        (generated, "# Generated\n\nGENERATED_BODY_MUST_NOT_LEAK\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    added = client.post("/api/sources/watch", json={"path": str(watch_folder)}).json()
    response = client.get("/api/sources").json()
    watched = next(item for item in response["watched_sources"] if item["path"] == str(watch_folder.resolve()))
    combined = f"{added} {response}"

    assert added["ok"] is True
    assert watched["path_type"] == "folder"
    assert watched["recursive"] is True
    assert watched["supported_file_count"] == 1
    assert watched["processed_count"] == 1
    assert watched["failed_count"] == 0
    assert watched["skipped_reason_summary"]["unsupported_extension"] == 1
    assert watched["skipped_reason_summary"]["temp_file"] == 1
    assert watched["skipped_reason_summary"]["hidden_file"] == 1
    assert watched["status_label"] in {"Watching", "Processed", "Has generated knowledge"}
    assert len(list(cards.rglob("*.md"))) == 1
    assert watched["status_label"] != "ready"
    assert watched["status"] != "ready"
    assert "Approved" not in combined
    assert "SUPPORTED_BODY_MUST_NOT_LEAK" not in combined
    assert "UNSUPPORTED_BODY_MUST_NOT_LEAK" not in combined
    assert "TEMP_BODY_MUST_NOT_LEAK" not in combined
    assert "HIDDEN_BODY_MUST_NOT_LEAK" not in combined
    assert "GENERATED_BODY_MUST_NOT_LEAK" not in combined


def test_sources_path_actions_are_allowlisted_and_do_not_read_file_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, _cards = _client(tmp_path, monkeypatch)
    source_file = tmp_path / "dogfood-vault" / "00-Inbox" / "ManualNotes" / "source-note.md"
    source_file.write_text("SOURCE_CONTENT_MUST_NOT_BE_READ", encoding="utf-8")
    outside = tmp_path.parent / f"outside-{tmp_path.name}.md"
    outside.write_text("OUTSIDE_CONTENT_MUST_NOT_BE_READ", encoding="utf-8")

    calls: list[tuple[list[str], dict]] = []

    def fake_run(args, **kwargs):
        calls.append((list(args), kwargs))

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("mindforge_web.services.web_path_action_service.sys.platform", "darwin")
    monkeypatch.setattr("mindforge_web.services.web_path_action_service.subprocess.run", fake_run)

    copied = client.post("/api/sources/path-actions/copy", json={"path": str(source_file)}).json()
    opened_file = client.post(
        "/api/sources/path-actions/reveal",
        json={"path": str(source_file)},
    ).json()
    opened_dir = client.post(
        "/api/sources/path-actions/reveal",
        json={"path": str(source_file.parent)},
    ).json()
    missing = client.post(
        "/api/sources/path-actions/reveal",
        json={"path": str(source_file.parent / "missing.md")},
    )
    rejected = client.post("/api/sources/path-actions/reveal", json={"path": str(outside)})
    combined = f"{copied} {opened_file} {opened_dir} {missing.text} {rejected.text}"

    assert copied["ok"] is True
    assert copied["path"] == str(source_file.resolve())
    assert opened_file["ok"] is True
    assert opened_dir["ok"] is True
    assert calls[0][0] == ["open", "-R", str(source_file.resolve())]
    assert calls[0][1].get("shell") is False
    assert calls[1][0] == ["open", str(source_file.parent.resolve())]
    assert calls[1][1].get("shell") is False
    assert missing.status_code == 404
    assert rejected.status_code == 403
    assert "SOURCE_CONTENT_MUST_NOT_BE_READ" not in combined
    assert "OUTSIDE_CONTENT_MUST_NOT_BE_READ" not in combined


def test_sources_status_names_processed_and_generated_knowledge_without_ready_or_approved(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, cards = _client(tmp_path, monkeypatch)
    processed = (
        tmp_path
        / "dogfood-vault"
        / "00-Inbox"
        / "_processed"
        / "ManualNotes"
        / "source-note.md"
    )
    processed.parent.mkdir(parents=True)
    processed.write_text("PROCESSED_SOURCE_BODY_MUST_NOT_LEAK", encoding="utf-8")
    _write_draft(cards)

    response = client.get("/api/sources").json()
    source = response["sources"][0]
    combined = f"{response}"

    assert source["display_status"] == "Processed"
    assert source["generated_knowledge_status"] == "Has generated knowledge"
    assert source["generated_card_count"] == 1
    assert source["generated_card_paths"][0].endswith("draft.md")
    assert "ready" not in combined
    assert "Approved" not in combined
    assert "PROCESSED_SOURCE_BODY_MUST_NOT_LEAK" not in combined
