"""按 ``LLMConfig`` 构建 alias → Provider 实例字典。"""

from __future__ import annotations

from typing import Any

from .base import LLMProvider, ProviderError
from .fake import FakeProvider
from .openai_compatible import OpenAICompatibleProvider

_BUILDERS = {
    "openai_compatible": lambda mc: OpenAICompatibleProvider.from_model_config(mc),
    "fake": lambda mc: FakeProvider(),
}


def build_providers(llm_config: Any) -> dict[str, LLMProvider]:
    providers: dict[str, LLMProvider] = {}
    for alias, mc in llm_config.models.items():
        builder = _BUILDERS.get(mc.type)
        if builder is None:
            raise ProviderError(
                f"llm.models.{alias}.type={mc.type!r} 未注册；"
                f"已知类型：{sorted(_BUILDERS)}"
            )
        providers[alias] = builder(mc)
    return providers


__all__ = ["build_providers"]
