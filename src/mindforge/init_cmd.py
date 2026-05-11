"""mindforge init — 初始化最小可用的 vault + 配置目录。

为什么 init 必须幂等：
- 用户可能多次运行（第二次为了补漏，第三次为了 --force 覆盖模板），
  我们绝不能在已存在的目录里覆写他手写的内容。
- 默认行为：只创建缺失目录与缺失文件；已存在的文件原样保留。
- ``--force`` 才允许覆写"由 MindForge 提供的模板配置"（不会覆写用户数据）。
- ``--dry-run`` 只产出"我将要做什么"的 plan，不写任何文件。

为什么 init 不创建 shell key 模板：
- first-run 产品主路径是 Web Setup / local secret store / provider key；
  自动创建 shell key 模板会把 advanced 兼容路径误塑造成新用户必须理解的设置方式。
- provider 运行时仍可保留 legacy/advanced 兼容，但 init 输出与文件副作用只服务
  普通用户第一天能完成的主路径。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ── vault 必备子目录（与 vault_template/ 对齐）─────────────────────────────
VAULT_DIRS: tuple[str, ...] = (
    "00-Inbox",
    "00-Inbox/WebClips",
    "00-Inbox/ChatExports",
    "00-Inbox/PDFs",
    "00-Inbox/Docs",
    "00-Inbox/ManualNotes",
    "20-Knowledge-Cards",
    "30-Projects",
    "80-Reviews",
    "90-System",
    "_attachments",
)


PlanAction = Literal["create_dir", "copy_file", "skip_exists", "overwrite_force"]
USER_CONFIG_ASSET = "mindforge.user.yaml"


@dataclass(frozen=True)
class PlanItem:
    action: PlanAction
    target: Path
    source: Path | None = None
    note: str = ""


@dataclass(frozen=True)
class InitPlan:
    items: tuple[PlanItem, ...] = field(default_factory=tuple)
    vault_root: Path = field(default_factory=Path)
    project_root: Path = field(default_factory=Path)

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for it in self.items:
            out[it.action] = out.get(it.action, 0) + 1
        return out


def build_plan(
    vault_root: Path,
    *,
    project_root: Path,
    repo_root: Path,
    force: bool = False,
) -> InitPlan:
    """构造 init 计划（不写任何文件）。

    参数:
        vault_root: 目标 vault（用户的 Obsidian 库根）
        project_root: MindForge 工作目录（``configs/`` 与本地运行状态落到这里）
        repo_root: MindForge 源码仓库根（用来拷贝 ``configs/`` / ``vault_template/``）
        force: 是否覆写 MindForge 提供的模板文件（**不**覆写用户数据）

    幂等保证：连续两次 build_plan 在同一磁盘状态下应返回完全相同的 items。
    """
    items: list[PlanItem] = []

    # 1) vault 目录骨架
    for sub in VAULT_DIRS:
        target = vault_root / sub
        if target.exists():
            items.append(PlanItem("skip_exists", target, note="dir already exists"))
        else:
            items.append(PlanItem("create_dir", target, note="vault skeleton"))

    # 2) 用户第一天只需要一个主配置入口。learning tracks / llm examples
    # 仍作为 package 内置资产供 process 与文档引用，但 init 不再把它们复制到
    # 用户项目里制造多个 LLM 配置入口。
    template_files: tuple[tuple[Path, Path, str], ...] = (
        (
            repo_root / "configs" / USER_CONFIG_ASSET,
            project_root / "configs" / "mindforge.yaml",
            "mindforge user override config",
        ),
    )
    for src, dst, note in template_files:
        if not src.exists():
            # 仓库里都缺，跳过（不是错误，doctor 会再次提醒）
            continue
        if dst.exists():
            if force:
                items.append(PlanItem("overwrite_force", dst, src, note=note))
            else:
                items.append(PlanItem("skip_exists", dst, src, note=f"{note} (use --force)"))
        else:
            items.append(PlanItem("copy_file", dst, src, note=note))

    return InitPlan(
        items=tuple(items),
        vault_root=vault_root.resolve(),
        project_root=project_root.resolve(),
    )


def execute_plan(plan: InitPlan) -> list[str]:
    """执行 plan；返回"实际做了什么"的人类可读列表。

    幂等：``skip_exists`` 不动；``copy_file`` 仅当目标不存在时写；
    ``overwrite_force`` 写入；``create_dir`` ``mkdir -p``。
    """
    actions: list[str] = []
    for it in plan.items:
        if it.action == "create_dir":
            it.target.mkdir(parents=True, exist_ok=True)
            actions.append(f"mkdir {it.target}")
        elif it.action == "copy_file":
            it.target.parent.mkdir(parents=True, exist_ok=True)
            if it.source is not None and it.source.exists():
                if it.source.name == USER_CONFIG_ASSET and it.target.name == "mindforge.yaml":
                    it.target.write_text(
                        _render_user_config_template(
                            it.source,
                            vault_root=plan.vault_root,
                            project_root=plan.project_root,
                        ),
                        encoding="utf-8",
                    )
                else:
                    it.target.write_bytes(it.source.read_bytes())
            else:
                # inline 默认（当前无 first-run fallback）
                it.target.write_text(_inline_default_for(it.target), encoding="utf-8")
            actions.append(f"create {it.target}")
        elif it.action == "overwrite_force":
            it.target.parent.mkdir(parents=True, exist_ok=True)
            if it.source is not None and it.source.exists():
                if it.source.name == USER_CONFIG_ASSET and it.target.name == "mindforge.yaml":
                    it.target.write_text(
                        _render_user_config_template(
                            it.source,
                            vault_root=plan.vault_root,
                            project_root=plan.project_root,
                        ),
                        encoding="utf-8",
                    )
                else:
                    it.target.write_bytes(it.source.read_bytes())
            else:
                it.target.write_text(_inline_default_for(it.target), encoding="utf-8")
            actions.append(f"overwrite {it.target}")
        elif it.action == "skip_exists":
            actions.append(f"skip   {it.target}")
    return actions


def _inline_default_for(target: Path) -> str:
    return ""


def _render_user_config_template(source: Path, *, vault_root: Path, project_root: Path) -> str:
    """渲染 init 用户 YAML，只替换 vault.root 并保留注释。

    这里不使用 ``yaml.safe_dump``：用户配置文件的注释就是第一天 setup UX 的一
    部分。这个 helper 刻意只认识模板里的一行 root，避免把它扩成通用 YAML
    编辑器。默认 vault 在 project root 下时写成 ``vault``，由 config loader
    按 project root 解析；这让配置可搬移，也避免用户误以为必须在固定 cwd
    执行命令。
    """

    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    in_vault = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not line.startswith(" ") and stripped.endswith(":"):
            in_vault = stripped == "vault:"
            continue
        if in_vault and line.startswith("  ") and stripped.startswith("root:"):
            newline = "\n" if line.endswith("\n") else ""
            rendered_root = _display_vault_root_for_template(vault_root, project_root)
            lines[idx] = f'  root: "{rendered_root}"{newline}'
            break
    return "".join(lines)


def _display_vault_root_for_template(vault_root: Path, project_root: Path) -> str:
    if vault_root.resolve() == (project_root / "vault").resolve():
        return "vault"
    return str(vault_root)


def is_initialized(vault_root: Path, project_root: Path) -> bool:
    """粗略检测：vault 必备目录与 mindforge.yaml 都存在。"""
    if not (project_root / "configs" / "mindforge.yaml").exists():
        return False
    must = ("00-Inbox", "20-Knowledge-Cards", "30-Projects")
    return all((vault_root / d).is_dir() for d in must)


def next_steps_hint() -> list[str]:
    return [
        "1) mindforge start  # 查看 first-run checklist",
        "2) mindforge status  # 只读查看 workspace/model/source/draft 状态",
        "3) mindforge web  # 打开 Web Setup，添加模型和 provider key",
        "4) mindforge watch add vault/00-Inbox/ManualNotes/<note>.md  # 注册 source 并启动后台 processing",
        "5) mindforge import <file-or-folder>  # 或一次性导入 source",
        "6) mindforge runs list  # 查看后台 processing runs",
        "7) mindforge approve list  # 有 ai_draft 后再审核",
        "8) mindforge library list  # 查看 approved knowledge",
    ]
