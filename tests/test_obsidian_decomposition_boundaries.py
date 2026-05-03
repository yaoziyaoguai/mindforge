"""新拆出来的 ``obsidian_cli_presenter`` / ``obsidian_manifest_policy`` 边界契约。

中文学习边界：
- ``obsidian_cli_presenter`` 是 CLI 展示层：只能依赖 ``rich`` 与少量 obsidian
  辅助函数，不能反向依赖 ``cli`` / ``obsidian_cli`` / Typer / approval /
  review / recall service / env / httpx。
- ``obsidian_manifest_policy`` 是 staged-export manifest 校验策略：只能依赖
  ``safety_policy``，不能依赖 Rich / Typer / CLI / RunLogger / Checkpoint /
  approval / review / recall。
- 这些 import 边界比单测重要：它们防止未来 refactor 把 service / runtime /
  IO 副作用悄悄塞进 presenter / policy。
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest


_PRESENTER = Path(__file__).resolve().parent.parent / "src" / "mindforge" / "obsidian_cli_presenter.py"
_POLICY = Path(__file__).resolve().parent.parent / "src" / "mindforge" / "obsidian_manifest_policy.py"


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


_PRESENTER_FORBIDDEN = {
    "mindforge.cli",
    "mindforge.obsidian_cli",
    "mindforge.approval_service",
    "mindforge.review_service",
    "mindforge.recall_service",
    "mindforge.run_logger",
    "mindforge.checkpoint",
    "mindforge.env_loader",
    "typer",
    "httpx",
    "dotenv",
    "os",
}


_POLICY_FORBIDDEN = {
    "mindforge.cli",
    "mindforge.obsidian_cli",
    "mindforge.obsidian_cli_presenter",
    "mindforge.approval_service",
    "mindforge.review_service",
    "mindforge.recall_service",
    "mindforge.run_logger",
    "mindforge.checkpoint",
    "mindforge.env_loader",
    "rich",
    "rich.console",
    "rich.table",
    "typer",
    "httpx",
    "dotenv",
}


def test_obsidian_cli_presenter_imports_have_no_runtime_or_service_dep() -> None:
    """presenter 不应反向依赖 CLI / business service / env / HTTP。"""

    imports = _module_imports(_PRESENTER)
    bad = imports & _PRESENTER_FORBIDDEN
    assert not bad, f"obsidian_cli_presenter 出现禁止的依赖: {sorted(bad)}"


def test_obsidian_manifest_policy_imports_are_pure() -> None:
    """manifest policy 只能依赖 safety_policy / stdlib，不引入 Rich/Typer/CLI/service。"""

    imports = _module_imports(_POLICY)
    bad = imports & _POLICY_FORBIDDEN
    assert not bad, f"obsidian_manifest_policy 出现禁止的依赖: {sorted(bad)}"


def test_obsidian_cli_presenter_import_has_no_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """``import obsidian_cli_presenter`` 不应触发 env 读取、HTTP 调用或文件写入。"""

    def _blocked_env(*_a: object, **_kw: object) -> None:
        raise AssertionError("import obsidian_cli_presenter 不应触发 env 读取")

    def _blocked_http(*_a: object, **_kw: object) -> None:
        raise AssertionError("import obsidian_cli_presenter 不应触发 HTTP 调用")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr("httpx.Client.post", _blocked_http)

    module = importlib.reload(importlib.import_module("mindforge.obsidian_cli_presenter"))

    assert hasattr(module, "build_stage_preview_table")
    assert hasattr(module, "format_doctor_icon")
    assert module.format_doctor_icon("ok") == "[green]✓[/green]"


def test_obsidian_manifest_policy_import_has_no_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """``import obsidian_manifest_policy`` 同样必须无 IO / env / HTTP 副作用。"""

    def _blocked_env(*_a: object, **_kw: object) -> None:
        raise AssertionError("import obsidian_manifest_policy 不应触发 env 读取")

    def _blocked_http(*_a: object, **_kw: object) -> None:
        raise AssertionError("import obsidian_manifest_policy 不应触发 HTTP 调用")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr("httpx.Client.post", _blocked_http)

    module = importlib.reload(importlib.import_module("mindforge.obsidian_manifest_policy"))

    assert hasattr(module, "check_safety_boundary")
    assert hasattr(module, "manifest_path_value")


def test_obsidian_remains_public_facade_for_preflight() -> None:
    """obsidian_preflight 必须仍可从 ``mindforge.obsidian`` 直接导入。"""

    obsidian = importlib.import_module("mindforge.obsidian")
    assert hasattr(obsidian, "obsidian_preflight")
    assert hasattr(obsidian, "ObsidianPreflightResult")


def test_obsidian_cli_presenter_round_trip_pure() -> None:
    """presenter 的纯字符串/Table 行为：相同输入产出一致。"""

    from mindforge.obsidian_cli_presenter import (
        format_copy_warning,
        format_dry_run_safety_footer,
        diff_preview_no_changes,
        stage_preview_next_command,
    )

    assert format_copy_warning() == format_copy_warning()
    assert "dry-run" in format_dry_run_safety_footer()
    assert diff_preview_no_changes() == "[dim]无差异。[/dim]"
    cmd = stage_preview_next_command(vault_root=Path("/tmp/v"), source_hint="a.md")
    assert "mindforge obsidian stage" in cmd
    assert "/tmp/v" in cmd
    assert "a.md" in cmd
