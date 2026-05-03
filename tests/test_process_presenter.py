"""``process_presenter`` 契约测试 / TDD characterization。

中文学习边界：
- ``process_presenter`` 只负责把 cli.py 提供的少量事实（source_path /
  cards 输出 path / writer 冲突标记 / skip_reason / error_stage / counts）
  翻译成 Rich markup 字符串。
- 它绝不写文件、绝不发 ``RunLogger.emit``、绝不调 LLM/网络、绝不读
  ``.env`` / ``os.environ``。这些 IO 与事件副作用必须留在 cli.py 的 process
  循环里，因为事件顺序（``card_written`` → ``source_processed``）是产品契约。
- 这套测试不构造 ``ProcessItemResult``：presenter 已显式选择不依赖
  ``process_service``，避免回到家族契约禁止的 service 依赖。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.process_presenter import (
    format_failed,
    format_next_hint,
    format_processed_dry_run,
    format_processed_real,
    format_skipped,
    format_summary,
)


def test_format_skipped_includes_path_and_reason() -> None:
    """skipped 行必须同时给出 source 路径和 skip_reason；颜色用 yellow。"""

    line = format_skipped(
        source_path="00-Inbox/foo.md", skip_reason="below_threshold"
    )
    assert "[yellow]skipped[/yellow]" in line
    assert "00-Inbox/foo.md" in line
    assert "below_threshold" in line


def test_format_failed_includes_stage_and_message() -> None:
    """failed 行必须给出 stage 与 error message；颜色用 red。"""

    line = format_failed(
        source_path="00-Inbox/bar.md",
        error_stage="distill",
        error_message="provider rate limit",
    )
    assert "[red]failed[/red]" in line
    assert "stage=distill" in line
    assert "provider rate limit" in line
    assert "00-Inbox/bar.md" in line


def test_format_processed_dry_run_shows_target_dir() -> None:
    """dry-run processed 必须用 cyan 标签并提示 would-write 目标目录。"""

    line = format_processed_dry_run(
        source_path="00-Inbox/baz.md",
        target_dir=Path("/tmp/vault/20-Knowledge-Cards/agent-runtime"),
    )
    assert "[cyan]dry-run[/cyan]" in line
    assert "would-write" in line
    assert "00-Inbox/baz.md" in line
    assert "agent-runtime" in line


def test_format_processed_real_marks_conflict_in_yellow() -> None:
    """有 conflict 时 tag 改成 yellow ``conflict``，无 conflict 时是 green ``processed``。"""

    ok = format_processed_real(
        source_path="00-Inbox/x.md",
        output_path=Path("/tmp/vault/20-Knowledge-Cards/agent-runtime/x.md"),
        conflict=False,
    )
    assert "[green]processed[/green]" in ok
    assert "→" in ok and "agent-runtime" in ok

    cf = format_processed_real(
        source_path="00-Inbox/x.md",
        output_path=Path("/tmp/vault/20-Knowledge-Cards/agent-runtime/x.md"),
        conflict=True,
    )
    assert "[yellow]conflict[/yellow]" in cf


def test_format_summary_reports_all_four_counts() -> None:
    """汇总行必须报告 seen / processed / skipped / failed 四项。"""

    line = format_summary({"seen": 5, "processed": 3, "skipped": 1, "failed": 1})
    assert "process 完成" in line
    assert "seen=5" in line
    assert "processed=3" in line
    assert "skipped=1" in line
    assert "failed=1" in line


def test_format_next_hint_returns_none_when_no_actionable_state() -> None:
    """没有 processed 也没有 skipped 时不应给 hint，避免噪音。"""

    assert format_next_hint({"seen": 0, "processed": 0, "skipped": 0, "failed": 0}) == []


def test_format_next_hint_after_processed_emphasizes_human_approval_boundary() -> None:
    """processed > 0 时 hint 必须复述 ``ai_draft until explicit human approval`` 边界。

    这是产品安全契约：UX completion 不能在没有人工批准时就把卡片当 production。
    """

    hints = format_next_hint(
        {"seen": 1, "processed": 1, "skipped": 0, "failed": 0}
    )
    joined = " | ".join(hints)
    assert "approve list" in joined
    assert "ai_draft" in joined and "human approval" in joined


def test_format_next_hint_after_skipped_only_suggests_scan_or_approve() -> None:
    """全 skipped 时引导用户去 scan 或 approve list，而不是夸大 processed。"""

    hints = format_next_hint(
        {"seen": 1, "processed": 0, "skipped": 1, "failed": 0}
    )
    joined = " | ".join(hints)
    assert "scan" in joined or "approve list" in joined
    assert "ai_draft" not in joined  # 避免误导用户以为有新卡片
