"""``mindforge provider`` 子命令 — fake-default + real-opt-in CLI 表面。

为什么单独一个 provider_cli 模块?
=================================

``cli.py`` 已经接近 5000 行, 我们坚持不重构、不大改; 同时 readiness /
smoke 这一组命令逻辑高度内聚, 适合放在独立文件中, 仅以最小 glue
(``app.add_typer``) 接入主 CLI。模式与 ``obsidian_cli`` / ``cubox_cli``
一致。

本模块的硬边界
==============

- **只** import ``provider_readiness`` / ``real_smoke`` / ``config``
  / ``app_context``;
- **不** import ``approval_service`` / ``writer`` / ``cards`` /
  ``obsidian*`` / ``cubox*`` / ``scanner``;
- 命令默认安全 (拒绝运行真实 smoke, 不打印 secret);
- 所有命令 exit code 0, 错误状态写入输出而非异常退出 — 便于脚本化
  集成与 dry-run 测试。
"""

from __future__ import annotations

from pathlib import Path

import typer

from .app_context import load_app_config
from .provider_readiness import build_readiness_report, render_readiness_report
from .real_smoke import run_synthetic_real_smoke

provider_app = typer.Typer(
    add_completion=False,
    help=(
        "Provider readiness & synthetic smoke (fake-default, real-opt-in). "
        "无 secret 打印; 默认绝不触发真实 LLM。"
    ),
)


@provider_app.command("readiness")
def provider_readiness_cmd(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="MindForge 配置文件路径",
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="输出格式: 'text' (人类可读, 默认) 或 'json' (脚本化消费)",
    ),
) -> None:
    """打印 provider readiness 报告 (无网络, 无 secret 打印)。"""
    app_cfg = load_app_config(config)
    report = build_readiness_report(app_cfg.llm)
    if output_format == "json":
        import json
        # JSON 模式仍然不含任何 env value; 只是把同一 dict 序列化, 便于
        # 脚本/CI 集成 (例如 "doctor" check 解析 opt_in_state 字段)。
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif output_format == "text":
        typer.echo(render_readiness_report(report))
    else:
        typer.echo(
            f"unknown --format {output_format!r}; expected 'text' or 'json'",
            err=True,
        )
        raise typer.Exit(code=2)


@provider_app.command("smoke")
def provider_smoke_cmd(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="MindForge 配置文件路径",
    ),
    allow_real: bool = typer.Option(
        False,
        "--allow-real",
        help=(
            "显式 opt-in 触发真实 provider 调用; 默认 False。"
            "未传时永远拒绝运行并打印拒绝原因。"
        ),
    ),
    alias: str = typer.Option(
        None,
        "--alias",
        help="指定 active profile 中的 alias; 默认取第一个非 fake alias",
    ),
) -> None:
    """运行 synthetic real-LLM smoke (gated by --allow-real)。

    无论运行与否, 输出都是 audit-trail 摘要, 不包含 secret value,
    不写入任何文件, ``human_approved`` 永远为 False。
    """
    app_cfg = load_app_config(config)
    result = run_synthetic_real_smoke(
        app_cfg.llm,
        allow_real=allow_real,
        alias=alias,
    )
    typer.echo("MindForge synthetic real-LLM smoke")
    typer.echo("=" * 40)
    typer.echo(f"ran                   : {result['ran']}")
    typer.echo(f"opt_in_state          : {result['opt_in_state']}")
    typer.echo(f"provider_type         : {result['provider_type']}")
    typer.echo(f"alias                 : {result['alias']}")
    typer.echo(f"output_artifact       : {result['output_artifact']}")
    typer.echo(f"human_approved        : {result['human_approved']}")
    typer.echo(f"written               : {result['written']}")
    typer.echo(f"synthetic_input_only  : {result['synthetic_input_only']}")
    if result["blocker"]:
        typer.echo(f"blocker               : {result['blocker']}")
    if result["output_excerpt_safe"]:
        typer.echo("")
        typer.echo("Output excerpt (scrubbed, truncated):")
        typer.echo(result["output_excerpt_safe"])


__all__ = ["provider_app"]
