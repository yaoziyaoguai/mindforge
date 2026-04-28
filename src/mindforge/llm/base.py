"""LLM provider 抽象基类 + 请求/响应数据契约。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """provider 层错误（网络 / 鉴权 / 服务端 / 解析等）。

    业务层捕获此异常 → 标 stage failed，并把 message 写进 state.json 与
    runs jsonl 的 ``error_message`` 字段。
    """


@dataclass(frozen=True)
class LLMRequest:
    """一次请求的载荷。业务侧不直接构造（由 LLMClient 内部组装）。"""

    prompt: str
    stage: str
    model: str
    max_tokens: int | None = None
    temperature: float | None = None
    response_format: str | None = None  # "json_object" 表示要求 JSON
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResult:
    """provider 返回的结构化结果。

    ``raw`` 仅用于调试，**不**写入 runs jsonl（避免泄漏正文 / token 浪费）。
    """

    text: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    raw: dict[str, Any] | None = None


class LLMProvider(ABC):
    """所有 provider 必须实现此接口。"""

    name: str = "abstract"
    type: str = "abstract"

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResult:
        """同步 LLM 调用；失败时抛 ProviderError（不在此层做重试）。"""


__all__ = ["LLMProvider", "LLMRequest", "LLMResult", "ProviderError"]
