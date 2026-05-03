"""v0.13 Stage 4 — controlled real-but-safe dogfooding preflight.

为什么单独一个 dogfood_safety 模块?
====================================

``dogfood plan`` (cli.py) 只是 checklist 静态导航; 它不告诉用户
"我现在要跑的这条 input 安全吗"。Stage 3 之后真实 LLM smoke 已可
opt-in, 接下来的关键风险是: 用户可能不小心把家目录、Obsidian vault、
或一个 Cubox 真实 dump 当作 dogfood 输入丢进 pipeline。

本模块提供一个**纯路径分类 + readiness 组合**的 preflight 报告器,
不读取 input 目录内容、不调用 LLM、不写任何东西; 只回答:

1. 这条 input path 属于哪类 (synthetic / non_sensitive_local /
   private_real_data_forbidden / obsidian_vault_forbidden /
   home_scan_forbidden);
2. 当前 LLM 状态是 fake-default 还是 real-opt-in;
3. 综合下来这次 dogfood run 应该 ``allowed`` / ``refused``;
4. refused 时给出明确的 ``blockers``;
5. 输出永远是 review-only artifact, 不是 ``human_approved``。

本模块的硬边界
==============

- **不** 列举 input 目录内容 (``Path.iterdir`` / ``glob``);
- **不** 读取任何文件内容;
- **不** import ``cli`` / ``approval_service`` / ``writer`` /
  ``cards`` / ``obsidian*`` / ``cubox*`` / ``scanner`` / ``processors``;
- **不** import 网络相关 (``requests`` / ``httpx`` / ``subprocess`` /
  ``dotenv``);
- **可以** 复用 ``provider_readiness`` 做 LLM 状态分类;
- 只用 ``pathlib.Path`` 的字符串/解析能力, 不触发文件系统遍历。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 路径分类常量 — 用字符串而不是 Enum, 让 JSON / 测试断言更直接。
CLASS_SYNTHETIC = "synthetic"
CLASS_NON_SENSITIVE_LOCAL = "non_sensitive_local"
CLASS_PRIVATE_REAL_DATA_FORBIDDEN = "private_real_data_forbidden"
CLASS_OBSIDIAN_VAULT_FORBIDDEN = "obsidian_vault_forbidden"
CLASS_HOME_SCAN_FORBIDDEN = "home_scan_forbidden"
CLASS_PATH_DOES_NOT_EXIST = "path_does_not_exist"

_SYNTHETIC_PARENTS = ("examples/demo-vault", "examples/custom-strategies")


def classify_input_path(
    path: Path,
    *,
    declared_non_sensitive: bool = False,
    cwd: Path | None = None,
    home: Path | None = None,
) -> str:
    """对 input path 做**纯静态**分类, 不读取任何文件内容。

    规则 (优先级从高到低):

    1. 路径不存在 → ``path_does_not_exist`` (refuse: 不能猜测意图);
    2. 路径解析后在 ``examples/demo-vault`` 或 ``examples/custom-strategies``
       下 → ``synthetic`` (最安全);
    3. 路径或其任意上级目录名 == ``.obsidian`` → ``obsidian_vault_forbidden``
       (Obsidian vault 标志目录, Stage 4 显式禁止);
    4. 路径解析后在用户 ``home`` 下且不在当前 ``cwd`` 下 →
       ``home_scan_forbidden``;
    5. 调用者显式 ``declared_non_sensitive=True`` 且其它规则未命中 →
       ``non_sensitive_local`` (用户为这条声明负责);
    6. 否则 → ``private_real_data_forbidden``。

    cwd / home 注入便于测试; 默认走真实 ``Path.cwd()`` / ``Path.home()``,
    但**只解析**, 不遍历。
    """
    cwd = (cwd or Path.cwd()).resolve()
    home = (home or Path.home()).resolve()

    if not path.exists():
        return CLASS_PATH_DOES_NOT_EXIST

    resolved = path.resolve()

    # synthetic 路径优先级最高 (白名单): examples/demo-vault 自身就是
    # Obsidian vault (含 .obsidian/), 但它是项目内显式 disposable 副本,
    # 必须允许 dogfood 使用。
    resolved_str = str(resolved).replace("\\", "/")
    for marker in _SYNTHETIC_PARENTS:
        if f"/{marker}" in resolved_str or resolved_str.endswith(marker):
            return CLASS_SYNTHETIC

    # 检测 .obsidian: 路径自身或任意 parent 是 .obsidian, 或任意 parent
    # 目录里**存在** .obsidian 子目录 (Obsidian vault 标志)
    for parent in (resolved, *resolved.parents):
        if parent.name == ".obsidian":
            return CLASS_OBSIDIAN_VAULT_FORBIDDEN
        if parent.is_dir() and (parent / ".obsidian").exists():
            return CLASS_OBSIDIAN_VAULT_FORBIDDEN

    # home_scan: 在 home 下且不在 cwd 下 (cwd 可能本身就在 home, 那是
    # 仓库工作目录, 仍允许)
    try:
        in_home = resolved.is_relative_to(home)
    except AttributeError:  # pragma: no cover -- Python <3.9 兼容
        in_home = str(resolved).startswith(str(home))
    try:
        in_cwd = resolved.is_relative_to(cwd)
    except AttributeError:  # pragma: no cover
        in_cwd = str(resolved).startswith(str(cwd))
    if in_home and not in_cwd:
        return CLASS_HOME_SCAN_FORBIDDEN

    if declared_non_sensitive:
        return CLASS_NON_SENSITIVE_LOCAL

    return CLASS_PRIVATE_REAL_DATA_FORBIDDEN


_REFUSING_CLASSES = {
    CLASS_PRIVATE_REAL_DATA_FORBIDDEN,
    CLASS_OBSIDIAN_VAULT_FORBIDDEN,
    CLASS_HOME_SCAN_FORBIDDEN,
    CLASS_PATH_DOES_NOT_EXIST,
}


def build_preflight_report(
    input_path: Path,
    *,
    declared_non_sensitive: bool,
    allow_real: bool,
    llm_config: Any,
    cwd: Path | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    """组合 input 分类 + LLM readiness, 输出 preflight 决策。

    返回 dict 包含:

    - ``input``: { path, classification }
    - ``provider``: opt_in_state / can_run_real_smoke (复用 readiness)
    - ``intent``: { allow_real, declared_non_sensitive }
    - ``decision``: { allowed: bool, blockers: list[str] }
    - ``output_contract``: 永久 review-only 的字段 (无 human_approved)

    决策规则:

    - input classification 在 _REFUSING_CLASSES 中 → refused
      (无论 allow_real 如何);
    - allow_real=True 且 LLM readiness 不是 ``ready`` → 加 blocker
      但不一定 refused (用户可以选择只跑 fake preview);
    - 默认 allowed=True 仅在 input classification ∈ {synthetic,
      non_sensitive_local} 时成立。
    """
    # 复用 v0.13 Stage 1 的 readiness 模块, 不重复实现 LLM 状态分类。
    from .provider_readiness import build_readiness_report

    classification = classify_input_path(
        input_path,
        declared_non_sensitive=declared_non_sensitive,
        cwd=cwd,
        home=home,
    )
    readiness = build_readiness_report(llm_config)

    blockers: list[str] = []
    if classification in _REFUSING_CLASSES:
        blockers.append(f"input classification={classification!r}")
    if declared_non_sensitive and classification == CLASS_PRIVATE_REAL_DATA_FORBIDDEN:
        # 防御: declared_non_sensitive 不应该绕过更高优先级的拒绝
        blockers.append(
            "declared_non_sensitive flag does not override forbidden classification"
        )
    if allow_real and not readiness["opt_in"]["can_run_real_smoke"]:
        blockers.append(
            f"allow_real=True but provider readiness opt_in_state="
            f"{readiness['opt_in']['opt_in_state']!r}; cannot run real provider"
        )

    allowed = (
        not blockers
        and classification in {CLASS_SYNTHETIC, CLASS_NON_SENSITIVE_LOCAL}
    )

    return {
        "input": {
            "path": str(input_path),
            "classification": classification,
        },
        "provider": {
            "opt_in_state": readiness["opt_in"]["opt_in_state"],
            "can_run_real_smoke": readiness["opt_in"]["can_run_real_smoke"],
            "active_profile": readiness["provider"]["active_profile"],
        },
        "intent": {
            "allow_real": allow_real,
            "declared_non_sensitive": declared_non_sensitive,
        },
        "decision": {
            "allowed": allowed,
            "blockers": blockers,
        },
        # 永久契约 — 任何调用 preflight 的命令都不应该写 vault / approve /
        # 标 human_approved。这些字段是文档化承诺, 不是开关。
        "output_contract": {
            "artifact_type": "review_packet" if allowed else "preflight_refusal",
            "writes_vault": False,
            "writes_cards": False,
            "approves": False,
            "human_approved": False,
        },
    }


def render_preflight_report(report: dict[str, Any]) -> str:
    """人类可读的 preflight 报告; 不含任何 secret value。"""
    lines = ["MindForge dogfood preflight", "=" * 40]
    lines.append(f"input.path           : {report['input']['path']}")
    lines.append(f"input.classification : {report['input']['classification']}")
    lines.append(f"provider.profile     : {report['provider']['active_profile']}")
    lines.append(f"provider.opt_in_state: {report['provider']['opt_in_state']}")
    lines.append(
        f"provider.can_run_real: {report['provider']['can_run_real_smoke']}"
    )
    lines.append(f"intent.allow_real    : {report['intent']['allow_real']}")
    lines.append(
        f"intent.non_sensitive : {report['intent']['declared_non_sensitive']}"
    )
    lines.append(f"decision.allowed     : {report['decision']['allowed']}")
    if report["decision"]["blockers"]:
        lines.append("decision.blockers    :")
        for b in report["decision"]["blockers"]:
            lines.append(f"  - {b}")
    lines.append(
        f"output_contract      : artifact_type="
        f"{report['output_contract']['artifact_type']}, "
        f"human_approved=False, writes_vault=False"
    )
    return "\n".join(lines)


__all__ = [
    "classify_input_path",
    "build_preflight_report",
    "render_preflight_report",
    "CLASS_SYNTHETIC",
    "CLASS_NON_SENSITIVE_LOCAL",
    "CLASS_PRIVATE_REAL_DATA_FORBIDDEN",
    "CLASS_OBSIDIAN_VAULT_FORBIDDEN",
    "CLASS_HOME_SCAN_FORBIDDEN",
    "CLASS_PATH_DOES_NOT_EXIST",
]
