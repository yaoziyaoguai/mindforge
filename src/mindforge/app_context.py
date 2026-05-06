"""CLI 可复用的 config / path resolution helper。

中文学习型说明：AppContext 层只做"把用户给的 config path 解析成本次命令可用
的本地路径集合"。它不做 recall/approve/review/Obsidian 业务判断，不依赖
Typer/Rich，不读取 `.env`，也不调用 LLM。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .assets_runtime import bundled_asset_path_for_process
from .config import ConfigError, MindForgeConfig, load_mindforge_config


class AppContextError(ValueError):
    """config/path resolution 的结构化错误，由 CLI 决定如何展示。"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class AppPaths:
    config_path: Path
    vault_root: Path
    inbox_path: Path
    cards_path: Path
    projects_path: Path
    state_workdir: Path
    runs_path: Path


@dataclass(frozen=True)
class AppContext:
    config: MindForgeConfig
    paths: AppPaths


@dataclass(frozen=True)
class ActiveVaultDecision:
    """本次命令使用哪个 vault 的只读决策结果。

    中文学习型说明：CLI 可以在任意目录运行。为了避免 scan 用一个 vault、
    state/index 又写到另一个目录，所有命令都先收敛到同一个 active vault。
    本结构只描述路径选择原因，不读取 source 正文、不写文件、不碰 `.env`。
    """

    root: Path
    reason: str
    configured_root: Path

    @property
    def configured_differs(self) -> bool:
        return self.root != self.configured_root


@dataclass(frozen=True)
class UserSourcePathResolution:
    """用户输入 source path 的解析结果。

    中文学习型说明：路径解析属于 CLI adapter 边界。service/pipeline 只应该接收
    已解析的绝对 source 路径，避免 import/watch/process 各自猜 cwd、project
    root 或 active vault，从而出现同一路径在不同命令里含义不同。
    """

    original: Path
    resolved: Path
    source: str
    cwd: Path
    project_root: Path | None
    active_vault: Path
    tried: tuple[Path, ...]


def load_app_config(
    config_path: Path,
    *,
    vault_override: Path | None = None,
    cwd: Path | None = None,
) -> MindForgeConfig:
    """加载 config 并应用本次命令的 vault override；不读 `.env`。

    中文学习型说明：是否加载 `.env` 仍由 CLI 入口显式决定。这里保持纯
    config/path resolution，避免 service/context 层悄悄改变 provider 环境。
    """
    config_path = resolve_config_path(config_path, cwd=cwd)
    try:
        cfg = load_mindforge_config(config_path)
    except ConfigError as e:
        raise AppContextError("invalid_config", str(e)) from e
    decision = resolve_active_vault(cfg, vault_override=vault_override, cwd=cwd)
    return apply_active_vault(cfg, decision)


def resolve_config_path(config_path: Path, *, cwd: Path | None = None) -> Path:
    return _resolve_config_path(config_path, cwd=cwd)


def _resolve_config_path(config_path: Path, *, cwd: Path | None) -> Path:
    """解析 CLI config path，默认配置缺失时回退到 package asset。

    中文学习型说明：安装态用户经常在任意目录运行 ``mindforge demo`` /
    ``dogfood readiness`` / ``doctor``，当前目录没有 ``configs/mindforge.yaml``
    是正常状态。默认路径会先从 cwd 向上寻找 MindForge project root，再
    回退到包内配置；如果用户显式传了其它 ``--config``，仍严格报错，避免把
    拼错的路径静默吞掉。
    """

    if config_path.exists():
        return config_path
    default = Path("configs/mindforge.yaml")
    if config_path == default:
        project_root = find_project_root(cwd)
        if project_root is not None:
            return project_root / "configs" / "mindforge.yaml"
        return bundled_asset_path_for_process("configs", "mindforge.yaml")
    raise AppContextError("missing_config", f"配置文件不存在：{config_path}")


def build_app_context(
    config_path: Path,
    *,
    vault_override: Path | None = None,
    cwd: Path | None = None,
) -> AppContext:
    """构建 console-independent AppContext；不创建目录、不写文件。"""
    resolved_config = _resolve_config_path(config_path, cwd=cwd)
    cfg = load_app_config(resolved_config, vault_override=vault_override, cwd=cwd)
    return AppContext(
        config=cfg,
        paths=AppPaths(
            config_path=resolved_config,
            vault_root=cfg.vault.root,
            inbox_path=cfg.vault.inbox_path,
            cards_path=cfg.vault.cards_path,
            projects_path=cfg.vault.projects_path,
            state_workdir=cfg.state.workdir,
            runs_path=cfg.state.runs_path,
        ),
    )


def find_project_root(start: Path | None = None) -> Path | None:
    """从 start 向上寻找 MindForge project root。

    规则很窄：包含 ``configs/mindforge.yaml`` 的目录就是 project root。
    这对应产品语义：用户在哪里运行 ``mindforge init``，哪里就是项目根；
    默认 ``vault.root``、本地 ``.env``、用户相对 source path 都围绕它解释。
    """

    current = (start or Path.cwd()).expanduser().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "configs" / "mindforge.yaml").is_file():
            return candidate
    return None


def detect_cwd_vault(cwd: Path | None = None) -> Path | None:
    """从 cwd 向上寻找 MindForge vault root；找不到返回 None。

    当前判断只使用目录形状：``00-Inbox`` 或 ``20-Knowledge-Cards`` 任一
    存在即可。fresh external vault 可能刚创建 ``00-Inbox``，还没有 cards
    目录；CLI 仍应把它当作当前 vault。``.mindforge`` 仅作为非项目目录的
    兼容信号，避免把 MindForge 源码 repo 的 runtime 目录误判成 vault。
    """

    current = (cwd or Path.cwd()).expanduser().resolve()
    candidates = (current, *current.parents)
    for candidate in candidates:
        if (
            (candidate / "00-Inbox").is_dir()
            or (candidate / "20-Knowledge-Cards").is_dir()
            or (
                (candidate / ".mindforge").is_dir()
                and not (candidate / "configs" / "mindforge.yaml").exists()
            )
        ):
            return candidate
    return None


def resolve_active_vault(
    cfg: MindForgeConfig,
    *,
    vault_override: Path | None = None,
    cwd: Path | None = None,
) -> ActiveVaultDecision:
    """按统一优先级选择 active vault。

    优先级：explicit ``--vault`` > cwd/ancestor vault > configured vault。
    这个规则保证用户在 vault root 内运行 ``mindforge scan`` 时，scanner、
    state/index、next command 全部指向同一个 vault。
    """

    project_root = _project_root_from_raw(cfg)
    configured = _resolve_configured_vault_root(cfg.vault.root, project_root)
    if vault_override is not None:
        return ActiveVaultDecision(
            root=vault_override.expanduser().resolve(),
            reason="explicit --vault",
            configured_root=configured,
        )
    cwd_vault = detect_cwd_vault(cwd)
    if cwd_vault is not None:
        return ActiveVaultDecision(
            root=cwd_vault,
            reason="cwd vault",
            configured_root=configured,
        )
    return ActiveVaultDecision(
        root=configured,
        reason="configured vault",
        configured_root=configured,
    )


def apply_active_vault(cfg: MindForgeConfig, decision: ActiveVaultDecision) -> MindForgeConfig:
    """把 active vault 应用到 cfg，并让相对 state.workdir 跟随 active vault。

    中文学习型说明：``state.workdir: .mindforge`` 是 vault-local runtime
    状态，不应再按任意 cwd 解析。否则会出现真实 dogfood 里看到的矛盾：
    state 写到当前目录，而 scanner/next command 使用另一个 vault。
    绝对 workdir 仍保持用户显式选择，不被重写。
    """

    new_vault = replace(cfg.vault, root=decision.root)
    state_raw = cfg.raw.get("state") if isinstance(cfg.raw, dict) else None
    workdir_raw = state_raw.get("workdir") if isinstance(state_raw, dict) else None
    new_state = cfg.state
    if isinstance(workdir_raw, str) and not Path(workdir_raw).expanduser().is_absolute():
        new_state = replace(cfg.state, workdir=decision.root / workdir_raw)
    metadata = {
        "_mindforge_active_vault": {
            "root": str(decision.root),
            "reason": decision.reason,
            "configured_root": str(decision.configured_root),
            "configured_differs": decision.configured_differs,
        }
    }
    project_root = _project_root_from_raw(cfg)
    config_path = _config_path_from_raw(cfg)
    if project_root is not None:
        metadata["_mindforge_project"] = {
            "root": str(project_root),
            "config_path": str(config_path) if config_path is not None else "",
        }
    return replace(cfg, vault=new_vault, state=new_state, raw={**cfg.raw, **metadata})


def apply_vault_override(cfg: MindForgeConfig, vault_override: Path | None) -> MindForgeConfig:
    """兼容旧调用：按 active-vault 规则应用显式 override。"""
    if vault_override is None:
        return cfg
    decision = resolve_active_vault(cfg, vault_override=vault_override)
    return apply_active_vault(cfg, decision)


def resolve_user_source_path(
    input_path: Path,
    *,
    cwd: Path,
    project_root: Path | None,
    active_vault: Path,
) -> UserSourcePathResolution:
    """把用户输入 source path 解析为存在的绝对路径。

    优先级：
    1. absolute path 原样解析；
    2. cwd-relative；
    3. project-root-relative；
    4. active-vault-relative。

    中文学习型说明：不存在的单文件/文件夹是输入错误，必须在 CLI 边界失败。
    这样 missing import 不会进入 discovery/process/checkpoint，也就不会写入
    processed/fingerprint/run state。
    """

    original = input_path.expanduser()
    tried: list[tuple[str, Path]] = []
    if original.is_absolute():
        tried.append(("absolute", original))
    else:
        tried.append(("cwd-relative", cwd / original))
        if project_root is not None:
            tried.append(("project-root-relative", project_root / original))
        tried.append(("active-vault-relative", active_vault / original))

    for source, candidate in tried:
        resolved = candidate.expanduser().resolve()
        if resolved.exists():
            return UserSourcePathResolution(
                original=input_path,
                resolved=resolved,
                source=source,
                cwd=cwd,
                project_root=project_root,
                active_vault=active_vault,
                tried=tuple(path.expanduser().resolve() for _kind, path in tried),
            )

    return UserSourcePathResolution(
        original=input_path,
        resolved=tried[0][1].expanduser().resolve(),
        source="not_found",
        cwd=cwd,
        project_root=project_root,
        active_vault=active_vault,
        tried=tuple(path.expanduser().resolve() for _kind, path in tried),
    )


def _resolve_configured_vault_root(root: Path, project_root: Path | None) -> Path:
    expanded = root.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    base = project_root or Path.cwd()
    return (base / expanded).resolve()


def _project_root_from_raw(cfg: MindForgeConfig) -> Path | None:
    raw = cfg.raw if isinstance(cfg.raw, dict) else {}
    meta = raw.get("_mindforge_config")
    if isinstance(meta, dict) and meta.get("project_root"):
        return Path(str(meta["project_root"])).expanduser().resolve()
    meta = raw.get("_mindforge_project")
    if isinstance(meta, dict) and meta.get("root"):
        return Path(str(meta["root"])).expanduser().resolve()
    return None


def _config_path_from_raw(cfg: MindForgeConfig) -> Path | None:
    raw = cfg.raw if isinstance(cfg.raw, dict) else {}
    meta = raw.get("_mindforge_config")
    if isinstance(meta, dict) and meta.get("path"):
        return Path(str(meta["path"])).expanduser().resolve()
    meta = raw.get("_mindforge_project")
    if isinstance(meta, dict) and meta.get("config_path"):
        text = str(meta["config_path"])
        return Path(text).expanduser().resolve() if text else None
    return None
