"""MindForge Local Console API tests.

中文学习型说明：这些测试使用临时 vault/config 验证 Web adapter 边界：
API 可以读取真实本地状态，但不能泄露 secret；approve 必须二次确认，且
最终仍走现有 approval_service 写入单张 ai_draft。
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest
from fastapi.testclient import TestClient

from mindforge.app_context import AppContextError
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
    assert editable["llm"]["available_providers"] == []
    assert editable["llm"]["providers"] == {}
    assert "never-return-this" not in f"{editable}"

    new_vault = tmp_path / "new-vault"
    saved = client.patch(
        "/api/config/editable",
        json={
            "vault_root": str(new_vault),
            "create_vault": True,
        },
    ).json()
    after_raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    combined = f"{saved} {cfg_path.read_text(encoding='utf-8')} {capsys.readouterr()}"

    assert saved["ok"] is True
    assert saved["status"]["vault"]["path"] == str(new_vault.resolve())
    assert saved["status"]["provider"]["active_profile"] == "fake"
    assert (new_vault / "00-Inbox").is_dir()
    assert after_raw["custom_unrelated"] == {"keep": "unchanged"}
    assert after_raw["triage"]["default_track"] == "unrouted"
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


def test_setup_provider_dropdown_uses_only_configured_real_providers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "active": "openai_compatible",
        "providers": {
            "openai_compatible": {
                "type": "openai_compatible",
                "api_key_env": "MINDFORGE_OPENAI_API_KEY",
                "default_model": "gpt-test",
            },
            "all_local": {
                "type": "local",
                "triage": "local_alias",
                "distill": "local_alias",
                "link_suggestion": "local_alias",
                "review_questions": "local_alias",
                "action_extraction": "local_alias",
            },
            "fake": {"type": "fake", "default_model": "fake-fast", "default_base_url": "fake://"},
            "test_default": {
                "type": "test",
                "triage": "test_alias",
                "distill": "test_alias",
                "link_suggestion": "test_alias",
                "review_questions": "test_alias",
                "action_extraction": "test_alias",
            },
        },
        "models": {
            "local_alias": {
                "provider": "local",
                "type": "local",
                "base_url": "http://127.0.0.1:11434",
                "model": "local-model",
            },
            "test_alias": {
                "provider": "test",
                "type": "test",
                "base_url": "test://",
                "model": "test-model",
            },
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    editable = client.get("/api/config/editable").json()
    provider = editable["llm"]["providers"]["openai_compatible"]

    assert editable["llm"]["active_provider"] == "openai_compatible"
    assert editable["llm"]["available_providers"] == ["openai_compatible"]
    assert sorted(editable["llm"]["providers"]) == ["openai_compatible"]
    assert "all_local" not in editable["llm"]["available_providers"]
    assert "anthropic_coding_plan" not in editable["llm"]["available_providers"]
    assert "fake" not in editable["llm"]["available_providers"]
    assert "test_default" not in editable["llm"]["available_providers"]
    assert provider["effective_model"] == "gpt-test"
    assert provider["model_source"] == "config_default"
    assert provider["effective_base_url"] is None
    assert provider["base_url_source"] == "missing"


def test_setup_editable_llm_view_uses_models_default_and_routing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    secret_value = "sk-test-secret-value-abcd"
    raw["llm"] = {
        "default_model": "strong",
        "models": {
            "cheap": {
                "type": "openai_compatible",
                "api_key_env": "MINDFORGE_LLM_API_KEY",
                "base_url": "https://router.example.com/v1",
                "model": "cheap-model",
            },
            "strong": {
                "type": "anthropic_compatible",
                "api_key_env": "MINDFORGE_LLM_API_KEY",
                "base_url": "https://router.example.com/anthropic",
                "model": "strong-model",
            },
            "local": {
                "type": "openai_compatible",
                "api_key_optional": True,
                "base_url": "http://localhost:11434/v1",
                "model": "local-model",
            },
            "fake_fast": {
                "type": "fake",
                "model": "fake-fast",
            },
        },
        "routing": {
            "triage": "cheap",
            "link_suggestion": "cheap",
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MINDFORGE_LLM_API_KEY", secret_value)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    editable = client.get("/api/config/editable").json()
    llm = editable["llm"]
    combined = f"{editable}"

    assert llm["default_model"] == "strong"
    assert sorted(llm["configured_model_ids"]) == ["cheap", "local", "strong"]
    assert sorted(llm["configured_models"]) == ["cheap", "local", "strong"]
    assert llm["routing"]["triage"] == "cheap"
    assert llm["routing"]["distill"] == "strong"
    assert llm["routing"]["review_questions"] == "strong"
    assert llm["routing_is_explicit"] is True
    assert llm["legacy_config_detected"] is False
    assert llm["validation_errors"] == []
    assert llm["configured_models"]["cheap"]["type"] == "openai_compatible"
    assert llm["configured_models"]["cheap"]["api_key_env"] == "MINDFORGE_LLM_API_KEY"
    assert llm["configured_models"]["cheap"]["api_key_secret_present"] is True
    assert llm["configured_models"]["cheap"]["api_key_masked_value"] == "sk-****abcd"
    assert llm["configured_models"]["local"]["api_key_optional"] is True
    assert llm["resolved_per_step_models"]["triage"]["model_id"] == "cheap"
    assert llm["resolved_per_step_models"]["distill"]["model_id"] == "strong"
    assert "fake_fast" not in llm["configured_models"]
    assert secret_value not in combined


def test_setup_editable_llm_view_reports_omitted_routing_and_legacy_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "default_model": "main",
        "models": {
            "main": {
                "type": "openai_compatible",
                "base_url": "https://router.example.com/v1",
                "model": "main-model",
            }
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    llm = client.get("/api/config/editable").json()["llm"]

    assert llm["routing_is_explicit"] is False
    assert llm["routing"] == {stage: "main" for stage in [
        "triage",
        "distill",
        "link_suggestion",
        "review_questions",
        "action_extraction",
    ]}

    legacy_raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    legacy_raw["llm"] = {
        "active_profile": "fake",
        "profiles": {
            "fake": {
                "triage": "fake_alias",
                "distill": "fake_alias",
                "link_suggestion": "fake_alias",
                "review_questions": "fake_alias",
                "action_extraction": "fake_alias",
            },
            "all_local": {
                "triage": "local_alias",
                "distill": "local_alias",
                "link_suggestion": "local_alias",
                "review_questions": "local_alias",
                "action_extraction": "local_alias",
            },
        },
        "models": {
            "fake_alias": {"provider": "fake", "type": "fake", "model": "fake"},
            "local_alias": {
                "provider": "local",
                "type": "openai_compatible",
                "base_url": "http://localhost:11434/v1",
                "model": "local-model",
            },
        },
    }
    cfg_path.write_text(yaml.safe_dump(legacy_raw, sort_keys=False), encoding="utf-8")

    legacy_llm = TestClient(create_app(config_path=cfg_path, host="127.0.0.1")).get(
        "/api/config/editable"
    ).json()["llm"]

    assert legacy_llm["legacy_config_detected"] is True
    assert any("Legacy LLM config detected" in warning for warning in legacy_llm["warnings"])
    assert legacy_llm["configured_models"] == {}
    assert "all_local" not in legacy_llm["configured_model_ids"]
    assert "fake_alias" not in f"{legacy_llm['configured_models']}"


def test_setup_save_writes_new_llm_format_without_legacy_profiles(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    response = client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://router.example.com/v1",
                    "model": "main-model",
                    "api_key_env": "MINDFORGE_LLM_API_KEY",
                },
                "strong": {
                    "type": "anthropic_compatible",
                    "base_url": "https://router.example.com/anthropic",
                    "model": "strong-model",
                    "api_key_env": "MINDFORGE_LLM_API_KEY",
                },
            },
            "routing": {"distill": "strong"},
        },
    )

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    text = cfg_path.read_text(encoding="utf-8")

    assert response.status_code == 200
    assert raw["llm"]["default_model"] == "main"
    assert sorted(raw["llm"]["models"]) == ["main", "strong"]
    assert raw["llm"]["routing"] == {"distill": "strong"}
    assert "active_profile" not in raw["llm"]
    assert "profiles" not in raw["llm"]
    assert "providers" not in raw["llm"]
    assert "stage_models" not in text


def test_setup_provider_dropdown_ignores_legacy_profile_defaults_in_main_ui(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "active_profile": "anthropic_coding_plan",
        "profiles": {
            "all_local": {
                "triage": "local_alias",
                "distill": "local_alias",
                "link_suggestion": "local_alias",
                "review_questions": "local_alias",
                "action_extraction": "local_alias",
            },
            "anthropic_coding_plan": {
                "triage": "anthropic_alias",
                "distill": "anthropic_alias",
                "link_suggestion": "anthropic_alias",
                "review_questions": "anthropic_alias",
                "action_extraction": "anthropic_alias",
            },
            "openai_compatible": {
                "triage": "openai_alias",
                "distill": "openai_alias",
                "link_suggestion": "openai_alias",
                "review_questions": "openai_alias",
                "action_extraction": "openai_alias",
            },
        },
        "models": {
            "local_alias": {
                "provider": "local",
                "type": "local",
                "base_url": "http://127.0.0.1:11434",
                "model": "local-model",
            },
            "anthropic_alias": {
                "provider": "anthropic",
                "type": "anthropic_compatible",
                "base_url": "https://api.anthropic.com",
                "model": "claude-test",
            },
            "openai_alias": {
                "provider": "openai_compatible",
                "type": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-test",
            },
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    editable = client.get("/api/config/editable").json()

    assert editable["llm"]["active_provider"] == "anthropic_coding_plan"
    assert editable["llm"]["available_providers"] == []
    assert editable["llm"]["providers"] == {}
    assert "all_local" not in f"{editable['llm']['available_providers']}"
    assert "anthropic_coding_plan" not in f"{editable['llm']['available_providers']}"
    assert "openai_compatible" not in f"{editable['llm']['available_providers']}"


def test_setup_active_provider_missing_reports_config_error_without_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "active": "missing_provider",
        "providers": {
            "anthropic": {
                "type": "anthropic",
                "api_key_env": "MINDFORGE_ANTHROPIC_API_KEY",
                "default_model": "claude-test",
            }
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(AppContextError) as exc_info:
        create_app(config_path=cfg_path, host="127.0.0.1")

    error_text = str(exc_info.value)
    assert "missing_provider" in error_text
    assert "fake" not in error_text.lower()


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
    assert listed["watched_sources"][0]["can_delete"] is True

    default_frequency_update = client.patch(
        "/api/sources/watch/default-inbox/frequency",
        json={"frequency": "daily"},
    ).json()
    assert default_frequency_update["ok"] is True
    default_stop = client.delete("/api/sources/watch/default-inbox").json()
    assert default_stop["ok"] is True
    assert default_stop["source_deleted"] is False
    assert default_stop["cards_deleted"] is False
    assert "only stops future monitoring" in default_stop["message"]

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
    user_sources = [source for source in registry.sources if not source.is_default]
    assert {source.path for source in user_sources} == {
        watch_file.resolve(),
        watch_folder.resolve(),
        registered_only_file.resolve(),
    }
    assert next(source for source in user_sources if source.path == registered_only_file.resolve()).frequency == "daily"

    deleted = client.delete(f"/api/sources/watch/{user_sources[0].id}").json()
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
    final_registry = WatchRegistry.load(vault / ".mindforge" / "watched_sources.json")
    assert len([source for source in final_registry.sources if not source.is_default]) == 2
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
    assert watched["status_label"] in {"Watching", "Processed"}
    assert len(list(cards.rglob("*.md"))) == 1
    assert watched["status_label"] != "ready"
    assert watched["status"] != "ready"
    assert "Approved" not in combined
    assert "SUPPORTED_BODY_MUST_NOT_LEAK" not in combined
    assert "UNSUPPORTED_BODY_MUST_NOT_LEAK" not in combined
    assert "TEMP_BODY_MUST_NOT_LEAK" not in combined
    assert "HIDDEN_BODY_MUST_NOT_LEAK" not in combined
    assert "GENERATED_BODY_MUST_NOT_LEAK" not in combined


def test_web_stop_watching_built_in_inbox_does_not_delete_knowledge_cards(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, cards = _client(tmp_path, monkeypatch)
    approved = _write_approved(cards)

    response = client.delete("/api/sources/watch/default-inbox").json()
    after = client.get("/api/sources/watch").json()
    built_in = next(item for item in after["watched_sources"] if item["id"] == "default-inbox")

    assert response["ok"] is True
    assert response["source_deleted"] is False
    assert response["cards_deleted"] is False
    assert "only stops future monitoring" in response["message"]
    assert approved.exists()
    assert "status: human_approved" in approved.read_text(encoding="utf-8")
    assert built_in["status"] == "paused"


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


# ============================================================================
# Model config + secret store 测试
# ============================================================================


def test_setup_add_model_writes_new_llm_models_entry(tmp_path: Path, monkeypatch) -> None:
    """Add model 写入 llm.models，API key 进入 secret store。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    response = client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://router.example.com/v1",
                    "model": "main-model",
                    "api_key": "sk-test-key-1234",
                    "api_key_action": "update",
                },
            },
        },
    )
    assert response.status_code == 200

    # 验证 YAML config
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert raw["llm"]["default_model"] == "main"
    assert "main" in raw["llm"]["models"]
    assert raw["llm"]["models"]["main"]["type"] == "openai_compatible"
    # YAML 里不应有 API key
    assert "api_key" not in raw["llm"]["models"]["main"]
    assert "sk-test" not in str(raw)

    # 验证 secret store
    secrets_path = tmp_path / ".mindforge" / "secrets.json"
    import json
    assert secrets_path.is_file()
    secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    assert secrets["main"] == "sk-test-key-1234"


def test_setup_edit_model_preserves_secret_when_empty_key(tmp_path: Path, monkeypatch) -> None:
    """Edit model 时 api_key 为空 → 保留已有 secret。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    # 先创建带 key 的模型
    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://router.example.com/v1",
                    "model": "main-model",
                    "api_key": "sk-original-key",
                    "api_key_action": "update",
                },
            },
        },
    )

    # 编辑：只改 model name，api_key 为空，api_key_action 为 keep
    client.patch(
        "/api/config/editable",
        json={
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://router.example.com/v1",
                    "model": "updated-model",
                    "api_key": "",
                    "api_key_action": "keep",
                },
            },
        },
    )

    import json
    secrets_path = tmp_path / ".mindforge" / "secrets.json"
    secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    assert secrets["main"] == "sk-original-key"


def test_setup_edit_model_clears_secret_on_explicit_action(tmp_path: Path, monkeypatch) -> None:
    """api_key_action=clear → 删除 secret store 中的 key。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    # 先创建带 key 的模型
    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://router.example.com/v1",
                    "model": "main-model",
                    "api_key": "sk-original-key",
                    "api_key_action": "update",
                },
            },
        },
    )

    # 清除 key
    client.patch(
        "/api/config/editable",
        json={
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://router.example.com/v1",
                    "model": "main-model",
                    "api_key_action": "clear",
                },
            },
        },
    )

    import json
    secrets_path = tmp_path / ".mindforge" / "secrets.json"
    secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    assert "main" not in secrets


def test_setup_delete_model_removes_config_and_secret(tmp_path: Path, monkeypatch) -> None:
    """Delete model → 从 config 和 secret store 都删除。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    # 创建两个模型
    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://r.example.com/v1",
                    "model": "main-model",
                    "api_key": "sk-main-key",
                    "api_key_action": "update",
                },
                "secondary": {
                    "type": "anthropic_compatible",
                    "base_url": "https://a.example.com",
                    "model": "secondary-model",
                    "api_key": "sk-secondary-key",
                    "api_key_action": "update",
                },
            },
        },
    )

    # 删除 secondary（从 models dict 中省略）
    response = client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://r.example.com/v1",
                    "model": "main-model",
                },
            },
        },
    )
    assert response.status_code == 200

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert "secondary" not in raw["llm"]["models"]

    import json
    secrets_path = tmp_path / ".mindforge" / "secrets.json"
    secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    assert "secondary" not in secrets
    assert secrets["main"] == "sk-main-key"


def test_setup_cannot_delete_default_model(tmp_path: Path, monkeypatch) -> None:
    """不允许删除 default_model 引用的模型。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://r.example.com/v1",
                    "model": "main-model",
                },
            },
        },
    )

    # 尝试删除 main 但保持 default_model=main
    response = client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {},
        },
    )
    assert response.status_code == 400


def test_setup_cannot_leave_routing_to_deleted_model(tmp_path: Path, monkeypatch) -> None:
    """不允许 routing 引用即将被删除的模型。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {"type": "openai_compatible", "base_url": "https://r.example.com/v1", "model": "main-model"},
                "strong": {"type": "anthropic_compatible", "base_url": "https://a.example.com", "model": "strong-model"},
            },
            "routing": {"distill": "strong"},
        },
    )

    # 尝试删 strong 但 routing 仍引用它
    response = client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {"type": "openai_compatible", "base_url": "https://r.example.com/v1", "model": "main-model"},
            },
        },
    )
    assert response.status_code == 400


def test_setup_api_key_never_returned_raw(tmp_path: Path, monkeypatch) -> None:
    """API response 永远不返回 raw API key。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://r.example.com/v1",
                    "model": "main-model",
                    "api_key": "sk-very-secret-key-1234",
                    "api_key_action": "update",
                },
            },
        },
    )

    editable = client.get("/api/config/editable").json()
    model = editable["llm"]["configured_models"]["main"]
    combined = f"{editable}"

    # 确认 masked 值存在
    assert model["api_key_masked_value"] == "sk-****1234"
    assert model["api_key_source"] == "local_secret"
    assert model["api_key_secret_present"] is True

    # raw key 绝不出现在 response 中
    assert "sk-very-secret-key-1234" not in combined
    assert "very-secret" not in combined


def test_setup_demo_model_labeled_correctly(tmp_path: Path, monkeypatch) -> None:
    """type=fake 的模型标记为 is_demo_model，api_key_source=demo。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)

    # 写入只有 fake 模型的 config
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "default_model": "demo",
        "models": {
            "demo": {
                "type": "fake",
                "base_url": "fake://",
                "model": "demo-model",
            },
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    editable = client.get("/api/config/editable").json()
    model = editable["llm"]["configured_models"].get("demo")
    assert model is not None, "demo model should appear when it is the only model"
    assert model["is_demo_model"] is True
    assert model["api_key_source"] == "demo"


def test_setup_default_model_dropdown_only_configured_models(tmp_path: Path, monkeypatch) -> None:
    """default_model 下拉只包含已配置的模型。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "a",
            "models": {
                "a": {"type": "openai_compatible", "base_url": "https://x.com/v1", "model": "a-model"},
                "b": {"type": "openai_compatible", "base_url": "https://y.com/v1", "model": "b-model"},
            },
        },
    )

    editable = client.get("/api/config/editable").json()
    ids = editable["llm"]["configured_model_ids"]
    assert sorted(ids) == ["a", "b"]


def test_setup_routing_dropdown_only_configured_models(tmp_path: Path, monkeypatch) -> None:
    """routing dropdown 只包含 configured models。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {"type": "openai_compatible", "base_url": "https://x.com/v1", "model": "main-model"},
            },
            "routing": {"distill": "main"},
        },
    )

    editable = client.get("/api/config/editable").json()
    for model_id in editable["llm"]["routing"].values():
        assert model_id in editable["llm"]["configured_model_ids"]


def test_setup_routing_omitted_uses_default_model(tmp_path: Path, monkeypatch) -> None:
    """routing 省略时所有 workflow step 使用 default_model。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {"type": "openai_compatible", "base_url": "https://x.com/v1", "model": "main-model"},
            },
        },
    )

    editable = client.get("/api/config/editable").json()
    assert editable["llm"]["routing_is_explicit"] is False
    for _stage, model_id in editable["llm"]["routing"].items():
        assert model_id == "main"


def test_setup_type_must_be_explicit_no_guessing(tmp_path: Path, monkeypatch) -> None:
    """type 必须显式选择，不能从 URL 自动猜。该验证由 config 层保证。"""
    from mindforge.config import ConfigError, load_mindforge_config

    yaml_path = tmp_path / "test.yaml"
    yaml_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {"root": str(tmp_path)},
                "llm": {
                    "default_model": "main",
                    "models": {
                        "main": {
                            "model": "some-model",
                            "base_url": "https://api.openai.com/v1",
                            # 故意缺失 type
                        },
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="type"):
        load_mindforge_config(yaml_path)


def test_setup_api_key_not_in_yaml_when_stored_in_secret_store(tmp_path: Path, monkeypatch) -> None:
    """API key 存在 secret store 时，YAML config 不应包含 raw key。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://r.example.com/v1",
                    "model": "main-model",
                    "api_key": "sk-sensitive-key-9999",
                    "api_key_action": "update",
                },
            },
        },
    )

    yaml_text = cfg_path.read_text(encoding="utf-8")
    assert "sk-sensitive" not in yaml_text
    assert "9999" not in yaml_text


def test_setup_secret_store_under_mindforge_dir(tmp_path: Path, monkeypatch) -> None:
    """Secret store 位于 .mindforge/secrets.json，已被 .gitignore 覆盖。"""
    from mindforge_web.services.secret_store import SecretStore

    store = SecretStore(tmp_path / ".mindforge" / "secrets.json")
    store.set("test-model", "sk-test-value")
    assert store.present("test-model") is True
    assert store.get("test-model") == "sk-test-value"
    assert store.masked("test-model") == "sk-****alue"
    store.remove("test-model")
    assert store.present("test-model") is False

    # 验证 .mindforge/ 在 gitignore 中
    gitignore = Path(__file__).parent.parent / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")
    assert ".mindforge/" in content


# ============================================================================
# Env var field cleanup 测试 —— 普通保存不写回 env 字段
# ============================================================================


def test_setup_save_does_not_write_env_var_fields(tmp_path: Path, monkeypatch) -> None:
    """Web 普通保存模型时不写出 api_key_env/base_url_env/model_env。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://router.example.com/v1",
                    "model": "main-model",
                    "api_key": "sk-test-key",
                    "api_key_action": "update",
                },
            },
        },
    )

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    model = raw["llm"]["models"]["main"]

    # 产品字段存在
    assert model["type"] == "openai_compatible"
    assert model["base_url"] == "https://router.example.com/v1"
    assert model["model"] == "main-model"

    # env var name 字段不应出现
    assert "api_key_env" not in model
    assert "base_url_env" not in model
    assert "model_env" not in model
    assert "version_env" not in model

    # API key raw value 不应在 YAML 中
    yaml_text = cfg_path.read_text(encoding="utf-8")
    assert "sk-test" not in yaml_text


def test_setup_save_cleans_up_legacy_env_fields(tmp_path: Path, monkeypatch) -> None:
    """已有 api_key_env/base_url_env 的旧配置，保存后应清理 env 字段。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)

    # 写入含 env 字段的旧格式配置
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "default_model": "main",
        "models": {
            "main": {
                "type": "openai_compatible",
                "base_url": "https://old.example.com/v1",
                "model": "old-model",
                "api_key_env": "MINDFORGE_LLM_API_KEY",
                "base_url_env": "MINDFORGE_LLM_BASE_URL",
                "model_env": "MINDFORGE_LLM_MODEL",
            },
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    # 保存：只改 model name，不传 env 字段
    client.patch(
        "/api/config/editable",
        json={
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://new.example.com/v1",
                    "model": "new-model",
                },
            },
        },
    )

    raw_after = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    model = raw_after["llm"]["models"]["main"]

    assert model["base_url"] == "https://new.example.com/v1"
    assert model["model"] == "new-model"
    assert "api_key_env" not in model
    assert "base_url_env" not in model
    assert "model_env" not in model


def test_setup_legacy_config_with_env_fields_still_loads(tmp_path: Path, monkeypatch) -> None:
    """旧配置有 api_key_env/base_url_env/model_env 时仍可正确加载和展示。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "default_model": "legacy",
        "models": {
            "legacy": {
                "type": "anthropic_compatible",
                "base_url": "https://legacy.example.com",
                "model": "legacy-model",
                "api_key_env": "MINDFORGE_LEGACY_KEY",
                "base_url_env": "MINDFORGE_LEGACY_URL",
                "model_env": "MINDFORGE_LEGACY_MODEL",
            },
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    # 模拟 env var 有值
    monkeypatch.setenv("MINDFORGE_LEGACY_KEY", "sk-legacy-key-value")
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    editable = client.get("/api/config/editable").json()
    model = editable["llm"]["configured_models"]["legacy"]

    # 读兼容：env 字段仍在响应中（供 Advanced 展示）
    assert model["api_key_env"] == "MINDFORGE_LEGACY_KEY"
    assert model["base_url_env"] == "MINDFORGE_LEGACY_URL"
    assert model["model_env"] == "MINDFORGE_LEGACY_MODEL"
    # API key 来自 env
    assert model["api_key_secret_present"] is True
    assert model["api_key_source"] == "env"
    # raw key 永不泄露
    assert "sk-legacy-key-value" not in f"{editable}"


def test_setup_api_key_env_presence_reads_from_config(tmp_path: Path, monkeypatch) -> None:
    """旧配置的 api_key_env 在 Advanced section 可读，但 raw value 不泄露。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "default_model": "main",
        "models": {
            "main": {
                "type": "openai_compatible",
                "base_url": "https://r.example.com/v1",
                "model": "main-model",
                "api_key_env": "MINDFORGE_LLM_API_KEY",
            },
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MINDFORGE_LLM_API_KEY", "sk-secret-env-value")
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    editable = client.get("/api/config/editable").json()
    model = editable["llm"]["configured_models"]["main"]
    response_text = f"{editable}"

    # env var name 在 Advanced 可读
    assert model["api_key_env"] == "MINDFORGE_LLM_API_KEY"
    # masked value 正确
    assert model["api_key_masked_value"] == "sk-****alue"
    # raw value 绝对不泄露
    assert "sk-secret-env-value" not in response_text


def test_setup_env_fields_not_in_main_ui_labels(tmp_path: Path, monkeypatch) -> None:
    """验证 legacy env 字段不在主 UI 标签中出现。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "default_model": "main",
        "models": {
            "main": {
                "type": "openai_compatible",
                "base_url": "https://r.example.com/v1",
                "model": "main-model",
                "api_key_env": "MINDFORGE_LLM_API_KEY",
                "base_url_env": "MINDFORGE_LLM_BASE_URL",
                "model_env": "MINDFORGE_LLM_MODEL",
            },
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    editable = client.get("/api/config/editable").json()
    model = editable["llm"]["configured_models"]["main"]

    # EditableModelConfig 不暴露 env var name 作为主字段
    # api_key_source 从 env 读取（而非 local_secret）
    assert "api_key_source" in model
    assert "is_demo_model" in model
    # env var name 仍可通过 api_key_env 读取（Advanced）
    assert model["api_key_env"] == "MINDFORGE_LLM_API_KEY"


def test_setup_secret_store_preserved_on_edit_no_env_fields(tmp_path: Path, monkeypatch) -> None:
    """Edit model 时空 API key → 保留 secret store，不写 env 字段。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    # 先创建带 key 的模型
    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://r.example.com/v1",
                    "model": "main-model",
                    "api_key": "sk-preserve-me",
                    "api_key_action": "update",
                },
            },
        },
    )

    # 编辑：api_key 为空，api_key_action keep
    client.patch(
        "/api/config/editable",
        json={
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://r.example.com/v1",
                    "model": "updated-model",
                },
            },
        },
    )

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    model = raw["llm"]["models"]["main"]
    assert model["model"] == "updated-model"
    assert "api_key_env" not in model
    assert "base_url_env" not in model

    import json
    secrets = json.loads((tmp_path / ".mindforge" / "secrets.json").read_text(encoding="utf-8"))
    assert secrets["main"] == "sk-preserve-me"


def test_setup_clear_key_removes_secret_not_env_fields(tmp_path: Path, monkeypatch) -> None:
    """Clear key → 删除 secret store，不写 env 字段。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://r.example.com/v1",
                    "model": "main-model",
                    "api_key": "sk-will-be-cleared",
                    "api_key_action": "update",
                },
            },
        },
    )

    client.patch(
        "/api/config/editable",
        json={
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://r.example.com/v1",
                    "model": "main-model",
                    "api_key_action": "clear",
                },
            },
        },
    )

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    model = raw["llm"]["models"]["main"]
    assert "api_key_env" not in model

    import json
    secrets = json.loads((tmp_path / ".mindforge" / "secrets.json").read_text(encoding="utf-8"))
    assert "main" not in secrets


def test_setup_default_model_and_routing_still_work_without_env_fields(tmp_path: Path, monkeypatch) -> None:
    """default_model 和 routing 在不用 env 字段时仍正常工作。"""
    cfg_path, _vault, _cards = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "a",
            "models": {
                "a": {"type": "openai_compatible", "base_url": "https://a.com/v1", "model": "a-model"},
                "b": {"type": "anthropic_compatible", "base_url": "https://b.com", "model": "b-model"},
            },
            "routing": {"distill": "b", "review_questions": "b"},
        },
    )

    editable = client.get("/api/config/editable").json()
    assert editable["llm"]["default_model"] == "a"
    assert editable["llm"]["routing"]["distill"] == "b"
    assert editable["llm"]["routing"]["triage"] == "a"  # fallback
    assert editable["llm"]["routing_is_explicit"] is True
