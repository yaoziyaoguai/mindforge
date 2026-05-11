"""Tests for ``mindforge.cubox_readiness`` service boundary.

边界守护要点 (与 provider_readiness 同款):
- presence-only: 永不读取 / 返回 / 打印 token value;
- G1 gate 始终关闭 (本模块不开闸);
- AST: 不 import HTTP client / cubox_api / llm / obsidian / cli /
    approval / writer / cards / scanner / env_loader / dotenv /
  subprocess / process_service。

中文学习型说明：Cubox readiness 仍可作为内部 presence-only service
被测试覆盖，但不再通过 legacy command 暴露为用户命令。第一阶段
用户主路径是本地 source + Web Setup + 后台 processing。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from mindforge.cubox_readiness import (
    classify_cubox_real_opt_in,
    inspect_cubox_config,
    render_cubox_readiness_report,
)


_TOKEN_VAR = "MINDFORGE_TEST_CUBOX_TOKEN_DUMMY"
_LEAK_SENTINEL = "leaked-cubox-token-zzzz9999"


def test_inspect_token_present_does_not_return_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_TOKEN_VAR, _LEAK_SENTINEL)
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    assert report["token_present"] is True
    assert _LEAK_SENTINEL not in repr(report)
    for v in report.values():
        assert _LEAK_SENTINEL not in repr(v)


def test_inspect_token_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_TOKEN_VAR, raising=False)
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    assert report["token_present"] is False


def test_inspect_empty_token_treated_as_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_TOKEN_VAR, "")
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    assert report["token_present"] is False


def test_classify_default_path_is_json_export_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_TOKEN_VAR, raising=False)
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    classification = classify_cubox_real_opt_in(report, allow_real=False)
    assert classification["opt_in_state"] == "json_export_default"
    assert report["g1_gate_open"] is False


def test_classify_token_present_no_allow_real(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_TOKEN_VAR, _LEAK_SENTINEL)
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    classification = classify_cubox_real_opt_in(report, allow_real=False)
    assert classification["opt_in_state"] == "token_env_only"
    assert report["g1_gate_open"] is False


def test_classify_allow_real_token_absent_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_TOKEN_VAR, raising=False)
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    classification = classify_cubox_real_opt_in(report, allow_real=True)
    assert classification["opt_in_state"] == "blocked"
    assert report["g1_gate_open"] is False
    assert classification["blockers"]


def test_classify_allow_real_token_present_ready_for_future_g1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_TOKEN_VAR, _LEAK_SENTINEL)
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    classification = classify_cubox_real_opt_in(report, allow_real=True)
    assert classification["opt_in_state"] == "ready_for_future_g1"
    # 即使 ready, gate 仍然 future-gated, 永不在本模块开启。
    assert report["g1_gate_open"] is False


def test_render_contains_pinned_literals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_TOKEN_VAR, _LEAK_SENTINEL)
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    classification = classify_cubox_real_opt_in(report, allow_real=False)
    text = render_cubox_readiness_report(report, classification)
    assert _LEAK_SENTINEL not in text
    for literal in (
        "cubox-real-opt-in",
        "token value not printed",
        "json export remains offline-only",
        "human approval required",
        "no .env content is read or printed",
        "G1",
    ):
        assert literal in text, f"missing pinned literal: {literal!r}"


def test_render_token_absent_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_TOKEN_VAR, raising=False)
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    classification = classify_cubox_real_opt_in(report, allow_real=False)
    text = render_cubox_readiness_report(report, classification)
    assert "json_export_default" in text


def test_module_imports_no_http_or_secrets() -> None:
    src = Path("src/mindforge/cubox_readiness.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    banned_modules = {
        "httpx", "requests", "urllib", "urllib.request", "http.client",
        "subprocess", "dotenv",
    }
    banned_prefixes = (
        "mindforge.cli", "mindforge.cubox_api", "mindforge.cubox_cli",
        "mindforge.llm", "mindforge.obsidian", "mindforge.obsidian_cli",
        "mindforge.obsidian_stage", "mindforge.approval_service",
        "mindforge.approver", "mindforge.writer", "mindforge.cards",
        "mindforge.scanner", "mindforge.env_loader",
        "mindforge.process_service", "mindforge.provider_readiness",
        "mindforge.real_smoke",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in banned_modules, alias.name
                assert not alias.name.startswith(banned_prefixes), alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            top = mod.split(".")[0] if mod else ""
            assert top not in banned_modules, mod
            assert not mod.startswith(banned_prefixes), mod


def test_service_default_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINDFORGE_CUBOX_TOKEN", raising=False)
    report = inspect_cubox_config()
    text = render_cubox_readiness_report(
        report,
        classify_cubox_real_opt_in(report, allow_real=False),
    )
    assert "cubox-real-opt-in" in text
    assert "token value not printed" in text
    assert "G1" in text


def test_service_render_does_not_leak_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_TOKEN_VAR, _LEAK_SENTINEL)
    report = inspect_cubox_config(token_env_var=_TOKEN_VAR)
    text = render_cubox_readiness_report(
        report,
        classify_cubox_real_opt_in(report, allow_real=False),
    )
    assert _LEAK_SENTINEL not in text
    assert "token_present:           True" in text
