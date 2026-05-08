"""LLM provider 抽象基类 + 请求/响应数据契约。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re
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


def redact_provider_error_text(text: str, *, limit: int = 300) -> str:
    """脱敏 provider 错误片段，避免 HTTP body/header 把 key 写入日志或 API 响应。

    中文学习型说明：provider 错误会被 CLI/Web/service 继续传播，所以脱敏必须在
    provider 边界完成。这里不尝试理解所有供应商格式，只处理常见 header、JSON
    字段和 sk-/Bearer 形态，并在最后截断，保证错误信息可诊断但不携带凭证。
    """

    if not text:
        return text
    sanitized = text.replace("\n", " ")
    patterns = (
        (r"(Authorization\s*:\s*Bearer\s+)[^,\s\"']+", r"\1[REDACTED]"),
        (r"(x-api-key\s*:\s*)[^,\s\"']+", r"\1[REDACTED]"),
        (r'("(?:api[_-]?key|access[_-]?token|token|authorization)"\s*:\s*")[^"]+(")', r"\1[REDACTED]\2"),
        (r"((?:api[_-]?key|access[_-]?token|token)=)[^&\s]+", r"\1[REDACTED]"),
        (r"\bsk-[A-Za-z0-9_\-]{8,}\b", "[REDACTED]"),
        (r"\bBearer\s+[A-Za-z0-9_\-\.]{12,}\b", "Bearer [REDACTED]"),
    )
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized[:limit]


__all__ = [
    "LLMProvider",
    "LLMRequest",
    "LLMResult",
    "ProviderError",
    "redact_provider_error_text",
]
