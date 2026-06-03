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
        # Authorization header: "Authorization: Bearer xxx"
        (r"(Authorization\s*:\s*Bearer\s+)[^,\s\"']+", r"\1[REDACTED]"),
        # Any *-api-key header: "X-DashScope-Api-Key: xxx", "x-api-key: xxx"
        (r"([\w-]*api[_-]?key\s*:\s*)[^,\s\"']+", r"\1[REDACTED]"),
        # JSON key fields: "api_key": "xxx", "token": "xxx", "authorization": "xxx"
        (r'("(?:api[_-]?key|access[_-]?token|token|authorization|secret)"\s*:\s*")[^"]+(")', r"\1[REDACTED]\2"),
        # Query params: api_key=xxx, token=xxx, access_token=xxx, key=xxx
        (r"((?:api[_-]?key|access[_-]?token|token|key)=)[^&\s]+", r"\1[REDACTED]"),
        # URL credentials: https://user:pass@example.com
        (r"(https?://)[^:@/\s]+:[^@/\s]+(@)", r"\1[REDACTED]\2"),
        # sk- tokens (OpenAI, Anthropic, etc.)
        (r"\bsk-[A-Za-z0-9_\-]{8,}\b", "[REDACTED]"),
        # ak- tokens (DashScope / Qwen style)
        (r"\bak-[A-Za-z0-9_\-]{8,}\b", "[REDACTED]"),
        # Bearer tokens in plain text
        (r"\bBearer\s+[A-Za-z0-9_\-\.]{12,}\b", "Bearer [REDACTED]"),
        # Long high-entropy token-like strings (mixed case + digits, 32+ chars)
        (r"\b[A-Za-z0-9_\-]{32,}\b", _redact_if_high_entropy),
    )
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized[:limit]


def _redact_if_high_entropy(match: re.Match) -> str:
    """仅当 token 含大小写+数字时替换为 [REDACTED]，避免误杀纯小写 hash。"""
    token = match.group(0)
    has_upper = any(c.isupper() for c in token)
    has_lower = any(c.islower() for c in token)
    has_digit = any(c.isdigit() for c in token)
    if has_upper and has_lower and has_digit:
        return "[REDACTED]"
    return token


__all__ = [
    "LLMProvider",
    "LLMRequest",
    "LLMResult",
    "ProviderError",
    "redact_provider_error_text",
]
