"""按 ``LLMConfig`` 构建 alias → Provider 实例字典。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mindforge.config import REQUIRED_STAGES

from .anthropic_compatible import AnthropicCompatibleProvider
from .base import LLMProvider, ProviderError
from .fake import FakeProvider
from .openai_compatible import OpenAICompatibleProvider


def _make_builder(mc_type: str):
    """返回闭包 builder，但允许 call site 注入 ``project_root``。

    设计要点：``_BUILDERS`` 原来用 lambda 捕获 mc_type，
    但不支持 ``project_root`` 注入。改为在 ``_build_provider``
    中按 type 分发，统一接受 ``project_root``。
    """
    if mc_type == "fake":
        return lambda mc, **kw: FakeProvider()
    if mc_type in ("openai", "openai_compatible"):
        return lambda mc, *, project_root=None, **kw: OpenAICompatibleProvider.from_model_config(
            mc, project_root=project_root
        )
    if mc_type in ("anthropic", "anthropic_compatible"):
        return lambda mc, *, project_root=None, **kw: AnthropicCompatibleProvider.from_model_config(
            mc, project_root=project_root
        )
    return None


def build_providers(
    llm_config: Any,
    *,
    project_root: Path | None = None,
) -> dict[str, LLMProvider]:
    """构建当前 processing routing 实际会用到的 alias 对应的 Provider。

    设计要点：**lazy by resolved stage routing**。声明在 ``llm.models`` 但五段
    processing 不引用的 alias 不会被实例化，避免逼迫用户为未使用的备选
    provider 准备 env / api_key。新 llm.routing 缺省时由 ``resolve_stage_alias``
    回退到 default_model；旧 profiles 仅作为兼容来源。
    """
    active = llm_config.active_profile
    if hasattr(llm_config, "resolve_stage_alias"):
        needed_aliases = {llm_config.resolve_stage_alias(stage) for stage in REQUIRED_STAGES}
    else:
        profile = llm_config.profiles.get(active, {})
        needed_aliases = set(profile.values())

    providers: dict[str, LLMProvider] = {}
    for alias in needed_aliases:
        mc = llm_config.models.get(alias)
        if mc is None:
            raise ProviderError(
                f"profile {active!r} 引用了未声明的 model alias={alias!r}；"
                f"请在 llm.models 下补充该 alias"
            )
        builder = _make_builder(mc.type)
        if builder is None:
            raise ProviderError(
                f"llm.models.{alias}.type={mc.type!r} 未注册；"
                f"已知类型：{sorted({t for t in ('openai', 'openai_compatible', 'anthropic', 'anthropic_compatible', 'fake')})}"
            )
        providers[alias] = builder(mc, project_root=project_root)
    return providers


def build_provider_for_model(
    model_config: Any,
    *,
    project_root: Path | None = None,
) -> LLMProvider:
    """按单个 model config 构建 provider，不读取 processing routing。

    中文学习型说明：processing pipeline 用 ``build_providers`` 只实例化五阶段
    routing 需要的 model；Wiki synthesis 是独立派生视图，不属于 processing
    stage，因此通过本入口按 ``wiki.model`` 直接构建 provider，避免把
    ``wiki_synthesis`` 塞进处理流水线。
    """

    builder = _make_builder(model_config.type)
    if builder is None:
        raise ProviderError(
            f"llm.models.{model_config.alias}.type={model_config.type!r} 未注册；"
            f"已知类型：{sorted({t for t in ('openai', 'openai_compatible', 'anthropic', 'anthropic_compatible', 'fake')})}"
        )
    return builder(model_config, project_root=project_root)


__all__ = ["build_providers", "build_provider_for_model"]
