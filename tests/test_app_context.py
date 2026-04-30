"""v0.7.15 — App context / config path resolution 测试。

学习要点：app_context 只负责把 config 与本次 vault override 解析成结构化路径，
不做业务处理、不依赖 CLI 展示层，也不会读取 `.env` 或调用 LLM。
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
import yaml

from mindforge.app_context import AppContextError, apply_vault_override, build_app_context, load_app_config


def _write_config(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "00-Inbox").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)
    cfg = {
        "version": 0.7,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {"enabled": [], "registry": {}},
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
            "models": {"fake_alias": {"provider": "fake", "type": "fake", "model": "fake"}},
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
    return cfg_path


def test_app_context_resolves_config_vault_and_state_paths(tmp_path: Path) -> None:
    """context 返回 CLI 可复用路径，但不创建 state/runs 文件。"""
    cfg_path = _write_config(tmp_path)

    ctx = build_app_context(cfg_path)

    assert ctx.paths.config_path == cfg_path
    assert ctx.paths.vault_root == tmp_path / "vault"
    assert ctx.paths.inbox_path == tmp_path / "vault" / "00-Inbox"
    assert ctx.paths.cards_path == tmp_path / "vault" / "20-Knowledge-Cards"
    assert ctx.paths.state_workdir == tmp_path / ".mindforge"
    assert ctx.paths.runs_path == tmp_path / ".mindforge" / "runs"
    assert not ctx.paths.state_workdir.exists()


def test_app_context_vault_override_keeps_relative_subdirs(tmp_path: Path) -> None:
    """vault override 只替换 root，不改 cards_dir/inbox_root 等相对目录配置。"""
    cfg = load_app_config(_write_config(tmp_path))
    override = tmp_path / "disposable-vault"

    overridden = apply_vault_override(cfg, override)

    assert overridden.vault.root == override.resolve()
    assert overridden.vault.cards_dir == cfg.vault.cards_dir
    assert overridden.vault.cards_path == override.resolve() / "20-Knowledge-Cards"


def test_app_context_missing_and_invalid_config_errors(tmp_path: Path) -> None:
    """missing/invalid config 由 context 抛结构化错误，CLI 决定如何展示。"""
    with pytest.raises(AppContextError) as missing:
        load_app_config(tmp_path / "missing.yaml")
    assert missing.value.kind == "missing_config"

    invalid = tmp_path / "bad.yaml"
    invalid.write_text("vault: [bad\n", encoding="utf-8")
    with pytest.raises(AppContextError) as bad:
        load_app_config(invalid)
    assert bad.value.kind == "invalid_config"


def test_app_context_works_from_non_repo_cwd(tmp_path: Path, monkeypatch) -> None:
    """使用绝对 config path 时，/tmp 等非 repo cwd 不影响路径解析。"""
    cfg_path = _write_config(tmp_path)
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    ctx = build_app_context(cfg_path)

    assert ctx.paths.vault_root == tmp_path / "vault"
    assert ctx.paths.cards_path.is_absolute()


def test_app_context_no_cli_env_llm_or_file_write_dependency(tmp_path: Path, monkeypatch) -> None:
    """context 不依赖 Typer/Rich，不读取 `.env`，不联网，也不写任何运行文件。"""
    cfg_path = _write_config(tmp_path)
    (tmp_path / ".env").write_text("SECRET=value\n", encoding="utf-8")

    def _blocked(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("app_context 不应触发外部边界")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked)
    monkeypatch.setattr("mindforge.llm.build_providers", _blocked)
    monkeypatch.setattr(socket, "socket", _blocked)

    ctx = build_app_context(cfg_path)
    source = Path("src/mindforge/app_context.py").read_text(encoding="utf-8")

    assert ctx.config.llm.active_profile == "fake"
    assert "import typer" not in source
    assert "from rich" not in source
    assert "load_dotenv" not in source
    assert "build_providers" not in source
    assert "write_text" not in source
    assert not (tmp_path / ".mindforge").exists()
