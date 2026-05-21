"""可执行 onboarding smoke：fixture vault 的测试路径不能回归。

只使用 examples/fixture-vault 的虚构资料；process smoke 通过显式 ``--profile fake``
在内存注入测试 provider，运行时产物写入 tmp_path。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()


def _copy_fixture_vault(tmp_path: Path) -> tuple[Path, Path]:
    src = Path("examples/fixture-vault")
    vault = tmp_path / "fixture-vault"
    shutil.copytree(src, vault)

    from mindforge.assets_runtime import bundled_text

    cfg = yaml.safe_load(bundled_text("configs", "mindforge.yaml"))
    cfg["vault"]["root"] = str(vault)
    # configs/mindforge.yaml 现在是 user-level override；测试只覆盖需要改写的
    # 用户字段，完整 state/logging 默认由 runtime defaults 合并。
    cfg.setdefault("state", {})["workdir"] = str(tmp_path / ".mindforge")
    cfg.setdefault("logging", {})["file"] = str(tmp_path / "mindforge.log")
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return vault, cfg_path


def test_fixture_vault_onboarding_smoke(tmp_path: Path, monkeypatch) -> None:
    vault, cfg = _copy_fixture_vault(tmp_path)

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("本地可用性 smoke 不应读取 .env")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)

    checks = [
        (["commands"], "命令地图"),
        (["next", "--config", str(cfg)], "MindForge next"),
        (["doctor", "--config", str(cfg)], "MindForge doctor"),
        (["scan", "--config", str(cfg)], "扫描完成"),
        # 旧 fixture 仍可覆盖内部兼容路径，但 smoke 输出不再把 profile 当成产品语义。
        (["process", "--config", str(cfg), "--profile", "fake", "--limit", "1"], "model setup"),
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
    vault, cfg = _copy_fixture_vault(tmp_path)
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


def test_packaged_default_assets_exist() -> None:
    """v0.5.2: package resources must contain the runtime defaults used by CLI."""
    root = files("mindforge.assets")
    for rel in (
        ("prompts", "triage", "v1.md"),
        ("prompts", "distill", "v1.md"),
        ("templates", "knowledge_card.md.j2"),
        ("configs", "learning_tracks.yaml"),
        ("configs", "mindforge.yaml"),
        ("fixtures", "sample_cubox_api_export.json"),
        ("examples", "fixture-vault", "README.md"),
    ):
        assert root.joinpath(*rel).is_file(), "/".join(rel)


def test_process_uses_packaged_assets_from_non_repo_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    """Packaged-like smoke: no repo-root prompts/templates are needed.

    The test changes cwd away from the repository and omits --prompts-dir,
    --tracks, and --template. If process still depended on Path("prompts") or
    Path("templates/..."), this would fail before writing a fake card.
    """
    _vault, cfg = _copy_fixture_vault(tmp_path)
    run_dir = tmp_path / "run-from-here"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)

    res = runner.invoke(app, ["process", "--config", str(cfg), "--profile", "fake", "--limit", "1"])
    assert res.exit_code == 0, res.output
    assert "processed=1" in res.output
    assert "Next: mindforge approve list" in res.output
    assert "explicit human approval" in res.output


def test_process_explicit_asset_paths_still_win(tmp_path: Path) -> None:
    """用户显式路径优先：v0.5.2 不能破坏自定义 prompt/template 实验。"""
    vault, cfg = _copy_fixture_vault(tmp_path)
    custom_template = tmp_path / "custom_card.md.j2"
    custom_template.write_text(
        "---\n"
        "id: {{ card.id }}\n"
        "title: \"CUSTOM {{ card.title }}\"\n"
        "status: ai_draft\n"
        "track: {{ card.track }}\n"
        "projects: []\n"
        "tags: []\n"
        "value_score: {{ card.value_score }}\n"
        "---\n\n"
        "CUSTOM TEMPLATE MARKER\n",
        encoding="utf-8",
    )

    res = runner.invoke(
        app,
        [
            "process",
            "--config",
            str(cfg),
            "--profile",
            "fake",
            "--limit",
            "5",  # v0.7.21: 默认只启用 plain_markdown，扫描整个 inbox，需要足够 limit 覆盖所有子目录
            "--prompts-dir",
            str(Path.cwd() / "prompts"),
            "--tracks",
            str(Path.cwd() / "configs" / "learning_tracks.yaml"),
            "--template",
            str(custom_template),
        ],
    )
    assert res.exit_code == 0, res.output
    written = list((vault / "20-Knowledge-Cards").rglob("*agent-runtime-checkpoint*.md"))
    assert any("CUSTOM TEMPLATE MARKER" in p.read_text(encoding="utf-8") for p in written)
