"""Doctor CLI adapter.

Doctor 是只读诊断入口：展示 runtime/config/path/safety/recovery 信号，
不读取 .env 内容、不调用网络、不打印 secret。
"""
from __future__ import annotations

from dataclasses import replace as _replace
from pathlib import Path

import typer

from .cli_runtime import console, load_cfg
from .presenters.doctor import doctor_icon as _pres_doctor_icon
from .presenters.doctor import ok_dir as _pres_ok_dir
from .services.doctor import compute_doctor_hints as _svc_compute_doctor_hints
from .services.doctor import dir_state as _svc_dir_state
from .services.doctor import doctor_paths as _svc_doctor_paths
from .services.doctor import doctor_recovery_checks as _svc_doctor_recovery_checks

doctor_app = typer.Typer(add_completion=False)


def _divider() -> None:
    console.print("[dim]" + "─" * 72 + "[/dim]")


def _print_runtime_section(config: Path) -> bool:
    import platform
    import sys

    from . import __version__

    console.print(f"[bold]MindForge doctor[/bold]  v{__version__}")
    _divider()
    console.print("[bold]Runtime[/bold]")
    console.print(f"  {_doctor_icon('ok')} Python            : {platform.python_version()} ({sys.executable})")
    console.print(f"  {_doctor_icon('info')} Platform          : {platform.platform()}")
    config_status = "ok" if config.exists() else "error"
    config_text = "exists" if config.exists() else "MISSING"
    console.print(f"  {_doctor_icon(config_status)} config path       : {config}  ({config_text})")
    if config.exists():
        return True
    _divider()
    console.print("[bold]Action items[/bold]")
    console.print(
        "  [critical] 缺少 mindforge.yaml → 运行: mindforge init --interactive",
        markup=False,
    )
    return False


def _load_doctor_cfg(config: Path, vault: Path | None):
    cfg = load_cfg(config, read_env=False)
    if vault is None:
        return cfg
    return _replace(cfg, vault=_replace(cfg.vault, root=vault.expanduser().resolve()))


def _print_vault_section(cfg) -> None:
    vault_root = cfg.vault.root
    _divider()
    console.print("[bold]Vault[/bold]")
    for label, path in (
        ("vault.root", vault_root),
        ("inbox", vault_root / cfg.vault.inbox_root),
        ("knowledge cards", vault_root / cfg.vault.cards_dir),
        ("projects", vault_root / cfg.vault.projects_dir),
        ("state workdir", Path(cfg.state.workdir)),
    ):
        console.print(f"  {_doctor_icon(_dir_state(path))} {label:<17}: {path}  ({_ok_dir(path)})")
    profile_state = "ok" if cfg.llm.active_profile in cfg.llm.profiles else "error"
    console.print(f"  {_doctor_icon(profile_state)} active_profile    : {cfg.llm.active_profile}")
    console.print(
        f"  {_doctor_icon('ok' if cfg.telemetry.local_only else 'warn')} telemetry.enabled : "
        f"{cfg.telemetry.enabled} (local_only={cfg.telemetry.local_only})"
    )


def _print_optional_installs_section() -> None:
    import importlib.util as _u

    pdf_ok = _u.find_spec("pypdf") is not None
    docx_ok = _u.find_spec("docx") is not None
    _divider()
    console.print("[bold]Optional installs[/bold]")
    pdf_msg = "installed" if pdf_ok else r"missing (pip install mindforge\[pdf])"
    docx_msg = "installed" if docx_ok else r"missing (pip install mindforge\[docx])"
    console.print(f"  {_doctor_icon('ok' if pdf_ok else 'info')} pypdf       : {pdf_msg}")
    console.print(f"  {_doctor_icon('ok' if docx_ok else 'info')} python-docx : {docx_msg}")


def _env_gitignore_state(cwd: Path) -> tuple[bool, bool]:
    env_file = cwd / ".env"
    gitignore = cwd / ".gitignore"
    if not env_file.exists():
        return False, False
    ignored = False
    if gitignore.exists():
        try:
            ignored = ".env" in gitignore.read_text(encoding="utf-8").splitlines()
        except OSError:
            ignored = False
    return True, ignored


def _print_git_runtime_risk(cwd: Path) -> None:
    import shutil
    import subprocess

    if not shutil.which("git"):
        return
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode("utf-8", "replace")
        risky = [
            line
            for line in out.splitlines()
            if any(k in line for k in (".mindforge", "telemetry.jsonl", "runs/", "state.json", ".env"))
        ]
        if risky:
            console.print(
                f"  {_doctor_icon('warn')} git status       : 检测到运行时产物可能被加入暂存（请勿提交）："
            )
            for item in risky[:5]:
                console.print(f"    {item}")
        else:
            console.print(f"  {_doctor_icon('ok')} git status       : 无敏感运行产物风险")
    except Exception:  # noqa: BLE001
        console.print(f"  {_doctor_icon('info')} git status       : (跳过)")


def _print_safety_section() -> None:
    cwd = Path.cwd()
    env_present, env_ignored = _env_gitignore_state(cwd)
    _divider()
    console.print("[bold]Safety[/bold]")
    if not env_present:
        console.print(f"  {_doctor_icon('info')} .env             : not present")
    elif env_ignored:
        console.print(f"  {_doctor_icon('ok')} .env             : present, gitignored (内容未被读取)")
    else:
        console.print(
            f"  {_doctor_icon('error')} .env             : present BUT not in .gitignore；"
            "立即把 .env 加入 .gitignore，避免误提交。"
        )
    _print_git_runtime_risk(cwd)


def _print_recovery_section(cfg, *, paths: bool) -> dict:
    _divider()
    console.print("[bold]Recovery checks[/bold]")
    recovery_hints = _doctor_recovery_checks(cfg)
    for state, label, detail in recovery_hints["rows"]:
        console.print(f"  {_doctor_icon(state)} {label:<22}: {detail}")
    if paths:
        _divider()
        console.print("[bold]Data safety paths[/bold]")
        for label, value in _doctor_paths(cfg):
            console.print(f"  {label:<18}: {value}")
    return recovery_hints


def _print_action_hints(cfg, recovery_hints: dict) -> None:
    # 中文学习：cards / BM25 / overdue / due 等业务推断已搬到
    # ``services.doctor.compute_doctor_hints``。CLI 在这里只做去重、排序、
    # 渲染，符合 thin adapter 边界。
    hints = _svc_compute_doctor_hints(cfg, list(recovery_hints["actions"]))
    if not hints:
        return
    hints = list(dict.fromkeys(hints))
    hints.sort(key=lambda item: {"try_first": -1, "critical": 0, "recommended": 1, "info": 2}.get(item[0], 9))
    _divider()
    console.print("[bold]Action items:[/bold]")
    for priority, hint in hints:
        console.print(f"  [{priority}] {hint}", markup=False)


@doctor_app.command()
def doctor(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="临时覆盖配置中的 vault.root（兼容 `mindforge doctor --vault PATH`）。",
    ),
    paths: bool = typer.Option(False, "--paths", help="展示本地会读/会写/不会写的目录边界"),
) -> None:
    """打印环境 + 配置 + 可选依赖 + .gitignore 风险快照。"""
    if not _print_runtime_section(config):
        return

    cfg = _load_doctor_cfg(config, vault)
    _print_vault_section(cfg)
    _print_optional_installs_section()
    _print_safety_section()
    recovery_hints = _print_recovery_section(cfg, paths=paths)
    _print_action_hints(cfg, recovery_hints)
    console.print(
        "[dim]说明：本命令不读 .env 内容、不发 HTTP、不打印 api_key / token。[/dim]"
    )


# Historical doctor pure-logic helpers extracted to services/doctor.py.
# Aliases preserved so existing imports (e.g. test_user_friendly_polish)
# keep working. Display helpers moved to presenters/doctor.py.
def _doctor_recovery_checks(cfg):
    return _svc_doctor_recovery_checks(cfg)


def _doctor_paths(cfg):
    return _svc_doctor_paths(cfg)


def _doctor_icon(state):
    return _pres_doctor_icon(state)


def _dir_state(p):
    return _svc_dir_state(p)


def _ok_dir(p):
    return _pres_ok_dir(p)
