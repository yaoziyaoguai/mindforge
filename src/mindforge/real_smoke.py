"""Synthetic real-LLM smoke helper — gated, audit-trailed, secret-safe。

为什么单独一个 real_smoke 模块?
===============================

``provider_readiness`` 只回答 "状态如何"; 但用户与测试还需要一个
**可执行的、显式 opt-in 的、最小语义的真实 provider smoke**, 用来:

1. 证明 fake-default 路径与 real-opt-in 路径都是真实存在的;
2. 在 ``--allow-real`` 显式传入时跑一次 synthetic-only 调用, 输出
   review-only artifact;
3. 在任何 guard 失败时返回结构化拒绝原因, 不静默 fallback、不重试
   放大、不打印任何 secret;
4. 输出 audit-trail dict 供测试断言 ``human_approved=False``、
   ``written=False``、``output_artifact == 'ai_draft_preview'``。

本模块的硬边界
==============

- **只** 消费 ``LLMConfig`` 与 ``llm.factory.build_providers``;
- **只** 使用 ``build_synthetic_prompt()`` 返回的硬编码 prompt;
  **不暴露** 任何接受 caller-supplied prompt 的函数;
- **永远不** 在返回值中包含 api_key / 任何 env value;
- **永远不** 把响应写入 cards / vault / approval / repo;
- **永远不** 把 ``human_approved`` 字段返回为 ``True``;
- **不** import ``cli`` / ``approval_service`` / ``writer`` / ``cards``
  / ``obsidian*`` / ``cubox*`` / ``scanner`` / ``env_loader`` /
  ``requests`` / ``httpx`` / ``subprocess`` / ``dotenv``;
- **可以** import ``llm.factory`` 与 ``llm.base`` (LLMRequest/LLMResult/
  ProviderError) — 这是 provider 标准契约入口, 不是绕过 factory。

调用 LLM 这件事本身由 ``llm.factory`` 内部封装的 provider 完成 —
本模块只编排 "是否允许 + 如何 audit + 如何脱敏摘要", 不直接发 HTTP。
"""

from __future__ import annotations

import re
from typing import Any

# 硬编码 synthetic prompt — 不接受外部输入, 不引用任何用户私人内容。
_SYNTHETIC_PROMPT = (
    "Summarise in one short paragraph why a knowledge-review workflow "
    "should always require explicit human approval before promoting "
    "an AI draft into permanent personal knowledge. Use neutral, "
    "non-personal language."
)

# 防御性 secret pattern: 即使 provider 响应里意外出现疑似 key, 也截断。
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?:Bearer\s+)[A-Za-z0-9._\-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
]
_EXCERPT_MAX_CHARS = 240


def build_synthetic_prompt() -> str:
    """返回硬编码 synthetic prompt。无参数; 无 caller 注入面。"""
    return _SYNTHETIC_PROMPT


def _scrub_excerpt(text: str) -> str:
    """对 provider 返回内容做最后一道脱敏 + 截断。"""
    if not text:
        return ""
    scrubbed = text
    for pat in _SECRET_PATTERNS:
        scrubbed = pat.sub("<redacted>", scrubbed)
    if len(scrubbed) > _EXCERPT_MAX_CHARS:
        scrubbed = scrubbed[:_EXCERPT_MAX_CHARS] + "…(truncated)"
    return scrubbed


def _refuse(reason: str, *, opt_in_state: str | None = None) -> dict[str, Any]:
    """构造拒绝运行的 audit-trail。所有字段都是 review-only。"""
    return {
        "ran": False,
        "blocker": reason,
        "opt_in_state": opt_in_state,
        "provider_type": None,
        "alias": None,
        "output_artifact": None,
        "output_excerpt_safe": None,
        "human_approved": False,
        "written": False,
        "synthetic_input_only": True,
    }


def _ready_opt_in_state_or_refusal(llm_config: Any, *, allow_real: bool) -> tuple[str, dict[str, Any] | None]:
    if not allow_real:
        return "", _refuse("--allow-real flag not provided (default safe refusal)")

    # 复用 readiness 模块做状态分类, 避免重复实现。
    from .provider_readiness import build_readiness_report

    report = build_readiness_report(llm_config)
    opt_in_state = report["opt_in"]["opt_in_state"]
    if opt_in_state != "ready":
        return opt_in_state, _refuse(
            f"opt_in_state={opt_in_state!r}; need 'ready' "
            "(active_profile != fake AND target alias api_key present)",
            opt_in_state=opt_in_state,
        )
    return opt_in_state, None


def _select_smoke_alias(
    llm_config: Any,
    *,
    alias: str | None,
    opt_in_state: str,
) -> tuple[str | None, dict[str, Any] | None]:
    profile = llm_config.profiles[llm_config.active_profile]
    candidates = [a for a in profile.values() if llm_config.models[a].type != "fake"]
    if alias is None:
        if not candidates:
            return None, _refuse("no non-fake alias in active profile", opt_in_state=opt_in_state)
        return candidates[0], None
    if alias not in candidates:
        return None, _refuse(
            f"alias {alias!r} not in active profile or is fake type",
            opt_in_state=opt_in_state,
        )
    return alias, None


def _build_smoke_provider(
    llm_config: Any,
    *,
    alias: str,
    opt_in_state: str,
) -> tuple[Any | None, dict[str, Any] | None]:
    # 真实调用 — 通过 factory 走标准路径; build_providers lazy-by-profile,
    # 只构造 active 的 alias。
    from .llm.factory import build_providers

    try:
        providers = build_providers(llm_config)
    except Exception as exc:
        return None, _refuse(
            f"provider construction failed: {type(exc).__name__}",
            opt_in_state=opt_in_state,
        )

    provider = providers.get(alias)
    if provider is None:
        return None, _refuse(f"provider for alias {alias!r} not built", opt_in_state=opt_in_state)
    return provider, None


def _build_smoke_request(mc: Any, *, alias: str, opt_in_state: str) -> tuple[Any | None, dict[str, Any] | None]:
    # provider 的标准入口是 ``LLMProvider.generate(LLMRequest) -> LLMResult``
    # (见 src/mindforge/llm/base.py)。real_smoke 必须严格走这个契约,
    # 否则会与 fake provider / OpenAICompatibleProvider /
    # AnthropicCompatibleProvider 全部解耦, 测试 stub 与真实 provider
    # 行为也会漂移。
    from .llm.base import LLMRequest

    try:
        return LLMRequest(
            prompt=build_synthetic_prompt(),
            stage="provider_smoke",
            model=mc.model or alias,
            max_tokens=128,
            temperature=0.0,
        ), None
    except Exception as exc:
        return None, _refuse(
            f"LLMRequest construction failed: {type(exc).__name__}",
            opt_in_state=opt_in_state,
        )


def _call_smoke_provider(provider: Any, request: Any, *, opt_in_state: str) -> tuple[Any | None, dict[str, Any] | None]:
    from .llm.base import ProviderError

    try:
        return provider.generate(request), None
    except ProviderError as exc:
        # ProviderError 是已知的 provider-layer 失败 (网络/鉴权/4xx/5xx);
        # 这里不重试, 不把 message 原样回显 (可能含 server 返回信息),
        # 只暴露异常类型, 避免意外泄漏。
        return None, _refuse(
            f"provider call failed (ProviderError): {type(exc).__name__}",
            opt_in_state=opt_in_state,
        )
    except Exception as exc:
        return None, _refuse(
            f"provider call failed: {type(exc).__name__}",
            opt_in_state=opt_in_state,
        )


def _result_metadata(result: Any) -> tuple[str, int | None, int | None, int | None]:
    # 容忍既符合 LLMResult 契约的真实 provider, 也允许返回 raw string
    # 的旧式 stub (向后兼容历史 test fixture)。
    from .llm.base import LLMResult

    if isinstance(result, LLMResult):
        return result.text, result.tokens_in, result.tokens_out, result.latency_ms
    return str(result) if result is not None else "", None, None, None


def _success_audit(
    *,
    opt_in_state: str,
    provider_type: str,
    alias: str,
    result: Any,
) -> dict[str, Any]:
    text, tokens_in, tokens_out, latency_ms = _result_metadata(result)
    return {
        "ran": True,
        "blocker": None,
        "opt_in_state": opt_in_state,
        "provider_type": provider_type,
        "alias": alias,
        "output_artifact": "ai_draft_preview",
        "output_excerpt_safe": _scrub_excerpt(text),
        # 真实调用的可观察 metadata; 这些字段不含 secret, 可以安全输出。
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        # 永久 False — 类型契约即文档。
        "human_approved": False,
        "written": False,
        "synthetic_input_only": True,
    }


def run_synthetic_real_smoke(
    llm_config: Any,
    *,
    allow_real: bool,
    alias: str | None = None,
) -> dict[str, Any]:
    """显式 opt-in 的最小真实 provider smoke。

    Guards (全部满足才执行):

    1. ``allow_real is True`` (调用方显式传入);
    2. ``llm_config.active_profile != 'fake'`` (profile 已切换);
    3. 目标 alias 在当前 profile 中且 ``type != 'fake'``;
    4. 目标 alias 的 ``api_key_env`` 在 ``os.environ`` 中存在
       (presence-only; 不读取 value, value 由 provider 内部按 env_var
       自行获取)。

    任意 guard 失败 → 返回 ``ran=False`` + ``blocker``; 不抛异常,
    不重试。

    Returns:
        audit-trail dict (字段见 ``_refuse`` / 成功路径)。
    """
    opt_in_state, refusal = _ready_opt_in_state_or_refusal(llm_config, allow_real=allow_real)
    if refusal is not None:
        return refusal

    alias, refusal = _select_smoke_alias(llm_config, alias=alias, opt_in_state=opt_in_state)
    if refusal is not None:
        return refusal
    assert alias is not None
    mc = llm_config.models[alias]

    provider, refusal = _build_smoke_provider(llm_config, alias=alias, opt_in_state=opt_in_state)
    if refusal is not None:
        return refusal
    request, refusal = _build_smoke_request(mc, alias=alias, opt_in_state=opt_in_state)
    if refusal is not None:
        return refusal
    result, refusal = _call_smoke_provider(provider, request, opt_in_state=opt_in_state)
    if refusal is not None:
        return refusal
    return _success_audit(
        opt_in_state=opt_in_state,
        provider_type=mc.type,
        alias=alias,
        result=result,
    )


__all__ = [
    "build_synthetic_prompt",
    "run_synthetic_real_smoke",
]
