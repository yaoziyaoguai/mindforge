"""P0 dogfood regression tests for active vault resolution.

这些测试复现真实使用里的矛盾：人在 vault root 里运行命令时，state path、
scanner vault、next command 必须指向同一个 active vault，不能一半来自 cwd、
一半来自 configured vault。

P0-1 修正：--config 显式提供时 configured vault 优先，不再被 cwd vault 覆盖。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.cards import read_card_frontmatter

runner = CliRunner()


def _write_config(tmp_path: Path, configured_vault: Path) -> Path:
    """写自定义路径的测试 config（触发 config_explicit=True）。"""
    cfg_path = tmp_path / "mindforge.yaml"
    _write_config_content(cfg_path, configured_vault, tmp_path)
    return cfg_path



def _write_config_content(cfg_path: Path, configured_vault: Path, tmp_path: Path) -> None:
    configured_vault.mkdir(parents=True, exist_ok=True)
    (configured_vault / "00-Inbox" / "ManualNotes").mkdir(parents=True, exist_ok=True)
    (configured_vault / "20-Knowledge-Cards").mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(configured_vault),
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


def _make_vault(path: Path, note_name: str = "second-note.md") -> Path:
    inbox = path / "00-Inbox" / "ManualNotes"
    cards = path / "20-Knowledge-Cards"
    inbox.mkdir(parents=True)
    cards.mkdir(parents=True)
    inbox.joinpath(note_name).write_text("# second note\n\nbody\n", encoding="utf-8")
    return path


def _make_fresh_inbox_vault(path: Path, note_name: str = "external-smoke-note.md") -> Path:
    inbox = path / "00-Inbox" / "ManualNotes"
    inbox.mkdir(parents=True)
    inbox.joinpath(note_name).write_text("# external smoke\n\nbody\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. --config 显式提供 → configured vault 优先（P0-1 修正）
# ---------------------------------------------------------------------------


def test_explicit_config_uses_configured_vault_not_cwd_vault(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """--config 显式提供时，configured vault 优先，不查找 cwd vault。"""
    configured = _make_vault(tmp_path / "configured-vault", "old.md")
    active = _make_vault(tmp_path / "active-vault", "second-note.md")
    cfg = _write_config(tmp_path, configured)
    monkeypatch.chdir(active)

    result = runner.invoke(app, ["scan", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "old.md" in result.output
    assert "second-note.md" not in result.output
    assert f"active vault: {configured}" in result.output


def test_explicit_config_child_cwd_uses_configured_vault(tmp_path: Path, monkeypatch) -> None:
    """--config 显式 + cwd 在另一个 vault 子目录 → configured vault 仍优先。"""
    configured = _make_vault(tmp_path / "configured-vault", "old.md")
    active = _make_vault(tmp_path / "active-vault", "second-note.md")
    cfg = _write_config(tmp_path, configured)
    child = active / "00-Inbox" / "ManualNotes"
    monkeypatch.chdir(child)

    result = runner.invoke(app, ["scan", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert f"active vault: {configured}" in result.output
    assert (configured / ".mindforge" / "state.json").exists()


# ---------------------------------------------------------------------------
# 2. --vault 始终最高优先级
# ---------------------------------------------------------------------------


def test_explicit_vault_wins_over_cwd_and_config(tmp_path: Path, monkeypatch) -> None:
    """--vault 始终最高优先级，即使 --config + cwd vault 都存在。"""
    configured = _make_vault(tmp_path / "configured-vault", "old.md")
    cwd_vault = _make_vault(tmp_path / "cwd-vault", "cwd.md")
    explicit = _make_vault(tmp_path / "explicit-vault", "explicit.md")
    cfg = _write_config(tmp_path, configured)
    monkeypatch.chdir(cwd_vault)

    result = runner.invoke(app, ["--vault", str(explicit), "scan", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "explicit.md" in result.output
    assert "cwd.md" not in result.output
    assert f"active vault: {explicit}" in result.output
    assert (explicit / ".mindforge" / "state.json").exists()


# ---------------------------------------------------------------------------
# 4. repo .mindforge 误判为 user vault（保持防护）
# ---------------------------------------------------------------------------


def test_repo_runtime_mindforge_is_not_mistaken_for_user_vault(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configured = _make_vault(tmp_path / "configured-vault", "old.md")
    repo_like = tmp_path / "repo"
    (repo_like / ".mindforge").mkdir(parents=True)
    (repo_like / "configs").mkdir()
    (repo_like / "configs" / "mindforge.yaml").write_text("version: 0.7\n", encoding="utf-8")
    cfg = _write_config(tmp_path, configured)
    monkeypatch.chdir(repo_like)

    result = runner.invoke(app, ["scan", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "old.md" in result.output
    assert f"active vault: {configured}" in result.output


# ---------------------------------------------------------------------------
# 5. --config 显式 → status/library/approve/index/recall 一致使用 configured vault
# ---------------------------------------------------------------------------


def test_status_with_explicit_config_uses_configured_vault(tmp_path: Path, monkeypatch) -> None:
    """--config 显式 → status 使用 configured vault，不检测 cwd vault。"""
    configured = _make_vault(tmp_path / "configured-vault", "old.md")
    fresh = _make_fresh_inbox_vault(tmp_path / "ExternalMindForgeVault")
    cfg = _write_config(tmp_path, configured)
    monkeypatch.chdir(fresh)

    result = runner.invoke(app, ["status", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "configured-vault" in result.output
    assert result.output.count("cwd vault") == 0  # P0-1: 不查找 cwd vault


def test_process_library_approve_index_recall_use_configured_vault(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """--config 显式 → process/library/approve/index/recall 一致使用 configured vault。"""
    configured = _make_vault(tmp_path / "configured-vault", "old.md")
    fresh = _make_fresh_inbox_vault(tmp_path / "ExternalMindForgeVault")
    cfg = _write_config(tmp_path, configured)
    monkeypatch.chdir(fresh)

    process = runner.invoke(app, ["process", "--config", str(cfg), "--profile", "fake", "--limit", "1"])
    assert process.exit_code == 0, process.output
    assert "old.md" in process.output
    assert "external-smoke-note.md" not in process.output
    assert f"active vault: {configured}" in process.output
    assert "Next: mindforge approve list --vault" in process.output

    library_draft = runner.invoke(app, ["library", "list", "--config", str(cfg)])
    assert library_draft.exit_code == 0, library_draft.output
    assert "old" in library_draft.output

    card = next(configured.joinpath("20-Knowledge-Cards").rglob("*.md"))
    rel_card = card.relative_to(configured).as_posix()
    show = runner.invoke(app, ["approve", "show", "--card", rel_card, "--config", str(cfg)])
    assert show.exit_code == 0, show.output
    approve = runner.invoke(app, ["approve", "--card", rel_card, "--confirm", "--config", str(cfg)])
    assert approve.exit_code == 0, approve.output
    assert read_card_frontmatter(card)["status"] == "human_approved"

    index = runner.invoke(app, ["index", "rebuild", "--config", str(cfg)])
    assert index.exit_code == 0, index.output
    assert (configured / ".mindforge" / "index" / "bm25.json").exists()
    assert not (fresh / ".mindforge" / "index" / "bm25.json").exists()

    recall = runner.invoke(app, ["recall", "--query", "old", "--config", str(cfg)])
    assert recall.exit_code == 0, recall.output
    assert f"Vault: vault.root={configured}" in recall.output
    assert "old" in recall.output
