"""Tests for ``mindforge.cubox_readiness`` + ``mindforge dogfood cubox-readiness``.

边界守护要点 (与 provider_readiness 同款):
- presence-only: 永不读取 / 返回 / 打印 token value;
- G1 gate 始终关闭 (本模块不开闸);
- AST: 不 import HTTP client / cubox_api / llm / obsidian / cli /
  approval / writer / cards / scanner / env_loader / dotenv /
  subprocess / process_service。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindforge.cli import app
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
        "json export is the safe dogfood path today",
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


def test_cli_default_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINDFORGE_CUBOX_TOKEN", raising=False)
    runner = CliRunner()
    result = runner.invoke(app, ["dogfood", "cubox-readiness"])
    assert result.exit_code == 0, result.output
    assert "cubox-real-opt-in" in result.output
    assert "token value not printed" in result.output
    assert "G1" in result.output


def test_cli_does_not_leak_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_TOKEN_VAR, _LEAK_SENTINEL)
    runner = CliRunner()
    result = runner.invoke(
        app, ["dogfood", "cubox-readiness", "--token-env", _TOKEN_VAR]
    )
    assert result.exit_code == 0, result.output
    assert _LEAK_SENTINEL not in result.output
    assert "token_present:           True" in result.output
