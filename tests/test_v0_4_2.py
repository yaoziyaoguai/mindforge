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
import socket
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app, _normalize_post_command_global_options
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
    assert "[[wikilinks]]" in out


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
    assert data["version"] == 2
    assert "status" in data
    assert "inbox_files" in data["status"]
    assert isinstance(data["suggestions"], list)
    assert all("command" in s and "reason" in s and "priority" in s for s in data["suggestions"])


def test_today_outputs_daily_loop_status_and_next_action(tmp_path: Path) -> None:
    """v0.5.4: today 是只读每日入口，展示状态和下一步，不触发加工。

    这里用真实 CLI runner 验证输出来自 vault/state/card 文件系统事实，而不是只测
    字符串拼接。命令不能读正文、不能 approve，也不能写 Obsidian notes。
    """
    cfg = _make_vault(tmp_path)
    inbox = tmp_path / "vault" / "00-Inbox" / "ManualNotes"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "daily.md").write_text("# Daily\n\nbody\n", encoding="utf-8")
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "draft-1", {
        "id": "draft-1", "title": "draft", "status": "ai_draft",
        "track": "agent-runtime", "value_score": 5,
    })

    res = runner.invoke(app, ["today", "--config", str(cfg)])
    assert res.exit_code == 0, res.output
    assert "MindForge today" in res.output
    assert "Daily status" in res.output
    assert "ai_draft=1" in res.output
    assert "Next actions" in res.output
    assert "approve list" in res.output


def test_today_json_is_parseable_and_does_not_read_env_or_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """today 必须是本地只读命令：不读 .env、不联网、不调用真实 LLM。"""
    cfg = _make_vault(tmp_path)
    (tmp_path / ".env").write_text("MINDFORGE_SECRET=must-not-leak\n", encoding="utf-8")

    import socket as _socket

    def _no_socket(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("today 不应联网")

    monkeypatch.setattr(_socket, "socket", _no_socket)
    res = runner.invoke(app, ["today", "--config", str(cfg), "--format", "json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["version"] == 1
    assert "status" in data and "suggestions" in data
    assert "must-not-leak" not in res.output


def test_daily_loop_empty_states_have_next_action_hints(tmp_path: Path) -> None:
    """空状态也要像产品：告诉用户下一步，而不是只输出 no match。"""
    cfg = _make_vault(tmp_path)

    approve = runner.invoke(app, ["approve", "list", "--config", str(cfg)])
    assert approve.exit_code == 0, approve.output
    assert "没有待 approve" in approve.output
    assert "profile fake" in approve.output

    recall = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "missing"])
    assert recall.exit_code == 0, recall.output
    assert "没有匹配" in recall.output
    assert "index rebuild" in recall.output

    weekly = runner.invoke(app, ["review", "weekly", "--config", str(cfg)])
    assert weekly.exit_code == 0, weekly.output
    assert "Next action" in weekly.output
    assert "approve list" in weekly.output


def test_backup_export_writes_safe_files_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.5.5: backup export 只导出安全摘要，不复制正文 secret，也不覆盖旧备份。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(
        cards,
        "approved",
        {"id": "approved", "title": "Approved", "status": "human_approved", "track": "agent-runtime"},
        body="## AI Summary\nBODY_SECRET_SHOULD_NOT_EXPORT\n",
    )
    _write_card(
        cards,
        "draft-secret",
        {"id": "draft-secret", "title": "DRAFT_SECRET_SHOULD_NOT_EXPORT", "status": "ai_draft"},
    )
    out_dir = tmp_path / "backup"

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("backup export 不应读取 .env")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    res = runner.invoke(app, ["backup", "export", "--config", str(cfg), "--output-dir", str(out_dir)])
    assert res.exit_code == 0, res.output
    assert (out_dir / "manifest.json").exists()
    exported = "\n".join(p.read_text(encoding="utf-8") for p in out_dir.glob("*.json"))
    assert "Approved" in exported
    assert "BODY_SECRET_SHOULD_NOT_EXPORT" not in exported
    assert "DRAFT_SECRET_SHOULD_NOT_EXPORT" not in exported
    assert ".env" not in exported

    second = runner.invoke(app, ["backup", "export", "--config", str(cfg), "--output-dir", str(out_dir)])
    assert second.exit_code == 2
    assert "拒绝覆盖" in second.output


def test_backup_export_works_from_non_repo_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """packaged-like smoke：backup export 不能依赖 repo cwd。"""
    cfg = _make_vault(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)

    res = runner.invoke(app, ["backup", "export", "--config", str(cfg), "--output-dir", "backup-out"])
    assert res.exit_code == 0, res.output
    assert (run_dir / "backup-out" / "manifest.json").exists()


def test_doctor_plus_reports_recovery_actions_and_paths(tmp_path: Path) -> None:
    """doctor plus 应给恢复检查和路径边界，帮助用户判断会读写哪里。"""
    cfg = _make_vault(tmp_path)
    res = runner.invoke(app, ["doctor", "--config", str(cfg), "--paths"])
    assert res.exit_code == 0, res.output
    assert "Recovery checks" in res.output
    assert "state.json" in res.output
    assert "bm25 index" in res.output
    assert "package assets" in res.output
    assert "Data safety paths" in res.output
    assert "writes backups" in res.output
    assert "index rebuild" in res.output or "mindforge scan" in res.output


def test_doctor_plus_no_env_network_or_obsidian_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """doctor plus 只读本地状态：不读 .env、不联网、不写 Obsidian 正式 notes。"""
    cfg = _make_vault(tmp_path)
    (tmp_path / ".env").write_text("SECRET=must-not-leak\n", encoding="utf-8")

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("doctor 不应读取 .env")

    def _blocked_socket(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("doctor 不应联网")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr(socket, "socket", _blocked_socket)
    res = runner.invoke(app, ["doctor", "--config", str(cfg), "--paths"])
    assert res.exit_code == 0, res.output
    assert "must-not-leak" not in res.output
    assert not (tmp_path / "vault" / "90-System" / "MindForge" / "Staging").exists()


def test_post_command_vault_normalization_keeps_cli_boundaries() -> None:
    """v0.5.1: 自然写法只对普通命令搬动，不能偷走 init/obsidian 的局部参数。"""
    assert _normalize_post_command_global_options(
        ["mindforge", "next", "--format", "json", "--vault", "examples/demo-vault"]
    ) == [
        "mindforge",
        "--vault",
        "examples/demo-vault",
        "next",
        "--format",
        "json",
    ]

    init_argv = ["mindforge", "init", "--vault", "/tmp/vault"]
    obsidian_argv = ["mindforge", "obsidian", "scan", "--vault", "/tmp/obsidian"]
    assert _normalize_post_command_global_options(init_argv) == init_argv
    assert _normalize_post_command_global_options(obsidian_argv) == obsidian_argv


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
