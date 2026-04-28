"""mindforge init — 初始化最小可用的 vault + 配置目录。

为什么 init 必须幂等：
- 用户可能多次运行（第二次为了补漏，第三次为了 --force 覆盖模板），
  我们绝不能在已存在的目录里覆写他手写的内容。
- 默认行为：只创建缺失目录与缺失文件；已存在的文件原样保留。
- ``--force`` 才允许覆写"由 MindForge 提供的模板配置"（不会覆写用户数据）。
- ``--dry-run`` 只产出"我将要做什么"的 plan，不写任何文件。

为什么 init 不创建真实 .env：
- .env 里通常会塞 API key；自动创建会诱导用户在第一时间填入 secret，
  风险大于便利。我们只发 ``.env.example`` 模板，提示用户自己填。
- doctor 也只检查 ``.env`` 是否在 ``.gitignore``，绝不读其内容。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ── vault 必备子目录（与 vault_template/ 对齐）─────────────────────────────
VAULT_DIRS: tuple[str, ...] = (
    "00-Inbox",
    "00-Inbox/Cubox",
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
        project_root: MindForge 工作目录（``configs/`` 与 ``.env.example`` 落到这里）
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

    # 2) 配置 + 模板文件（来自仓库 configs/ + .env.example）
    template_files: tuple[tuple[Path, Path, str], ...] = (
        (
            repo_root / "configs" / "mindforge.yaml",
            project_root / "configs" / "mindforge.yaml",
            "mindforge config",
        ),
        (
            repo_root / "configs" / "learning_tracks.yaml",
            project_root / "configs" / "learning_tracks.yaml",
            "learning tracks",
        ),
        (
            repo_root / "configs" / "llm.example.yaml",
            project_root / "configs" / "llm.example.yaml",
            "llm example",
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

    # 3) .env.example —— 不创建真实 .env
    env_example_dst = project_root / ".env.example"
    env_example_src = repo_root / ".env.example"
    if env_example_dst.exists():
        items.append(
            PlanItem(
                "overwrite_force" if force else "skip_exists",
                env_example_dst,
                env_example_src if env_example_src.exists() else None,
                note=".env.example (use --force)" if not force else ".env.example",
            )
        )
    else:
        items.append(
            PlanItem(
                "copy_file",
                env_example_dst,
                env_example_src if env_example_src.exists() else None,
                note=".env.example (inline default)" if not env_example_src.exists() else ".env.example",
            )
        )

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
                it.target.write_bytes(it.source.read_bytes())
            else:
                # inline 默认（.env.example fallback）
                it.target.write_text(_inline_default_for(it.target), encoding="utf-8")
            actions.append(f"create {it.target}")
        elif it.action == "overwrite_force":
            it.target.parent.mkdir(parents=True, exist_ok=True)
            if it.source is not None and it.source.exists():
                it.target.write_bytes(it.source.read_bytes())
            else:
                it.target.write_text(_inline_default_for(it.target), encoding="utf-8")
            actions.append(f"overwrite {it.target}")
        elif it.action == "skip_exists":
            actions.append(f"skip   {it.target}")
    return actions


def _inline_default_for(target: Path) -> str:
    if target.name == ".env.example":
        return (
            "# MindForge .env example — copy to .env and fill in real values.\n"
            "# .env MUST be in .gitignore. MindForge never reads .env content;\n"
            "# providers read it via env vars.\n"
            "# MINDFORGE_LLM_API_KEY=sk-...\n"
        )
    return ""


def is_initialized(vault_root: Path, project_root: Path) -> bool:
    """粗略检测：vault 必备目录与 mindforge.yaml 都存在。"""
    if not (project_root / "configs" / "mindforge.yaml").exists():
        return False
    must = ("00-Inbox", "20-Knowledge-Cards", "30-Projects")
    return all((vault_root / d).is_dir() for d in must)


def next_steps_hint() -> list[str]:
    return [
        "1) 把要处理的资料放进 00-Inbox/ 的子目录（Cubox / WebClips / ChatExports / PDFs / Docs / ManualNotes）",
        "2) 编辑 configs/mindforge.yaml 选择 llm.active_profile（默认 fake，不调真实 LLM）",
        "3) 如需真实 LLM：把 .env.example 复制为 .env 并填入 API key（.env 必须在 .gitignore）",
        "4) mindforge scan          # 扫描 inbox",
        "5) mindforge process --profile fake --limit 1   # 跑一遍 5-stage pipeline",
        "6) mindforge approve list  # 看看产出哪些 ai_draft",
        "7) mindforge approve --card 20-Knowledge-Cards/...md  # 显式人工 approve",
        "8) mindforge review due / mindforge recall / mindforge project context  # 日用",
        "9) mindforge doctor        # 任何时刻自检",
    ]
