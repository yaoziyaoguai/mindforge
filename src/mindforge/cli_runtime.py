"""CLI adapter runtime helpers.

中文学习型说明：这里是 Typer adapter 层的共享运行时边界，只放所有 CLI
命令都必须共用的入口能力：Console、配置加载、全局 vault override、
profile override 与 argv 归一化。它不是业务 ``utils/common`` 垃圾桶；
source / strategy / service / presenter 层都不应依赖本模块。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import typer
from rich.console import Console

from .app_context import AppContextError, load_app_config, resolve_user_source_path
from .config import MindForgeConfig, with_fake_llm_profile
from .env_loader import load_dotenv_silently

console = Console()


def global_vault_override() -> Path | None:
    """读取 CLI 入口设置的 vault override；不读取 `.env` 文件。"""
    import os as _os

    override = _os.environ.get("MINDFORGE_VAULT_OVERRIDE")
    if not override:
        return None
    return Path(override)


def load_cfg(config_path: Path, *, read_env: bool = True) -> MindForgeConfig:
    """CLI adapter 的统一配置入口。

    只有用户显式走需要真实 provider env 的 CLI 路径时才允许 ``read_env=True``；
    fake/safe 路径必须传 ``read_env=False``，从而保持 no API key required。

    中文学习型说明：config resolution 统一走 ``app_context.load_app_config``，
    它会按 --config > --workspace > cwd 向上查找 > 全局 active workspace 的
    优先级链解析。找不到时给出 workspace-aware 友好错误提示。

    当 ``--config`` 显式指定时，config_explicit=True 阻止 cwd vault 覆盖
    config 的 configured vault。
    """

    if read_env:
        load_dotenv_silently(Path.cwd())
    try:
        # cwd-first / vault-first 是 CLI 产品规则，不是 app_context 的偶然默认值。
        # 这里显式传入 Path.cwd()，确保 scan/process/library/approve/index/recall
        # 等共享入口都用同一个 active-vault 解析边界。
        config_explicit = (config_path != Path("configs/mindforge.yaml"))
        return load_app_config(
            config_path,
            vault_override=global_vault_override(),
            cwd=Path.cwd(),
            config_explicit=config_explicit,
        )
    except AppContextError as e:
        if e.kind in {"no_workspace", "stale_workspace", "missing_config", "invalid_workspace"}:
            console.print(f"[red]✗ {e}[/red]")
            raise typer.Exit(code=2) from e
        console.print(f"[red]✗ 配置错误：{e}[/red]")
        console.print(
            "[dim]提示：请检查 vault.root、sources.enabled、llm.active "
            "三个字段是否合法。[/dim]"
        )
        raise typer.Exit(code=2) from e


def active_vault_resolution_notice(cfg: MindForgeConfig) -> str | None:
    """返回 active vault / project root / config path 的用户可读说明。

    中文学习型说明：active vault 决策是产品语义，不只是路径工具函数。
    这里只展示“本次正在用什么”，configured vault 只在确实不同且只是 fallback
    candidate 时以说明文字出现，避免用户误以为命令写到了 configured vault。
    JSON 命令不要调用本函数的渲染包装，避免污染机器可读输出。
    """

    active_meta = (
        cfg.raw.get("_mindforge_active_vault", {})
        if isinstance(cfg.raw, dict)
        else {}
    )
    project_meta = (
        cfg.raw.get("_mindforge_project", {})
        if isinstance(cfg.raw, dict)
        else {}
    )
    if not isinstance(active_meta, dict):
        return None
    lines = [
        f"project root: {project_meta.get('root') or '(none detected)'}",
        f"config path : {project_meta.get('config_path') or '(bundled/default)'}",
        f"active vault: {active_meta.get('root') or cfg.vault.root}",
        f"vault source: {active_meta.get('reason') or 'configured vault'}",
    ]
    if active_meta.get("configured_differs"):
        lines.append(
            "configured vault is fallback candidate only: "
            f"{active_meta.get('configured_root') or '(unknown)'}"
        )
    return "\n".join(lines)


def render_active_vault_resolution_notice(cfg: MindForgeConfig) -> None:
    """在 human CLI 输出中打印 active-vault 选择提示。"""

    notice = active_vault_resolution_notice(cfg)
    if notice:
        console.print(notice, markup=False, style="dim", soft_wrap=True)


def render_source_path_not_found(resolution) -> None:
    """展示用户 source path 解析失败；不读取文件内容、不碰 `.env`。"""

    console.print(f"File not found: {resolution.original}", markup=False, style="red", soft_wrap=True)
    console.print(f"cwd: {resolution.cwd}", markup=False, soft_wrap=True)
    console.print(
        f"project root: {resolution.project_root or '(none detected)'}",
        markup=False,
        soft_wrap=True,
    )
    console.print(f"active vault: {resolution.active_vault}", markup=False, soft_wrap=True)
    console.print("tried candidates:", markup=False)
    for candidate in resolution.tried:
        console.print(f"  - {candidate}", markup=False, soft_wrap=True)
    console.print(
        "Hint: cd to the MindForge project root, pass an absolute path, or use --vault for the target vault.",
        markup=False,
        soft_wrap=True,
    )


def resolve_source_path_for_cli(cfg: MindForgeConfig, target: Path) -> Path:
    """CLI 统一 source path 解析入口；失败时打印定位信息并以 code=2 退出。

    中文学习型说明：import/watch 的业务 service 不应该理解用户 shell cwd、
    project root 或 active vault。CLI adapter 在这里把用户输入收敛成绝对路径，
    后续 pipeline 只处理明确存在的 source。
    """

    project_meta = cfg.raw.get("_mindforge_project", {}) if isinstance(cfg.raw, dict) else {}
    project_root = (
        Path(str(project_meta["root"]))
        if isinstance(project_meta, dict) and project_meta.get("root")
        else None
    )
    resolution = resolve_user_source_path(
        target,
        cwd=Path.cwd().resolve(),
        project_root=project_root,
        active_vault=cfg.vault.root,
    )
    if resolution.source == "not_found":
        render_source_path_not_found(resolution)
        raise typer.Exit(code=2)
    return resolution.resolved


def override_active_profile(
    cfg: MindForgeConfig, profile: str | None
) -> MindForgeConfig:
    """如果 CLI 传了 --profile，就基于现有 cfg 派生一份临时 LLMConfig。"""

    if not profile:
        return cfg
    if profile == "fake" and profile not in cfg.llm.profiles:
        # 中文学习型说明：fake 现在是 dev/offline 兼容能力，不再写在用户默认配置里。
        # ``--profile fake`` 仍可显式触发，但只在内存中注入，避免污染 YAML / Setup。
        return replace(cfg, llm=with_fake_llm_profile(cfg.llm))
    if profile not in cfg.llm.profiles:
        console.print(
            f"[red]--profile {profile!r} 不在 llm.profiles 中；"
            f"已知：{sorted(cfg.llm.profiles)}[/red]"
        )
        raise typer.Exit(code=2)
    new_llm = replace(cfg.llm, active_profile=profile)
    return replace(cfg, llm=new_llm)


def apply_provider_selection(
    cfg: MindForgeConfig,
    *,
    provider: str | None,
    legacy_profile: str | None,
) -> MindForgeConfig:
    """应用本次命令的 provider 选择，保持 CLI adapter 边界集中。

    中文学习型说明：产品主路径是 ``llm.active``；``--provider`` 只是临时覆盖；
    ``--profile`` 继续作为 legacy alias。这里统一把三者收敛到现有
    ``LLMConfig.active_profile``，避免 watch/import/process 各自复制选择逻辑。
    """

    selected = provider or legacy_profile
    source = "--provider" if provider else ("legacy --profile" if legacy_profile else "llm.active")
    if not selected:
        # 中文学习型说明：当用户尚未配置任何真实模型（default_model=None、
        # models={}）时，自动注入 fake profile，使 "安全模式：本地模拟" 成为
        # 真正的零配置 demo 体验。fake models 仅在内存中注入，不会写入 YAML
        # 或污染 Setup 主 UI。用户配置真实模型后 fake 自动退出。
        if cfg.llm.default_model is None and not cfg.llm.models:
            safe_llm = with_fake_llm_profile(cfg.llm)
            return replace(
                cfg,
                llm=safe_llm,
                raw={
                    **cfg.raw,
                    "_mindforge_provider_selection": {
                        "selected": "fake",
                        "source": f"auto-fallback ({source} — no models configured)",
                    },
                },
            )
        return replace(
            cfg,
            raw={
                **cfg.raw,
                "_mindforge_provider_selection": {
                    "selected": cfg.llm.active_profile,
                    "source": source,
                },
            },
        )
    if selected == "fake" and selected not in cfg.llm.profiles:
        # fake provider 只服务显式 dev/offline 命令；不作为 configured model 暴露。
        safe_llm = with_fake_llm_profile(cfg.llm)
        return replace(
            cfg,
            llm=safe_llm,
            raw={
                **cfg.raw,
                "_mindforge_provider_selection": {
                    "selected": selected,
                    "source": source,
                },
            },
        )
    if selected not in cfg.llm.profiles:
        option = "--provider" if provider else "--profile"
        noun = "llm.providers" if provider else "llm.profiles"
        console.print(
            f"[red]{option} {selected!r} 不在 {noun} 中；"
            f"已知：{sorted(cfg.llm.profiles)}[/red]"
        )
        raise typer.Exit(code=2)
    if provider and legacy_profile and provider != legacy_profile:
        console.print(
            f"[yellow]provider selection: using --provider {provider!r}; "
            f"legacy --profile {legacy_profile!r} ignored.[/yellow]",
            markup=False,
        )
    new_llm = replace(cfg.llm, active_profile=selected)
    return replace(
        cfg,
        llm=new_llm,
        raw={
            **cfg.raw,
            "_mindforge_provider_selection": {
                "selected": selected,
                "source": source,
            },
        },
    )


_COMMANDS_WITH_LOCAL_VAULT_OPTION = {"init", "obsidian", "setup"}


def normalize_post_command_global_options(argv: list[str]) -> list[str]:
    """把后置 ``--vault`` / ``--workspace`` 归一化为 Typer 全局参数位置。

    ``init`` / ``obsidian`` / ``config init`` 拥有自己的局部 ``--vault``
    语义，不能搬动；其他命令的 ``--vault`` / ``--workspace`` 表示全局 override。
    """

    if len(argv) < 3:
        return argv

    option_takes_value = {
        "--config", "-c", "--vault", "--workspace", "-w", "--obsidian-vault",
    }
    command_idx: int | None = None
    i = 1
    while i < len(argv):
        token = argv[i]
        if token == "--":
            return argv
        if token.startswith("-"):
            if token in option_takes_value and i + 1 < len(argv):
                i += 2
                continue
            i += 1
            continue
        command_idx = i
        break

    if command_idx is None:
        return argv
    nested_command = next(
        (a for a in argv[command_idx + 1:] if not a.startswith("-")),
        "",
    )
    if (
        argv[command_idx] in _COMMANDS_WITH_LOCAL_VAULT_OPTION
        or (argv[command_idx] == "config" and nested_command == "init")
    ):
        return argv

    # 可搬动的全局选项及其带值形式
    global_options_with_value = {"--vault", "--workspace"}
    moved: list[str] = []
    rest: list[str] = []
    i = 1
    while i < len(argv):
        token = argv[i]
        if i <= command_idx:
            rest.append(token)
            i += 1
            continue
        if token in global_options_with_value and i + 1 < len(argv):
            moved.extend([token, argv[i + 1]])
            i += 2
            continue
        for opt in global_options_with_value:
            if token.startswith(f"{opt}="):
                moved.extend([opt, token.split("=", 1)[1]])
                i += 1
                break
        else:
            rest.append(token)
            i += 1

    if not moved:
        return argv
    return [argv[0], *moved, *rest]
