"""CLI ``mindforge cubox dry-run`` contract tests — Red phase first.

本文件先写、production 后写。设计原则：

- **单一 use-case 入口**：本命令是 Cubox JSON export 文件的本地预检入口，
  与 Scanner（vault inbox 目录扫描）并列；二者最终都汇聚到 ``SourceMux``，
  这是真正的复用点。
- **零网络/零 .env/零 LLM/零 vault 写入**：dry-run 不接真实 Cubox API、
  不调 LLM、不生成 ai_draft / human_approved、不写 Obsidian。
- **薄 CLI**：命令体只做 args 解析 + adapter+mux 编排 + presenter 渲染，
  不引入新 service / repository / orchestrator（单 use-case 造服务即贫血）。
- **架构边界由测试守护**：core 模块不准 import 新 presenter；presenter 不准
  import provider / processor / approval / vault writer。
"""

from __future__ import annotations

import ast
import json
import socket
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()

FIXTURE = Path(__file__).parent / "fixtures" / "sample_cubox_api_export.json"


def _write_export(tmp_path: Path, items: list[dict[str, Any]]) -> Path:
    p = tmp_path / "export.json"
    p.write_text(json.dumps(items), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. UX — command surface
# ---------------------------------------------------------------------------


def test_cubox_group_appears_in_help() -> None:
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "cubox" in res.stdout.lower()


def test_cubox_dry_run_appears_in_cubox_help() -> None:
    res = runner.invoke(app, ["cubox", "--help"])
    assert res.exit_code == 0
    assert "dry-run" in res.stdout.lower()


def test_cubox_dry_run_requires_export_arg() -> None:
    res = runner.invoke(app, ["cubox", "dry-run"])
    assert res.exit_code != 0


def test_cubox_dry_run_missing_file_user_friendly_error(tmp_path: Path) -> None:
    res = runner.invoke(app, ["cubox", "dry-run", "--export", str(tmp_path / "nope.json")])
    assert res.exit_code != 0
    out = (res.stdout + (res.stderr or "")).lower()
    assert "nope.json" in out or "not found" in out or "不存在" in out


def test_cubox_dry_run_malformed_export_user_friendly_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    res = runner.invoke(app, ["cubox", "dry-run", "--export", str(bad)])
    assert res.exit_code != 0
    out = (res.stdout + (res.stderr or "")).lower()
    assert "json" in out or "解析" in out or "malformed" in out


# ---------------------------------------------------------------------------
# 2. UX — summary content
# ---------------------------------------------------------------------------


def test_cubox_dry_run_empty_export_summary(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [])
    res = runner.invoke(app, ["cubox", "dry-run", "--export", str(p)])
    assert res.exit_code == 0
    assert "0" in res.stdout


def test_cubox_dry_run_happy_path_shows_counts_and_source_name() -> None:
    res = runner.invoke(app, ["cubox", "dry-run", "--export", str(FIXTURE)])
    assert res.exit_code == 0, res.stdout
    out = res.stdout
    assert "cubox_api" in out
    # fixture 包含 2 条
    assert "2" in out


def test_cubox_dry_run_dedup_via_source_mux(tmp_path: Path) -> None:
    item = {"id": "dup", "title": "T", "content": "x"}
    p = _write_export(tmp_path, [item, dict(item), dict(item)])
    res = runner.invoke(app, ["cubox", "dry-run", "--export", str(p)])
    assert res.exit_code == 0, res.stdout
    out = res.stdout.lower()
    # 去重后 yielded=1，deduped=2
    assert "dedup" in out or "去重" in out
    assert "2" in out


def test_cubox_dry_run_limit_caps_sample(tmp_path: Path) -> None:
    items = [{"id": f"i-{n}", "title": f"T{n}"} for n in range(5)]
    p = _write_export(tmp_path, items)
    res = runner.invoke(
        app, ["cubox", "dry-run", "--export", str(p), "--limit", "2"]
    )
    assert res.exit_code == 0, res.stdout
    # 至多 2 个 sample 标题出现
    titles_seen = sum(1 for n in range(5) if f"T{n}" in res.stdout)
    assert titles_seen <= 2


def test_cubox_dry_run_json_output_shape(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [{"id": "a", "title": "A"}])
    res = runner.invoke(app, ["cubox", "dry-run", "--export", str(p), "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout.strip().splitlines()[-1])
    assert payload["items_seen"] == 1
    assert payload["yielded"] == 1
    assert payload["deduped"] == 0
    assert payload["by_source"] == {"cubox_api": 1}
    assert isinstance(payload["sample"], list)


# ---------------------------------------------------------------------------
# 3. Safety — no leakage / no side effect
# ---------------------------------------------------------------------------


def test_cubox_dry_run_summary_does_not_leak_token_or_body(tmp_path: Path) -> None:
    p = _write_export(
        tmp_path,
        [
            {
                "id": "x",
                "title": "Title-X",
                "url": "https://example.com/secret-path",
                "author": "alice@example.com",
                "content": "SUPER-SECRET-BODY-MARKER-zzz",
            }
        ],
    )
    res = runner.invoke(app, ["cubox", "dry-run", "--export", str(p), "--json"])
    assert res.exit_code == 0
    out = res.stdout
    assert "SUPER-SECRET-BODY-MARKER-zzz" not in out
    assert "alice@example.com" not in out
    assert "secret-path" not in out


def test_cubox_dry_run_does_not_open_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("dry-run 不应建立网络连接")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)
    p = _write_export(tmp_path, [{"id": "x", "title": "T"}])
    res = runner.invoke(app, ["cubox", "dry-run", "--export", str(p)])
    assert res.exit_code == 0


# ---------------------------------------------------------------------------
# 4. Architecture — boundary AST guards
# ---------------------------------------------------------------------------


_PRESENTER_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "mindforge"
    / "cubox_dryrun_presenter.py"
)

_FORBIDDEN_PRESENTER_IMPORTS = {
    "mindforge.processor",
    "mindforge.pipeline",
    "mindforge.providers",
    "mindforge.providers.factory",
    "mindforge.approval_service",
    "mindforge.review_service",
    "mindforge.vault_writer",
    "mindforge.workspace",
    "mindforge.env_loader",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_presenter_module_exists_and_has_no_forbidden_imports() -> None:
    assert _PRESENTER_PATH.exists(), f"presenter 模块未创建：{_PRESENTER_PATH}"
    names = _imported_modules(_PRESENTER_PATH)
    leaked = names & _FORBIDDEN_PRESENTER_IMPORTS
    assert not leaked, f"presenter 不应 import：{leaked}"


def test_core_modules_do_not_import_dry_run_presenter() -> None:
    # 反向依赖检查：核心 pipeline 不准依赖 dry-run presenter
    src = Path(__file__).resolve().parent.parent / "src" / "mindforge"
    targets = [src / n for n in (
        "processor.py", "pipeline.py", "scanner.py", "source_mux.py",
        "approval_service.py", "review_service.py",
    )]
    for t in targets:
        if not t.exists():
            continue
        names = _imported_modules(t)
        assert "mindforge.cubox_dryrun_presenter" not in names, (
            f"{t.name} 不应 import cubox_dryrun_presenter"
        )
