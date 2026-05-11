"""Watched source schedule 与 baseline diff 语义测试。

这些测试保护核心产品原则：
- frequency 只属于用户显式添加的顶层 watched source；
- 子文件不注册成独立 watched source；
- Source changes can create new drafts；
- Source deletion never deletes approved knowledge；
- Knowledge reduction is always manual；
- Watch is additive by default。
"""

from __future__ import annotations

from pathlib import Path
import time

import yaml
from typer.testing import CliRunner

from mindforge.approval_service import approve_explicit_card
from mindforge.cards import read_card_frontmatter
from mindforge.cli import app
from mindforge.cli_runtime import load_cfg
from mindforge.config import load_mindforge_config
from mindforge.watch_registry import WatchRegistry
from mindforge.watch_registry import registry_path_for_vault, update_watch_source
from mindforge_web.services.processing_run_service import get_processing_run

runner = CliRunner()


def _write_config(tmp_path: Path) -> tuple[Path, Path]:
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
                    "active": "fake",
                    "providers": {
                        "fake": {"type": "fake", "purpose": "offline tests"},
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


def _cards(vault: Path) -> list[Path]:
    return sorted((vault / "20-Knowledge-Cards").rglob("*.md"))


def _registry(vault: Path) -> WatchRegistry:
    return WatchRegistry.load(vault / ".mindforge" / "watched_sources.json")


def _run_id_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("run_id: "):
            return line.split("run_id: ", 1)[1].strip()
    raise AssertionError(f"missing run_id in output:\n{output}")


def _wait_for_watch_add_run(cfg_path: Path, output: str, *, timeout: float = 5.0) -> None:
    """watch add 已是后台 processing；baseline 测试需等待初始 run 落盘。

    中文学习型说明：这些测试关注 schedule/baseline diff，不应把 watch add
    拉回同步主路径。等待 durable run 完成等价于用户稍后查看 run/status。
    """

    run_id = _run_id_from_output(output)
    cfg = load_cfg(cfg_path, read_env=False)
    deadline = time.monotonic() + timeout
    latest = None
    while time.monotonic() < deadline:
        latest = get_processing_run(cfg, run_id)
        if latest is not None and latest.status not in {"queued", "running"}:
            assert latest.status in {"succeeded", "partial_failed", "skipped"}, latest
            return
        time.sleep(0.05)
    raise AssertionError(f"watch add run did not finish: {run_id}, latest={latest}")


def test_watch_add_file_and_folder_store_frequency_on_top_level_source_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    file_source = tmp_path / "file.md"
    folder = tmp_path / "folder"
    nested = folder / "nested" / "note.md"
    file_source.write_text("# File\n\nbody\n", encoding="utf-8")
    nested.parent.mkdir(parents=True)
    nested.write_text("# Nested\n\nbody\n", encoding="utf-8")

    file_added = runner.invoke(app, ["watch", "add", str(file_source), "--every", "daily", "--config", str(cfg)])
    folder_added = runner.invoke(app, ["watch", "add", str(folder), "--recursive", "--every", "weekly", "--config", str(cfg)])

    assert file_added.exit_code == 0, file_added.output
    assert folder_added.exit_code == 0, folder_added.output
    sources = _registry(vault).sources
    assert [(source.path_type, source.frequency) for source in sources] == [
        ("file", "daily"),
        ("folder", "weekly"),
    ]
    assert [source.path for source in sources] == [file_source.resolve(), folder.resolve()]
    assert nested.resolve() not in [source.path for source in sources]


def test_watch_add_rejects_invalid_frequency(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "file.md"
    source.write_text("# File\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["watch", "add", str(source), "--every", "cron:* * * * *", "--config", str(cfg)])

    assert result.exit_code == 2
    assert "Unsupported watch frequency" in result.output


def test_watch_scan_default_scans_due_sources_but_skips_not_due(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    due = tmp_path / "due.md"
    not_due = tmp_path / "not-due.md"
    due.write_text("# Due\n\nbody\n", encoding="utf-8")
    not_due.write_text("# Not Due\n\nbody\n", encoding="utf-8")
    due_added = runner.invoke(app, ["watch", "add", str(due), "--every", "hourly", "--config", str(cfg)])
    not_due_added = runner.invoke(app, ["watch", "add", str(not_due), "--every", "weekly", "--config", str(cfg)])
    assert due_added.exit_code == 0, due_added.output
    assert not_due_added.exit_code == 0, not_due_added.output
    _wait_for_watch_add_run(cfg, due_added.output)
    _wait_for_watch_add_run(cfg, not_due_added.output)
    assert len(_cards(vault)) == 2
    due_source = _registry(vault).sources[0]
    update_watch_source(
        vault,
        registry_path_for_vault(vault),
        due_source.id,
        next_scan_at="2000-01-01T00:00:00+00:00",
    )

    due.write_text("# Due\n\nchanged body\n", encoding="utf-8")
    not_due.write_text("# Not Due\n\nchanged body\n", encoding="utf-8")
    result = runner.invoke(app, ["watch", "scan", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "scanned=1" in result.output
    assert "not_due=1" in result.output
    assert len(_cards(vault)) == 3


def test_watch_scan_all_and_specific_source_can_override_due_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("# First\n\nbody\n", encoding="utf-8")
    second.write_text("# Second\n\nbody\n", encoding="utf-8")
    first_added = runner.invoke(app, ["watch", "add", str(first), "--every", "weekly", "--config", str(cfg)])
    second_added = runner.invoke(app, ["watch", "add", str(second), "--every", "weekly", "--config", str(cfg)])
    assert first_added.exit_code == 0, first_added.output
    assert second_added.exit_code == 0, second_added.output
    _wait_for_watch_add_run(cfg, first_added.output)
    _wait_for_watch_add_run(cfg, second_added.output)
    first.write_text("# First\n\nchanged body\n", encoding="utf-8")
    second.write_text("# Second\n\nchanged body\n", encoding="utf-8")

    scan_all = runner.invoke(app, ["watch", "scan", "--all", "--config", str(cfg)])
    assert scan_all.exit_code == 0, scan_all.output
    assert "scanned=2" in scan_all.output
    assert len(_cards(vault)) == 4

    first.write_text("# First\n\nchanged again\n", encoding="utf-8")
    source_id = _registry(vault).sources[0].id
    specific = runner.invoke(app, ["watch", "scan", source_id, "--config", str(cfg)])

    assert specific.exit_code == 0, specific.output
    assert "scanned=1" in specific.output
    assert len(_cards(vault)) == 5


def test_baseline_diff_tracks_added_changed_unchanged_and_deleted_without_deleting_knowledge(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    folder = tmp_path / "folder"
    unchanged = folder / "unchanged.md"
    changed = folder / "changed.md"
    deleted = folder / "deleted.md"
    for path in (unchanged, changed, deleted):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n\nbody\n", encoding="utf-8")
    added = runner.invoke(app, ["watch", "add", str(folder), "--every", "manual", "--config", str(cfg)])
    assert added.exit_code == 0, added.output
    _wait_for_watch_add_run(cfg, added.output)
    assert len(_cards(vault)) == 3

    approve_explicit_card(load_mindforge_config(cfg), _cards(vault)[0])
    changed.write_text("# changed\n\nnew version\n", encoding="utf-8")
    deleted.unlink()
    new_file = folder / "new.md"
    new_file.write_text("# new\n\nbody\n", encoding="utf-8")
    scan = runner.invoke(app, ["watch", "scan", str(folder), "--config", str(cfg)])

    assert scan.exit_code == 0, scan.output
    assert "added=1" in scan.output
    assert "changed=1" in scan.output
    assert "unchanged=1" in scan.output
    assert "deleted=1" in scan.output
    registry_source = _registry(vault).sources[0]
    assert registry_source.diff_counts["deleted"] == 1
    assert any(item.status == "deleted" for item in registry_source.baseline.values())
    assert len(_cards(vault)) == 5
    assert any(read_card_frontmatter(card)["status"] == "human_approved" for card in _cards(vault))


def test_deleted_watched_folder_is_marked_missing_and_keeps_knowledge(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    folder = tmp_path / "folder"
    source = folder / "note.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Note\n\nbody\n", encoding="utf-8")
    added = runner.invoke(app, ["watch", "add", str(folder), "--every", "manual", "--config", str(cfg)])
    assert added.exit_code == 0, added.output
    _wait_for_watch_add_run(cfg, added.output)
    assert len(_cards(vault)) == 1
    source.unlink()
    folder.rmdir()

    result = runner.invoke(app, ["watch", "scan", str(folder), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "Missing" in result.output
    registry_source = _registry(vault).sources[0]
    assert registry_source.status == "missing"
    assert len(_cards(vault)) == 1


def test_watch_pause_resume_remove_commands_preserve_cards(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "source.md"
    source.write_text("# Source\n\nbody\n", encoding="utf-8")
    added = runner.invoke(app, ["watch", "add", str(source), "--every", "hourly", "--config", str(cfg)])
    assert added.exit_code == 0, added.output
    _wait_for_watch_add_run(cfg, added.output)
    source_id = _registry(vault).sources[0].id

    paused = runner.invoke(app, ["watch", "pause", source_id, "--config", str(cfg)])
    status = runner.invoke(app, ["watch", "status", "--config", str(cfg)])
    resumed = runner.invoke(app, ["watch", "resume", source_id, "--config", str(cfg)])
    removed = runner.invoke(app, ["watch", "remove", source_id, "--config", str(cfg)])

    assert paused.exit_code == 0, paused.output
    assert "paused" in status.output
    assert resumed.exit_code == 0, resumed.output
    assert removed.exit_code == 0, removed.output
    assert len(_cards(vault)) == 1
    assert _registry(vault).sources == ()
