"""LLMClient — 业务唯一入口；按 stage 路由 + 重试 + 结构化结果。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .base import LLMProvider, LLMRequest, LLMResult, ProviderError


@dataclass(frozen=True)
class ResolvedModel:
    """``stage`` → ``model_alias`` → 具体 provider/model 的解析结果。"""

    stage: str
    model_alias: str
    provider: str
    actual_model: str
    type: str


@dataclass(frozen=True)
class StageCallResult:
    """一次 stage 调用的完整结果（路由 + 响应）。"""

    resolved: ResolvedModel
    result: LLMResult


class LLMClient:
    def __init__(
        self,
        *,
        llm_config: Any,
        providers: dict[str, LLMProvider],
    ) -> None:
        self._cfg = llm_config
        self._providers = providers

    def resolve_model_for_stage(self, stage: str) -> ResolvedModel:
        mc = self._cfg.resolve_stage(stage)
        alias = self._cfg.profiles[self._cfg.active_profile][stage]
        # model_env：允许从环境变量覆盖模型名（同 endpoint 切换 fast / strong / deep）
        actual_model = mc.model
        model_env = getattr(mc, "model_env", None)
        if model_env:
            import os
            override = os.environ.get(model_env)
            if override:
                actual_model = override
        return ResolvedModel(
            stage=stage,
            model_alias=alias,
            provider=mc.provider,
            actual_model=actual_model,
            type=mc.type,
        )

    def generate(
        self,
        *,
        stage: str,
        prompt: str,
        options: dict[str, Any] | None = None,
    ) -> StageCallResult:
        resolved = self.resolve_model_for_stage(stage)
        provider = self._providers[resolved.model_alias]
        mc = self._cfg.models[resolved.model_alias]

        opts = options or {}
        request = LLMRequest(
            prompt=prompt,
            stage=stage,
            model=resolved.actual_model,
            temperature=opts.get("temperature"),
            max_tokens=opts.get("max_tokens"),
            response_format=opts.get("response_format"),
        )

        attempts = max(1, mc.max_retries + 1)
        last_err: ProviderError | None = None
        for i in range(attempts):
            try:
                result = provider.generate(request)
                return StageCallResult(resolved=resolved, result=result)
            except ProviderError as e:
                last_err = e
                if i < attempts - 1:
                    time.sleep(0.2 * (i + 1))  # 简单线性退避
        assert last_err is not None
        raise last_err


__all__ = ["LLMClient", "ResolvedModel", "StageCallResult"]
