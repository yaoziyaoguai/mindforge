"""v0.4.2 — `mindforge commands` / `mindforge next` / SourceAdapter 架构稳定性测试。

学习要点
========
- ``commands`` / ``next`` 是产品体验闭环，不能调 LLM、不能读 .env、不能联网；
- ``SourceAdapter`` 架构必须保持插件化：新增 source_type 只改 registry，
  不动 scanner / processor 任何一行；
- ``SourceDocument`` 的 ``adapter_name`` 字段是 v0.4.2 新增追溯位，
  必须由 Scanner 自动回填。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.config import load_mindforge_config
from mindforge.scanner import Scanner
from mindforge.sources.base import SourceAdapter, SourceDocument, compute_content_hash
from mindforge.sources.registry import _BUILTIN_ADAPTERS, build_active_adapters

runner = CliRunner()


# ---------------------------------------------------------------------------
# 复用 v0.3.1 的 vault 构造
# ---------------------------------------------------------------------------
def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "30-Projects").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)

    cfg = {
        "version": 0.3,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {
            "enabled": ["plain_markdown"],
            "registry": {
                "plain_markdown": {
                    "adapter": "PlainMarkdownAdapter",
                    "inbox_subdir": "ManualNotes",
                    "file_glob": "*.md",
                }
            },
        },
        "state": {
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
            "backup_state": True,
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "fake_alias",
                    "distill": "fake_alias",
                    "link_suggestion": "fake_alias",
                    "review_questions": "fake_alias",
                    "action_extraction": "fake_alias",
                }
            },
            "models": {
                "fake_alias": {
                    "provider": "fake_provider",
                    "type": "fake",
                    "model": "fake-model",
                }
            },
        },
        "prompts": {
            "triage_version": "v1",
            "distill_version": "v1",
            "link_suggestion_version": "v1",
            "review_questions_version": "v1",
            "action_extraction_version": "v1",
        },
        "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
    }
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return cfg_path


def _write_card(cards: Path, name: str, fm: dict, body: str = "## AI Summary\nx\n") -> None:
    front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items())
    (cards / f"{name}.md").write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")


# ===========================================================================
# `mindforge commands`
# ===========================================================================
def test_commands_lists_key_groups() -> None:
    """commands 输出应覆盖主要场景：初始化 / 数据输入 / 审核 / 搜索 / 复习 / 项目上下文。"""
    res = runner.invoke(app, ["commands"])
    assert res.exit_code == 0
    out = res.output
    for kw in ["初始化", "数据输入", "审核", "搜索", "复习", "项目上下文", "可观测"]:
        assert kw in out, f"commands 输出缺少 group: {kw}"
    # 至少包含 init / scan / approve / index / recall / review / project
    for cmd in ["mindforge init", "mindforge scan", "mindforge approve", "mindforge index",
                "mindforge recall", "mindforge review", "mindforge project"]:
        assert cmd in out


def test_commands_does_not_leak_secrets() -> None:
    """commands 是纯静态字符串，不应包含 secret 关键字。"""
    res = runner.invoke(app, ["commands"])
    assert res.exit_code == 0
    low = res.output.lower()
    for forbidden in ["api_key", "authorization:", "bearer ", "anthropic_api_key", ".env="]:
        assert forbidden not in low


# ===========================================================================
# `mindforge next`
# ===========================================================================
def test_next_without_config_suggests_init(tmp_path: Path) -> None:
    """配置不存在时 next 应当建议 init，且不抛错。"""
    res = runner.invoke(app, ["next", "--config", str(tmp_path / "missing.yaml")])
    assert res.exit_code == 0
    assert "mindforge init" in res.output


def test_next_empty_vault_suggests_inbox_or_index(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    res = runner.invoke(app, ["next", "--config", str(cfg)])
    assert res.exit_code == 0
    # 无原料 + 无索引 → 至少一条与 inbox 或 index 相关的建议
    assert ("inbox" in res.output or "index rebuild" in res.output)


def test_next_suggests_approve_when_drafts_exist(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "draft-1", {
        "id": "draft-1", "title": "draft", "status": "ai_draft",
        "track": "agent-runtime", "value_score": 5,
    })
    res = runner.invoke(app, ["next", "--config", str(cfg)])
    assert res.exit_code == 0
    assert "approve list" in res.output


def test_next_suggests_index_rebuild_when_index_missing(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "card-1", {
        "id": "card-1", "title": "x", "status": "human_approved",
        "track": "agent-runtime", "value_score": 5,
    })
    res = runner.invoke(app, ["next", "--config", str(cfg)])
    assert res.exit_code == 0
    assert "index rebuild" in res.output


def test_next_json_format_is_parseable(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    res = runner.invoke(app, ["next", "--config", str(cfg), "--format", "json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["version"] == 1
    assert isinstance(data["suggestions"], list)
    assert all("command" in s and "reason" in s for s in data["suggestions"])


def test_next_does_not_read_env_or_call_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """next 必须无网络、无 .env 读取。"""
    cfg = _make_vault(tmp_path)
    # 写一个假 .env 但确保 next 不读它内容
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=secret-must-not-leak\n", encoding="utf-8")

    # 拦截 HTTP（通过禁用 socket）
    import socket as _socket

    def _no_socket(*a, **kw):  # pragma: no cover - 只在被违规调用时触发
        raise RuntimeError("next 不应发起 socket 调用")

    monkeypatch.setattr(_socket, "socket", _no_socket)

    res = runner.invoke(app, ["next", "--config", str(cfg)])
    assert res.exit_code == 0
    assert "secret-must-not-leak" not in res.output
    assert "ANTHROPIC_API_KEY" not in res.output


# ===========================================================================
# SourceAdapter 架构稳定性
# ===========================================================================
def test_adapter_registry_includes_all_v041_adapters() -> None:
    """v0.4.2 的 6 个内置 adapter 必须都注册。"""
    expected = {
        "CuboxMarkdownAdapter",
        "PlainMarkdownAdapter",
        "WebClipMarkdownAdapter",
        "PdfAdapter",
        "DocxAdapter",
        "ChatExportAdapter",
    }
    assert expected <= set(_BUILTIN_ADAPTERS.keys())


def test_adapter_registry_can_build_from_config(tmp_path: Path) -> None:
    cfg_path = _make_vault(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    adapters = build_active_adapters(cfg.sources)
    assert "plain_markdown" in adapters
    a = adapters["plain_markdown"]
    assert isinstance(a, SourceAdapter)
    assert a.source_type == "plain_markdown"


def test_scanner_backfills_adapter_name(tmp_path: Path) -> None:
    """Scanner 必须把 adapter_name 写到 SourceDocument 上，便于追溯。"""
    cfg_path = _make_vault(tmp_path)
    inbox = tmp_path / "vault" / "00-Inbox" / "ManualNotes"
    (inbox / "demo.md").write_text("# Demo\n\nbody\n", encoding="utf-8")

    cfg = load_mindforge_config(cfg_path)
    scanner = Scanner(cfg)
    results = scanner.scan_all()
    assert len(results) == 1
    assert results[0].ok
    doc = results[0].document
    assert doc is not None
    assert doc.adapter_name  # 已被 Scanner 回填
    assert "Adapter" in doc.adapter_name


def test_source_document_is_immutable_contract() -> None:
    """SourceDocument 是 frozen dataclass — 下游加工无法私改其内容。"""
    doc = SourceDocument(
        source_id="x",
        source_type="plain_markdown",
        source_path="/a/b.md",
        raw_text="hello",
        content_hash=compute_content_hash("hello"),
    )
    with pytest.raises(Exception):
        doc.raw_text = "tampered"  # type: ignore[misc]


def test_demo_vault_exists_and_has_minimum_assets() -> None:
    """examples/demo-vault/ 必须存在且包含最小资产，供文档与 smoke 引用。"""
    root = Path(__file__).resolve().parent.parent / "examples" / "demo-vault"
    assert root.exists(), "examples/demo-vault/ 必须存在"
    assert (root / "README.md").exists()
    assert (root / "00-Inbox" / "Cubox").is_dir()
    assert (root / "00-Inbox" / "WebClips").is_dir()
    assert (root / "00-Inbox" / "ChatExports").is_dir()
    assert (root / "30-Projects" / "my-first-agent.md").exists()
    cards = list((root / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) >= 2


def test_demo_vault_does_not_contain_secrets() -> None:
    """demo vault 必须不含任何 secret 关键字 / 真实 token / .env。"""
    root = Path(__file__).resolve().parent.parent / "examples" / "demo-vault"
    forbidden = ["sk-ant-", "sk-proj-", "Bearer ", "ANTHROPIC_API_KEY=", "OPENAI_API_KEY="]
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name == ".env":
            raise AssertionError("demo vault 不能含 .env")
        text = p.read_text(encoding="utf-8", errors="ignore")
        for f in forbidden:
            assert f not in text, f"{p} 含敏感片段 {f!r}"
