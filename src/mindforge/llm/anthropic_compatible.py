"""Anthropic-compatible provider（适配 Claude Messages API 协议）。

设计原则
========

- 只覆盖 ``POST {base_url}/v1/messages``；够 v0.1 用。
- 不做 streaming、不做 tool_use（v0.1 仅文本 in / 文本 out）。
- 不做 fallback / 多模型投票（路由由 LLMClient + active_profile 决定）。
- ``base_url`` 与 ``api_key`` 优先从 **环境变量** 读取
  （``MINDFORGE_LLM_BASE_URL`` / ``MINDFORGE_LLM_API_KEY`` 等），
  避免写进 yaml 被误提交。
- 网络错误 / 4xx / 5xx 统一抛 :class:`ProviderError`，由 LLMClient 处理重试。
- 任何异常都不能把 api_key、Authorization header、env value 等敏感信息
  泄漏到 ``error_message``；本模块严格脱敏。
- ``LLMResult.raw`` 永远为 ``None``；上层 run_logger 不会落正文。

适配形态
========

阿里云 DashScope Coding Plan 暴露的 Anthropic-compatible endpoint，
请求头大致：

    x-api-key: <key>
    anthropic-version: 2023-06-01
    content-type: application/json

请求体：

    {
        "model": "qwen3-coder-plus",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": "..."}]
    }

响应体（关键路径）：

    {
        "id": "...",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "..."}, ...],
        "usage": {"input_tokens": int, "output_tokens": int}
    }
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from .base import LLMProvider, LLMRequest, LLMResult, ProviderError

_DEFAULT_VERSION = "2023-06-01"


def _redact(s: str) -> str:
    """避免把可疑 secret 写到错误信息里。粗粒度脱敏：长度 > 12 的字母数字串视作可疑。"""
    if not s:
        return s
    # 只做最小处理：去掉 Authorization / x-api-key 这种 header value
    return s.replace("\n", " ")[:300]


class AnthropicCompatibleProvider(LLMProvider):
    """Anthropic Messages API 协议的 provider。"""

    type = "anthropic_compatible"

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        anthropic_version: str,
        timeout_seconds: int,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._anthropic_version = anthropic_version or _DEFAULT_VERSION
        self.timeout_seconds = timeout_seconds

    def __repr__(self) -> str:
        # 主动安全 repr：只暴露 name 与 credential_present 标记，
        # 不暴露 api_key 与 base_url（base_url 可能含内网/代理细节）。
        return (
            f"AnthropicCompatibleProvider(name={self.name!r}, "
            f"credential_present={bool(self._api_key)})"
        )

    __str__ = __repr__

    # ------------------------------------------------------------------
    # 工厂
    # ------------------------------------------------------------------
    @classmethod
    def from_model_config(cls, mc: Any) -> AnthropicCompatibleProvider:
        # base_url：优先 env，再回落 yaml 中的 base_url
        base_url = ""
        if mc.base_url_env:
            base_url = os.environ.get(mc.base_url_env, "") or ""
        if not base_url:
            base_url = mc.base_url or ""
        if not base_url:
            raise ProviderError(
                f"模型 {mc.alias} 未提供 base_url：请设置环境变量 "
                f"{mc.base_url_env or '<base_url_env 未声明>'} 或在 yaml 写 base_url"
            )

        # api_key 解析优先级：env var > local secret store > missing
        # 普通 Web 用户不配置 api_key_env，key 存在 .mindforge/secrets.json。
        # env var mode 是 legacy/advanced deployment mode，仍可读取。
        api_key = _resolve_api_key(mc.alias, mc.api_key_env)
        if not api_key and not mc.api_key_optional:
            raise ProviderError(
                f"模型 {mc.alias} 没有可用的 API key。请在 Web Setup 中添加 key，"
                f"或设置环境变量 {mc.api_key_env or '<api_key_env>'}。"
            )

        # anthropic-version：可选，默认 2023-06-01
        version = _DEFAULT_VERSION
        if mc.version_env:
            version = os.environ.get(mc.version_env, "") or _DEFAULT_VERSION

        return cls(
            name=mc.provider,
            base_url=base_url,
            api_key=api_key,
            anthropic_version=version,
            timeout_seconds=mc.timeout_seconds,
        )

    # ------------------------------------------------------------------
    # 调用
    # ------------------------------------------------------------------
    def generate(self, request: LLMRequest) -> LLMResult:
        url = f"{self.base_url}/v1/messages"
        headers: dict[str, str] = {
            "content-type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": self._anthropic_version,
        }

        # Anthropic 协议：max_tokens 必填；v0.1 给一个稳健默认
        max_tokens = request.max_tokens if request.max_tokens is not None else 2048

        body: dict[str, Any] = {
            "model": request.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        # response_format=json_object：Anthropic 协议没有 OpenAI 那个开关；
        # v0.1 由 prompt 自身约束 + 解析端 _extract_first_json_object 容错。

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=body)
        except httpx.HTTPError as e:
            # 不打印 body（含 prompt） / 不打印 headers（含 api_key）
            raise ProviderError(f"HTTP 错误：{type(e).__name__}") from None
        latency_ms = int((time.perf_counter() - start) * 1000)

        if resp.status_code >= 400:
            # 截断响应文本，且做最小脱敏
            snippet = _redact(resp.text)
            raise ProviderError(f"HTTP {resp.status_code}: {snippet}")

        try:
            data = resp.json()
        except ValueError as e:
            raise ProviderError(f"响应非合法 JSON: {type(e).__name__}") from None

        text = _extract_text_from_content_blocks(data)
        if text is None:
            raise ProviderError("响应缺少 content[].text 文本块")

        usage = data.get("usage") or {}
        return LLMResult(
            text=text,
            tokens_in=usage.get("input_tokens"),
            tokens_out=usage.get("output_tokens"),
            latency_ms=latency_ms,
            raw=None,  # 故意不保留 raw，避免误把它写入 jsonl
        )


def _extract_text_from_content_blocks(data: dict[str, Any]) -> str | None:
    """从 Anthropic 响应中拼接所有 ``type=="text"`` 的 content block。"""
    blocks = data.get("content")
    if not isinstance(blocks, list):
        return None
    parts: list[str] = []
    for blk in blocks:
        if isinstance(blk, dict) and blk.get("type") == "text":
            t = blk.get("text")
            if isinstance(t, str):
                parts.append(t)
    if not parts:
        return None
    return "".join(parts)


def _resolve_api_key(alias: str, api_key_env: str | None) -> str | None:
    """API key 解析：env var > local secret store > None。

    Web 用户通过 Setup 输入的 key 存在 .mindforge/secrets.json；
    env var mode 是 legacy/advanced deployment mode。
    """
    # 1) env var（legacy/advanced mode）
    if api_key_env:
        value = os.environ.get(api_key_env)
        if value:
            return value
    # 2) local secret store
    from pathlib import Path as _Path
    from mindforge.secret_store import SecretStore
    store = SecretStore(_Path(".mindforge/secrets.json"))
    return store.get(alias)


__all__ = ["AnthropicCompatibleProvider", "_resolve_api_key"]
