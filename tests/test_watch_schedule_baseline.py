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


def _wait_for_scan_runs(output: str, cfg_path: Path, *, timeout: float = 5.0) -> None:
    """等待 watch scan 创建的 background processing runs 全部完成。

    中文学习型说明：watch scan 现在为每个有变更的 source 创建一个 background
    ProcessingRun。测试需要等待所有 run 完成后再检查结果。
    """
    run_ids = [line.split("run_id=", 1)[1].strip() for line in output.splitlines() if "run_id=" in line]
    if not run_ids:
        return
    cfg = load_cfg(cfg_path, read_env=False)
    deadline = time.monotonic() + timeout
    pending = set(run_ids)
    while time.monotonic() < deadline and pending:
        done = set()
        for rid in list(pending):
            latest = get_processing_run(cfg, rid)
            if latest is not None and latest.status not in {"queued", "running"}:
                done.add(rid)
        pending -= done
        if pending:
            time.sleep(0.05)
    if pending:
        raise AssertionError(f"watch scan runs did not finish: {pending}")


def _run_id_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("run_id: "):
            return line.split("run_id: ", 1)[1].strip()
    # watch scan 输出中 run_id 格式变为 "run_id=..."
    for line in output.splitlines():
        if "run_id=" in line:
            return line.split("run_id=", 1)[1].strip()
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
            assert latest.status in {"succeeded", "partial_failed", "skipped", "failed", "needs_model_setup"}, latest
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
    # watch scan 现在是异步：等待 background processing run 完成
    _wait_for_scan_runs(result.output, cfg)
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
    # watch scan 现在是异步：等待 background processing runs 完成
    _wait_for_scan_runs(scan_all.output, cfg)
    assert len(_cards(vault)) == 4

    first.write_text("# First\n\nchanged again\n", encoding="utf-8")
    source_id = _registry(vault).sources[0].id
    specific = runner.invoke(app, ["watch", "scan", source_id, "--config", str(cfg)])

    assert specific.exit_code == 0, specific.output
    assert "scanned=1" in specific.output
    # watch scan 现在是异步：等待 background processing run 完成
    _wait_for_scan_runs(specific.output, cfg)
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
    # watch scan 现在是异步：等待 background processing run 完成
    _wait_for_scan_runs(scan.output, cfg)
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


# ——————————————————————————————————————
# watch retry / no-output 边界测试
# ——————————————————————————————————————


def _write_no_model_config(tmp_path: Path) -> tuple[Path, Path]:
    """创建无模型配置（模拟 model setup incomplete 场景）。

    中文学习型说明：用于模拟用户首次安装后未配置模型、或模型配置错误导致
    HTTP 401/404 后 run failed 的真实场景。
    """
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True, exist_ok=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True, exist_ok=True)
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
                        },
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
                    "default_model": None,
                    "models": {},
                    "routing": {},
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


def _rewrite_config_with_fake_provider(cfg_path: Path, vault: Path) -> None:
    """将无模型 config 替换为 fake provider config（模拟用户修正模型配置）。

    中文学习型说明：模拟用户看到 HTTP 401/404 后，到 Web Setup 修正了 provider
    key/base_url/model，然后 retry 同一个 watched folder。
    """
    cfg_path.write_text(
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
                        },
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
                "logging": {"level": "INFO", "file": str(cfg_path.parent / "mf.log")},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_changed_targets_includes_unchanged_with_null_last_processed(
    tmp_path: Path,
) -> None:
    """_changed_targets_from_baseline 应纳入 unchanged 但 last_processed_at=null 的文件。

    中文学习型说明：这是 watch retry 的核心规则。文件内容未变但从未成功处理过
    （如上次 run 因 model error 失败），retry 时必须重新进入 processing。
    """
    from mindforge.ingestion_service import _changed_targets_from_baseline
    from mindforge.watch_registry import WatchFileSnapshot

    now = "2026-01-01T00:00:00+00:00"
    path = tmp_path / "test.md"
    path.write_text("# test\n", encoding="utf-8")

    # 模拟：文件 unchanged + last_processed_at=null
    baseline = {
        "test.md": WatchFileSnapshot(
            relative_path="test.md",
            path=path,
            content_hash="abc123",
            size=len("# test\n"),
            mtime=path.stat().st_mtime,
            last_seen_at=now,
            last_processed_at=None,
            status="unchanged",
        ),
        "already_done.md": WatchFileSnapshot(
            relative_path="already_done.md",
            path=path,
            content_hash="abc123",
            size=len("# test\n"),
            mtime=path.stat().st_mtime,
            last_seen_at=now,
            last_processed_at=now,
            status="unchanged",
        ),
    }
    diff = {"added": 0, "changed": 0, "unchanged": 2, "deleted": 0, "skipped": 0}

    result = _changed_targets_from_baseline(baseline, diff)

    # unchanged + last_processed_at=null → retry target
    assert path in result, (
        "unchanged 但 last_processed_at=null 的文件必须作为 retry target"
    )
    # unchanged + last_processed_at 非空 → 不 retry
    assert len(result) == 1, f"should only retry unprocessed items, got {len(result)}"


def test_changed_targets_empty_when_all_processed(
    tmp_path: Path,
) -> None:
    """全部 unchanged 且 last_processed_at 已设置时，不应返回任何 retry target。"""
    from mindforge.ingestion_service import _changed_targets_from_baseline
    from mindforge.watch_registry import WatchFileSnapshot

    now = "2026-01-01T00:00:00+00:00"
    path = tmp_path / "done.md"
    path.write_text("# done\n", encoding="utf-8")

    baseline = {
        "done.md": WatchFileSnapshot(
            relative_path="done.md",
            path=path,
            content_hash="abc123",
            size=len("# done\n"),
            mtime=path.stat().st_mtime,
            last_seen_at=now,
            last_processed_at=now,
            status="unchanged",
        ),
    }
    diff = {"added": 0, "changed": 0, "unchanged": 1, "deleted": 0, "skipped": 0}

    result = _changed_targets_from_baseline(baseline, diff)

    assert result == [], "全部已处理的 unchanged 文件不应产生 retry target"


def test_failed_run_does_not_update_last_processed_at(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """failed run 后 source.last_processed_at 必须保持 null（或旧值），不能更新。

    中文学习型说明：如果 failed run 后 source.last_processed_at 被错误更新为 now，
    下一次 scan 会把 source 视为"刚处理过"，不 retry。这是用户报告的核心 bug。
    """
    cfg, vault = _write_no_model_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "source.md"
    source.write_text("# Test\n\nbody\n", encoding="utf-8")

    added = runner.invoke(app, ["watch", "add", str(source), "--every", "manual", "--config", str(cfg)])
    assert added.exit_code == 0, added.output

    # 无模型配置 → background run 应失败
    _wait_for_watch_add_run(cfg, added.output)
    reg = _registry(vault)
    assert len(reg.sources) == 1
    # 关键断言：failed run 后 source-level last_processed_at 必须为 null
    assert reg.sources[0].last_processed_at is None, (
        f"failed run 后 last_processed_at 必须为 null，实际为 {reg.sources[0].last_processed_at!r}"
    )


def test_unchanged_unprocessed_file_retried_after_model_fix(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """模拟真实用户路径：model error → fix model → retry → draft 生成。

    中文学习型说明：用户第一次 watch add 时模型配置错误（HTTP 401/404），run failed。
    用户到 Web Setup 修正模型配置后，再次执行 watch scan --all。
    系统必须重新处理第一次失败的文件，并生成 ai_draft，不能 no-output succeeded。
    """
    # 第一阶段：无模型配置 → watch add → run failed
    cfg, vault = _write_no_model_config(tmp_path)
    monkeypatch.chdir(vault)
    source_file = tmp_path / "note.md"
    source_file.write_text("# My Note\n\nImportant content here.\n", encoding="utf-8")

    added_no_model = runner.invoke(
        app, ["watch", "add", str(source_file), "--every", "manual", "--config", str(cfg)]
    )
    assert added_no_model.exit_code == 0, added_no_model.output
    _wait_for_watch_add_run(cfg, added_no_model.output)
    # 无模型 → 确认没有 draft 生成
    assert len(_cards(vault)) == 0
    reg_after_fail = _registry(vault)
    assert reg_after_fail.sources[0].last_processed_at is None

    # 第二阶段：修正模型配置（模拟用户在 Web Setup 修正 provider）
    _rewrite_config_with_fake_provider(cfg, vault)
    source_id = reg_after_fail.sources[0].id

    # retry: watch scan --all
    scan = runner.invoke(app, ["watch", "scan", "--all", "--config", str(cfg)])
    assert scan.exit_code == 0, scan.output
    _wait_for_scan_runs(scan.output, cfg)

    # 关键断言：retry 后必须生成 draft
    cards = _cards(vault)
    assert len(cards) > 0, (
        f"retry after model fix 应生成 ai_draft，但 20-Knowledge-Cards 为空。\n"
        f"scan output: {scan.output}"
    )
    # source-level last_processed_at 应更新为成功处理时间
    reg_final = _registry(vault)
    assert reg_final.sources[0].last_processed_at is not None, (
        "retry 成功后 last_processed_at 不应为 null"
    )


def test_no_output_run_status_is_failed_not_succeeded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """discovered > 0 但 drafts=0 skipped=0 errors=0 时，run 必须标记为 failed。

    中文学习型说明：这是防止伪成功的关键检查。如果 scan 发现了文件但 processing
    没有产生任何 output，run 必须 failed 并给出明确消息，不能 succeeded。
    """
    # 使用无模型 config：discovered=1 但 processor 报错 → errors=1
    # 但当所有文件都 unchanged+unprocessed 且无 model 时，watch_scan CLi 创建
    # background run，worker 进入 watch_scan_sources(process_changes=True)。
    # _changed_targets_from_baseline 返回文件（unchanged + last_processed_at=null），
    # 进入 _ingest_targets_summary → LLM 配置缺失 → errors=1。
    # 这个场景 run 应为 failed 而不是 succeeded。
    cfg, vault = _write_no_model_config(tmp_path)
    monkeypatch.chdir(vault)
    source_file = tmp_path / "doc.md"
    source_file.write_text("# Doc\n\nbody\n", encoding="utf-8")

    # 先用 fake provider 创建 baseline（模拟之前有 baseline 记录）
    _rewrite_config_with_fake_provider(cfg, vault)
    added = runner.invoke(
        app, ["watch", "add", str(source_file), "--every", "manual", "--config", str(cfg)]
    )
    assert added.exit_code == 0, added.output
    _wait_for_watch_add_run(cfg, added.output)
    # fake provider 应生成 draft
    assert len(_cards(vault)) > 0

    # 现在把 baseline item 的 last_processed_at 篡改为 null，
    # 模拟"文件存在但从未成功处理"的状态（如之前 run failed 留下的残留）
    reg = _registry(vault)
    source = reg.sources[0]
    tampered_baseline = {}
    for key, item in source.baseline.items():
        tampered_baseline[key] = type(item)(
            relative_path=item.relative_path,
            path=item.path,
            content_hash=item.content_hash,
            size=item.size,
            mtime=item.mtime,
            last_seen_at=item.last_seen_at,
            last_processed_at=None,
            status=item.status,
            skipped_reason=item.skipped_reason,
        )
    update_watch_source(
        vault,
        registry_path_for_vault(vault),
        source.id,
        last_processed_at=None,
        baseline=tampered_baseline,
    )
    source_id = source.id

    # 切换回无模型 config → retry → 应 failed（不是 succeeded）
    _write_no_model_config(tmp_path)
    scan = runner.invoke(app, ["watch", "scan", source_id, "--config", str(cfg)])
    assert scan.exit_code == 0, scan.output
    _wait_for_scan_runs(scan.output, cfg)

    # 检查 background run 状态：应为 failed
    run_id = _run_id_from_output(scan.output)
    run = get_processing_run(load_cfg(cfg, read_env=False), run_id)
    assert run is not None
    assert run.status in {"failed", "needs_model_setup"}, (
        f"no-output run 必须为 failed，实际 status={run.status}, "
        f"summary={run.summary}, message={run.message}"
    )
    assert "succeeded" not in run.status, (
        f"run status 不能为 succeeded: {run.status}"
    )


def test_baseline_item_last_processed_updated_on_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """成功处理后，baseline item 的 last_processed_at 必须更新。

    中文学习型说明：只有这样才能确保下一次 scan 不把已处理文件当作 retry target。
    """
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source_file = tmp_path / "fresh.md"
    source_file.write_text("# Fresh\n\nbody\n", encoding="utf-8")

    added = runner.invoke(
        app, ["watch", "add", str(source_file), "--every", "manual", "--config", str(cfg)]
    )
    assert added.exit_code == 0, added.output
    _wait_for_watch_add_run(cfg, added.output)

    reg = _registry(vault)
    assert len(reg.sources) == 1
    source = reg.sources[0]
    # 至少有一个 baseline item 的 last_processed_at 已更新
    processed_items = [
        item for item in source.baseline.values()
        if item.last_processed_at is not None
    ]
    assert len(processed_items) > 0, (
        f"成功处理后 baseline item last_processed_at 应更新，"
        f"实际 baseline: {dict(source.baseline)}"
    )
