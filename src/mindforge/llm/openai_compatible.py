"""OpenAI 兼容 provider（覆盖 OpenAI / Ollama / LM Studio 等）。

设计原则
========

- 只覆盖 ``POST {base_url}/chat/completions``；够 v0.1 用。
- 不做 streaming（v0.1 同步即可）。
- 不做 fallback / 多模型投票（路由由 LLMClient + active_profile 决定）。
- ``api_key`` 通过 ``api_key_env`` 环境变量读取；``api_key_optional=True``
  时缺失也允许（典型场景：本地 Ollama）。
- 网络错误 / 4xx / 5xx 统一抛 :class:`ProviderError`，由 LLMClient 处理重试。
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx

from mindforge.provider_defaults import DEFAULT_PROVIDER_TIMEOUT_SECONDS

from .base import LLMProvider, LLMRequest, LLMResult, ProviderError, redact_provider_error_text


class OpenAICompatibleProvider(LLMProvider):
    type = "openai_compatible"

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str | None,
        timeout_seconds: int,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds or DEFAULT_PROVIDER_TIMEOUT_SECONDS

    def __repr__(self) -> str:
        # 主动安全 repr：只暴露 name 与 credential_present 标记，
        # 不暴露 api_key 与 base_url（base_url 可能含内网/代理细节）。
        return (
            f"OpenAICompatibleProvider(name={self.name!r}, "
            f"credential_present={bool(self.api_key)})"
        )

    __str__ = __repr__

    @classmethod
    def from_model_config(cls, mc: Any, *, project_root: Path | None = None) -> OpenAICompatibleProvider:
        # base_url：优先 env，再回落 yaml；type=openai 默认使用 OpenAI 官方 API
        base_url = ""
        if getattr(mc, "base_url_env", None):
            base_url = os.environ.get(mc.base_url_env, "") or ""
        if not base_url:
            base_url = mc.base_url or ""
        if not base_url and getattr(mc, "type", "") == "openai":
            base_url = "https://api.openai.com/v1"
        if not base_url:
            raise ProviderError(
                f"模型 {mc.alias} 未提供 base_url：请设置环境变量 "
                f"{mc.base_url_env or '<base_url_env 未声明>'} 或在 yaml 写 base_url"
            )

        # api_key 解析优先级：env var > workspace secret store > CWD fallback
        # 普通 Web 用户不配置 api_key_env，key 存在 .mindforge/secrets.json。
        # project_root 是 P0-2 修复的关键参数：provider 不再从 CWD 猜 secrets path。
        from mindforge.llm.anthropic_compatible import _resolve_api_key
        api_key = _resolve_api_key(
            mc.alias,
            getattr(mc, "api_key_env", None),
            project_root=project_root,
        )
        if not api_key and not mc.api_key_optional:
            raise ProviderError(
                "Model setup is incomplete. Add a provider API key in Web Setup "
                "or the local secret store, then retry processing."
            )
        return cls(
            name=mc.provider,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=mc.timeout_seconds,
        )

    def generate(self, request: LLMRequest) -> LLMResult:
        url = f"{self.base_url}/chat/completions"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.max_tokens is not None:
            body["max_tokens"] = request.max_tokens
        if request.response_format == "json_object":
            body["response_format"] = {"type": "json_object"}

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=body)
        except httpx.ReadTimeout:
            raise ProviderError(
                "Provider timed out while waiting for the model endpoint. "
                "Check the model endpoint, network/proxy, or increase timeout_seconds, then retry."
            ) from None
        except httpx.HTTPError as e:
            raise ProviderError(f"HTTP 错误：{type(e).__name__}") from None
        latency_ms = int((time.perf_counter() - start) * 1000)

        if resp.status_code >= 400:
            snippet = redact_provider_error_text(resp.text)
            raise ProviderError(f"HTTP {resp.status_code}: {snippet}")

        try:
            data = resp.json()
        except ValueError as e:
            raise ProviderError(f"响应非合法 JSON: {e}") from e

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"响应缺少 choices[0].message.content: {e}") from e

        usage = data.get("usage") or {}
        return LLMResult(
            text=text,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            latency_ms=latency_ms,
            raw=None,  # 故意不保留 raw，避免误把它写入 jsonl
        )


__all__ = ["OpenAICompatibleProvider"]
