"""Init / config / setup CLI adapters.

本模块负责本地配置和 vault 骨架初始化。它不读取 .env、不调用 provider，
只复制 package assets 并在用户显式选项下改写安全配置字段。
"""
from __future__ import annotations

from pathlib import Path

import typer

from . import init_presenter as _ip
from .app_context import AppContextError, load_app_config
from .cli_runtime import console, global_vault_override, load_cfg
from .config import ConfigError, MindForgeConfig, load_mindforge_config
from .presenters.local_status import (
    render_config_status,
    render_friendly_error,
    render_status_json,
)
from .services.local_status import build_local_status_snapshot, friendly_config_error
from .presenters.doctor import doctor_icon as _doctor_icon
from .services.doctor import config_doctor_rows as _svc_config_doctor_rows

init_config_app = typer.Typer(add_completion=False)
config_app = typer.Typer(add_completion=False, help="本地配置 / setup 诊断（safe-by-default）")


def _bundled_repo_root() -> Path:
    # v0.5.2：init 的默认 configs 来自 package assets，而不是仓库根。
    # 真实 dogfood 后，init 只复制 mindforge.yaml；learning tracks 等仍作为
    # package 内置资产被 process 使用。vault 目录骨架仍由 VAULT_DIRS
    # 显式创建，不依赖 repo-root vault_template。
    from .assets_runtime import bundled_asset_path_for_process

    return bundled_asset_path_for_process()


def _resolve_non_interactive_vault(vault: Path | None, project_root: Path) -> Path:
    if vault is not None:
        return vault.expanduser().resolve()
    cfg_path = project_root / "configs" / "mindforge.yaml"
    if cfg_path.exists():
        try:
            cfg = load_mindforge_config(cfg_path)
            return cfg.vault.root
        except ConfigError:
            return (project_root / "vault").resolve()
    return (project_root / "vault").resolve()


def _interactive_init_choices(*, project_root: Path, repo_root: Path, vault_dirs: tuple[str, ...]) -> tuple[Path, bool, str]:
    default_vault = Path("~/MindForgeVault").expanduser()
    profile_names = _available_profile_names(project_root, repo_root)
    default_profile = "fake" if "fake" in profile_names else (profile_names[0] if profile_names else "fake")
    console.print("[bold]MindForge init --interactive[/bold]")
    console.print("[dim]说明：telemetry 只写本地文件，不上传；init 不读取 .env、不调用 LLM。[/dim]")
    console.print(
        f"[dim]已注册 profile：{', '.join(profile_names) if profile_names else '(未能读取，默认 fake)'}[/dim]"
    )
    try:
        target_vault = _prompt_interactive_vault(default_vault=default_vault, vault_dirs=vault_dirs)
        telemetry_enabled = typer.confirm(
            "启用本地 telemetry？（仅写 .mindforge/telemetry.jsonl，不上传）",
            default=True,
        )
        console.print(
            "[yellow]提示：真实 provider 需要单独配置 .env；MindForge init 不会读取 .env。[/yellow]"
        )
        active_profile = _prompt_interactive_profile(
            default_profile=default_profile,
            profile_names=profile_names,
        )
        return target_vault, telemetry_enabled, active_profile
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]已中断；尚未写入任何文件。[/yellow]")
        raise typer.Exit(code=130) from None
    except typer.Abort:
        console.print("\n[yellow]已中断；尚未写入任何文件。[/yellow]")
        raise typer.Exit(code=130) from None


def _prompt_interactive_vault(*, default_vault: Path, vault_dirs: tuple[str, ...]) -> Path:
    vault_text = typer.prompt("vault 路径", default=str(default_vault)).strip()
    if not vault_text:
        console.print("[red]✗ vault 路径不能为空。请重新运行 init --interactive。[/red]")
        raise typer.Exit(code=2)
    target_vault = Path(vault_text).expanduser().resolve()
    _validate_interactive_vault_target(target_vault, vault_dirs)
    return target_vault


def _prompt_interactive_profile(*, default_profile: str, profile_names: list[str]) -> str:
    profile_text = typer.prompt("active_profile", default=default_profile).strip()
    if not profile_text:
        console.print("[red]✗ active_profile 不能为空。[/red]")
        raise typer.Exit(code=2)
    if profile_names and profile_text not in profile_names:
        console.print(
            f"[red]✗ active_profile={profile_text!r} 不在已注册 profile 中：{profile_names}[/red]"
        )
        raise typer.Exit(code=2)
    return profile_text


def _print_init_plan(
    *,
    plan,
    force: bool,
    dry_run: bool,
    interactive: bool,
    telemetry_enabled: bool | None,
    active_profile: str | None,
) -> None:
    for line in _ip.format_plan_header(plan):
        console.print(line)
    for line in _ip.format_mode_lines(force=force, dry_run=dry_run, interactive=interactive):
        console.print(line)
    for line in _ip.format_interactive_summary(
        interactive=interactive,
        telemetry_enabled=telemetry_enabled,
        active_profile=active_profile,
    ):
        console.print(line)
    console.print(_ip.format_plan_summary(plan.summary()))


def _execute_init_plan(
    *,
    plan,
    project_root: Path,
    telemetry_enabled: bool | None,
    active_profile: str | None,
) -> None:
    from .init_cmd import execute_plan, next_steps_hint

    actions = execute_plan(plan)
    for line in actions:
        console.print(_ip.format_execute_action(line))

    cfg_dst = (project_root / "configs" / "mindforge.yaml").resolve()
    _rewrite_init_config(
        cfg_dst,
        vault_root=plan.vault_root,
        telemetry_enabled=telemetry_enabled,
        active_profile=active_profile,
    )

    for line in _ip.format_next_steps(next_steps_hint()):
        console.print(line)
    console.print(_ip.format_safety_footer())


@init_config_app.command()
def init(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="目标 vault 根目录（默认：当前 mindforge.yaml 中 vault.root；"
        "若不存在则用 ./vault）",
    ),
    project_root: Path = typer.Option(
        Path("."),
        "--project-root",
        help="MindForge 工作目录（configs/ 与 .env.example 落在这里；默认当前目录）",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="覆写 MindForge 提供的模板配置文件（**不**会覆写用户数据目录）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="只打印 plan，不写文件",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="交互式初始化：选择 vault 路径、telemetry、本次 active_profile",
    ),
) -> None:
    """初始化最小可用的 vault 骨架与配置文件。

    幂等保证：多次运行不会重复创建已存在的目录或覆盖用户文件；只有 ``--force``
    才允许覆写 MindForge 自带的模板。
    """
    from .init_cmd import VAULT_DIRS, build_plan

    repo_root = _bundled_repo_root()
    project_root = project_root.resolve()

    if interactive:
        target_vault, interactive_telemetry_enabled, interactive_active_profile = (
            _interactive_init_choices(
                project_root=project_root,
                repo_root=repo_root,
                vault_dirs=VAULT_DIRS,
            )
        )
    else:
        target_vault = _resolve_non_interactive_vault(vault, project_root)
        interactive_telemetry_enabled = None
        interactive_active_profile = None

    plan = build_plan(
        target_vault, project_root=project_root, repo_root=repo_root, force=force
    )
    _print_init_plan(
        plan=plan,
        force=force,
        dry_run=dry_run,
        interactive=interactive,
        telemetry_enabled=interactive_telemetry_enabled,
        active_profile=interactive_active_profile,
    )

    if dry_run:
        for item in plan.items:
            console.print(_ip.format_dry_run_item(item.action, target=item.target, note=item.note))
        console.print(_ip.format_dry_run_completion())
        return

    _execute_init_plan(
        plan=plan,
        project_root=project_root,
        telemetry_enabled=interactive_telemetry_enabled,
        active_profile=interactive_active_profile,
    )


def _available_profile_names(project_root: Path, repo_root: Path) -> list[str]:
    """只读 yaml profile 名，不读取 .env、不解析 provider 环境变量。"""
    import yaml as _yaml

    for cfg_path in (
        project_root / "configs" / "mindforge.yaml",
        repo_root / "configs" / "mindforge.yaml",
    ):
        if not cfg_path.exists():
            continue
        try:
            data = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            llm = data.get("llm") if isinstance(data, dict) else None
            profiles = llm.get("profiles") if isinstance(llm, dict) else None
            if isinstance(profiles, dict):
                return sorted(str(k) for k in profiles)
        except Exception:  # noqa: BLE001
            continue
    return ["fake"]


def _validate_interactive_vault_target(target_vault: Path, vault_dirs: tuple[str, ...]) -> None:
    if target_vault.exists() and not target_vault.is_dir():
        console.print(f"[red]✗ vault 路径不是目录：{target_vault}[/red]")
        raise typer.Exit(code=2)
    if not target_vault.exists():
        return
    visible = [p for p in target_vault.iterdir() if not p.name.startswith(".")]
    if not visible:
        return
    required = {"00-Inbox", "20-Knowledge-Cards", "30-Projects"}
    if required <= {p.name for p in target_vault.iterdir()}:
        return
    allowed = {Path(d).parts[0] for d in vault_dirs}
    unknown = [p.name for p in visible if p.name not in allowed]
    if unknown:
        console.print(
            f"[red]✗ 目标目录已存在且不是 MindForge vault：{target_vault}[/red]"
        )
        console.print(
            "[dim]请选择空目录，或指向已有 MindForge vault。检测到的非 vault 内容："
            f"{', '.join(sorted(unknown)[:5])}[/dim]"
        )
        raise typer.Exit(code=2)


def _rewrite_init_config(
    cfg_dst: Path,
    *,
    vault_root: Path,
    telemetry_enabled: bool | None,
    active_profile: str | None,
) -> None:
    # 把刚拷过来的 mindforge.yaml 改成本次 init 选择；否则 doctor 会指向模板路径。
    # 真实 dogfood 后，注释就是配置 UX 的一部分：这里只做文本级字段替换，
    # 不再 safe_dump 整份 YAML，避免丢失"secret 不进 YAML"等关键说明。
    if not cfg_dst.exists():
        return
    try:
        changed: list[str] = []
        text = cfg_dst.read_text(encoding="utf-8")
        new_text = _replace_yaml_scalar_in_block(
            text,
            block_name="vault",
            key="root",
            value=str(vault_root),
            quote=True,
        )
        if new_text != text:
            text = new_text
            changed.append(f"vault.root → {vault_root}")
        if telemetry_enabled is not None:
            new_text = _replace_yaml_scalar_in_block(
                text,
                block_name="telemetry",
                key="enabled",
                value="true" if telemetry_enabled else "false",
                quote=False,
            )
            if new_text != text:
                text = new_text
                changed.append(f"telemetry.enabled → {telemetry_enabled}")
        if active_profile:
            new_text = _replace_yaml_scalar_in_block(
                text,
                block_name="llm",
                key="active_profile",
                value=active_profile,
                quote=False,
            )
            if new_text != text:
                text = new_text
                changed.append(f"llm.active_profile → {active_profile}")
        if changed:
            cfg_dst.write_text(text, encoding="utf-8")
            console.print(f"  rewrote {cfg_dst}  " + "；".join(changed))
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]提示：未能改写 mindforge.yaml（{e}），请手工编辑 yaml。[/yellow]")


def _replace_yaml_scalar_in_block(
    text: str,
    *,
    block_name: str,
    key: str,
    value: str,
    quote: bool,
) -> str:
    """在顶层 YAML block 中替换一个简单 scalar，保留整份模板注释。

    本 helper 刻意很窄：只服务 init 的三处固定字段，不试图成为通用 YAML
    编辑器。这样避免新增 ruamel.yaml 之类重依赖，也避免 ``safe_dump`` 把
    用户最需要的配置说明全部抹掉。
    """

    lines = text.splitlines(keepends=True)
    in_block = False
    rendered = f'"{value}"' if quote else value
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not line.startswith(" ") and stripped.endswith(":"):
            in_block = stripped == f"{block_name}:"
            continue
        if in_block and line.startswith("  ") and stripped.startswith(f"{key}:"):
            comment = ""
            if "#" in line:
                before_hash, hash_part = line.split("#", 1)
                if before_hash.strip().startswith(f"{key}:"):
                    comment = "  #" + hash_part.rstrip("\n")
            newline = "\n" if line.endswith("\n") else ""
            lines[idx] = f"  {key}: {rendered}{comment}{newline}"
            return "".join(lines)
    return text


@config_app.command("show")
def config_show(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("text", "--format", help="text | json"),
) -> None:
    """展示当前本地配置视图；只读 yaml，不读 .env、不解析真实 provider。"""
    cfg = load_cfg(config, read_env=False)
    payload = _config_ux_payload(config, cfg)
    if output_format == "json":
        import json as _json

        print(_json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _print_config_ux_payload("MindForge config show", payload)


@config_app.command("doctor")
def config_doctor(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """诊断 setup/config 风险，并给出下一步命令。"""
    console.print(f"[bold]MindForge config doctor[/bold] · {config}")
    if not config.exists():
        console.print("[red]✗ config missing[/red]")
        console.print("Next: mindforge config init --output <path> --vault <vault>", markup=False)
        console.print(
            "Safe defaults: config only; secrets via env/.env; no API call during init.",
            markup=False,
        )
        raise typer.Exit(code=2)
    try:
        cfg = load_app_config(config, vault_override=global_vault_override())
    except AppContextError as e:
        console.print(f"[red]✗ config invalid[/red] {e}")
        console.print("Next: fix YAML, or run `mindforge config init --dry-run` to inspect a safe template.")
        raise typer.Exit(code=2) from e

    payload = _config_ux_payload(config, cfg)
    _print_config_ux_payload("Config status", payload)
    rows = _config_doctor_rows(cfg)
    console.print("[bold]Validation[/bold]")
    for state, label, detail, next_action in rows:
        console.print(f"  {_doctor_icon(state)} {label:<18}: {detail}")
        if next_action:
            console.print(f"    next: {next_action}", markup=False)
    if all(state != "error" for state, *_rest in rows):
        console.print("[green]✓ config looks safe for local fake-provider use[/green]")


@config_app.command("status")
def config_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    as_json: bool = typer.Option(False, "--json", help="输出机器可读 JSON。"),
) -> None:
    """展示真实本地配置 readiness；只显示 key presence，不显示 secret value。"""
    try:
        snapshot = build_local_status_snapshot(
            config,
            vault_override=global_vault_override(),
            cwd=Path.cwd(),
        )
    except AppContextError as exc:
        render_friendly_error(console, friendly_config_error(config, str(exc)))
        raise typer.Exit(code=2) from exc
    if as_json:
        render_status_json(snapshot)
        return
    render_config_status(console, snapshot)


@config_app.command("init")
def config_init(
    output: Path = typer.Option(Path("configs/mindforge.yaml"), "--output", "-o"),
    vault: Path = typer.Option(Path("vault"), "--vault", help="写入配置中的 vault.root"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只打印计划，不写文件"),
    force: bool = typer.Option(False, "--force", help="允许覆盖已有 config 文件"),
) -> None:
    """生成最小本地配置文件；默认真实 dogfood profile 且拒绝覆盖。

    中文学习型说明：这是 setup UX 的轻量入口，不替代 `mindforge init` 的 vault
    骨架创建；它只从 package asset 复制一份安全默认 yaml，并改写少量字段。
    """
    plan = _build_config_init_plan(output=output, vault=vault, force=force)
    _print_config_init_plan(plan, dry_run=dry_run)
    if dry_run:
        return
    if output.exists() and not force:
        console.print("[red]✗ config 已存在，拒绝覆盖。使用 --force 才会覆盖。[/red]")
        raise typer.Exit(code=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(plan["content"], encoding="utf-8")
    console.print(f"[green]✓ wrote config[/green] {output}")
    console.print("Next: mindforge config doctor --config <path>", markup=False)


@init_config_app.command("setup")
def setup_cmd(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    vault: Path = typer.Option(Path("vault"), "--vault"),
    dry_run: bool = typer.Option(True, "--dry-run/--write", help="默认 dry-run；--write 才落盘 config"),
    force: bool = typer.Option(False, "--force", help="搭配 --write 才允许覆盖 config"),
) -> None:
    """第一天 setup plan：CLI-first、默认 dry-run、不调用 provider。"""
    console.print("[bold]MindForge setup[/bold]")
    console.print("Mode: dry-run" if dry_run else "Mode: write config", markup=False)
    console.print(
        "Safety: writes config only; secrets stay in env/.env; no LLM call; no Obsidian formal-note writes.",
        markup=False,
    )
    plan = _build_config_init_plan(output=config, vault=vault, force=force)
    _print_config_init_plan(plan, dry_run=dry_run)
    console.print("Next after setup: mindforge start --config <path>", markup=False)
    if not dry_run:
        if config.exists() and not force:
            console.print("[red]✗ config 已存在，拒绝覆盖。使用 --force 才会覆盖。[/red]")
            raise typer.Exit(code=2)
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(plan["content"], encoding="utf-8")
        console.print(f"[green]✓ wrote config[/green] {config}")


def _config_ux_payload(config_path: Path, cfg: MindForgeConfig) -> dict[str, object]:
    """把 MindForgeConfig 压成 setup UX 摘要；不包含 secret 或 provider env 值。"""
    return {
        "config_path": str(config_path),
        "vault_root": str(cfg.vault.root),
        "paths": {
            "inbox": str(cfg.vault.inbox_path),
            "cards": str(cfg.vault.cards_path),
            "projects": str(cfg.vault.projects_path),
            "state": str(cfg.state.state_path),
            "runs": str(cfg.state.runs_path),
            "index": str(cfg.state.workdir / "index" / "bm25.json"),
            "review": "frontmatter review_after fields",
            "backups": str(cfg.state.workdir / "backups"),
        },
        "active_profile": cfg.llm.active_profile,
        "safe_by_default": {
            "fake_provider": cfg.llm.active_profile == "fake",
            "reads_env": False,
            "calls_real_llm": False,
            "writes_formal_obsidian_notes": False,
            "telemetry_upload": False,
        },
        "next": "mindforge doctor --paths",
    }


def _print_config_ux_payload(title: str, payload: dict[str, object]) -> None:
    """打印短配置摘要；保持 CLI 可扫读，不展开完整 yaml。"""
    console.print(f"[bold]{title}[/bold]")
    console.print(f"config        : {payload['config_path']}")
    console.print(f"vault.root    : {payload['vault_root']}")
    console.print(f"active_profile: {payload['active_profile']}")
    paths = payload["paths"]
    if isinstance(paths, dict):
        console.print("[bold]Paths[/bold]")
        for key, value in paths.items():
            console.print(f"  {key:<8}: {value}")
    safety = payload["safe_by_default"]
    if isinstance(safety, dict):
        console.print("[bold]Safety[/bold]")
        for key, value in safety.items():
            console.print(f"  {key:<28}: {value}")
    console.print(f"Next: {payload['next']}", markup=False)


def _config_doctor_rows(cfg):
    return _svc_config_doctor_rows(cfg)


def _build_config_init_plan(*, output: Path, vault: Path, force: bool) -> dict[str, object]:
    """从 package asset 生成主配置内容，保留注释并只替换 vault.root。"""
    from .assets_runtime import bundled_text

    content = _replace_yaml_scalar_in_block(
        bundled_text("configs", "mindforge.yaml"),
        block_name="vault",
        key="root",
        value=str(vault.expanduser().resolve()),
        quote=True,
    )
    return {
        "output": output,
        "vault": vault.expanduser().resolve(),
        "exists": output.exists(),
        "force": force,
        "content": content,
    }


def _print_config_init_plan(plan: dict[str, object], *, dry_run: bool) -> None:
    console.print("[bold]Config init plan[/bold]")
    console.print(f"output : {plan['output']}")
    console.print(f"vault  : {plan['vault']}")
    console.print(f"exists : {plan['exists']}  force={plan['force']}")
    console.print(
        "defaults: active_profile=openai_compatible, secrets via env/.env, no API call during init",
        markup=False,
    )
    if dry_run:
        console.print("[dim]dry-run: no files written[/dim]")
