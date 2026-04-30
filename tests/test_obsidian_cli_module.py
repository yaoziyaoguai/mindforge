"""v0.7.19 — Obsidian CLI adapter 模块边界测试。

这些测试不验证 Obsidian 业务逻辑本身；业务逻辑已有 service/CLI 黑盒测试保护。
这里专门保护模块边界：`obsidian_cli.py` 可以是 Typer/Rich command adapter，但
导入它不能读 `.env`、不能调 LLM、不能写正式 notes，也不能反向依赖 recall /
approval / review service。
"""

from __future__ import annotations

import importlib
import inspect

import typer
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.obsidian_cli import obsidian_app


runner = CliRunner()


def test_obsidian_app_importable_from_obsidian_cli() -> None:
    """新模块必须导出可挂载的 Typer app，而不是只暴露零散 helper。"""

    assert isinstance(obsidian_app, typer.Typer)


def test_top_level_cli_mounts_obsidian_app() -> None:
    """top-level cli.py 应只挂载 Obsidian command adapter，命令路径保持不变。"""

    res = runner.invoke(app, ["obsidian", "--help"])

    assert res.exit_code == 0, res.output
    assert "Obsidian Binding" in res.output


def test_obsidian_commands_remain_registered() -> None:
    """迁移后关键子命令不能丢失，也不能重命名。"""

    res = runner.invoke(app, ["obsidian", "--help"])

    assert res.exit_code == 0, res.output
    for command in ("doctor", "scan", "links", "stage", "preflight", "next"):
        assert command in res.output


def test_import_obsidian_cli_has_no_env_llm_or_note_write_side_effects(
    tmp_path,
    monkeypatch,
) -> None:
    """import adapter 只能注册命令；不得读取 `.env`、联网或写任何文件。"""

    sentinel = tmp_path / "formal-note.md"
    sentinel.write_text("formal note\n", encoding="utf-8")

    def _blocked_env(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("import obsidian_cli 不应读取 .env")

    def _blocked_http(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("import obsidian_cli 不应调用 LLM/HTTP")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr("httpx.Client.post", _blocked_http)

    module = importlib.reload(importlib.import_module("mindforge.obsidian_cli"))

    assert isinstance(module.obsidian_app, typer.Typer)
    assert sentinel.read_text(encoding="utf-8") == "formal note\n"


def test_obsidian_cli_has_no_reverse_business_service_dependency() -> None:
    """Obsidian adapter 不应反向依赖 approval/review/recall 业务服务。"""

    import mindforge.obsidian_cli as module

    source = inspect.getsource(module)

    assert "approval_service" not in source
    assert "review_service" not in source
    assert "recall_service" not in source


def test_import_order_has_no_cycle() -> None:
    """obsidian_cli 可在 cli 前后独立导入，避免形成 cli <-> obsidian_cli 循环。"""

    obsidian_module = importlib.import_module("mindforge.obsidian_cli")
    cli_module = importlib.import_module("mindforge.cli")
    res = runner.invoke(cli_module.app, ["obsidian", "--help"])

    assert isinstance(obsidian_module.obsidian_app, typer.Typer)
    assert isinstance(cli_module.obsidian_app, typer.Typer)
    assert res.exit_code == 0, res.output
