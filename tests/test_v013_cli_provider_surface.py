"""v0.13 Stage 1 — provider readiness service + AST import-boundary.

产品语义迁移:
- ``mindforge provider`` 已不再是用户 CLI 主路径；
- readiness/smoke 仍作为 service contract 保留，供 Web Setup / tests
  做 presence-only 诊断；
- 测试不能为了方便重新注册 legacy command group。

AST 边界: provider_readiness.py / real_smoke.py / input_safety.py 不
反向 import CLI / approval / writer / cards / obsidian* / cubox* /
scanner / dotenv / requests / httpx / subprocess。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from mindforge.assets_runtime import bundled_asset_path_for_process
from mindforge.app_context import load_app_config
from mindforge.provider_readiness import build_readiness_report, render_readiness_report
from mindforge.real_smoke import run_synthetic_real_smoke


def test_provider_readiness_service_renders_without_network():
    cfg = load_app_config(bundled_asset_path_for_process("configs", "mindforge.yaml"))
    text = render_readiness_report(build_readiness_report(cfg.llm))
    assert "fake-default" in text
    assert "readiness report" in text.lower()


def test_provider_smoke_service_refuses_without_allow_real():
    cfg = load_app_config(bundled_asset_path_for_process("configs", "mindforge.yaml"))
    result = run_synthetic_real_smoke(cfg.llm, allow_real=False)
    assert result["ran"] is False
    assert result["human_approved"] is False
    assert "allow-real" in result["blocker"]


def test_provider_smoke_service_does_not_return_secret(monkeypatch):
    # 即使 env 中存在 api_key, 不传 allow_real 也不应触发或返回 secret。
    monkeypatch.setenv("MF_FAKE_TEST_KEY_CLI_LEAK", "leaked-secret-1234567890")
    cfg = load_app_config(bundled_asset_path_for_process("configs", "mindforge.yaml"))
    result = run_synthetic_real_smoke(cfg.llm, allow_real=False)
    assert "leaked-secret-1234567890" not in repr(result)


_GUARDED = (
    Path("src/mindforge/provider_readiness.py"),
    Path("src/mindforge/real_smoke.py"),
    Path("src/mindforge/input_safety.py"),
    Path("src/mindforge/cubox_readiness.py"),
)

# real_smoke 允许 import mindforge.llm.factory。所有 readiness/safety service
# 都禁止 import 下列副作用模块。
_FORBIDDEN_PREFIXES = (
    "mindforge.cli",
    "mindforge.approval_service",
    "mindforge.approver",
    "mindforge.approve_presenter",
    "mindforge.writer",
    "mindforge.cards",
    "mindforge.process_service",
    "mindforge.review_service",
    "mindforge.review_presenter",
    "mindforge.recall_service",
    "mindforge.recall_presenter",
    "mindforge.obsidian",
    "mindforge.obsidian_cli",
    "mindforge.obsidian_stage",
    "mindforge.obsidian_workflow",
    "mindforge.cubox_cli",
    "mindforge.cubox_dryrun_presenter",
    "mindforge.scanner",
    "mindforge.env_loader",
    "mindforge.processors",
    "dotenv",
    "requests",
    "httpx",
    "subprocess",
)


def _collect_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # 相对 import: 规范化成 mindforge.<module> 以便 forbidden
                # 列表也能覆盖 (避免 'from .env_loader import X' 绕过守卫)。
                if node.module:
                    out.append(f"mindforge.{node.module}")
                continue
            if node.module:
                out.append(node.module)
    return out


_PER_FILE_ALLOWLIST: dict[Path, set[str]] = {}


@pytest.mark.parametrize("path", _GUARDED, ids=lambda p: p.name)
def test_provider_files_do_not_reverse_import_runtime(path: Path):
    assert path.exists(), path
    imports = _collect_imports(path)
    allow = _PER_FILE_ALLOWLIST.get(path, set())
    bad = sorted(
        {
            n
            for n in imports
            for prefix in _FORBIDDEN_PREFIXES
            if (n == prefix or n.startswith(prefix + ".")) and n not in allow
        }
    )
    assert not bad, (
        f"{path} reverse-imports forbidden runtime modules: {bad}; "
        "provider readiness/smoke/cli must stay decoupled from approval, "
        "writer, cards, obsidian, cubox, dotenv, network."
    )


def test_provider_readiness_imports_no_factory():
    """provider_readiness 不应 import llm.factory — 只 inspect, 不构造。"""
    imports = _collect_imports(Path("src/mindforge/provider_readiness.py"))
    bad = [n for n in imports if n.startswith("mindforge.llm")]
    assert not bad, f"provider_readiness must not import mindforge.llm.*; got {bad}"
