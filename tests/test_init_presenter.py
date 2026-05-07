"""``init_presenter`` 契约测试 / TDD characterization。

中文学习边界：
- ``init_presenter`` 只负责把 ``InitPlan`` 与 ``execute_plan`` 的结果翻译成
  Rich markup 字符串。
- 它绝不调 ``typer.prompt`` / ``typer.confirm``：所有交互式用户输入留在
  cli.py 的 ``init`` 命令体内，因为 prompt 是 CLI adapter 的职责。
- 它绝不写 ``configs/mindforge.yaml``，绝不读 ``.env``。文件副作用属于
  ``init_cmd.execute_plan`` 与 ``_rewrite_init_config``。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.init_cmd import build_plan
from mindforge.init_presenter import (
    format_dry_run_completion,
    format_dry_run_item,
    format_execute_action,
    format_interactive_summary,
    format_mode_lines,
    format_next_steps,
    format_plan_header,
    format_plan_summary,
    format_safety_footer,
)


def _make_plan(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    return build_plan(
        tmp_path / "vault",
        project_root=tmp_path / "proj",
        repo_root=repo,
        force=False,
    )


def test_format_plan_header_lists_vault_and_project_root(tmp_path: Path) -> None:
    """plan header 必须包含 vault.root 与 project root，便于用户核对路径。"""

    plan = _make_plan(tmp_path)
    lines = format_plan_header(plan)
    text = "\n".join(lines)
    assert "MindForge init" in text
    assert "vault.root" in text and str(plan.vault_root) in text
    assert "project root" in text and str(plan.project_root) in text


def test_format_mode_lines_emits_only_active_modes() -> None:
    """force / dry_run / interactive 三个 mode 标签按需出现，避免误导。"""

    none = format_mode_lines(force=False, dry_run=False, interactive=False)
    assert none == []

    forced = format_mode_lines(force=True, dry_run=False, interactive=False)
    assert any("force" in line.lower() for line in forced)

    dr = format_mode_lines(force=False, dry_run=True, interactive=False)
    assert any("dry-run" in line for line in dr)

    inter = format_mode_lines(force=False, dry_run=False, interactive=True)
    assert any("interactive" in line for line in inter)


def test_format_interactive_summary_omits_when_not_interactive() -> None:
    """非 interactive 时不输出 telemetry / default_model 行；interactive 时必须输出。"""

    assert (
        format_interactive_summary(
            interactive=False,
            telemetry_enabled=None,
            active_profile=None,
        )
        == []
    )

    lines = format_interactive_summary(
        interactive=True,
        telemetry_enabled=True,
        active_profile="main",
    )
    text = " ".join(lines)
    assert "telemetry" in text and "True" in text and "local_only=True" in text
    assert "default_model" in text and "main" in text


def test_format_plan_summary_reports_four_action_counts(tmp_path: Path) -> None:
    """plan 汇总必须给四个动作的计数：create_dir / copy_file / overwrite_force / skip_exists。"""

    plan = _make_plan(tmp_path)
    line = format_plan_summary(plan.summary())
    for key in ("create_dir", "copy_file", "overwrite_force", "skip_exists"):
        assert key in line


def test_format_dry_run_item_uses_distinct_tag_per_action() -> None:
    """dry-run 列表里 4 种 action 必须有可区分的视觉 tag。"""

    tags = {
        action: format_dry_run_item(action, target=Path("/tmp/x"), note="n")
        for action in ("create_dir", "copy_file", "overwrite_force", "skip_exists")
    }
    assert "[green]" in tags["create_dir"]
    assert "[green]" in tags["copy_file"]
    assert "[yellow]" in tags["overwrite_force"]
    assert "[dim]" in tags["skip_exists"]
    for line in tags.values():
        assert "/tmp/x" in line


def test_format_dry_run_completion_states_no_files_written() -> None:
    """dry-run 完成提示必须明确说"未写任何文件"，避免用户误以为已落盘。"""

    line = format_dry_run_completion()
    assert "未写任何文件" in line


def test_format_execute_action_indents_for_visual_alignment() -> None:
    """execute 阶段每条 action 行都按两空格缩进，与 plan 列表风格一致。"""

    line = format_execute_action("created /tmp/foo")
    assert line.startswith("  ")
    assert "created /tmp/foo" in line


def test_format_next_steps_starts_with_bold_heading() -> None:
    """Next steps 必须是 bold 标题加缩进的 step 列表。"""

    lines = format_next_steps(["mindforge demo", "mindforge doctor"])
    assert any("Next steps" in line and "[bold]" in line for line in lines)
    indented = [line for line in lines if line.startswith("  ")]
    assert any("mindforge demo" in line for line in indented)
    assert any("mindforge doctor" in line for line in indented)


def test_format_safety_footer_reaffirms_no_env_no_llm() -> None:
    """init 安全 footer 必须复述 ``不创建/不读 .env`` 与 ``不调 LLM``。"""

    line = format_safety_footer()
    assert ".env" in line
    assert "LLM" in line
