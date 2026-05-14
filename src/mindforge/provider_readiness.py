"""Provider readiness 报告 — fake-default + real-opt-in 安全审计模块。

为什么单独一个 provider_readiness 模块?
=======================================

到 v0.13 Stage 0 为止, MindForge 的 provider 路径已经具备:

- ``llm/factory.build_providers`` lazy 构建 (仅 ``active_profile`` 涉及
  的 alias 实例化);
- ``configs/mindforge.yaml`` 默认 ``active_profile: fake``;
- ``env_loader`` 静默加载 .env, 不打印任何 KEY/VALUE。

但 **没有** 一个面向用户与测试的统一入口告诉:

- 当前是不是 fake-default;
- 真实 provider opt-in 是 partially-ready / fully-ready / blocked;
- 哪些 alias 缺 api_key (presence-only, 永不返回 value);
- 调用方应不应该被允许触发真实 LLM smoke。

这就是 ``provider_readiness`` 的唯一职责: 把 ``LLMConfig`` 翻译成
**不含 secret value 的 readiness 报告**, 供 CLI 渲染、tests 断言、
未来 UI 消费。它本身 **不调用** 任何真实 provider, 不构造 LLM
client。

本模块的硬边界 (高内聚 + 信息隐藏)
==================================

- **只** 消费 ``LLMConfig`` (来自 ``config.py``);
- **只** 通过 ``os.environ.__contains__`` 检查 env 是否存在
  (presence-only); **永远不** 读取或返回 env value;
- **只** 返回 ``dict`` (report) 与 ``str`` (rendered text);
- **不** 构造任何 LLM client / provider;
- **不** 调用 ``card-writer`` / ``approval-service`` / cli;
- **不** 触碰 dotenv / 真实文件系统 / 网络;
- **不** import ``cli`` / ``approval_service`` / ``writer`` / ``cards``
  / ``obsidian*`` / ``cubox*`` / ``scanner`` / ``env_loader`` /
  ``requests`` / ``httpx`` / ``subprocess``。

报告字段不含任何 approve-flag 字面量为 ``True`` 的可能 — readiness
报告永远是 review-only 工件。
"""

from __future__ import annotations

import os
from typing import Any, Literal

OptInState = Literal[
    "fake_default",   # active_profile == fake; 真实路径完全未启用
    "env_only",       # api_key 在 env 中, 但 active_profile 仍是 fake → 误以为开了
    "profile_only",   # active_profile != fake, 但 alias api_key 缺失 → 不可用
    "ready",          # active_profile != fake 且全部 alias api_key 存在
    "blocked",        # 部分 alias 配置异常 (例: 缺 api_key_env 配置项)
]


def inspect_provider_config(llm_config: Any) -> dict[str, Any]:
    """检查 ``LLMConfig`` 状态, 返回 presence-only 元数据报告。

    返回字段:

    - ``active_profile``: str
    - ``aliases``: list[dict] — 每项 ``{alias, type, api_key_env,
      api_key_present, base_url_env_present, in_active_profile}``
    - ``active_alias_count``: int
    - ``active_aliases_missing_key``: list[str]

    安全保证:

    - 不返回任何 env value;
    - 不读取 .env 文件;
    - 不构造 provider;
    - 不发起任何网络调用。
    """
    active_profile = llm_config.active_profile
    profile = llm_config.profiles.get(active_profile, {})
    active_aliases = set(profile.values())

    aliases: list[dict[str, Any]] = []
    missing_in_active: list[str] = []

    for alias, mc in sorted(llm_config.models.items()):
        api_key_env = getattr(mc, "api_key_env", None)
        base_url_env = getattr(mc, "base_url_env", None)
        # presence-only: 仅判断 env var 是否存在, 永不取值。
        # presence-only：env 可以检查变量是否存在；secret store 不在本模块读取，
        # 避免 readiness 诊断触碰 raw secret 文件内容。
        api_key_present = bool(api_key_env) and api_key_env in os.environ
        base_url_env_present = bool(base_url_env) and base_url_env in os.environ
        in_active = alias in active_aliases

        aliases.append(
            {
                "alias": alias,
                "type": mc.type,
                "api_key_env": api_key_env,
                "api_key_present": api_key_present,
                "base_url_env_present": base_url_env_present,
                "in_active_profile": in_active,
            }
        )

        if (
            in_active
            and mc.type != "fake"
            and not getattr(mc, "api_key_optional", False)
            and not api_key_present
        ):
            missing_in_active.append(alias)

    return {
        "active_profile": active_profile,
        "aliases": aliases,
        "active_alias_count": len(active_aliases),
        "active_aliases_missing_key": missing_in_active,
    }


def classify_real_opt_in(report: dict[str, Any]) -> dict[str, Any]:
    """根据 ``inspect_provider_config`` 的结果分类 opt-in 状态。

    返回 ``{opt_in_state, blockers, can_run_real_smoke}``。
    """
    active_profile = report["active_profile"]
    aliases = report["aliases"]
    missing = report["active_aliases_missing_key"]

    blockers: list[str] = []
    state: OptInState

    is_fake_profile = active_profile == "fake"
    any_real_alias_in_profile = any(
        a["in_active_profile"] and a["type"] != "fake" for a in aliases
    )
    any_api_key_anywhere = any(a["api_key_present"] for a in aliases)

    if is_fake_profile and not any_real_alias_in_profile:
        if any_api_key_anywhere:
            state = "env_only"
            blockers.append(
                "active_profile=fake; env 中存在 api_key 但未切换 profile, "
                "real provider 未启用 (这是默认安全状态)"
            )
        else:
            state = "fake_default"
    elif any_real_alias_in_profile and missing:
        state = "profile_only"
        for alias in missing:
            blockers.append(f"alias {alias!r} 缺少 api_key (env 不存在)")
    elif any_real_alias_in_profile and not missing:
        state = "ready"
    else:
        state = "blocked"
        blockers.append("provider 配置无法分类: 既非 fake 也无可用真实 alias")

    return {
        "opt_in_state": state,
        "blockers": blockers,
        # readiness 仅声明 "条件齐全, 可被允许触发"; 实际触发还需调用方传 allow_real。
        "can_run_real_smoke": state == "ready",
    }


def build_readiness_report(llm_config: Any) -> dict[str, Any]:
    """组合 inspect + classify, 返回完整 readiness 报告。

    报告 schema:

    - ``provider``: ``inspect_provider_config`` 输出
    - ``opt_in``: ``classify_real_opt_in`` 输出
    - ``invariants``: 固定声明字段, 供 tests 断言
    """
    provider = inspect_provider_config(llm_config)
    opt_in = classify_real_opt_in(provider)
    return {
        "provider": provider,
        "opt_in": opt_in,
        "invariants": {
            "fake_is_default": True,
            "secret_value_not_returned": True,
            "human_approval_required": True,
            "synthetic_only_smoke_input": True,
            "real_output_is_review_only": True,
        },
    }


def render_readiness_report(report: dict[str, Any]) -> str:
    """把 readiness 报告渲染为人类可读纯文本。

    渲染必含的固定 token (供 tests 与文档稳定):

    - ``fake-default``
    - ``real provider opt-in``
    - ``secret value not printed``
    - ``human approval required``
    - ``synthetic-only smoke input``
    """
    provider = report["provider"]
    opt_in = report["opt_in"]

    lines: list[str] = []
    lines.append("MindForge provider readiness report")
    lines.append("=" * 40)
    lines.append(f"active_profile: {provider['active_profile']}")
    lines.append(f"opt_in_state: {opt_in['opt_in_state']}")
    lines.append(f"can_run_real_smoke: {opt_in['can_run_real_smoke']}")
    lines.append("")
    lines.append("Invariants:")
    lines.append("  - fake-default (default safe path is fake provider)")
    lines.append("  - real provider opt-in (must switch active_profile + pass --allow-real)")
    lines.append("  - secret value not printed (api_key presence only, never value)")
    lines.append("  - human approval required (real output never becomes human_approved)")
    lines.append("  - synthetic-only smoke input (real smoke uses hard-coded prompt)")
    lines.append("")
    lines.append("Aliases:")
    for a in provider["aliases"]:
        marker = "*" if a["in_active_profile"] else " "
        lines.append(
            f"  {marker} {a['alias']:<20} type={a['type']:<22} "
            f"api_key_present={a['api_key_present']}"
        )
    if opt_in["blockers"]:
        lines.append("")
        lines.append("Blockers:")
        for b in opt_in["blockers"]:
            lines.append(f"  - {b}")
    return "\n".join(lines)


__all__ = [
    "OptInState",
    "inspect_provider_config",
    "classify_real_opt_in",
    "build_readiness_report",
    "render_readiness_report",
]
