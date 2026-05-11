"""Legacy command aliases must only redirect to the new product path.

中文学习型说明：这组测试锁定真正的 semantic migration，而不是
``hidden=True``。旧命令不能继续作为 Typer command/group 存在；真实
进程入口只允许输出迁移提示，指向 Web Setup、local source、background
processing、review/approve/library/wiki 主路径。
"""

from __future__ import annotations

import subprocess
import sys

from typer.testing import CliRunner

from mindforge.cli import app


runner = CliRunner()


def _registered_commands() -> set[str]:
    names: set[str] = set()
    for cmd in app.registered_commands:
        names.add(cmd.name or cmd.callback.__name__)
    for grp in app.registered_groups:
        names.add(grp.name)
    return names


def test_legacy_commands_are_not_registered_in_typer_app() -> None:
    """旧 product semantic 不能继续作为完整 command 或 group 存在。"""

    commands = _registered_commands()
    for legacy in ("demo", "dogfood", "cubox", "provider", "llm"):
        assert legacy not in commands


def test_direct_typer_access_no_longer_runs_legacy_commands() -> None:
    """测试内部也不能绕过 ``main`` 继续执行旧命令组。"""

    for args in (
        ["demo"],
        ["dogfood", "quickstart"],
        ["cubox", "dry-run"],
        ["provider", "readiness"],
        ["llm", "ping"],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code != 0
        assert "No such command" in result.output


def test_process_entrypoint_redirects_legacy_commands_without_help_surface() -> None:
    """真实 CLI 旧 argv 只给 migration message，不再显示旧 help 页面。"""

    for command, target in (
        ("demo", "mindforge web"),
        ("dogfood", "mindforge web"),
        ("cubox", "mindforge watch add <local-file-or-folder>"),
        ("provider", "mindforge web"),
        ("llm", "mindforge web"),
    ):
        result = subprocess.run(
            [sys.executable, "-m", "mindforge", command, "--help"],
            cwd=".",
            text=True,
            capture_output=True,
            check=False,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 2
        assert "This legacy command has been removed." in combined
        assert target in combined
        for forbidden in (
            "quickstart",
            "dry-run",
            "readiness",
            "fake-default",
            "fake provider",
            "active_profile",
            "token_env",
        ):
            assert forbidden not in combined
