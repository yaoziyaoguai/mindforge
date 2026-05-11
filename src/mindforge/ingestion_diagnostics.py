"""Human-facing ingestion diagnostics.

中文学习型说明：diagnostics 是 CLI 展示层，不是 provider 或 ingestion 业务层。
它只渲染已经收敛好的失败/跳过事实，不能读取 `.env`，也不能打印 secret。
"""

from __future__ import annotations

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


__all__ = [
    "ProviderFailureDetail",
    "SkippedDocumentDetail",
    "friendly_missing_key_error",
    "print_ingestion_diagnostics",
    "print_provider_failure",
    "provider_failure_detail",
]
