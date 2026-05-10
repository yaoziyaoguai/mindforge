"""LLM provider CLI diagnostics.

本模块只做 provider env presence 检查，不发 HTTP、不打印 secret value。
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from .cli_runtime import apply_provider_selection, console, load_cfg

llm_app = typer.Typer(
    add_completion=False,
    add_help_option=False,
    help="Internal model diagnostics; use Web Setup for product configuration.",
)

# ---------------------------------------------------------------------------
# llm ping — 只校验 active_profile 涉及的 env，不发 HTTP
# ---------------------------------------------------------------------------


@llm_app.command("ping")
def llm_ping(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Legacy alias for --provider；临时覆盖 provider。",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="高级临时覆盖 llm.active 指向的 provider。",
    ),
) -> None:
    """校验当前 active_profile 涉及的所有模型 env 是否齐全。

    本命令**不发任何 HTTP 请求**，不消耗配额。它只回答：
    - active_profile 涉及哪些 alias / provider / type / 真实 model 名
    - 每个模型需要哪些 env，是否已 set（不打印 value！只报告 set / unset）
    """
    import os
    cfg = load_cfg(config)
    cfg = apply_provider_selection(cfg, provider=provider, legacy_profile=profile)

    profile_map = cfg.llm.profiles[cfg.llm.active_profile]
    aliases_used = sorted(set(profile_map.values()))

    console.print(f"active_profile = [bold]{cfg.llm.active_profile}[/bold]")
    table = Table(title="LLM Provider 校验（不发 HTTP）", show_lines=True)
    table.add_column("alias")
    table.add_column("provider")
    table.add_column("type")
    table.add_column("model (resolved)")
    table.add_column("env required")
    table.add_column("env status")

    all_ok = True
    for alias in aliases_used:
        mc = cfg.llm.models[alias]
        actual_model = mc.model
        if mc.model_env and os.environ.get(mc.model_env):
            actual_model = os.environ[mc.model_env]

        env_reqs: list[tuple[str, str, bool]] = []
        if mc.base_url_env:
            env_reqs.append(("base_url", mc.base_url_env, not bool(mc.base_url)))
        if mc.api_key_env:
            env_reqs.append(("api_key", mc.api_key_env, not mc.api_key_optional))
        elif mc.type != "fake" and not mc.api_key_optional:
            # Web Setup 主路径把 key 存在 secret store，不写 api_key_env。
            # 本诊断不读取 secret 文件内容，只把缺少可验证凭证标成 required。
            env_reqs.append(("api_key", f"secret_store:{alias}", True))
        if mc.version_env:
            env_reqs.append(("version", mc.version_env, False))
        if mc.model_env:
            env_reqs.append(("model", mc.model_env, False))

        status_lines: list[str] = []
        for label, var, required in env_reqs:
            present = bool(os.environ.get(var))
            mark = "[green]set[/green]" if present else (
                "[red]MISSING[/red]" if required else "[yellow]unset (optional)[/yellow]"
            )
            status_lines.append(f"{label}={var} {mark}")
            if required and not present:
                all_ok = False

        env_required_summary = "\n".join(
            f"{lbl} ← {var}{' (required)' if req else ' (optional)'}"
            for lbl, var, req in env_reqs
        ) or "(none)"
        env_status_summary = "\n".join(status_lines) or "(none)"

        table.add_row(
            alias,
            mc.provider,
            mc.type,
            actual_model or "(empty)",
            env_required_summary,
            env_status_summary,
        )

    console.print(table)
    if all_ok:
        console.print("[green]✓ 所需 env 全部齐备；可以进行 smoke test。[/green]")
    else:
        console.print("[red]✗ 有必填 env 未设置。请在 .env 或 shell export 后重试。[/red]")
        raise typer.Exit(code=1)


# ===========================================================================
# M4 — review / recall / project memory
# ===========================================================================
#
# 设计原则（详见 README.md 的 review / recall 说明）：
# - 五个命令全部不调 LLM、不读 .env、不改源文件、不写 state.json
