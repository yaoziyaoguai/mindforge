"""CLI ``mindforge cubox preview-ai-draft`` contract tests — Red phase first.

本命令是 Cubox dogfood loop 的下一层：把本地 Cubox JSON export 解析的
``SourceDocument`` 送入既有 ``KnowledgeStrategy``（``fake`` profile +
``FakeProvider``），生成 **in-memory** ai_draft preview，**永不**：

- 读 ``.env``；
- 联网；
- 调真实 LLM / 真实 Cubox API；
- 写 ``.mindforge/runs/*.jsonl``；
- 写 Obsidian vault；
- 生成 ``human_approved``；
- 自动 approve；
- 展示 ai_draft 正文（避免在 stdout 泄漏 fake 渲染出来的内容观感）。

设计原则：与 ``cubox dry-run`` 平级，是独立子命令而**不是** flag。
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
_REPO = Path(__file__).resolve().parent.parent


def _write_export(tmp_path: Path, items: list[dict[str, Any]]) -> Path:
    p = tmp_path / "export.json"
    p.write_text(json.dumps(items), encoding="utf-8")
    return p


@pytest.fixture
def runs_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """提供一个 sentinel 目录；测试结束断言里面没产生任何 jsonl。

    这个 fixture 是无侧效观察器，不强制 CLI 把 runs 写到这里——CLI 应该
    完全不写。如果未来 CLI 误用 RunLogger，本目录依然为空，但既有
    ``.mindforge/runs/`` 也可能出现新文件；那时由
    ``test_does_not_create_runs_jsonl_anywhere_under_tmp`` 在 cwd=tmp 的
    场景下守护。
    """

    return tmp_path / "runs-sentinel"


# ---------------------------------------------------------------------------
# 1. UX — command surface
# ---------------------------------------------------------------------------


def test_preview_subcommand_is_not_advertised_by_direct_help() -> None:
    res = runner.invoke(app, ["cubox", "--help"])
    assert res.exit_code != 0
    assert "preview-ai-draft" not in res.stdout


def test_preview_requires_export_arg() -> None:
    res = runner.invoke(app, ["cubox", "preview-ai-draft"])
    assert res.exit_code != 0


def test_preview_missing_file_user_friendly_error(tmp_path: Path) -> None:
    res = runner.invoke(
        app, ["cubox", "preview-ai-draft", "--export", str(tmp_path / "nope.json")]
    )
    assert res.exit_code != 0
    out = (res.stdout + (res.stderr or "")).lower()
    assert "nope.json" in out or "不存在" in out


def test_preview_malformed_export_user_friendly_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    res = runner.invoke(app, ["cubox", "preview-ai-draft", "--export", str(bad)])
    assert res.exit_code != 0
    out = (res.stdout + (res.stderr or "")).lower()
    assert "json" in out or "解析" in out


# ---------------------------------------------------------------------------
# 2. UX — summary content
# ---------------------------------------------------------------------------


def test_preview_empty_export_summary(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [])
    res = runner.invoke(app, ["cubox", "preview-ai-draft", "--export", str(p)])
    assert res.exit_code == 0
    assert "0" in res.stdout


def test_preview_happy_path_counts_outcomes() -> None:
    res = runner.invoke(app, ["cubox", "preview-ai-draft", "--export", str(FIXTURE)])
    assert res.exit_code == 0, res.stdout
    out = res.stdout
    # fixture 有 2 条
    assert "2" in out
    # outcome 至少分桶展示（processed / skipped / failed）
    out_low = out.lower()
    assert any(k in out_low for k in ("processed", "skipped", "failed"))


def test_preview_dedup_via_source_mux(tmp_path: Path) -> None:
    item = {"id": "dup", "title": "T", "content": "x"}
    p = _write_export(tmp_path, [item, dict(item), dict(item)])
    res = runner.invoke(app, ["cubox", "preview-ai-draft", "--export", str(p)])
    assert res.exit_code == 0, res.stdout
    out = res.stdout.lower()
    assert "dedup" in out or "去重" in out


def test_preview_limit_caps_processed(tmp_path: Path) -> None:
    items = [{"id": f"i-{n}", "title": f"T{n}", "content": f"c{n}"} for n in range(5)]
    p = _write_export(tmp_path, items)
    res = runner.invoke(
        app, ["cubox", "preview-ai-draft", "--export", str(p), "--limit", "2", "--json"]
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout.strip().splitlines()[-1])
    # 只跑前 2 个 → outcomes 数量 <= 2
    assert len(payload["outcomes"]) <= 2


def test_preview_json_output_shape(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [{"id": "a", "title": "A", "content": "hello"}])
    res = runner.invoke(
        app, ["cubox", "preview-ai-draft", "--export", str(p), "--json"]
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout.strip().splitlines()[-1])
    assert payload["items_seen"] == 1
    assert "yielded" in payload
    assert "deduped" in payload
    assert "by_status" in payload
    assert isinstance(payload["outcomes"], list)
    if payload["outcomes"]:
        item = payload["outcomes"][0]
        # 每个 outcome 暴露 status / track / value_score / has_card_payload，
        # **绝不**暴露 card_payload 正文 / raw_text / source_url / author。
        assert set(item.keys()) <= {
            "title",
            "source_id_short",
            "status",
            "track",
            "value_score",
            "has_card_payload",
            "skip_reason",
            "error_message",
        }


# ---------------------------------------------------------------------------
# 3. Safety — no body / credential / runs / vault leakage
# ---------------------------------------------------------------------------


def test_preview_does_not_print_card_body(tmp_path: Path) -> None:
    p = _write_export(
        tmp_path,
        [
            {
                "id": "x",
                "title": "T",
                "url": "https://example.com/secret-path",
                "author": "alice@example.com",
                "content": "SUPER-SECRET-BODY-MARKER-zzz",
            }
        ],
    )
    res = runner.invoke(
        app, ["cubox", "preview-ai-draft", "--export", str(p), "--json"]
    )
    assert res.exit_code == 0
    out = res.stdout
    assert "SUPER-SECRET-BODY-MARKER-zzz" not in out
    assert "alice@example.com" not in out
    assert "secret-path" not in out


def test_preview_does_not_open_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("preview 不应建立网络连接")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)
    p = _write_export(tmp_path, [{"id": "x", "title": "T", "content": "c"}])
    res = runner.invoke(app, ["cubox", "preview-ai-draft", "--export", str(p)])
    assert res.exit_code == 0


def test_preview_does_not_create_runs_jsonl_under_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    p = _write_export(tmp_path, [{"id": "x", "title": "T", "content": "c"}])
    res = runner.invoke(app, ["cubox", "preview-ai-draft", "--export", str(p)])
    assert res.exit_code == 0
    # cwd 下不能出现任何 *.jsonl（RunLogger 写的就是这个后缀）
    leaked = list(tmp_path.rglob("*.jsonl"))
    assert leaked == [], f"preview 不应写 runs jsonl：{leaked}"


def test_preview_human_approved_label_never_appears(tmp_path: Path) -> None:
    p = _write_export(tmp_path, [{"id": "x", "title": "T", "content": "c"}])
    res = runner.invoke(app, ["cubox", "preview-ai-draft", "--export", str(p)])
    assert res.exit_code == 0
    assert "human_approved" not in res.stdout


# ---------------------------------------------------------------------------
# 4. Architecture — boundary AST guards
# ---------------------------------------------------------------------------


_PRESENTER_PATH = (
    _REPO / "src" / "mindforge" / "cubox_preview_presenter.py"
)

_FORBIDDEN_PRESENTER_IMPORTS = {
    "mindforge.processor",
    "mindforge.processors",
    "mindforge.processors.pipeline",
    "mindforge.providers",
    "mindforge.providers.factory",
    "mindforge.approval_service",
    "mindforge.approver",
    "mindforge.review_service",
    "mindforge.reviewer",
    "mindforge.vault",
    "mindforge.writer",
    "mindforge.env_loader",
    "mindforge.run_logger",
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


def test_preview_presenter_module_exists_and_has_no_forbidden_imports() -> None:
    assert _PRESENTER_PATH.exists(), f"preview presenter 模块未创建：{_PRESENTER_PATH}"
    names = _imported_modules(_PRESENTER_PATH)
    leaked = names & _FORBIDDEN_PRESENTER_IMPORTS
    assert not leaked, f"preview presenter 不应 import：{leaked}"


def test_core_modules_do_not_import_preview_presenter() -> None:
    src = _REPO / "src" / "mindforge"
    targets = [src / n for n in (
        "processor.py", "pipeline.py", "scanner.py", "source_mux.py",
        "approval_service.py", "review_service.py",
    )]
    for t in targets:
        if not t.exists():
            continue
        names = _imported_modules(t)
        assert "mindforge.cubox_preview_presenter" not in names, (
            f"{t.name} 不应 import cubox_preview_presenter"
        )
