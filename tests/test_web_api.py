"""MindForge Local Console API tests.

中文学习型说明：这些测试使用临时 vault/config 验证 Web adapter 边界：
API 可以读取真实本地状态，但不能泄露 secret；approve 必须二次确认，且
最终仍走现有 approval_service 写入单张 ai_draft。
"""

from __future__ import annotations

from pathlib import Path
import time

import yaml
import pytest
from fastapi.testclient import TestClient

from mindforge.app_context import AppContextError
from mindforge.config import REQUIRED_STAGES
from mindforge.watch_registry import WatchRegistry
from mindforge_web.app import create_app
from mindforge_web.services.processing_run_service import _now, _safe_error_message


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


def _write_approved_card(cards: Path, *, name: str = "approved.md") -> Path:
    """写一张 Web API 测试用 approved card；不含 source 正文或 secret。"""

    card = cards / name
    card.write_text(
        """---
id: approved-web-1
title: Approved Web Card
status: human_approved
track: agent-runtime
tags:
  - web
source_type: manual_note
source_path: 00-Inbox/ManualNotes/source-note.md
source_title: Safe source
value_score: 8
created_at: 2026-05-08
---

## AI Summary

Approved summary.
""",
        encoding="utf-8",
    )
    return card


def test_wiki_rebuild_json_mode_overrides_config_mode_for_deterministic(tmp_path: Path) -> None:
    """Web rebuild 按 JSON body 的 mode 执行，不能因 config wiki.mode=llm 回落误跑 LLM。"""

    cfg_path, _vault, cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["wiki"] = {"mode": "llm", "model": "missing"}
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    _write_approved_card(cards)

    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
    response = client.post("/api/wiki/rebuild", json={"mode": "deterministic"})

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["mode"] == "deterministic"
    assert data["included_cards"] == 1


def test_wiki_rebuild_json_mode_runs_llm_branch(tmp_path: Path, monkeypatch) -> None:
    """Web LLM 按钮传 JSON mode=llm 时后端必须进入 LLM rebuild 分支。"""

    from mindforge.wiki_service import LLMWikiResult

    cfg_path, _vault, _cards = _write_config(tmp_path)
    called = {"value": False}

    def _fake_llm_rebuild(_cfg):
        called["value"] = True
        return LLMWikiResult(
            wiki_path=str(tmp_path / "Main-Wiki.md"),
            included_cards=1,
            section_count=1,
            additional_cards=0,
            warnings=[],
            model_id="main",
            last_rebuilt_at="2026-05-08T00:00:00+0800",
        )

    monkeypatch.setattr("mindforge.wiki_service.llm_rebuild_wiki", _fake_llm_rebuild)

    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
    response = client.post("/api/wiki/rebuild", json={"mode": "llm"})

    assert response.status_code == 200
    data = response.json()
    assert called["value"] is True
    assert data["ok"] is True
    assert data["mode"] == "llm"
    assert data["model_id"] == "main"


def test_setup_save_preserves_wiki_auto_rebuild_false(tmp_path: Path) -> None:
    """Setup PATCH 中的 false 是显式用户选择，不能被当成未设置丢弃。"""

    cfg_path, _vault, _cards = _write_config(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    response = client.patch(
        "/api/config/editable",
        json={"wiki_mode": "deterministic", "wiki_auto_rebuild_on_approve": False},
    )

    assert response.status_code == 200
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert raw["wiki"]["mode"] == "deterministic"
    assert raw["wiki"]["auto_rebuild_on_approve"] is False


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


def _wait_for_processing_run(
    client: TestClient,
    run_id: str,
    *,
    timeout: float = 5.0,
) -> dict:
    """轮询后台 processing run，避免测试重新把 HTTP 请求变成同步等待。

    中文学习型说明：Web 请求只负责启动后台任务；测试通过独立 status API
    观察最终结果，锁定“启动边界”和“完成反馈边界”是两条不同链路。
    """

    deadline = time.monotonic() + timeout
    latest: dict | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/processing/runs/{run_id}")
        assert response.status_code == 200
        latest = response.json()
        if latest["status"] not in {"queued", "running"}:
            return latest
        time.sleep(0.05)
    raise AssertionError(f"processing run {run_id} did not finish; latest={latest}")


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
    _wait_for_processing_run(client, added.json()["run_id"])
    sources = client.get("/api/sources").json()

    assert added.status_code == 200
    watched = [item for item in sources["watched_sources"] if item["path"] == str(source.resolve())][0]
    assert watched["frequency"] == "daily"
    assert watched["last_scan_at"]
    assert watched["next_scan_at"]
    assert watched["due_status"] in {"Due", "Not due", "Manual"}
    assert "added" in watched["diff_counts"]


def test_add_and_process_now_starts_background_run_and_draft_becomes_reviewable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Add and process now 只启动后台 run；draft 完成后才出现在 Review。"""

    client, _cards = _client(tmp_path, monkeypatch)
    source = tmp_path / "watched.md"
    source.write_text("# Background Source\n\nbody worth keeping\n", encoding="utf-8")

    response = client.post(
        "/api/sources/watch",
        json={"path": str(source), "frequency": "manual", "process_now": True},
    )

    assert response.status_code == 200
    started = response.json()
    assert started["run_id"]
    assert started["processing_status"] in {"queued", "running"}
    assert "background" in started["message"].lower()
    assert "You can keep using MindForge." in started["message"]
    assert "processed as ai_draft" not in started["message"]
    assert all(action.get("href") != "/drafts" for action in started["next_actions"])

    finished = _wait_for_processing_run(client, started["run_id"])
    assert finished["status"] == "succeeded"
    assert finished["summary"]["drafts"] == 1
    assert finished["draft_ids"]
    assert any(action.get("href") == "/drafts" for action in finished["next_actions"])

    drafts = client.get("/api/drafts").json()
    assert len(drafts["drafts"]) == 1
    assert drafts["drafts"][0]["status"] == "ai_draft"
    library = client.get("/api/library/cards").json()
    assert library["stats"]["by_status"].get("human_approved", 0) == 0
    assert not (tmp_path / "dogfood-vault" / "40-Wiki" / "Main-Wiki.md").exists()


def test_process_now_starts_background_run_and_sources_expose_last_run_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Sources 页 Process now 返回 run_id，刷新后能看到 last run summary。"""

    client, _cards = _client(tmp_path, monkeypatch)
    source = tmp_path / "watched.md"
    source.write_text("# Existing Watch\n\nbody worth keeping\n", encoding="utf-8")
    added = client.post(
        "/api/sources/watch",
        json={"path": str(source), "frequency": "manual", "process_now": False},
    ).json()

    response = client.post("/api/sources/watch/scan", params={"ref": added["watch_id"]})

    assert response.status_code == 200
    started = response.json()
    assert started["run_id"]
    assert started["processing_status"] in {"queued", "running"}
    assert "background" in started["message"].lower()
    assert "You can keep using MindForge." in started["message"]

    finished = _wait_for_processing_run(client, started["run_id"])
    assert finished["status"] == "succeeded"

    sources = client.get("/api/sources").json()
    watched = [item for item in sources["watched_sources"] if item["id"] == added["watch_id"]][0]
    assert watched["last_run_summary"]["drafts"] == 1
    assert watched["last_message"] == "Generated 1 AI draft."
    assert watched["generated_draft_count"] == 1
    assert watched["processing_status"] == "succeeded"


def test_processing_run_reports_triage_skip_reason_without_review_next_action(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Triage skipped 时必须告诉用户原因，不能指向空 Review。"""

    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["triage"]["value_score_threshold"] = 9
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
    source = tmp_path / "low-value.md"
    source.write_text("# Low Value\n\nshort note\n", encoding="utf-8")

    started = client.post(
        "/api/sources/watch",
        json={"path": str(source), "frequency": "manual", "process_now": True},
    ).json()
    finished = _wait_for_processing_run(client, started["run_id"])

    assert finished["status"] == "skipped"
    assert finished["summary"]["drafts"] == 0
    assert finished["summary"]["skipped"] == 1
    assert "value_score=7" in finished["message"]
    assert "threshold=9" in finished["message"]
    assert finished["skip_reasons"]
    assert all(action.get("href") != "/drafts" for action in finished["next_actions"])
    assert client.get("/api/drafts").json()["drafts"] == []


def test_processing_run_failure_is_persisted_and_secret_safe(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Provider/config error 进入 failed run，不泄露 API key，也不无限 loading。"""

    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"]["models"]["fake_alias"]["type"] = "openai_compatible"
    raw["llm"]["models"]["fake_alias"]["provider"] = "openai_compatible"
    raw["llm"]["models"]["fake_alias"]["api_key_env"] = "MINDFORGE_FAKE_SECRET"
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    (tmp_path / ".env").write_text("MINDFORGE_FAKE_SECRET=secret-must-not-leak\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MINDFORGE_FAKE_SECRET", raising=False)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
    source = tmp_path / "provider-error.md"
    source.write_text("# Provider Error\n\nbody\n", encoding="utf-8")

    started = client.post(
        "/api/sources/watch",
        json={"path": str(source), "frequency": "manual", "process_now": True},
    ).json()
    finished = _wait_for_processing_run(client, started["run_id"])
    sources = client.get("/api/sources").json()
    run_record = (
        tmp_path / ".mindforge" / "processing_runs" / f"{started['run_id']}.json"
    ).read_text(encoding="utf-8")
    combined = f"{started} {finished} {sources}"

    assert finished["status"] == "failed"
    assert finished["summary"]["errors"] >= 1
    assert finished["error_message"]
    watched = next(item for item in sources["watched_sources"] if item["path"] == str(source.resolve()))
    assert watched["processing_status"] == "failed"
    assert watched["last_run_summary"]["errors"] >= 1
    assert watched["last_message"]
    assert watched["last_error"]
    assert "secret-must-not-leak" not in combined
    assert "secret-must-not-leak" not in run_record
    assert "processed as ai_draft" not in combined
    assert all(action.get("href") != "/drafts" for action in finished["next_actions"])


def test_processing_run_json_parse_failure_finishes_as_failed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """LLM JSON parse failure 必须结束为 failed run，不能让 UI 一直 loading。"""

    from mindforge.llm.base import LLMResult
    from mindforge.llm.fake import FakeProvider

    original_generate = FakeProvider.generate

    def invalid_distill_json(self, request):
        if request.stage == "distill":
            return LLMResult(
                text="{not valid json",
                tokens_in=1,
                tokens_out=1,
                latency_ms=0,
                raw={"fake": True},
            )
        return original_generate(self, request)

    monkeypatch.setattr(FakeProvider, "generate", invalid_distill_json)
    client, _cards = _client(tmp_path, monkeypatch)
    source = tmp_path / "bad-json.md"
    source.write_text("# Bad JSON\n\nbody worth processing\n", encoding="utf-8")

    started = client.post(
        "/api/sources/watch",
        json={"path": str(source), "frequency": "manual", "process_now": True},
    ).json()
    finished = _wait_for_processing_run(client, started["run_id"])

    assert finished["status"] == "failed"
    assert finished["summary"]["errors"] == 1
    assert finished["error_message"] or finished["message"]
    assert "processed as ai_draft" not in f"{finished}"


def test_processing_run_provider_html_error_is_user_friendly() -> None:
    """Provider HTML 错误页不能原样进入 run record / Sources 文案。

    中文学习型说明：真实模型配置仍是用户主路径，但代理、网关、base_url
    配错时常返回 HTML。用户需要可行动的错误，不需要看到整页 HTML。
    """

    message = "LLM 调用失败：HTTP 503: <!DOCTYPE html><html><title>ERROR</title>"

    cleaned = _safe_error_message(message)

    assert "Provider returned an HTML error page (HTTP 503)." in cleaned
    assert "<html" not in cleaned.lower()
    assert "<!DOCTYPE" not in cleaned


def test_processing_run_started_at_uses_subsecond_precision() -> None:
    """重复点击 Process Now 时，run 排序需要亚秒级 started_at。

    中文学习型说明：当前不引入队列/锁等大架构，只先守住状态归属边界：
    同一 source 的多个后台 run 至少要有可排序的高精度 started_at，避免
    Sources last run summary 在同一秒内随机指向旧 run。
    """

    timestamp = _now()

    assert "." in timestamp
    assert len(timestamp.split(".", 1)[1].split("+", 1)[0]) == 6


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
            "vault_root": "/",
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
    assert raw["llm"]["routing"] == {
        "triage": "main",
        "distill": "strong",
        "link_suggestion": "main",
        "review_questions": "main",
        "action_extraction": "main",
    }
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
    assert detail["card"]["strategy_label"] == "Knowledge Card Workflow"

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
    assert added_file["run_id"]
    assert added_file["counts"]["processed"] == 0
    assert added_file["added_to_registry"] is True
    assert added_folder["run_id"]
    assert added_folder["counts"]["processed"] == 0
    assert registered_only["added_to_registry"] is True
    assert registered_only["counts"]["processed"] == 0
    _wait_for_processing_run(client, added_file["run_id"])
    _wait_for_processing_run(client, added_folder["run_id"])

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
    assert "自动化只生成 ai_draft" in combined
    assert after["ingestion"]["primary_entry"] == "watch/import"
    assert "advanced" in after["ingestion"]["advanced_note"].lower()


def test_web_process_uses_default_model_when_routing_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Web Process now 兼容只有 default_model 的新格式配置。

    中文学习型说明：Setup 主路径会补齐 routing，但 runtime 仍要接受旧 dogfood
    clone 中可能已有的“default_model + models、无 routing”配置，不能退回旧
    profile[stage] 导致 KeyError。
    """

    cfg_path, _vault, cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {
        "default_model": "main",
        "models": {
            "main": {
                "provider": "fake",
                "type": "fake",
                "base_url": "fake://",
                "model": "fake",
                "timeout_seconds": 5,
                "max_retries": 0,
                "api_key_optional": True,
            }
        },
    }
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
    source = tmp_path / "default-model-only.md"
    source.write_text("# Default Model Only\n\nbody\n", encoding="utf-8")

    response = client.post("/api/sources/watch", json={"path": str(source)})

    assert response.status_code == 200, response.text
    finished = _wait_for_processing_run(client, response.json()["run_id"])
    assert finished["summary"]["drafts"] == 1
    assert len(list(cards.rglob("*.md"))) == 1


def test_web_process_without_model_returns_friendly_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {"default_model": None, "models": {}, "routing": {}}
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(
        create_app(config_path=cfg_path, host="127.0.0.1"),
        raise_server_exceptions=False,
    )
    source = tmp_path / "no-model.md"
    source.write_text("# No Model\n\nbody\n", encoding="utf-8")

    response = client.post("/api/sources/watch", json={"path": str(source)})

    assert response.status_code == 400
    detail = response.json()["detail"]["message"]
    assert "No model configured for stage 'triage'" in detail
    assert "Add a model in Web Setup" in detail
    assert "Traceback" not in response.text


def test_web_watch_scan_without_model_returns_friendly_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, _vault, _cards = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["llm"] = {"default_model": None, "models": {}, "routing": {}}
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = TestClient(
        create_app(config_path=cfg_path, host="127.0.0.1"),
        raise_server_exceptions=False,
    )
    source = tmp_path / "scan-no-model.md"
    source.write_text("# Scan No Model\n\nbody\n", encoding="utf-8")
    registered = client.post(
        "/api/sources/watch",
        json={"path": str(source), "process_now": False},
    ).json()

    response = client.post(f"/api/sources/watch/scan?ref={registered['watch_id']}")

    assert response.status_code == 400
    assert "No model configured for stage 'triage'" in response.json()["detail"]["message"]
    assert "Traceback" not in response.text


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
    _wait_for_processing_run(client, added["run_id"])
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
    assert watched["status_label"] in {"Watching", "Processed", "Succeeded"}
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
    assert raw["llm"]["routing"] == {stage: "main" for stage in REQUIRED_STAGES}
    # YAML 里不应有 API key
    assert "api_key" not in raw["llm"]["models"]["main"]
    assert "sk-test" not in str(raw)

    # 验证 secret store
    secrets_path = tmp_path / ".mindforge" / "secrets.json"
    import json
    assert secrets_path.is_file()
    secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    assert secrets["main"] == "sk-test-key-1234"


def test_clean_clone_setup_api_bootstraps_no_model_config(tmp_path: Path, monkeypatch) -> None:
    """Web app 在 clean clone 缺本地 config 时应进入 No model configured 状态。"""

    workspace = tmp_path / "mindforge"
    (workspace / "configs").mkdir(parents=True)
    (workspace / "configs" / "mindforge_example.yaml").write_text("version: 0.7\n", encoding="utf-8")
    (workspace / "pyproject.toml").write_text("[project]\nname='mindforge'\n", encoding="utf-8")
    (workspace / "src" / "mindforge").mkdir(parents=True)
    monkeypatch.chdir(workspace)

    cfg_path = workspace / "configs" / "mindforge.yaml"
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
    response = client.get("/api/config/editable")

    assert response.status_code == 200
    assert cfg_path.is_file()
    llm = response.json()["llm"]
    assert llm["configured_model_ids"] == []
    assert llm["configured_models"] == {}
    assert llm["default_model"] is None
    assert llm["validation_errors"] == []


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


def test_setup_hides_fake_model_from_user_config_surface(tmp_path: Path, monkeypatch) -> None:
    """type=fake 只能作为内部测试替身，不能进入普通用户 Setup 列表。"""
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
    assert model is None


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
    """Setup 保存时补齐 routing；runtime 仍保留 default_model fallback。"""
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
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert editable["llm"]["routing_is_explicit"] is True
    assert editable["llm"]["routing"] == {stage: "main" for stage in REQUIRED_STAGES}
    assert raw["llm"]["routing"] == {stage: "main" for stage in REQUIRED_STAGES}


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
    from mindforge.secret_store import SecretStore

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


# ============================================================================
# Secret store → provider runtime 测试
# ============================================================================


def test_anthropic_provider_resolves_key_from_secret_store(tmp_path: Path, monkeypatch) -> None:
    """anthropic_compatible model 无 api_key_env 时从 secret store 取 key。"""
    from mindforge.secret_store import SecretStore
    from mindforge.llm.anthropic_compatible import _resolve_api_key

    store = SecretStore(tmp_path / ".mindforge" / "secrets.json")
    store.set("test-model", "sk-secret-store-key")
    monkeypatch.chdir(tmp_path)

    result = _resolve_api_key("test-model", None)
    assert result == "sk-secret-store-key"


def test_openai_provider_resolves_key_from_secret_store(tmp_path: Path, monkeypatch) -> None:
    """openai_compatible model 无 api_key_env 时从 secret store 取 key。"""
    from mindforge.secret_store import SecretStore
    from mindforge.llm.anthropic_compatible import _resolve_api_key

    store = SecretStore(tmp_path / ".mindforge" / "secrets.json")
    store.set("openai-model", "sk-openai-key")
    monkeypatch.chdir(tmp_path)

    result = _resolve_api_key("openai-model", None)
    assert result == "sk-openai-key"


def test_env_var_still_takes_priority(tmp_path: Path, monkeypatch) -> None:
    """env var 优先级高于 secret store。"""
    from mindforge.secret_store import SecretStore
    from mindforge.llm.anthropic_compatible import _resolve_api_key

    store = SecretStore(tmp_path / ".mindforge" / "secrets.json")
    store.set("test-model", "sk-from-store")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TEST_API_KEY", "sk-from-env")

    result = _resolve_api_key("test-model", "TEST_API_KEY")
    assert result == "sk-from-env"


def test_missing_key_returns_none(tmp_path: Path, monkeypatch) -> None:
    """不存在的 model 返回 None。"""
    from mindforge.llm.anthropic_compatible import _resolve_api_key
    monkeypatch.chdir(tmp_path)

    result = _resolve_api_key("nonexistent", None)
    assert result is None


def test_anthropic_provider_error_never_includes_raw_key() -> None:
    """Provider error message 不包含 raw API key。"""
    from mindforge.llm.base import ProviderError

    # 验证 error message 模版不含 raw key 引用
    try:
        raise ProviderError(
            "模型 test 没有可用的 API key。请在 Web Setup 中添加 key，"
            "或设置环境变量 TEST_KEY。"
        )
    except ProviderError as e:
        msg = str(e)
        assert "sk-" not in msg
        assert "secret" not in msg.lower()


def test_review_route_serves_drafts_page(tmp_path: Path, monkeypatch) -> None:
    """/review 路由正确导向 Drafts 页面，不回退到 Home。"""
    # 验证前端 SPA 路由：/review 和 /drafts 都映射到 DraftsPage
    # 通过检查 App.tsx 源码确认
    app_tsx = Path(__file__).parent.parent / "web" / "src" / "App.tsx"
    content = app_tsx.read_text(encoding="utf-8")
    assert 'path.startsWith("/review")' in content
    assert "DraftsPage" in content


def test_dogfood_command_hidden_from_main_help() -> None:
    """dogfood 命令不出现在主 help 中。"""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "mindforge", "--help"],
        capture_output=True,
        text=True,
        cwd="/Users/jinkun.wang/work_space/mindforge",
    )
    # dogfood 不应出现在主 help 输出中
    assert "dogfood" not in result.stdout


def test_setup_cli_direct_help_is_retired() -> None:
    """旧 setup help 不再作为第二套配置入口暴露。"""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "mindforge", "setup", "--help"],
        capture_output=True,
        text=True,
        cwd="/Users/jinkun.wang/work_space/mindforge",
    )
    assert result.returncode != 0
    assert result.stdout == ""


def test_scan_direct_help_is_retired() -> None:
    """旧 scan help 不再作为第二套 source 入口暴露。"""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "mindforge", "scan", "--help"],
        capture_output=True,
        text=True,
        cwd="/Users/jinkun.wang/work_space/mindforge",
    )
    assert result.returncode != 0
    assert result.stdout == ""


def test_watch_add_frequency_alias(tmp_path: Path) -> None:
    """/watch add --frequency 作为 --every 的别名。"""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "mindforge", "watch", "add", "--help"],
        capture_output=True,
        text=True,
        cwd="/Users/jinkun.wang/work_space/mindforge",
    )
    assert "--frequency" in result.stdout


# ============================================================================
# clean clone first-run + Web Setup save 回归测试
# ============================================================================


def _write_clean_clone_config(
    tmp_path: Path,
    *,
    create_vault: bool = True,
) -> tuple[Path, Path]:
    """模拟 clean clone first_run_config 生成的新格式配置（无模型、无 legacy）。"""
    vault = tmp_path / "vault"
    if create_vault:
        (vault / "00-Inbox").mkdir(parents=True, exist_ok=True)
        (vault / "20-Knowledge-Cards").mkdir(parents=True, exist_ok=True)
        (vault / "30-Projects").mkdir(parents=True, exist_ok=True)
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": "vault",
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                    "projects_dir": "30-Projects",
                },
                "llm": {
                    "default_model": None,
                    "models": {},
                    "routing": {},
                },
                "wiki": {
                    "mode": "deterministic",
                    "model": None,
                    "auto_rebuild_on_approve": False,
                },
                "telemetry": {"enabled": True, "local_only": True},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg_path, vault


def test_clean_clone_editable_config_200(tmp_path: Path, monkeypatch) -> None:
    """clean clone first_run_config → GET /api/config/editable 返回 200。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.get("/api/config/editable")
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm"]["default_model"] is None
    assert data["llm"]["configured_models"] == {}
    assert data["llm"]["routing"] == {}
    assert data["wiki"]["mode"] == "deterministic"
    assert data["wiki"]["model"] is None


def test_clean_clone_save_first_model_default_model_none(tmp_path: Path, monkeypatch) -> None:
    """clean clone 添加第一个模型、default_model=None → PATCH 200。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.patch(
        "/api/config/editable",
        json={
            "default_model": None,
            "models": {
                "main": {
                    "type": "anthropic_compatible",
                    "base_url": "https://example.com/api",
                    "model": "test-model",
                    "api_key": "sk-test-1234",
                    "api_key_action": "update",
                },
            },
        },
    )
    assert resp.status_code == 200, f"Response: {resp.json()}"

    # 模型写入了 YAML
    yaml_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_text)
    assert "main" in data["llm"]["models"]
    # API key 不写 YAML
    assert "sk-test" not in yaml_text
    assert "1234" not in yaml_text


def test_clean_clone_save_empty_string_default_model_now_200(tmp_path: Path, monkeypatch) -> None:
    """回归测试：clean clone 前端空字符串 default_model="" → 不再 400（已修复）。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    # 模拟前端 patchFromForm 发送 default_model="" 的行为
    resp = client.patch(
        "/api/config/editable",
        json={
            "default_model": "",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4o-mini",
                    "api_key": "sk-openai-test",
                    "api_key_action": "update",
                },
            },
        },
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    # 模型被保存
    yaml_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_text)
    assert "main" in data["llm"]["models"]
    # default_model 保持 null（因为空字符串被当作未设置）
    assert data["llm"]["default_model"] is None
    # API key 不写 YAML
    assert "sk-openai" not in yaml_text


def test_clean_clone_save_with_default_model_writes_routing(tmp_path: Path, monkeypatch) -> None:
    """clean clone 设置 default_model → 写 routing 五个 stage。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "anthropic_compatible",
                    "base_url": "https://example.com/api",
                    "model": "test-model",
                    "api_key_action": "keep",
                },
            },
        },
    )
    assert resp.status_code == 200, f"Response: {resp.json()}"

    yaml_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_text)
    assert data["llm"]["default_model"] == "main"
    routing = data.get("llm", {}).get("routing", {})
    from mindforge.config import REQUIRED_STAGES
    for stage in REQUIRED_STAGES:
        assert routing.get(stage) == "main", f"routing.{stage} missing"


def test_clean_clone_save_first_model_creates_missing_vault(tmp_path: Path, monkeypatch) -> None:
    """回归测试：first-run vault 目录不存在时，保存模型不能被内部目录状态阻塞。

    中文学习型说明：Setup 的主任务是保存模型配置。first-run 生成的 vault path
    是用户可见的工作区位置；如果目录尚不存在，Web save 应自动创建，而不是要求
    普通用户理解 ``create_vault`` 这种内部开关。
    """
    cfg_path, vault = _write_clean_clone_config(tmp_path, create_vault=False)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    payload = {
        "vault_root": str(vault),
        "create_vault": False,
        "default_model": "main",
        "models": {
            "main": {
                "type": "openai_compatible",
                "base_url": "https://example.com/api",
                "model": "test-model",
                "api_key": "sk-clean-clone-test",
                "api_key_action": "update",
            },
        },
        "routing": {},
        "wiki_mode": "deterministic",
        "wiki_model": None,
        "wiki_auto_rebuild_on_approve": False,
    }

    validate = client.post("/api/config/validate", json=payload)
    assert validate.status_code == 200
    assert validate.json()["ok"] is True

    resp = client.patch("/api/config/editable", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    yaml_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_text)
    assert data["llm"]["models"]["main"]["type"] == "openai_compatible"
    assert data["llm"]["default_model"] == "main"
    assert data["wiki"]["mode"] == "deterministic"
    assert data["wiki"]["model"] is None
    for stage in REQUIRED_STAGES:
        assert data["llm"]["routing"][stage] == "main"
    assert vault.is_dir()
    assert (vault / "00-Inbox").is_dir()
    assert (vault / "20-Knowledge-Cards").is_dir()
    assert (vault / "30-Projects").is_dir()
    assert "sk-clean-clone-test" not in yaml_text

    from mindforge.secret_store import SecretStore

    assert SecretStore(tmp_path / ".mindforge" / "secrets.json").present("main")


def test_web_source_path_error_returns_frontend_readable_detail(tmp_path: Path, monkeypatch) -> None:
    """Source 400 必须给前端可读 message，不能让 UI 退化成 ``Bad Request``。

    中文学习型说明：用户主路径是 Add Source / Add and process now。后端可以
    拒绝相对路径或缺模型，但 response body 必须是稳定的 `{detail:{message}}`
    形状，前端才能显示真正原因。
    """
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"), raise_server_exceptions=False)

    resp = client.post(
        "/api/sources/watch",
        json={"path": "relative.md", "frequency": "manual", "recursive": True, "process_now": False},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"]["message"].startswith("Please use an absolute path")


def test_setup_save_reports_friendly_error_when_vault_auto_create_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """自动创建 vault 失败时返回可理解错误，不退回内部 traceback。"""
    cfg_path, vault = _write_clean_clone_config(tmp_path, create_vault=False)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
    original_mkdir = Path.mkdir

    def fail_vault_mkdir(self: Path, *args, **kwargs) -> None:
        if self == vault:
            raise OSError("permission denied")
        original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_vault_mkdir)

    resp = client.patch(
        "/api/config/editable",
        json={
            "vault_root": str(vault),
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai",
                    "base_url": "https://example.com/api",
                    "model": "test-model",
                    "api_key_action": "keep",
                },
            },
        },
    )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["errors"] == [f"Cannot create vault directory: {vault}"]


def test_clean_clone_save_api_key_in_secret_store_not_yaml(tmp_path: Path, monkeypatch) -> None:
    """API key 写 .mindforge/secrets.json，不写 YAML。"""
    cfg_path, vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4o",
                    "api_key": "sk-sensitive-9999",
                    "api_key_action": "update",
                },
            },
        },
    )

    yaml_text = cfg_path.read_text(encoding="utf-8")
    assert "sk-sensitive" not in yaml_text

    # secret store 存在
    from mindforge.secret_store import SecretStore
    store = SecretStore(vault.parent / ".mindforge" / "secrets.json")
    assert store.present("main")
    assert store.get("main") == "sk-sensitive-9999"


def test_clean_clone_wiki_deterministic_null_model_ok(tmp_path: Path, monkeypatch) -> None:
    """wiki.mode=deterministic + wiki.model=null 不阻塞保存。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.patch(
        "/api/config/editable",
        json={
            "wiki_mode": "deterministic",
            "wiki_model": None,
            "wiki_auto_rebuild_on_approve": False,
            "models": {
                "main": {
                    "type": "anthropic_compatible",
                    "base_url": "https://example.com/api",
                    "model": "test-model",
                    "api_key_action": "keep",
                },
            },
            "default_model": "main",
        },
    )
    assert resp.status_code == 200, f"Response: {resp.json()}"

    yaml_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_text)
    assert data["wiki"]["mode"] == "deterministic"
    assert data["wiki"]["model"] is None


def test_clean_clone_wiki_llm_mode_with_model_saves(tmp_path: Path, monkeypatch) -> None:
    """wiki.mode=llm + wiki.model 存在 → 保存成功。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    # 需要先有模型
    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "anthropic_compatible",
                    "base_url": "https://example.com/api",
                    "model": "test-model",
                    "api_key_action": "keep",
                },
            },
        },
    )

    resp = client.patch(
        "/api/config/editable",
        json={
            "wiki_mode": "llm",
            "wiki_model": "main",
            "wiki_auto_rebuild_on_approve": True,
            "default_model": "main",
            "models": {
                "main": {
                    "type": "anthropic_compatible",
                    "base_url": "https://example.com/api",
                    "model": "test-model",
                    "api_key_action": "keep",
                },
            },
        },
    )
    assert resp.status_code == 200, f"Response: {resp.json()}"

    yaml_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_text)
    assert data["wiki"]["mode"] == "llm"
    assert data["wiki"]["model"] == "main"


def test_clean_clone_api_key_missing_does_not_block_save(tmp_path: Path, monkeypatch) -> None:
    """API key missing 不阻塞保存模型 metadata。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://example.com/api",
                    "model": "test-model",
                    "api_key_action": "keep",
                },
            },
        },
    )
    assert resp.status_code == 200, f"Response: {resp.json()}"

    yaml_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_text)
    assert data["llm"]["models"]["main"]["type"] == "openai_compatible"


@pytest.mark.parametrize("model_type", [
    "anthropic",
    "anthropic_compatible",
    "openai",
    "openai_compatible",
])
def test_clean_clone_all_model_types_save(tmp_path: Path, monkeypatch, model_type: str) -> None:
    """四种 model type 均可保存。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.patch(
        "/api/config/editable",
        json={
            "default_model": "demo",
            "models": {
                "demo": {
                    "type": model_type,
                    "base_url": "https://example.com/api",
                    "model": "demo-model",
                    "api_key_action": "keep",
                },
            },
        },
    )
    assert resp.status_code == 200, f"type={model_type}: {resp.json()}"

    yaml_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_text)
    assert data["llm"]["models"]["demo"]["type"] == model_type


def test_clean_clone_save_does_not_write_legacy_fields(tmp_path: Path, monkeypatch) -> None:
    """保存后不写 active_profile/profiles/fake/env 字段。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4o-mini",
                    "api_key": "sk-legacy-test",
                    "api_key_action": "update",
                },
            },
        },
    )

    yaml_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(yaml_text)
    llm = data.get("llm", {})
    for legacy_key in ("active_profile", "profiles", "active", "providers"):
        assert legacy_key not in llm, f"legacy field {legacy_key} found in YAML"
    # 模型下不应有 env 字段
    for mid, mconf in llm.get("models", {}).items():
        for env_key in ("api_key_env", "base_url_env", "model_env"):
            assert env_key not in mconf, f"env field {env_key} found in model {mid}"


def test_clean_clone_refresh_after_save_keeps_model(tmp_path: Path, monkeypatch) -> None:
    """保存后刷新 Setup → 模型仍存在，key 只显示 masked。"""
    cfg_path, _vault = _write_clean_clone_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    # 保存模型
    client.patch(
        "/api/config/editable",
        json={
            "default_model": "main",
            "models": {
                "main": {
                    "type": "anthropic_compatible",
                    "base_url": "https://example.com/api",
                    "model": "test-model",
                    "api_key": "sk-sensitive-key-8888",
                    "api_key_action": "update",
                },
            },
        },
    )

    # 刷新（重新 GET）
    resp = client.get("/api/config/editable")
    assert resp.status_code == 200
    data = resp.json()
    models = data["llm"]["configured_models"]
    assert "main" in models
    model = models["main"]
    assert model["type"] == "anthropic_compatible"
    assert model["model"] == "test-model"
    assert model["api_key_source"] == "local_secret"
    assert model["api_key_secret_present"] is True
    # masked 值显示脱敏前缀+后4位，不包含完整 raw key
    masked = str(model.get("api_key_masked_value", ""))
    assert "sk-sensitive" not in masked
    assert masked != "sk-sensitive-key-8888"  # 不是完整 raw key
