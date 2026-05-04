"""Safe dogfooding CLI adapter.

Dogfood 命令只渲染 runbook、做静态 preflight 或 readiness presence check；
不执行真实 Cubox / LLM / Obsidian write。
"""
from __future__ import annotations

from pathlib import Path

import typer

from .app_context import load_app_config
from .cli_runtime import console


dogfood_app = typer.Typer(add_completion=False, help="非敏感本地 dogfooding 计划与 checklist")

@dogfood_app.command("plan")
def dogfood_plan(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="非敏感 disposable vault 副本路径；省略时使用全局 --vault 或 examples/demo-vault",
    ),
) -> None:
    """输出非敏感 dogfooding 命令路径；不执行、不读 .env、不写 vault。

    中文学习型说明：这是 checklist/命令导航层，不是自动化 runner。真实
    dogfooding 必须由用户拿可丢弃副本逐条执行，避免工具误改正式资料。
    """
    import os as _os

    chosen = vault or Path(_os.environ.get("MINDFORGE_VAULT_OVERRIDE", "examples/demo-vault"))
    console.print("[bold]MindForge non-sensitive dogfooding plan[/bold]")
    console.print(f"vault copy: {chosen}")
    print("Safety: disposable non-sensitive copy only; no .env, no real LLM, no Obsidian formal-note writes.")
    console.print("[bold]Commands[/bold]")
    for command, note in _dogfood_command_snippets(chosen):
        print(f"- {command}")
        print(f"  {note}")
    console.print("Checklist: docs/templates/NON_SENSITIVE_DOGFOODING_CHECKLIST.md", markup=False)


def _dogfood_command_snippets(vault: Path) -> list[tuple[str, str]]:
    """集中维护 dogfooding 命令，供 CLI 与测试共同使用，减少文档漂移。"""
    v = str(vault)
    return [
        (f"mindforge doctor --vault {v} --paths", "确认本地路径和安全边界"),
        (f"mindforge scan --vault {v}", "扫描非敏感 inbox"),
        (f"mindforge process --profile fake --limit 1 --vault {v}", "只用 fake provider 生成 ai_draft"),
        (f"mindforge approve list --vault {v}", "查看待人工批准草稿"),
        (f"mindforge approve show --card <card-path> --vault {v}", "预览单张草稿安全摘要"),
        (f"mindforge recall --query \"agent\" --vault {v}", "检索 human_approved knowledge"),
        (f"mindforge review weekly --vault {v}", "生成本周学习任务"),
        (f"mindforge backup export --vault {v} --output-dir /tmp/mindforge-backup", "导出安全备份"),
        (f"mindforge obsidian stage --vault {v} --source <note.md> --dry-run", "只预览 staging，不写正式 notes"),
        (f"mindforge today --vault {v}", "回到每日入口检查下一步"),
    ]


@dogfood_app.command("preflight")
def dogfood_preflight(
    input_path: Path = typer.Argument(
        ...,
        help=(
            "要 dogfood 的输入路径; 不会被读取或遍历, 只做静态分类。"
            "推荐 examples/demo-vault 下的 synthetic 路径。"
        ),
    ),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="MindForge 配置文件路径",
    ),
    declare_non_sensitive: bool = typer.Option(
        False,
        "--declare-non-sensitive",
        help=(
            "用户明确声明此路径为 non-sensitive local 数据 (非 home / "
            "非 Obsidian vault / 非真实 Cubox dump); 由用户为该声明负责。"
        ),
    ),
    allow_real: bool = typer.Option(
        False,
        "--allow-real",
        help="opt-in 校验真实 LLM 路径是否就绪 (不发起任何调用)",
    ),
) -> None:
    """v0.13 Stage 4 — 静态 dogfood preflight; 只做分类决策, 不读 input。

    中文学习型说明: 这是一个**纯静态**的安全闸门。它不会列举 input
    目录、不会读取任何文件、不会调用 LLM、不会写 vault。它只回答:
    "如果你现在以这条 path + 这组开关跑 dogfood, 是否安全。" 真正的
    执行仍由用户走 ``dogfood plan`` 中列出的命令逐条手动触发。
    """
    from .dogfood_safety import build_preflight_report, render_preflight_report
    from .env_loader import load_dotenv_silently

    load_dotenv_silently(Path.cwd())
    app_cfg = load_app_config(config)
    report = build_preflight_report(
        input_path,
        declared_non_sensitive=declare_non_sensitive,
        allow_real=allow_real,
        llm_config=app_cfg.llm,
    )
    print(render_preflight_report(report))
    if not report["decision"]["allowed"]:
        raise typer.Exit(code=2)


@dogfood_app.command("cubox-readiness")
def dogfood_cubox_readiness(
    token_env: str = typer.Option(
        "MINDFORGE_CUBOX_TOKEN",
        "--token-env",
        help=(
            "Cubox API token 环境变量名 (presence-only 检查; 永不打印 value)。"
            "默认 MINDFORGE_CUBOX_TOKEN; 用户可显式传任意名字。"
        ),
    ),
    allow_real: bool = typer.Option(
        False,
        "--allow-real",
        help=(
            "opt-in 校验未来 G1 真实 Cubox HTTP 路径解锁条件 (不发起任何调用)。"
            "G1 在本仓库内仍然 future-gated; 此命令永远不会真实拉取 Cubox。"
        ),
    ),
) -> None:
    """Cubox 真实路径 readiness 诊断 — presence-only, 不联网, 永不打印 token。

    中文学习型说明: 这是 readiness 报告, 不是真实拉取入口。它只回答:
    "如果你想用真实 Cubox 路径, 你的 env / 配置是否就绪。" 真实 dogfood
    数据路径 (今天就能跑) 是 ``mindforge cubox dry-run --export <file.json>``
    —— 用 Cubox web Settings → Export 导出的官方 JSON 文件做完全离线
    的预检 + ai_draft 生成, 不需要 token, 不联网。真实 HTTP API 路径
    被 future G1 gate 把守, 永远不会被本命令自动触发。
    """
    from .cubox_readiness import (
        classify_cubox_real_opt_in,
        inspect_cubox_config,
        render_cubox_readiness_report,
    )

    report = inspect_cubox_config(token_env_var=token_env)
    classification = classify_cubox_real_opt_in(report, allow_real=allow_real)
    print(render_cubox_readiness_report(report, classification))


@dogfood_app.command("quickstart")
def dogfood_quickstart(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help=(
            "项目专用 / demo vault 路径; 省略时使用 examples/demo-vault。"
            "新用户应**只**指定项目专用 vault, 永不指定真实 home Obsidian vault。"
        ),
    ),
    cubox_export: Path | None = typer.Option(
        None,
        "--cubox-export",
        help=(
            "可选: 本地 Cubox JSON export 文件路径 (Cubox web → Settings → "
            "Export 导出); 命令只渲染建议命令, 不读取该文件。"
        ),
    ),
) -> None:
    """新用户 10 分钟跑通 MindForge 的 quickstart 命令导航 (不执行命令)。

    中文学习型说明: 这是 **runbook 渲染器**, 不是自动化 runner。它列
    出新用户从安装 → fake provider smoke → Cubox JSON export 预检 →
    ai_draft → Obsidian 项目 vault dry-run 的完整路径, 让用户自己复制
    粘贴执行, 避免工具误改正式资料。永不调用真实 LLM / Cubox API /
    Obsidian write / human_approved 路径。
    """
    import os as _os

    chosen_vault = vault or Path(
        _os.environ.get("MINDFORGE_VAULT_OVERRIDE", "examples/demo-vault")
    )
    print("MindForge real dogfooding quickstart (read-only runbook)")
    print("=========================================================")
    print(f"vault: {chosen_vault}")
    if cubox_export:
        print(f"cubox export: {cubox_export}")
    print("")
    print("Safety: this command renders commands only; it does NOT execute")
    print("them. Commands below stay on the fake-default + dry-run path.")
    print("No .env content is read. No token is printed. No real LLM is")
    print("called. No formal Obsidian write. No human_approved is produced.")
    print("")
    print("Steps:")
    for idx, (command, note) in enumerate(
        _dogfood_quickstart_steps(chosen_vault, cubox_export), start=1
    ):
        print(f"  {idx:>2}. {command}")
        print(f"      {note}")
    print("")
    print("Limits: start with --limit 5; never exceed --limit 20 first run;")
    print("        no full Cubox sync exists — JSON export is opt-in per item.")
    print("Rollback: every step above is dry-run by default; obsidian stage")
    print("        --write only touches <vault>/staging/. Use a disposable")
    print("        project vault (cp -r examples/demo-vault /tmp/dogfood-vault).")
    print("Token: Cubox API token is a secret. Never paste, never commit,")
    print("        never print. cubox-readiness only ever returns a bool.")
    print("")
    print("Full guide: docs/REAL_DOGFOOD_QUICKSTART.md")


def _dogfood_quickstart_steps(
    vault: Path, cubox_export: Path | None
) -> list[tuple[str, str]]:
    """集中维护 quickstart 命令, 供 CLI 与测试共同使用, 减少文档漂移。

    Cubox 步骤分两条路径:
    - 用户提供 ``--cubox-export`` 时, 给出针对该文件的具体命令;
    - 否则给出"如何从 Cubox web 导出"的提示 + 通用占位命令。
    """
    v = str(vault)
    cubox_path = str(cubox_export) if cubox_export else "<file.json>"
    cubox_hint = (
        "替换 <file.json> 为 Cubox web → Settings → Export 导出的 JSON 文件"
        if cubox_export is None
        else "已使用你提供的 Cubox export 文件"
    )
    return [
        (
            "mindforge doctor --paths",
            "确认本地路径与安全边界 (确认 active_profile=fake)",
        ),
        (
            "mindforge provider readiness --config configs/mindforge.yaml",
            "确认 LLM provider 是 fake-default; api_key value 永不打印",
        ),
        (
            "mindforge dogfood cubox-readiness --token-env MINDFORGE_CUBOX_TOKEN",
            "确认 Cubox 真实路径 readiness; 不联网, 不打印 token",
        ),
        (
            f"mindforge cubox dry-run --export {cubox_path}",
            f"Cubox JSON export 离线预检 (真实数据, 零网络)。{cubox_hint}",
        ),
        (
            f"mindforge cubox preview-ai-draft --export {cubox_path} --limit 5",
            "对前 5 条用 fake provider 生成 ai_draft (review-only; 永远不要 --limit > 20 第一次跑)",
        ),
        (
            "mindforge dogfood preflight examples/demo-vault --declare-non-sensitive",
            "静态 dogfood 路径分类; 不读输入, 不调 LLM, 不写 vault",
        ),
        (
            f"mindforge obsidian doctor --vault {v}",
            "确认项目 vault 安全 (only the path you pass, no home scan)",
        ),
        (
            f"mindforge obsidian scan --vault {v} --limit 5",
            "扫描项目 vault 中的非敏感 Markdown",
        ),
        (
            f"mindforge obsidian stage --vault {v} --source <note.md> --dry-run",
            "项目 vault staging dry-run (默认 --dry-run; --write 才真写)",
        ),
        (
            "mindforge approve list",
            "查看待人工 approve 的 ai_draft (永远只能由 approver.approve_card 晋升)",
        ),
    ]
