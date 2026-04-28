"""run_logger 单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mindforge.run_logger import (
    EVENT_RUN_FAILED,
    EVENT_RUN_FINISHED,
    EVENT_RUN_STARTED,
    EVENT_SOURCE_SEEN,
    RunLogger,
    _generate_run_id,
    summarize_latest_run,
)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def test_run_id_format() -> None:
    rid = _generate_run_id()
    # 形如 2026-04-28T13-00-00_ab12cd
    assert len(rid) == 26
    date_part, suffix = rid.rsplit("_", 1)
    assert len(suffix) == 6 and all(c in "0123456789abcdef" for c in suffix)
    # 日期部分使用 T 与 - 分隔，没有冒号
    assert ":" not in date_part


def test_context_manager_emits_start_and_finish(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    with RunLogger(runs_dir, command="scan") as logger:
        logger.emit(EVENT_SOURCE_SEEN, source_type="cubox_markdown", path="a.md")

    events = _read_jsonl(logger.jsonl_path)
    assert [e["event"] for e in events] == [EVENT_RUN_STARTED, EVENT_SOURCE_SEEN, EVENT_RUN_FINISHED]
    # 每条事件都带 run_id 与 ts
    assert all(e["run_id"] == logger.run_id for e in events)
    assert all("ts" in e for e in events)
    # 第一条带 command
    assert events[0]["command"] == "scan"


def test_context_manager_emits_failed_on_exception_and_propagates(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    logger_ref: RunLogger | None = None
    with pytest.raises(RuntimeError, match="boom"):
        with RunLogger(runs_dir, command="scan") as logger:
            logger_ref = logger
            raise RuntimeError("boom")
    assert logger_ref is not None
    events = _read_jsonl(logger_ref.jsonl_path)
    assert events[0]["event"] == EVENT_RUN_STARTED
    assert events[-1]["event"] == EVENT_RUN_FAILED
    assert "RuntimeError: boom" in events[-1]["error_message"]


def test_emit_rejects_unknown_field(tmp_path: Path) -> None:
    with RunLogger(tmp_path / "runs", command="scan") as logger:
        with pytest.raises(ValueError, match="不在白名单"):
            logger.emit(EVENT_SOURCE_SEEN, raw_text="敏感原文")  # noqa: S106


def test_emit_after_close_raises(tmp_path: Path) -> None:
    logger = RunLogger(tmp_path / "runs", command="scan")
    logger.open()
    logger.close()
    with pytest.raises(RuntimeError, match="已关闭"):
        logger.emit(EVENT_SOURCE_SEEN, source_type="x")


def test_runs_dir_created_lazily(tmp_path: Path) -> None:
    runs_dir = tmp_path / "deep" / "runs"
    assert not runs_dir.exists()
    with RunLogger(runs_dir, command="scan"):
        pass
    assert runs_dir.exists() and runs_dir.is_dir()


def test_jsonl_is_append_only(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    logger = RunLogger(runs_dir, command="scan", run_id="2026-04-28T13-00-00_aaaaaa")
    with logger:
        logger.emit(EVENT_SOURCE_SEEN, source_type="cubox_markdown")
    # 同 run_id 再开一次，应当 append 而非覆盖
    logger2 = RunLogger(runs_dir, command="scan", run_id="2026-04-28T13-00-00_aaaaaa")
    with logger2:
        logger2.emit(EVENT_SOURCE_SEEN, source_type="plain_markdown")
    events = _read_jsonl(logger.jsonl_path)
    # 两次 run_started + 两次事件 + 两次 run_finished = 6 条
    assert len(events) == 6
    assert events[0]["event"] == EVENT_RUN_STARTED
    assert events[2]["event"] == EVENT_RUN_FINISHED
    assert events[3]["event"] == EVENT_RUN_STARTED


def test_summarize_latest_run_none_when_missing(tmp_path: Path) -> None:
    assert summarize_latest_run(tmp_path / "nope") is None
    (tmp_path / "empty").mkdir()
    assert summarize_latest_run(tmp_path / "empty") is None


def test_summarize_latest_run_returns_non_sensitive_summary(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    with RunLogger(runs_dir, command="scan") as logger:
        logger.emit(EVENT_SOURCE_SEEN, source_type="cubox_markdown", path="a.md")
        logger.emit(EVENT_SOURCE_SEEN, source_type="plain_markdown", path="b.md")

    summary = summarize_latest_run(runs_dir)
    assert summary is not None
    assert summary.command == "scan"
    assert summary.event_count == 4  # start + 2 + finish
    assert summary.last_event == EVENT_RUN_FINISHED
    assert summary.failed is False
    assert summary.run_id == logger.run_id


def test_summarize_latest_run_marks_failed(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    try:
        with RunLogger(runs_dir, command="scan"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    summary = summarize_latest_run(runs_dir)
    assert summary is not None
    assert summary.failed is True
    assert summary.last_event == EVENT_RUN_FAILED


def test_summarize_latest_run_picks_latest_by_mtime(tmp_path: Path) -> None:
    import os
    import time

    runs_dir = tmp_path / "runs"
    with RunLogger(runs_dir, command="scan", run_id="2020-01-01T00-00-00_aaaaaa") as a:
        a.emit(EVENT_SOURCE_SEEN, source_type="x")
    # 把 a 的 mtime 拨到很早
    old = time.time() - 3600
    os.utime(a.jsonl_path, (old, old))

    with RunLogger(runs_dir, command="status", run_id="2020-01-01T00-00-01_bbbbbb") as b:
        b.emit(EVENT_SOURCE_SEEN, source_type="y")

    summary = summarize_latest_run(runs_dir)
    assert summary is not None
    assert summary.path == b.jsonl_path
    assert summary.command == "status"
