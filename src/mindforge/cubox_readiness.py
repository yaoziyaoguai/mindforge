"""Cubox readiness 报告 — Cubox real-API opt-in 安全审计模块。

为什么单独一个 cubox_readiness 模块?
=====================================

到 v0.13 闭环为止, MindForge 的 Cubox 路径已经具备:

- ``CuboxApiAdapter.parse_export``: 离线解析 Cubox JSON export
  (real Cubox 数据, 零网络);
- ``CuboxApiAdapter.fetch_inbox``: 显式 ``NotImplementedError``,
  作为未来 G1 真实 HTTP API 的 opt-in 闸门;
- ``CuboxApiCredential.__repr__``: secret-safe (永不打印 token);
  用真实 Cubox export 做内部 fixture/preflight 验证, 不联网。

但 **没有** 一个面向新用户与测试的统一入口告诉:

- "我配置的 Cubox token 环境变量到底有没有生效?"
- "当前 Cubox 真实 API gate 是否仍关闭?"
- "future G1 真实 HTTP API 的解锁条件还差什么?"

这就是 ``cubox_readiness`` 的唯一职责: 把 "有没有 token / 有没有
explicit opt-in / G1 gate 是否打开" 翻译成 **不含 secret value 的
readiness 报告**, 供 CLI 渲染、tests 断言。它本身 **不调用** 任何
真实 Cubox API, 不读取 ``.env`` 文件内容, 不持有任何 secret value。

本模块的硬边界 (高内聚 + 信息隐藏)
==================================

- **只** 通过 ``os.environ.__contains__`` 与 ``os.environ.get``
  bool 判断检查 env 是否存在 (presence-only); **永远不** 把 env
  value 放进返回值, **永远不** 打印 value;
- **只** 返回 ``dict`` (report) 与 ``str`` (rendered text);
- **不** 构造 ``CuboxApiAdapter`` 实例;
- **不** 调用 ``parse_export`` / ``fetch_inbox``;
- **不** 触碰 dotenv / 真实文件系统 / 网络;
- **不** import ``cli`` / ``approval_service`` / ``writer`` /
  ``cards`` / ``obsidian*`` / ``provider_readiness`` / ``llm`` /
  ``scanner`` / ``env_loader`` / ``requests`` / ``httpx`` /
  ``urllib.request`` / ``subprocess`` / ``cubox_api`` 实现细节。

报告字段不含任何 approve-flag 字面量为 ``True`` 的可能 — readiness
报告永远是 review-only 工件, 永不产生 ``human_approved``。

设计参照
========

与 ``provider_readiness.py`` 同款架构: 纯数据 + 纯渲染 +
opt-in 状态机。这种对称让 CLI / tests / 未来 UI 用同一种方式消费
provider readiness 与 cubox readiness, 降低认知负担。
"""

from __future__ import annotations

import os
from typing import Literal

CuboxOptInState = Literal[
    "json_export_default",   # 默认安全路径: 用 cubox dry-run 跑本地 JSON export
    "token_env_only",        # token env var 存在, 但用户未 --allow-real → 误以为开了
    "ready_for_future_g1",   # token env var 存在 + 用户 --allow-real → 满足 G1 解锁条件
    "blocked",               # token env var 名称非法 / 缺失等
]


def inspect_cubox_config(*, token_env_var: str = "MINDFORGE_CUBOX_TOKEN") -> dict[str, object]:
    """检查 Cubox 真实 API opt-in 状态, 返回 presence-only 元数据报告。

    参数
    ----
    token_env_var:
        用户**显式指定**的环境变量名。默认 ``MINDFORGE_CUBOX_TOKEN``,
        但允许用户传任意名字; 与 ``CuboxApiCredential.from_env`` 的
        显式约定一致, 永不查找隐式默认变量名 (例如 ``CUBOX_TOKEN``)
        以避免与无关项目的 env 冲突。

    返回字段
    --------
    - ``token_env_var``: 用户传入的变量名 (字面量, 非 value)
    - ``token_present``: bool — env 中是否存在该 var
    - ``json_export_path_recommended``: 内部说明，不是用户命令
    - ``g1_gate_open``: bool — 永远 False (G1 当前未开放)
    - ``hint``: 中英短提示, 不含 token value

    安全保证
    --------
    - 不返回任何 env value;
    - 不读取 ``.env`` 文件;
    - 不构造 ``CuboxApiAdapter``;
    - 不发起任何网络调用;
    - 永远不可能在返回值里出现 token 字面量。
    """
    if not token_env_var or not isinstance(token_env_var, str):
        return {
            "token_env_var": "",
            "token_present": False,
            "json_export_path_recommended": "offline JSON export remains internal-only",
            "g1_gate_open": False,
            "blocked_reason": "token_env_var must be a non-empty string",
        }

    # presence-only: 永不把 value 取出来; 即便取出来也立刻丢弃。
    token_present = token_env_var in os.environ and bool(os.environ.get(token_env_var, ""))

    return {
        "token_env_var": token_env_var,
        "token_present": token_present,
        "json_export_path_recommended": "offline JSON export remains internal-only",
        "g1_gate_open": False,  # G1 真实 HTTP API 路径在本仓库内未开放
    }


def classify_cubox_real_opt_in(
    report: dict[str, object],
    *,
    allow_real: bool,
) -> dict[str, object]:
    """把 inspect 报告 + 用户显式 ``allow_real`` flag 翻译成 opt-in 状态。

    设计要点
    --------

    - ``allow_real=False`` → 永远停在安全侧 (不论 token 是否存在);
    - ``allow_real=True`` 且 ``token_present=True`` → 满足 future G1
      解锁条件, 但 G1 gate 在本仓库内仍然关闭 (gate_open=False), 所以
      最终态是 ``ready_for_future_g1``, 而**不是**直接执行真实调用;
    - ``allow_real=True`` 但 ``token_present=False`` → ``blocked``,
      返回 masked 诊断, 不暴露 token value (因为根本没有);
    - 任何分支都附 ``next_action`` 字段, 引导用户走安全路径
      (``cubox dry-run`` 永远是兜底)。
    """
    if report.get("blocked_reason"):
        return {
            "opt_in_state": "blocked",
            "blockers": [str(report["blocked_reason"])],
            "next_action": str(report["json_export_path_recommended"]),
        }

    token_present = bool(report.get("token_present", False))
    if not allow_real:
        return {
            "opt_in_state": "json_export_default" if not token_present else "token_env_only",
            "blockers": [],
            "next_action": str(report["json_export_path_recommended"]),
        }

    if not token_present:
        return {
            "opt_in_state": "blocked",
            "blockers": [
                f"--allow-real requested but env var "
                f"{report.get('token_env_var', '')!r} is not set",
            ],
            "next_action": str(report["json_export_path_recommended"]),
        }

    return {
        "opt_in_state": "ready_for_future_g1",
        "blockers": [
            "G1 (real Cubox HTTP ingestion) is future-gated; this readiness "
            "check confirms preconditions only — no network call is made",
        ],
        "next_action": str(report["json_export_path_recommended"]),
    }


def render_cubox_readiness_report(
    report: dict[str, object],
    classification: dict[str, object],
) -> str:
    """渲染 readiness 报告为人类可读文本; 永不打印 token value。

    输出格式刻意保留固定字面量 (例如 ``cubox-real-opt-in``,
    ``token value not printed``, ``human approval required``,
    ``json export remains offline-only``), 让测试 / 文档可
    以稳定断言, 防止 wording 漂移。
    """
    lines: list[str] = []
    lines.append("MindForge Cubox readiness (cubox-real-opt-in)")
    lines.append("==============================================")
    lines.append(f"token_env_var:           {report.get('token_env_var', '')!r}")
    lines.append(f"token_present:           {bool(report.get('token_present', False))}")
    lines.append("token value not printed")
    lines.append(f"g1_gate_open:            {bool(report.get('g1_gate_open', False))}")
    lines.append("")
    lines.append(f"opt_in_state:            {classification.get('opt_in_state', '')}")
    blockers = classification.get("blockers") or []
    if blockers:
        lines.append("blockers:")
        for b in blockers:
            lines.append(f"  - {b}")
    lines.append("")
    lines.append("Offline fixture path (works today):")
    lines.append("  json export remains offline-only")
    lines.append(f"  -> {classification.get('next_action', '')}")
    lines.append("")
    lines.append("Boundaries:")
    lines.append("  - human approval required for any human_approved record")
    lines.append("  - real Cubox HTTP API path is future-gated (G1)")
    lines.append("  - no .env content is read or printed by this command")
    return "\n".join(lines)


__all__ = [
    "CuboxOptInState",
    "inspect_cubox_config",
    "classify_cubox_real_opt_in",
    "render_cubox_readiness_report",
]
