"""CLI e2e tests for simple watch/import ingestion.

这些测试用 fake provider 与临时 vault 验证用户级 ingestion 入口：
watch = 注册并立即处理，import = 一次性处理且不注册。两者都只能生成
ai_draft，不能自动 approve。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.approval_service import approve_explicit_card
from mindforge.cards import read_card_frontmatter
from mindforge.cli import app
from mindforge.config import load_mindforge_config
from mindforge.watch_registry import WatchRegistry

runner = CliRunner()


def _write_config(tmp_path: Path, *, active_profile: str = "fake") -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    cfg = tmp_path / "mindforge.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
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
                    "workdir": ".mindforge",
                    "state_file": "state.json",
                    "runs_dir": "runs",
                    "index_file": "index.jsonl",
                    "backup_state": True,
                },
                "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
                "llm": {
                    "active_profile": active_profile,
                    "profiles": {
                        "fake": {
                            "triage": "fake_alias",
                            "distill": "fake_alias",
                            "link_suggestion": "fake_alias",
                            "review_questions": "fake_alias",
                            "action_extraction": "fake_alias",
                        },
                        "openai_compatible": {
                            "triage": "openai_alias",
                            "distill": "openai_alias",
                            "link_suggestion": "openai_alias",
                            "review_questions": "openai_alias",
                            "action_extraction": "openai_alias",
                        },
                        "anthropic": {
                            "triage": "anthropic_alias",
                            "distill": "anthropic_alias",
                            "link_suggestion": "anthropic_alias",
                            "review_questions": "anthropic_alias",
                            "action_extraction": "anthropic_alias",
                        },
                    },
                    "models": {
                        "fake_alias": {
                            "provider": "fake",
                            "type": "fake",
                            "base_url": "fake://",
                            "model": "fake",
                            "timeout_seconds": 5,
                            "max_retries": 0,
                        },
                        "openai_alias": {
                            "provider": "openai_compatible",
                            "type": "openai_compatible",
                            "base_url": "https://example.invalid/v1",
                            "api_key_env": "MINDFORGE_OPENAI_API_KEY",
                            "model": "gpt-4o-mini",
                            "timeout_seconds": 5,
                            "max_retries": 0,
                        },
                        "anthropic_alias": {
                            "provider": "anthropic",
                            "type": "anthropic_compatible",
                            "base_url_env": "MINDFORGE_ANTHROPIC_BASE_URL",
                            "base_url": "https://api.anthropic.com",
                            "api_key_env": "MINDFORGE_ANTHROPIC_API_KEY",
                            "model_env": "MINDFORGE_ANTHROPIC_MODEL",
                            "model": "claude-3-5-haiku-latest",
                            "timeout_seconds": 5,
                            "max_retries": 0,
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
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg, vault


def _card_paths(vault: Path) -> list[Path]:
    return sorted((vault / "20-Knowledge-Cards").rglob("*.md"))


def test_watch_list_shows_default_inbox(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)

    result = runner.invoke(app, ["watch", "list", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "default-inbox" in result.output
    assert "00-Inbox" in result.output
    assert "default" in result.output


def test_watch_add_file_registers_and_generates_ai_draft_once(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "external-file.md"
    source.write_text("# External File\n\nbody\n", encoding="utf-8")

    first = runner.invoke(app, ["watch", "add", str(source), "--config", str(cfg)])
    second = runner.invoke(app, ["watch", "add", str(source), "--config", str(cfg)])

    assert first.exit_code == 0, first.output
    assert "registered" in first.output
    assert "processed=1" in first.output
    assert second.exit_code == 0, second.output
    assert "already registered" in second.output
    assert "already_processed" in second.output
    cards = _card_paths(vault)
    assert len(cards) == 1
    assert read_card_frontmatter(cards[0])["status"] == "ai_draft"
    assert read_card_frontmatter(cards[0])["source_path"] == str(source.resolve())
    assert WatchRegistry.load(vault / ".mindforge" / "watched_sources.json").sources[0].path == source.resolve()
    assert source.exists()


def test_watch_add_openai_compatible_missing_key_fails_without_fake_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """真实 provider 缺 key 时必须友好失败，不能偷偷落回 fake。

    中文学习型说明：watch/import 是真实 dogfood 主入口，但自动化边界仍然只到
    ``ai_draft``。缺少真实 provider secret 时，正确行为是明确告诉用户如何设置
    env，而不是用 fake 内容冒充真实模型产物。
    """

    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.watch_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "real-provider-note.md"
    source.write_text("# Real Provider Note\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["watch", "add", str(source), "--profile", "openai_compatible", "--config", str(cfg)],
    )

    assert result.exit_code == 2, result.output
    assert "real provider openai_compatible requires MINDFORGE_OPENAI_API_KEY" in result.output
    assert "Do not put secrets in YAML" in result.output
    assert "fake/demo remains available with --profile fake" in result.output
    assert _card_paths(vault) == []


def test_watch_add_anthropic_missing_key_fails_without_fake_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.watch_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "anthropic-note.md"
    source.write_text("# Anthropic Note\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["watch", "add", str(source), "--profile", "anthropic", "--config", str(cfg)],
    )

    assert result.exit_code == 2, result.output
    assert "real provider anthropic requires MINDFORGE_ANTHROPIC_API_KEY" in result.output
    assert "Do not put secrets in YAML" in result.output
    assert "fake/demo remains available with --profile fake" in result.output
    assert _card_paths(vault) == []


def test_watch_add_folder_and_delete_preserves_source_and_cards(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    folder = tmp_path / "folder"
    source = folder / "folder-note.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Folder Note\n\nbody\n", encoding="utf-8")

    added = runner.invoke(app, ["watch", "add", str(folder), "--config", str(cfg)])
    registry = WatchRegistry.load(vault / ".mindforge" / "watched_sources.json")
    deleted = runner.invoke(app, ["watch", "delete", registry.sources[0].id, "--config", str(cfg)])

    assert added.exit_code == 0, added.output
    assert "processed=1" in added.output
    assert deleted.exit_code == 0, deleted.output
    assert "deleted" in deleted.output
    assert source.exists()
    assert len(_card_paths(vault)) == 1
    assert WatchRegistry.load(vault / ".mindforge" / "watched_sources.json").sources == ()


def test_import_file_and_folder_do_not_register_watch(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    one = tmp_path / "import-one.md"
    folder = tmp_path / "import-folder"
    two = folder / "import-two.md"
    one.write_text("# Import One\n\nbody\n", encoding="utf-8")
    two.parent.mkdir(parents=True)
    two.write_text("# Import Two\n\nbody\n", encoding="utf-8")

    imported_file = runner.invoke(app, ["import", str(one), "--config", str(cfg)])
    imported_folder = runner.invoke(app, ["import", str(folder), "--config", str(cfg)])

    assert imported_file.exit_code == 0, imported_file.output
    assert imported_folder.exit_code == 0, imported_folder.output
    assert "imported" in imported_file.output
    assert "imported" in imported_folder.output
    assert len(_card_paths(vault)) == 2
    assert not (vault / ".mindforge" / "watched_sources.json").exists()


def test_import_openai_compatible_missing_key_fails_without_fake_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.import_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "real-import-note.md"
    source.write_text("# Real Import Note\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["import", str(source), "--profile", "openai_compatible", "--config", str(cfg)],
    )

    assert result.exit_code == 2, result.output
    assert "real provider openai_compatible requires MINDFORGE_OPENAI_API_KEY" in result.output
    assert "Set it via shell export or local .env" in result.output
    assert "fake/demo remains available with --profile fake" in result.output
    assert _card_paths(vault) == []


def test_import_anthropic_missing_key_fails_without_fake_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.import_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "anthropic-import.md"
    source.write_text("# Anthropic Import\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["import", str(source), "--profile", "anthropic", "--config", str(cfg)],
    )

    assert result.exit_code == 2, result.output
    assert "real provider anthropic requires MINDFORGE_ANTHROPIC_API_KEY" in result.output
    assert "Set it via shell export or local .env" in result.output
    assert "fake/demo remains available with --profile fake" in result.output
    assert _card_paths(vault) == []


def test_watch_delete_default_and_approve_boundary(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "approval-boundary.md"
    source.write_text("# Approval Boundary\n\nbody\n", encoding="utf-8")

    add = runner.invoke(app, ["watch", "add", str(source), "--config", str(cfg)])
    reject_delete = runner.invoke(app, ["watch", "delete", "default-inbox", "--config", str(cfg)])
    cfg_obj = load_mindforge_config(cfg)
    card = _card_paths(vault)[0]

    assert add.exit_code == 0, add.output
    assert reject_delete.exit_code == 2, reject_delete.output
    assert "default 00-Inbox cannot be deleted" in reject_delete.output
    assert read_card_frontmatter(card)["status"] == "ai_draft"
    approve = approve_explicit_card(cfg_obj, card)
    assert approve.error is None
    assert read_card_frontmatter(card)["status"] == "human_approved"
