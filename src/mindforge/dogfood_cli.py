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


@dogfood_app.command("init-demo")
def dogfood_init_demo(
    target: Path = typer.Option(
        ...,
        "--target",
        help="要创建的 disposable demo vault 目录；已存在时默认拒绝覆盖。",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="显式覆盖已存在的 --target。只删除 target 本身，不扫描其它目录。",
    ),
) -> None:
    """从 package assets 创建安装态可用的 disposable demo vault。

    中文学习型说明：这是安装态 dogfood 的 bootstrap 命令，不是业务管线。
    它只复制 MindForge 自带的虚构 demo vault 到用户指定目标；不读取真实
    vault、不读 `.env`、不调 LLM/Cubox API、不写 human_approved。
    """
    from .demo_assets import init_demo_vault

    try:
        result = init_demo_vault(target, force=force)
    except FileExistsError:
        console.print(f"target already exists: {target}", markup=False)
        console.print(
            "Next: choose a new --target, delete the disposable directory, or rerun with --force.",
            markup=False,
        )
        raise typer.Exit(code=2) from None

    t = result.target
    console.print("[bold]MindForge demo vault initialized[/bold]")
    print(f"target       : {t}")
    print(f"files_copied : {result.files_copied}")
    print("safety       : packaged fictional demo data only; no .env, no LLM, no approve")
    print("")
    print("Next:")
    print(f"  mindforge dogfood readiness --vault {t}")
    print(f"  mindforge dogfood quickstart --vault {t}")
    print(f"  mindforge doctor --vault {t}")
    print(f"  rm -rf {t}")


@dogfood_app.command("plan")
def dogfood_plan(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="非敏感 disposable vault 副本路径；省略时使用全局 --vault 或 /tmp/dogfood-vault",
    ),
) -> None:
    """输出非敏感 dogfooding 命令路径；不执行、不读 .env、不写 vault。

    中文学习型说明：这是 checklist/命令导航层，不是自动化 runner。真实
    dogfooding 必须由用户拿可丢弃副本逐条执行，避免工具误改正式资料。
    """
    import os as _os

    chosen = vault or Path(_os.environ.get("MINDFORGE_VAULT_OVERRIDE", "/tmp/dogfood-vault"))
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
            "安装态推荐先运行 `mindforge dogfood init-demo --target /tmp/dogfood-vault`。"
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


@dogfood_app.command("readiness")
def dogfood_readiness(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help=(
            "项目专用 / disposable vault 路径; 省略时使用 /tmp/dogfood-vault。"
            "本命令只做静态路径分类, 不读取 vault 内容。"
        ),
    ),
    cubox_export: Path | None = typer.Option(
        None,
        "--cubox-export",
        help="可选 Cubox JSON export 路径; 只检查路径是否存在, 不读取文件内容。",
    ),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="MindForge 配置文件路径",
    ),
    declare_non_sensitive: bool = typer.Option(
        True,
        "--declare-non-sensitive/--no-declare-non-sensitive",
        help="声明 --vault 是项目专用 / 非敏感 disposable 副本; 默认开启。",
    ),
) -> None:
    """汇总 dogfood 前置安全状态；只读报告，不执行任何 dogfood 步骤。

    中文学习型说明：这是 `demo` 和 `quickstart` 中间的产品化检查点。
    它回答“我现在这条 vault / export / provider 状态是否适合复制
    quickstart 命令”，但绝不读取 `.env`、不读取 Cubox export 内容、
    不调用真实 LLM/Cubox API、不写 vault、不 approve。
    """
    import os as _os

    from .dogfood_safety import (
        dogfood_readiness_report,
        render_dogfood_readiness_report,
    )

    chosen_vault = vault or Path(
        _os.environ.get("MINDFORGE_VAULT_OVERRIDE", "/tmp/dogfood-vault")
    )
    app_cfg = load_app_config(config)
    report = dogfood_readiness_report(
        vault=chosen_vault,
        cubox_export=cubox_export,
        declared_non_sensitive=declare_non_sensitive,
        llm_config=app_cfg.llm,
    )
    print(render_dogfood_readiness_report(report))
    if not report["decision"]["ready"]:
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
            "项目专用 / demo vault 路径; 省略时使用 /tmp/dogfood-vault。"
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
        _os.environ.get("MINDFORGE_VAULT_OVERRIDE", "/tmp/dogfood-vault")
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
    print("        project vault:")
    print("        mindforge dogfood init-demo --target /tmp/dogfood-vault")
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
            f"mindforge dogfood readiness --vault {v}"
            + (f" --cubox-export {cubox_path}" if cubox_export else ""),
            "一条命令确认 vault/provider/export 是否适合复制本 runbook (只读; 不读 export 内容)",
        ),
        (
            f"mindforge doctor --vault {v} --paths",
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
            f"mindforge dogfood preflight {v} --declare-non-sensitive",
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
            f"mindforge approve list --vault {v}",
            "查看待人工 approve 的 ai_draft (永远只能由 approver.approve_card 晋升)",
        ),
    ]
