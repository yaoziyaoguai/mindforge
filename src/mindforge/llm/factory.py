"""按 ``LLMConfig`` 构建 alias → Provider 实例字典。"""

from __future__ import annotations

from typing import Any

from .anthropic_compatible import AnthropicCompatibleProvider
from .base import LLMProvider, ProviderError
from .fake import FakeProvider
from .openai_compatible import OpenAICompatibleProvider

_BUILDERS = {
    "openai": lambda mc: OpenAICompatibleProvider.from_model_config(mc),
    "openai_compatible": lambda mc: OpenAICompatibleProvider.from_model_config(mc),
    "anthropic": lambda mc: AnthropicCompatibleProvider.from_model_config(mc),
    "anthropic_compatible": lambda mc: AnthropicCompatibleProvider.from_model_config(mc),
    "fake": lambda mc: FakeProvider(),
}


def build_providers(llm_config: Any) -> dict[str, LLMProvider]:
    """构建当前 ``active_profile`` 实际会用到的 alias 对应的 Provider。

    设计要点：**lazy by profile**。声明在 ``llm.models`` 但当前 profile 不引用的
    alias 不会被实例化，避免逼迫用户为未使用的备选 provider 准备 env / api_key。
    profile 切换后下一次构建会自然包含新 alias。
    """
    active = llm_config.active_profile
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
        builder = _BUILDERS.get(mc.type)
        if builder is None:
            raise ProviderError(
                f"llm.models.{alias}.type={mc.type!r} 未注册；"
                f"已知类型：{sorted(_BUILDERS)}"
            )
        providers[alias] = builder(mc)
    return providers


def build_provider_for_model(model_config: Any) -> LLMProvider:
    """按单个 model config 构建 provider，不读取 processing routing。

    中文学习型说明：processing pipeline 用 ``build_providers`` 只实例化五阶段
    routing 需要的 model；Wiki synthesis 是独立派生视图，不属于 processing
    stage，因此通过本入口按 ``wiki.model`` 直接构建 provider，避免把
    ``wiki_synthesis`` 塞进处理流水线。
    """

    builder = _BUILDERS.get(model_config.type)
    if builder is None:
        raise ProviderError(
            f"llm.models.{model_config.alias}.type={model_config.type!r} 未注册；"
            f"已知类型：{sorted(_BUILDERS)}"
        )
    return builder(model_config)


__all__ = ["build_providers", "build_provider_for_model"]
