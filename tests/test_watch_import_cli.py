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


def _write_config(tmp_path: Path, *, active_provider: str = "fake") -> tuple[Path, Path]:
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
                    "active": active_provider,
                    "providers": {
                        "fake": {
                            "type": "fake",
                            "purpose": "offline_demo_ci_deterministic_tests",
                        },
                        "openai_compatible": {
                            "type": "openai_compatible",
                            "api_key_env": "MINDFORGE_OPENAI_API_KEY",
                            "default_base_url": "https://example.invalid/v1",
                            "default_model": "gpt-4o-mini",
                        },
                        "anthropic": {
                            "type": "anthropic",
                            "api_key_env": "MINDFORGE_ANTHROPIC_API_KEY",
                            "base_url_env": "MINDFORGE_ANTHROPIC_BASE_URL",
                            "model_env": "MINDFORGE_ANTHROPIC_MODEL",
                            "default_base_url": "https://api.anthropic.com",
                            "default_model": "claude-3-5-haiku-latest",
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


def _write_project_config(project_root: Path, *, active_provider: str = "fake") -> tuple[Path, Path]:
    """写入接近 init 产物的 project config，验证 CLI 默认路径解析。

    中文学习型说明：这里刻意把 ``vault.root`` 写成相对路径 ``vault``，测试
    loader 是否按 project root 解析，而不是按当前 shell cwd 解析。
    """

    vault = project_root / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    cfg = project_root / "configs" / "mindforge.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {"root": "vault"},
                "llm": {
                    "active": active_provider,
                    "providers": {
                        "fake": {
                            "type": "fake",
                            "purpose": "offline_demo_ci_deterministic_tests",
                        },
                        "openai_compatible": {
                            "type": "openai_compatible",
                            "api_key_env": "MINDFORGE_OPENAI_API_KEY",
                            "default_base_url": "https://example.invalid/v1",
                            "default_model": "gpt-4o-mini",
                        },
                    },
                },
                "telemetry": {"enabled": True, "local_only": True},
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
    assert "fake/demo remains available with --provider fake" in result.output
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
    assert "fake/demo remains available with --provider fake" in result.output
    assert _card_paths(vault) == []


def test_watch_add_uses_llm_active_without_cli_provider(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="openai_compatible")
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.watch_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "active-openai.md"
    source.write_text("# Active OpenAI\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["watch", "add", str(source), "--config", str(cfg)])

    assert result.exit_code == 2, result.output
    assert "real provider openai_compatible requires MINDFORGE_OPENAI_API_KEY" in result.output
    assert _card_paths(vault) == []


def test_watch_add_provider_override_wins_over_active(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="anthropic")
    monkeypatch.chdir(vault)
    source = tmp_path / "override-fake.md"
    source.write_text("# Override Fake\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["watch", "add", str(source), "--provider", "fake", "--config", str(cfg)],
    )

    assert result.exit_code == 0, result.output
    assert "processed=1" in result.output
    assert len(_card_paths(vault)) == 1


def test_watch_add_unknown_provider_override_is_friendly(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "unknown-provider.md"
    source.write_text("# Unknown Provider\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["watch", "add", str(source), "--provider", "ghost", "--config", str(cfg)],
    )

    assert result.exit_code == 2, result.output
    assert "--provider 'ghost'" in result.output
    assert "llm.providers" in result.output


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


def test_import_missing_file_fails_and_does_not_poison_future_processing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """missing import 是输入错误，不能写 processed/fingerprint 状态。

    真实 smoke 暴露过：先 import 不存在文件得到 seen=0，之后创建同名文件再
    import 会被 skipped。这个回归测试证明空跑不会污染后续处理。
    """

    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    missing = vault / "00-Inbox" / "ManualNotes" / "later-note.md"

    failed = runner.invoke(app, ["import", str(missing), "--provider", "fake", "--config", str(cfg)])

    assert failed.exit_code == 2, failed.output
    assert "File not found" in failed.output
    assert "cwd:" in failed.output
    assert "project root:" in failed.output
    assert "active vault:" in failed.output
    assert "tried" in failed.output
    assert "candidates" in failed.output
    assert _card_paths(vault) == []

    missing.write_text("# Later Note\n\nbody\n", encoding="utf-8")
    imported = runner.invoke(app, ["import", str(missing), "--provider", "fake", "--config", str(cfg)])
    pending = runner.invoke(app, ["approve", "list", "--config", str(cfg)])

    assert imported.exit_code == 0, imported.output
    assert "processed=1 skipped=0 failed=0 seen=1" in imported.output
    assert pending.exit_code == 0, pending.output
    assert "[1]" in pending.output
    assert "Later Note" in pending.output or "later-note" in pending.output


def test_import_resolves_project_root_relative_path(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    _cfg, vault = _write_project_config(project)
    note = vault / "00-Inbox" / "ManualNotes" / "project-relative.md"
    note.write_text("# Project Relative\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project)

    result = runner.invoke(
        app,
        ["import", "vault/00-Inbox/ManualNotes/project-relative.md", "--provider", "fake"],
    )

    assert result.exit_code == 0, result.output
    assert "processed=1 skipped=0 failed=0 seen=1" in result.output
    assert "project root:" in result.output
    assert len(_card_paths(vault)) == 1


def test_import_resolves_vault_relative_path_from_vault_root(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    _cfg, vault = _write_project_config(project)
    note = vault / "00-Inbox" / "ManualNotes" / "vault-relative.md"
    note.write_text("# Vault Relative\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    result = runner.invoke(app, ["import", "00-Inbox/ManualNotes/vault-relative.md", "--provider", "fake"])

    assert result.exit_code == 0, result.output
    assert "processed=1 skipped=0 failed=0 seen=1" in result.output
    assert f"active vault: {vault.resolve()}" in result.output
    assert len(_card_paths(vault)) == 1


def test_import_resolves_cwd_relative_path_from_project_child(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    _cfg, vault = _write_project_config(project)
    child = project / "workspace" / "notes"
    child.mkdir(parents=True)
    note = child / "cwd-relative.md"
    note.write_text("# Cwd Relative\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(child)

    result = runner.invoke(app, ["import", "./cwd-relative.md", "--provider", "fake"])

    assert result.exit_code == 0, result.output
    assert "processed=1 skipped=0 failed=0 seen=1" in result.output
    assert len(_card_paths(vault)) == 1


def test_import_resolves_absolute_path(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    _cfg, vault = _write_project_config(project)
    note = tmp_path / "absolute-note.md"
    note.write_text("# Absolute Note\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project / "vault")

    result = runner.invoke(app, ["import", str(note), "--provider", "fake"])

    assert result.exit_code == 0, result.output
    assert "processed=1 skipped=0 failed=0 seen=1" in result.output
    assert len(_card_paths(vault)) == 1


def test_watch_add_resolves_project_root_relative_path(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    _cfg, vault = _write_project_config(project)
    note = vault / "00-Inbox" / "ManualNotes" / "watch-project-relative.md"
    note.write_text("# Watch Project Relative\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project)

    result = runner.invoke(
        app,
        ["watch", "add", "vault/00-Inbox/ManualNotes/watch-project-relative.md", "--provider", "fake"],
    )

    assert result.exit_code == 0, result.output
    assert "processed=1 skipped=0 failed=0 seen=1" in result.output
    registry = WatchRegistry.load(vault / ".mindforge" / "watched_sources.json")
    assert registry.sources[0].path == note.resolve()


def test_watch_add_missing_file_fails_before_registry_write(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    missing = vault / "00-Inbox" / "ManualNotes" / "missing-watch.md"

    result = runner.invoke(app, ["watch", "add", str(missing), "--provider", "fake", "--config", str(cfg)])

    assert result.exit_code == 2, result.output
    assert "File not found" in result.output
    assert not (vault / ".mindforge" / "watched_sources.json").exists()
    assert _card_paths(vault) == []


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
    assert "fake/demo remains available with --provider fake" in result.output
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
    assert "fake/demo remains available with --provider fake" in result.output
    assert _card_paths(vault) == []


def test_import_uses_llm_active_without_cli_provider(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="anthropic")
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.import_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "active-anthropic-import.md"
    source.write_text("# Active Anthropic Import\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["import", str(source), "--config", str(cfg)])

    assert result.exit_code == 2, result.output
    assert "real provider anthropic requires MINDFORGE_ANTHROPIC_API_KEY" in result.output
    assert _card_paths(vault) == []


def test_import_provider_override_wins_over_legacy_profile(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="fake")
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.import_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "provider-wins.md"
    source.write_text("# Provider Wins\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "import",
            str(source),
            "--provider",
            "anthropic",
            "--profile",
            "fake",
            "--config",
            str(cfg),
        ],
    )

    assert result.exit_code == 2, result.output
    assert "real provider anthropic requires MINDFORGE_ANTHROPIC_API_KEY" in result.output
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
