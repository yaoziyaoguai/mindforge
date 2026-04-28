"""LLM 抽象 + 多 provider + 静态 stage 路由（M2 引入）。

设计目标
========

把"业务模块"和"具体 LLM 提供方"彻底解耦：

- 业务模块（``triager`` / ``distiller`` / ``linker`` / ``review_questions`` /
  ``action_extraction``）只调用 ``LLMClient.generate(stage, ...)``。
- 它们**不知道**当前 stage 走的是哪个 provider、哪个 model、用了什么 base_url
  或 api_key。这些全部被 ``mindforge.yaml.llm`` 配置 + ``LLMClient`` 内部消化。

为什么这样设计
==============

1. **可替换性**：同一段业务逻辑能在 cloud / local / fake 之间切换，零改码。
2. **可观察性**：每次调用统一打 ``llm_call`` 事件（stage / model_alias /
   provider / actual_model / prompt_version / input_file_hash / tokens /
   latency / status），由 ``run_logger`` 一份白名单字段托底，不会泄漏原文。
3. **v0.1 克制**：**不**做 fallback、投票、智能路由、token-aware routing。
   只做"按 active_profile 把 stage 静态映射成一个 ModelConfig"。
"""

from .base import LLMProvider, LLMRequest, LLMResult, ProviderError
from .client import LLMClient, ResolvedModel, StageCallResult
from .factory import build_providers
from .fake import FakeProvider
from .openai_compatible import OpenAICompatibleProvider

__all__ = [
    "LLMProvider",
    "LLMRequest",
    "LLMResult",
    "ProviderError",
    "FakeProvider",
    "OpenAICompatibleProvider",
    "build_providers",
    "LLMClient",
    "ResolvedModel",
    "StageCallResult",
]
