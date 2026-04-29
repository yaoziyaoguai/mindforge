"""可执行 onboarding smoke：demo vault 的主路径不能回归。

只使用 examples/demo-vault 的虚构资料和 fake provider；运行时产物写入 tmp_path。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()


def _copy_demo_vault(tmp_path: Path) -> tuple[Path, Path]:
    src = Path("examples/demo-vault")
    vault = tmp_path / "demo-vault"
    shutil.copytree(src, vault)

    cfg = yaml.safe_load(Path("configs/mindforge.yaml").read_text(encoding="utf-8"))
    cfg["vault"]["root"] = str(vault)
    cfg["state"]["workdir"] = str(tmp_path / ".mindforge")
    cfg["logging"]["file"] = str(tmp_path / "mindforge.log")
    cfg["llm"]["active_profile"] = "fake"
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return vault, cfg_path


def test_demo_vault_onboarding_smoke(tmp_path: Path, monkeypatch) -> None:
    vault, cfg = _copy_demo_vault(tmp_path)

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("本地可用性 smoke 不应读取 .env")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)

    checks = [
        (["commands"], "命令地图"),
        (["next", "--config", str(cfg)], "MindForge next"),
        (["doctor", "--config", str(cfg)], "MindForge doctor"),
        (["scan", "--config", str(cfg)], "扫描完成"),
        (["process", "--config", str(cfg), "--profile", "fake", "--limit", "1"], "active_profile"),
        (["approve", "list", "--config", str(cfg)], "ai_draft"),
        (["index", "rebuild", "--config", str(cfg)], "索引已写入"),
        (["recall", "--config", str(cfg), "--query", "checkpoint runtime"], "agent-runtime-checkpoint"),
        (
            ["project", "context", "my-first-agent", "--config", str(cfg), "--target", "claude-code"],
            "Project Context",
        ),
    ]

    for args, expected in checks:
        res = runner.invoke(app, args)
        assert res.exit_code == 0, f"{args}\n{res.output}"
        assert expected in res.output, f"{args}\n{res.output}"

    assert not (vault / ".mindforge").exists()
    assert (tmp_path / ".mindforge").exists()


def test_post_command_vault_works_through_real_cli_main(tmp_path: Path) -> None:
    """回归真实 CLI 入口：CliRunner(app) 会绕过 main()，这里用子进程覆盖 argv 归一化。"""
    vault, cfg = _copy_demo_vault(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mindforge.cli",
            "next",
            "--config",
            str(cfg),
            "--vault",
            str(vault),
            "--format",
            "json",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert str(vault) in result.stdout
