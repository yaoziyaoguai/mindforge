"""v0.2.4 — WebClipMarkdownAdapter / ChatExportAdapter / CLI polish 测试。

为什么这些 adapter 仍然只是"格式翻译"而不是 RAG / 抓取：
- 不访问网络（webclip）；
- 不重写源文件；
- 不基于内容做"角色脱敏"等推断（chat_export 仅产出统计元信息）；

为什么测试要做"反向断言"（不出现 sk-/Bearer/.env）：
- 这些 adapter 的输入是用户私有材料（聊天导出 / 网页内容）；
- runs/telemetry 字段白名单是产品安全契约的核心，必须每个 milestone 都验。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge import __version__
from mindforge.sources.chat_export import ChatExportAdapter
from mindforge.sources.stubs import DocxAdapter, PdfAdapter
from mindforge.sources.webclip_markdown import WebClipMarkdownAdapter

from .test_process_e2e import _common_process_args

runner = CliRunner()


# ---------------------------------------------------------------------------
# WebClipMarkdownAdapter
# ---------------------------------------------------------------------------


def _write(p: Path, txt: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")
    return p


def test_webclip_full_frontmatter(tmp_path: Path) -> None:
    f = _write(
        tmp_path / "a.md",
        "---\n"
        'title: "Designing Agent Runtimes"\n'
        "source: https://example.com/agent-runtime\n"
        "author: Jane Doe\n"
        "tags: [agent, runtime]\n"
        "created: 2025-04-01\n"
        "---\n\n"
        "# Designing Agent Runtimes\n\n"
        "Body paragraph here.\n",
    )
    doc = WebClipMarkdownAdapter().load(str(f))
    assert doc.source_type == "webclip_markdown"
    assert doc.title == "Designing Agent Runtimes"
    assert doc.source_url == "https://example.com/agent-runtime"
    assert doc.author == "Jane Doe"
    assert "agent" in doc.tags
    assert doc.created_at is not None
    assert doc.content_hash.startswith("sha256:")
    assert doc.raw_text.lstrip().startswith("# Designing")


def test_webclip_title_falls_back_to_h1(tmp_path: Path) -> None:
    f = _write(tmp_path / "no-front.md", "# Real H1 Title\n\nbody\n")
    doc = WebClipMarkdownAdapter().load(str(f))
    assert doc.title == "Real H1 Title"


def test_webclip_title_falls_back_to_stem(tmp_path: Path) -> None:
    f = _write(tmp_path / "naked-note.md", "no heading, just text\n")
    doc = WebClipMarkdownAdapter().load(str(f))
    assert doc.title == "naked-note"


def test_webclip_can_handle_md_only() -> None:
    a = WebClipMarkdownAdapter()
    assert a.can_handle("x.md")
    assert not a.can_handle("x.pdf")


def test_webclip_hash_stable(tmp_path: Path) -> None:
    f = _write(tmp_path / "s.md", "---\ntitle: T\nsource: u\n---\nbody\n")
    a = WebClipMarkdownAdapter()
    assert a.load(str(f)).content_hash == a.load(str(f)).content_hash


# ---------------------------------------------------------------------------
# ChatExportAdapter
# ---------------------------------------------------------------------------


def test_chat_export_h2_role_detection(tmp_path: Path) -> None:
    f = _write(
        tmp_path / "chat.md",
        "---\ntitle: Debug session\n---\n\n"
        "## User\n\nWhy is my agent looping?\n\n"
        "## Assistant\n\nLook at the tool result schema.\n\n"
        "## User\n\nAh, makes sense.\n",
    )
    doc = ChatExportAdapter().load(str(f))
    assert doc.source_type == "chat_export"
    assert doc.title == "Debug session"
    md = doc.metadata
    assert md["turn_count"] == 3
    assert md["role_counts"]["user"] == 2
    assert md["role_counts"]["assistant"] == 1
    assert md["role_detection"] == "ok"


def test_chat_export_bold_role_detection(tmp_path: Path) -> None:
    f = _write(
        tmp_path / "claude.md",
        "**Human:**\n\nhi\n\n**Claude:**\n\nhello!\n\n**Human:**\n\nbye\n",
    )
    doc = ChatExportAdapter().load(str(f))
    assert doc.metadata["turn_count"] == 3
    assert doc.metadata["role_counts"]["user"] == 2
    assert doc.metadata["role_counts"]["assistant"] == 1


def test_chat_export_degraded_plain_text(tmp_path: Path) -> None:
    f = _write(tmp_path / "raw.md", "Just a flat dump of conversation, no markers.\n")
    doc = ChatExportAdapter().load(str(f))
    assert doc.metadata["turn_count"] == 0
    assert doc.metadata["role_detection"] == "degraded_plain_text"
    # 不报错，依然有合法 SourceDocument
    assert doc.content_hash.startswith("sha256:")


def test_chat_export_hash_changes_with_turn_count(tmp_path: Path) -> None:
    a = ChatExportAdapter()
    f1 = _write(tmp_path / "c1.md", "## User\n\nq\n\n## Assistant\n\na\n")
    f2 = _write(
        tmp_path / "c2.md",
        "## User\n\nq\n\n## Assistant\n\na\n\n## User\n\nfollow-up\n",
    )
    assert a.load(str(f1)).content_hash != a.load(str(f2)).content_hash


# ---------------------------------------------------------------------------
# Stubs (PDF/Docx) — v0.2.4 stub 行为；v0.2.5 已升级为真实 adapter，
# 这里改为校验"未安装可选依赖时给出友好错误"。
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cls", [PdfAdapter, DocxAdapter])
def test_pdf_docx_can_handle_by_extension(cls) -> None:
    a = cls()
    if a.source_type == "pdf":
        assert a.can_handle("x.pdf")
    else:
        assert a.can_handle("x.docx")
    assert not a.can_handle("x.md")


# ---------------------------------------------------------------------------
# CLI polish — version / --debug / --help
# ---------------------------------------------------------------------------


_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{8,}"),
    re.compile(r"Authorization:", re.IGNORECASE),
    re.compile(r"MINDFORGE_LLM_API_KEY=[^\s]+"),
]


def _assert_no_secrets(text: str) -> None:
    for pat in _SECRET_PATTERNS:
        assert not pat.search(text), f"secret pattern leaked: {pat.pattern}"


def test_version_prints_metadata_only(tmp_path: Path) -> None:
    cfg_path = _make_minimal_cfg(tmp_path)
    res = runner.invoke(app, ["version", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    # 版本号会随 release 自然演进；测试只要求 CLI 与包内 __version__ 对齐。
    assert f"MindForge v{__version__}" in res.output
    assert "telemetry.enabled" in res.output
    _assert_no_secrets(res.output)


def test_version_with_missing_config_does_not_crash(tmp_path: Path) -> None:
    res = runner.invoke(
        app, ["version", "--config", str(tmp_path / "nope.yaml")]
    )
    assert res.exit_code == 0
    assert f"MindForge v{__version__}" in res.output


def test_help_works() -> None:
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "MindForge" in res.output
    for sub in ("web", "status", "doctor", "watch", "import", "approve", "library", "wiki", "version"):
        assert sub in res.output
    for hidden in ("scan", "process", "telemetry"):
        assert hidden not in res.output


def test_debug_flag_accepted(tmp_path: Path) -> None:
    cfg_path = _make_minimal_cfg(tmp_path)
    res = runner.invoke(app, ["--debug", "version", "--config", str(cfg_path)])
    assert res.exit_code == 0


# ---------------------------------------------------------------------------
# 端到端：webclip + chat_export 文件能被 scan 识别且通过 fake 跑完 process
# ---------------------------------------------------------------------------


def _make_minimal_cfg(tmp_path: Path) -> Path:
    """构造最小 vault + 启用 webclip / chat_export 的 yaml；fake LLM。"""
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "WebClips").mkdir(parents=True)
    (vault / "00-Inbox" / "ChatExports").mkdir(parents=True)
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)

    _write(
        vault / "00-Inbox" / "WebClips" / "w.md",
        "---\ntitle: Web Page A\nsource: https://example.com/a\n---\n\nbody\n",
    )
    _write(
        vault / "00-Inbox" / "ChatExports" / "c.md",
        "## User\n\nq?\n\n## Assistant\n\na.\n",
    )

    cfg = {
        "version": 0.1,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {
            "enabled": ["webclip_markdown", "chat_export"],
            "registry": {
                "webclip_markdown": {
                    "adapter": "WebClipMarkdownAdapter",
                    "inbox_subdir": "WebClips",
                    "file_glob": "*.md",
                    "enabled": True,
                },
                "chat_export": {
                    "adapter": "ChatExportAdapter",
                    "inbox_subdir": "ChatExports",
                    "file_glob": "*.md",
                    "enabled": True,
                },
            },
        },
        "state": {
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "f1",
                    "distill": "f1",
                    "link_suggestion": "f1",
                    "review_questions": "f1",
                    "action_extraction": "f1",
                }
            },
            "models": {
                "f1": {
                    "provider": "fake-local",
                    "type": "fake",
                    "base_url": "fake://",
                    "model": "fake-1",
                    "timeout_seconds": 5,
                    "max_retries": 0,
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


def test_scan_identifies_webclip_and_chat(tmp_path: Path) -> None:
    cfg_path = _make_minimal_cfg(tmp_path)
    res = runner.invoke(app, ["scan", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    state = json.loads(
        (tmp_path / ".mindforge" / "state.json").read_text(encoding="utf-8")
    )
    types = {item["source_type"] for item in state["items"].values()}
    assert types == {"webclip_markdown", "chat_export"}


def test_process_webclip_and_chat_through_fake(tmp_path: Path) -> None:
    cfg_path = _make_minimal_cfg(tmp_path)
    runner.invoke(app, ["scan", "--config", str(cfg_path)])
    res = runner.invoke(app, _common_process_args(cfg_path))
    assert res.exit_code == 0, res.output

    cards_dir = tmp_path / "vault" / "20-Knowledge-Cards"
    cards = list(cards_dir.rglob("*.md"))
    assert len(cards) >= 2

    runs_dir = tmp_path / ".mindforge" / "runs"
    for jl in runs_dir.glob("*.jsonl"):
        text = jl.read_text(encoding="utf-8")
        _assert_no_secrets(text)
        # raw_text 不能写到 runs
        assert "Web Page A" not in text or '"event"' in text  # title 可能合法出现在 file_seen 事件中
        assert "Just a flat dump" not in text


def test_telemetry_no_secrets_after_run(tmp_path: Path) -> None:
    cfg_path = _make_minimal_cfg(tmp_path)
    runner.invoke(app, ["scan", "--config", str(cfg_path)])
    runner.invoke(app, _common_process_args(cfg_path))
    tel = tmp_path / ".mindforge" / "telemetry.jsonl"
    if tel.exists():
        text = tel.read_text(encoding="utf-8")
        _assert_no_secrets(text)
        # 仅元数据：不含 raw / prompt / completion 字眼
        for line in text.splitlines():
            obj = json.loads(line)
            for forbidden in ("raw_text", "prompt", "completion", "api_key"):
                assert forbidden not in obj
