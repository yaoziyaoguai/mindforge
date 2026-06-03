"""Ingestion diagnostics contract tests."""

from __future__ import annotations

import pytest

from mindforge.ingestion_diagnostics import classify_provider_error


@pytest.mark.parametrize(
    "message",
    [
        "HTTP 429 insufficient quota",
        "insufficient quota",
        "quota exceeded",
        "exceeded your current quota",
        "billing quota exhausted",
        "insufficient credits",
    ],
)
def test_provider_quota_errors_take_priority_over_generic_429(message: str) -> None:
    """quota 语义必须优先于 HTTP 429/rate-limit 的泛化分类。

    中文学习型说明：429 既可能是短暂限流，也可能是余额/配额耗尽。前者建议
    等待重试，后者需要处理 billing/quota；如果先匹配 429，就会给用户错误的
    remediation。
    """

    classification = classify_provider_error(message)

    assert classification.error_type == "provider_quota_exceeded"
    assert "quota" in classification.safe_message.lower()


@pytest.mark.parametrize(
    "message",
    [
        "HTTP 429 rate limit",
        "too many requests",
        "provider throttled the request",
    ],
)
def test_provider_rate_limit_remains_generic_for_non_quota_429(message: str) -> None:
    """非 quota 的 429/rate-limit 仍归为 provider_rate_limited。"""

    classification = classify_provider_error(message)

    assert classification.error_type == "provider_rate_limited"
    assert "retry" in (classification.retry_hint or "").lower()


def test_provider_error_safe_message_does_not_echo_raw_payload_or_secret() -> None:
    """safe_message 不能回显 provider raw response、token 或 payload。"""

    raw_payload = "HTTP 429 insufficient quota token=sk-test-secret raw_body={\"secret\":\"value\"}"

    classification = classify_provider_error(raw_payload)

    assert classification.error_type == "provider_quota_exceeded"
    assert "sk-test-secret" not in classification.safe_message
    assert "raw_body" not in classification.safe_message
    assert "secret" not in classification.safe_message.lower()

def test_network_connectivity_errors() -> None:
    classification = classify_provider_error("httpx.ConnectError: [Errno 61] Connection refused")
    assert classification.error_type == "network_connectivity_error"
    assert "模型连接失败" in classification.safe_message

    classification = classify_provider_error("httpx.ReadTimeout: The read operation timed out")
    assert classification.error_type == "network_connectivity_error"
    assert "模型连接失败" in classification.safe_message

def test_generic_provider_error_is_network_centric_now() -> None:
    classification = classify_provider_error("HTTP 500 Internal Server Error")
    assert classification.error_type == "provider_error"
    assert "模型连接失败" in classification.safe_message
