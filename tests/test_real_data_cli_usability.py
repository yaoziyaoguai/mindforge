"""Real Data CLI usability milestone tests.

中文学习型说明：这些测试用临时 fictional vault/workspace 模拟真实本地数据，
不读取用户真实 vault、不加载真实 `.env` value、不调用真实 LLM/Cubox API。
目标是锁住 CLI 作为 thin adapter 的真实数据可用路径：状态诊断、草稿查看、
显式确认 approve、以及本地词法 recall。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()


def _write_config(tmp_path: Path) -> tuple[Path, Path, Path]:
    """构造最小本地 workspace；所有路径都在 tmp_path 下，避免触碰真实资料。"""

    vault = tmp_path / "fictional-vault"
    inbox = vault / "00-Inbox" / "ManualNotes"
    cards = vault / "20-Knowledge-Cards"
    projects = vault / "30-Projects"
    inbox.mkdir(parents=True)
    cards.mkdir(parents=True)
    projects.mkdir(parents=True)
    inbox.joinpath("source-note.md").write_text("# Fictional source\nsafe summary\n", encoding="utf-8")

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


def _write_card(cards: Path, name: str, *, status: str, body: str) -> Path:
    card = cards / f"{name}.md"
    card.write_text(
        f"""---
id: {name}
title: {name.replace("-", " ").title()}
status: {status}
track: agent-runtime
projects:
  - local-cli
tags:
  - usability
source_type: manual_note
source_title: Fictional Source
value_score: 8
---

## AI Summary

{body}
""",
        encoding="utf-8",
    )
    return card


def _prepare_workspace(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    cfg_path, _vault, cards = _write_config(tmp_path)
    _write_card(cards, "draft-one", status="ai_draft", body="DRAFT_PRIVATE_SENTINEL")
    _write_card(cards, "approved-one", status="human_approved", body="approved lexical anchor")
    tmp_path.joinpath(".env").write_text(
        "MINDFORGE_FAKE_SECRET=SECRET_VALUE_MUST_NOT_LEAK\n"
        "MINDFORGE_CUBOX_TOKEN=CUBOX_SECRET_MUST_NOT_LEAK\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith("MINDFORGE_"):
            monkeypatch.delenv(key, raising=False)
    return cfg_path, cards / "draft-one.md"


def test_cli_status_is_real_data_safe_and_secret_free(tmp_path: Path, monkeypatch) -> None:
    cfg_path, _draft = _prepare_workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["status", "--config", str(cfg_path)])

    assert result.exit_code == 0, result.output
    assert "MindForge local status" in result.output
    assert "local-only" in result.output
    assert "explicit_approval_required" in result.output
    assert "pending ai_draft=1" in result.output.replace("\n", "")
    assert "human_approved" in result.output
    assert "local lexical recall" in result.output
    assert "MINDFORGE_FAKE_SECRET" not in result.output
    assert "SECRET_VALUE_MUST_NOT_LEAK" not in result.output
    assert "CUBOX_SECRET_MUST_NOT_LEAK" not in result.output
    assert "DRAFT_PRIVATE_SENTINEL" not in result.output


def test_cli_status_json_is_scriptable_without_secret_values(tmp_path: Path, monkeypatch) -> None:
    cfg_path, _draft = _prepare_workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["status", "--config", str(cfg_path), "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["safety"]["write_mode"] == "explicit_approval_required"
    assert payload["cards"]["by_status"]["ai_draft"] == 1
    assert payload["cards"]["by_status"]["human_approved"] == 1
    combined = json.dumps(payload, ensure_ascii=False)
    assert "SECRET_VALUE_MUST_NOT_LEAK" not in combined
    assert "CUBOX_SECRET_MUST_NOT_LEAK" not in combined


def test_config_status_missing_config_is_friendly() -> None:
    missing = Path("/tmp/mindforge-no-such-config-for-test.yaml")

    result = runner.invoke(app, ["config", "status", "--config", str(missing)])

    assert result.exit_code == 2
    assert "What happened" in result.output
    assert "Why it matters" in result.output
    assert "How to fix" in result.output
    assert "Safe next command" in result.output
    assert "Traceback" not in result.output


def test_workspace_status_reports_source_and_vault_without_private_content(
    tmp_path: Path, monkeypatch
) -> None:
    cfg_path, _draft = _prepare_workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["workspace", "status", "--config", str(cfg_path)])

    assert result.exit_code == 0, result.output
    assert "Workspace status" in result.output
    assert "plain_markdown" in result.output
    assert "file_count" in result.output
    assert "DRAFT_PRIVATE_SENTINEL" not in result.output


def test_approve_show_hides_body_by_default_and_show_content_is_explicit(
    tmp_path: Path, monkeypatch
) -> None:
    cfg_path, draft = _prepare_workspace(tmp_path, monkeypatch)

    default = runner.invoke(app, ["approve", "show", "--config", str(cfg_path), "--card", str(draft)])
    explicit = runner.invoke(
        app,
        ["approve", "show", "--config", str(cfg_path), "--card", str(draft), "--show-content"],
    )

    assert default.exit_code == 0, default.output
    assert "DRAFT_PRIVATE_SENTINEL" not in default.output
    assert explicit.exit_code == 0, explicit.output
    assert "DRAFT_PRIVATE_SENTINEL" in explicit.output


def test_approve_requires_confirm_and_uses_explicit_boundary(tmp_path: Path, monkeypatch) -> None:
    cfg_path, draft = _prepare_workspace(tmp_path, monkeypatch)

    refused = runner.invoke(app, ["approve", "--config", str(cfg_path), "--card", str(draft)])
    assert refused.exit_code == 2
    assert "requires --confirm" in refused.output
    assert "status: ai_draft" in draft.read_text(encoding="utf-8")

    approved = runner.invoke(
        app,
        ["approve", "--config", str(cfg_path), "--card", str(draft), "--confirm"],
    )
    assert approved.exit_code == 0, approved.output
    assert "status: human_approved" in draft.read_text(encoding="utf-8")


def test_recall_empty_query_is_friendly_and_local_lexical(tmp_path: Path, monkeypatch) -> None:
    cfg_path, _draft = _prepare_workspace(tmp_path, monkeypatch)

    empty = runner.invoke(app, ["recall", "--config", str(cfg_path), "--query", ""])
    hit = runner.invoke(app, ["recall", "--config", str(cfg_path), "--query", "anchor"])

    assert empty.exit_code == 2
    assert "query is empty" in empty.output
    assert "local lexical recall" in empty.output
    assert "Traceback" not in empty.output
    assert hit.exit_code == 0, hit.output
    assert "local lexical recall" in hit.output
    assert "not RAG" in hit.output
