"""Human-facing ingestion diagnostics.

中文学习型说明：diagnostics 是 CLI 展示层，不是 provider 或 ingestion 业务层。
它只渲染已经收敛好的失败/跳过事实，不能读取 `.env`，也不能打印 secret。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rich.console import Console

from .config import MindForgeConfig


@dataclass(frozen=True)
class ProviderFailureDetail:
    selected_provider: str
    provider_type: str
    selection_source: str
    config_path: str
    active_vault: str
    missing_env_var: str | None
    base_url_source: str
    model_source: str
    message: str


@dataclass(frozen=True)
class SkippedDocumentDetail:
    source_path: str
    normalized_path: str
    source_id_short: str
    fingerprint_short: str
    reason: str
    matched_record: str | None = None
    hint: str | None = None


MODEL_SETUP_INCOMPLETE_MESSAGE = (
    "Model setup is incomplete. Add a provider API key in Web Setup or the "
    "local secret store, then retry processing."
)


def provider_failure_detail(cfg: MindForgeConfig, message: str) -> ProviderFailureDetail:
    """把 provider 构建失败转为可诊断但不泄密的结构。

    中文学习型说明：这里只检查 selected provider 涉及的 model/env。不能检查
    所有 providers，也不能 fallback 到 fake，否则用户会误以为 real LLM 已经跑通。
    """

    selected = cfg.llm.active_profile
    aliases = cfg.llm.profiles.get(selected, {})
    first_alias = next(iter(aliases.values()), "")
    model = cfg.llm.models.get(first_alias)
    missing_env = missing_env_from_message(message)
    provider_type = display_provider_type(model.type if model is not None else selected)
    config_path = _config_path(cfg)
    return ProviderFailureDetail(
        selected_provider=selected,
        provider_type=provider_type,
        selection_source=selection_source(cfg),
        config_path=config_path,
        active_vault=str(cfg.vault.root),
        missing_env_var=missing_env,
        base_url_source=config_or_default(getattr(model, "base_url", None) if model else None),
        model_source=config_or_default(getattr(model, "model", None) if model else None),
        message=friendly_missing_key_error(message) or message,
    )


def print_ingestion_diagnostics(console: Console, summary) -> None:
    provider = getattr(summary, "provider_failure", None)
    if provider is not None:
        print_provider_failure(console, provider)
    if getattr(summary, "skipped", ()):
        console.print("[bold]Skipped documents:[/bold]")
        for item in summary.skipped:
            console.print(f"- source path: {item.source_path}", markup=False, soft_wrap=True)
            console.print(f"  normalized path: {item.normalized_path}", markup=False, soft_wrap=True)
            console.print(f"  source id: {item.source_id_short}", markup=False)
            console.print(f"  fingerprint: {item.fingerprint_short}", markup=False)
            console.print(f"  reason: {item.reason}", markup=False)
            if item.matched_record:
                console.print(f"  matched state key: {item.matched_record}", markup=False, soft_wrap=True)
            if item.hint:
                console.print(f"  hint: {item.hint}", markup=False, soft_wrap=True)


def print_provider_failure(console: Console, provider: ProviderFailureDetail) -> None:
    console.print("[bold]Provider failure[/bold]")
    console.print(f"selected provider: {provider.selected_provider}", markup=False)
    console.print(f"provider type: {provider.provider_type}", markup=False)
    console.print(f"selection source: {provider.selection_source}", markup=False)
    console.print(f"config path: {provider.config_path}", markup=False, soft_wrap=True)
    console.print(f"active vault: {provider.active_vault}", markup=False, soft_wrap=True)
    console.print(f"base_url source: {provider.base_url_source}", markup=False)
    console.print(f"model source: {provider.model_source}", markup=False)
    console.print(provider.message, markup=False, soft_wrap=True)


def selection_source(cfg: MindForgeConfig) -> str:
    raw = cfg.raw if isinstance(cfg.raw, dict) else {}
    meta = raw.get("_mindforge_provider_selection")
    if isinstance(meta, dict):
        return str(meta.get("source") or "llm.active")
    return "llm.active"


def display_provider_type(provider_type: str) -> str:
    return "anthropic" if provider_type == "anthropic_compatible" else provider_type


def config_or_default(value: str | None) -> str:
    return "configured" if value else "default"


def missing_env_from_message(message: str) -> str | None:
    return None


def friendly_missing_key_error(message: str) -> str | None:
    if looks_like_missing_key(message):
        return MODEL_SETUP_INCOMPLETE_MESSAGE
    return None


def looks_like_missing_key(message: str) -> bool:
    return (
        "未设置" in message
        or "requires" in message
        or "要求环境变量" in message
        or "没有可用的 API key" in message
        or "API key" in message
    )


def _config_path(cfg: MindForgeConfig) -> str:
    project_meta = cfg.raw.get("_mindforge_project", {}) if isinstance(cfg.raw, dict) else {}
    if isinstance(project_meta, dict) and project_meta.get("config_path"):
        return str(project_meta["config_path"])
    config_meta = cfg.raw.get("_mindforge_config", {}) if isinstance(cfg.raw, dict) else {}
    if isinstance(config_meta, dict) and config_meta.get("path"):
        return str(config_meta["path"])
    return "(unknown)"


# ---------------------------------------------------------------------------
# provider error 分类 —— CLI / Web / API 共用
#
# 中文学习型说明：provider 在 HTTP/client 层抛出的异常信息可能包含 raw
# response body、status code 等，不能直接暴露给用户。这里的分类函数把错误
# 归一化成稳定 error_type + 不泄密的 safe_message，让 CLI、Web run detail、
# API response 使用同一口径，避免各层各自拼文案导致口径分裂。
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderErrorClassification:
    """provider error 的结构化分类结果；不包含 raw payload / secret。"""

    error_type: str
    """稳定分类值：``provider_rate_limited`` / ``provider_quota_exceeded`` /
    ``provider_error`` / ``unknown``。"""

    safe_message: str
    """用户可读的安全消息；不含 raw response body / token / key。"""

    retry_hint: str | None
    """可操作的 retry 建议；由展示层决定是否渲染。"""


# 用于匹配 rate limit 相关模式的编译正则（不区分大小写）。
_RATE_LIMIT_RE = re.compile(
    r"rate.limit|too many requests|429|throttl",
    re.IGNORECASE,
)
_QUOTA_RE = re.compile(
    r"quota.*(exceeded|limit|insufficient)|insufficient.*quota",
    re.IGNORECASE,
)


def classify_provider_error(message: str, status_code: int | None = None) -> ProviderErrorClassification:
    """把 provider error message / status code 分类为稳定 error_type。

    调用方（CLI presenter / Web run detail / API response）都应使用本函数，
    而不是各自 regex 猜测。

    Args:
        message: provider 抛出的错误消息（可能包含 raw response）。
        status_code: HTTP status code（如果可获取）。

    Returns:
        ``ProviderErrorClassification``：稳定 error_type + 不泄密 safe_message。
    """
    # 中文学习型说明：只匹配公认的安全模式；禁止把 raw message 直接拼接进
    # safe_message，防止 provider response body 中的敏感信息泄露给前端。
    if status_code == 429 or _RATE_LIMIT_RE.search(message):
        return ProviderErrorClassification(
            error_type="provider_rate_limited",
            safe_message=(
                "Provider rate limited. Wait a moment and retry, or reduce "
                "concurrency and batch size. If this persists, check your "
                "provider quota and billing status."
            ),
            retry_hint=(
                "Wait 30-60 seconds and retry. Reduce concurrent processing "
                "or split large imports into smaller batches."
            ),
        )
    if _QUOTA_RE.search(message):
        return ProviderErrorClassification(
            error_type="provider_quota_exceeded",
            safe_message=(
                "Provider quota exceeded. Check your quota or billing status "
                "in the provider dashboard, or switch to a different provider."
            ),
            retry_hint=(
                "Verify quota in your provider dashboard. Consider switching "
                "to a different provider or model."
            ),
        )
    # generic provider error：不暴露 raw message，但保留 error_type 区分
    return ProviderErrorClassification(
        error_type="provider_error",
        safe_message=(
            "Provider request failed. Check your model configuration, "
            "API endpoint, and network connectivity."
        ),
        retry_hint=None,
    )


__all__ = [
    "ProviderErrorClassification",
    "ProviderFailureDetail",
    "SkippedDocumentDetail",
    "classify_provider_error",
    "friendly_missing_key_error",
    "print_ingestion_diagnostics",
    "print_provider_failure",
    "provider_failure_detail",
]
