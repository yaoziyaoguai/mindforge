"""v0.3 — BM25 lexical recall 测试。

为什么必须测 source_excerpt 不入索引：v0.3 的安全核心承诺就是"BM25 永远不
索引原始 source 内容"。哪怕一次回归都不能放过 —— 否则等于让 ai_draft 中潜在
的隐私 token 被任何 ``mindforge recall --query`` 命中并打印到 stdout。

为什么必须测 default human_approved：与 M4 recall 一致的安全默认。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge import lexical_index as lx
from mindforge.cards import iter_cards
from mindforge.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# fixture
# ---------------------------------------------------------------------------


def _make_vault(tmp_path: Path) -> Path:
    """造一个最小 vault + 几张多样化卡片 + 一个 mindforge.yaml。"""
    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "30-Projects").mkdir(parents=True)
    cards.mkdir(parents=True)

    def write(name: str, fm: dict, body: str) -> None:
        front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items())
        (cards / f"{name}.md").write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")

    write(
        "react-checkpoint",
        {
            "id": "react-checkpoint",
            "title": "ReAct Loop checkpoint 与状态机",
            "status": "human_approved",
            "track": "agent-runtime",
            "projects": ["my-first-agent"],
            "tags": ["agent", "runtime", "checkpoint"],
            "source_type": "plain_markdown",
            "value_score": 8,
        },
        "## AI Summary\n- checkpoint 是 agent runtime 的关键设计\n"
        "- 状态机配合 ReAct loop\n\n"
        "## Source Excerpt\n> zzqxwpvk9999 不应被索引\n\n"
        "## Human Note\nqqzzkkmm8888 也不应被索引\n",
    )
    write(
        "harness-eval",
        {
            "id": "harness-eval",
            "title": "Harness evaluation pipeline",
            "status": "human_approved",
            "track": "harness-engineering",
            "projects": ["agent-tool-harness"],
            "tags": ["harness", "evaluation"],
            "source_type": "cubox_markdown",
            "value_score": 6,
        },
        "## AI Summary\nharness 用来评估 agent\n",
    )
    write(
        "draft-agent",
        {
            "id": "draft-agent",
            "title": "Agent draft note",
            "status": "ai_draft",
            "track": "agent-runtime",
            "projects": ["my-first-agent"],
            "tags": ["agent", "draft"],
            "source_type": "manual_note",
        },
        "## AI Summary\ndraft only checkpoint mention\n",
    )

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
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return cfg_path


# ---------------------------------------------------------------------------
# tokenizer
# ---------------------------------------------------------------------------


def test_tokenize_ascii_lowercase():
    assert lx.tokenize("ReAct Agent-Runtime checkpoint") == [
        "react", "agent", "runtime", "checkpoint",
    ]


def test_tokenize_cjk_per_char():
    toks = lx.tokenize("状态机 + ReAct")
    assert "状" in toks and "态" in toks and "机" in toks
    assert "react" in toks


def test_tokenize_empty():
    assert lx.tokenize("") == []
    assert lx.tokenize("!!!") == []


# ---------------------------------------------------------------------------
# build / search
# ---------------------------------------------------------------------------


def test_build_index_excludes_source_excerpt_and_human_note(tmp_path: Path):
    """硬保证：source_excerpt / human_note 中的 token 不进入索引。"""
    cfg = _make_vault(tmp_path)
    vault_root = Path(yaml.safe_load(cfg.read_text())["vault"]["root"])
    cards = iter_cards(vault_root, "20-Knowledge-Cards").cards
    index = lx.build_index(cards)

    all_tokens: set[str] = set()
    for d in index.docs:
        for toks in d.fields.values():
            all_tokens.update(toks)

    # 这两个 token 只出现在 Source Excerpt / Human Note；绝不能出现在索引里。
    assert "zzqxwpvk9999" not in all_tokens
    assert "qqzzkkmm8888" not in all_tokens


def test_search_default_filters_to_human_approved(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    vault_root = Path(yaml.safe_load(cfg.read_text())["vault"]["root"])
    cards = iter_cards(vault_root, "20-Knowledge-Cards").cards
    idx = lx.build_index(cards)
    hits = lx.search(idx, "agent")
    statuses = {h.doc.status for h in hits}
    assert statuses == {"human_approved"}


def test_search_include_drafts_opens_up(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    vault_root = Path(yaml.safe_load(cfg.read_text())["vault"]["root"])
    cards = iter_cards(vault_root, "20-Knowledge-Cards").cards
    idx = lx.build_index(cards)
    hits = lx.search(idx, "agent", include_drafts=True)
    statuses = {h.doc.status for h in hits}
    assert "ai_draft" in statuses
    assert "human_approved" in statuses


def test_search_field_weight_title_beats_tag_only(tmp_path: Path):
    """title 命中应当比仅 tags 命中得分更高（同 term）。"""
    cfg = _make_vault(tmp_path)
    vault_root = Path(yaml.safe_load(cfg.read_text())["vault"]["root"])
    cards = iter_cards(vault_root, "20-Knowledge-Cards").cards
    idx = lx.build_index(cards)
    hits = lx.search(idx, "checkpoint")
    # checkpoint 命中 react-checkpoint（title + tags + body），不命中 harness-eval
    assert hits, "checkpoint 应当至少命中一张卡"
    assert hits[0].doc.id == "react-checkpoint"


def test_search_pre_filter_by_track(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    vault_root = Path(yaml.safe_load(cfg.read_text())["vault"]["root"])
    cards = iter_cards(vault_root, "20-Knowledge-Cards").cards
    idx = lx.build_index(cards)
    hits = lx.search(idx, "checkpoint", track="harness-engineering")
    # harness 卡完全不含 "checkpoint"
    assert not hits


def test_search_explain_breakdown(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    vault_root = Path(yaml.safe_load(cfg.read_text())["vault"]["root"])
    cards = iter_cards(vault_root, "20-Knowledge-Cards").cards
    idx = lx.build_index(cards)
    hits = lx.search(idx, "checkpoint")
    assert hits
    fhs = hits[0].field_hits
    assert any(fh.field == "title" for fh in fhs)
    # 贡献分降序
    contribs = [fh.contribution for fh in fhs]
    assert contribs == sorted(contribs, reverse=True)


def test_empty_query_returns_empty(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    vault_root = Path(yaml.safe_load(cfg.read_text())["vault"]["root"])
    cards = iter_cards(vault_root, "20-Knowledge-Cards").cards
    idx = lx.build_index(cards)
    assert lx.search(idx, "") == []
    assert lx.search(idx, "    ") == []


# ---------------------------------------------------------------------------
# 持久化
# ---------------------------------------------------------------------------


def test_save_load_roundtrip(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    vault_root = Path(yaml.safe_load(cfg.read_text())["vault"]["root"])
    cards = iter_cards(vault_root, "20-Knowledge-Cards").cards
    idx = lx.build_index(cards)
    p = tmp_path / "idx.json"
    idx.save(p)
    loaded = lx.BM25Index.load(p)
    assert loaded.schema_version == idx.schema_version
    assert len(loaded.docs) == len(idx.docs)
    h1 = lx.search(idx, "checkpoint")
    h2 = lx.search(loaded, "checkpoint")
    assert [h.doc.rel_path for h in h1] == [h.doc.rel_path for h in h2]
    assert [round(h.score, 6) for h in h1] == [round(h.score, 6) for h in h2]


def test_diff_index_detects_changes(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    vault_root = Path(yaml.safe_load(cfg.read_text())["vault"]["root"])
    cards1 = iter_cards(vault_root, "20-Knowledge-Cards").cards
    idx = lx.build_index(cards1)
    diff = lx.diff_index(idx, cards1)
    assert diff.fresh

    # 加一张新卡 → stale
    new = vault_root / "20-Knowledge-Cards" / "newone.md"
    new.write_text(
        '---\nid: new1\ntitle: new\nstatus: human_approved\n---\n\nbody\n',
        encoding="utf-8",
    )
    cards2 = iter_cards(vault_root, "20-Knowledge-Cards").cards
    diff2 = lx.diff_index(idx, cards2)
    assert not diff2.fresh
    assert any("newone.md" in rp for rp in diff2.added)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_index_rebuild_and_status(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    r1 = runner.invoke(app, ["index", "rebuild", "--config", str(cfg)])
    assert r1.exit_code == 0, r1.output
    assert "索引已写入" in r1.output

    idx_path = tmp_path / ".mindforge" / "index" / "bm25.json"
    assert idx_path.exists()

    r2 = runner.invoke(app, ["index", "status", "--config", str(cfg)])
    assert r2.exit_code == 0, r2.output
    assert "fresh" in r2.output


def test_cli_index_status_when_missing(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    r = runner.invoke(app, ["index", "status", "--config", str(cfg)])
    assert r.exit_code == 0
    assert "索引文件不存在" in r.output
    assert "rebuild" in r.output


def test_cli_recall_query_basic(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    runner.invoke(app, ["index", "rebuild", "--config", str(cfg)])
    r = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "checkpoint"])
    assert r.exit_code == 0, r.output
    assert "engine=bm25" in r.output
    assert "react-checkpoint" in r.output
    # ai_draft 默认排除
    assert "draft-agent" not in r.output


def test_cli_recall_query_explain(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    r = runner.invoke(
        app, ["recall", "--config", str(cfg), "--query", "checkpoint", "--explain"]
    )
    assert r.exit_code == 0, r.output
    # explain 至少打印一行 field 行
    assert "title" in r.output or "tags" in r.output


def test_cli_recall_query_include_drafts(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    r = runner.invoke(
        app,
        ["recall", "--config", str(cfg), "--query", "agent", "--include-drafts"],
    )
    assert r.exit_code == 0
    assert "draft-agent" in r.output
    assert "react-checkpoint" in r.output


def test_cli_recall_query_secret_token_never_matches(tmp_path: Path):
    """端到端硬保证：source_excerpt 与 human_note 中的 token 不可能命中。"""
    cfg = _make_vault(tmp_path)
    for q in ("zzqxwpvk9999", "qqzzkkmm8888"):
        r = runner.invoke(
            app,
            ["recall", "--config", str(cfg), "--query", q, "--include-drafts"],
        )
        assert r.exit_code == 0
        assert "react-checkpoint" not in r.output
        assert "draft-agent" not in r.output
        assert "harness-eval" not in r.output


def test_cli_recall_query_json_format(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    r = runner.invoke(
        app,
        ["recall", "--config", str(cfg), "--query", "checkpoint", "--format", "json"],
    )
    assert r.exit_code == 0
    payload = json.loads(r.output)
    assert payload["engine"] == "bm25"
    assert payload["query"]["query_provided"] is True
    assert "query_hash" in payload["query"]
    assert payload["count"] >= 1
    item = payload["items"][0]
    # JSON 安全字段：不暴露 doc_len / fields / 原始 query
    assert set(item.keys()) <= {
        "score", "id", "title", "rel_path", "status", "track",
        "projects", "tags", "source_type", "created_at", "explain",
    }


def test_cli_recall_query_limit(tmp_path: Path):
    cfg = _make_vault(tmp_path)
    r = runner.invoke(
        app,
        ["recall", "--config", str(cfg), "--query", "agent", "--include-drafts", "--limit", "1"],
    )
    assert r.exit_code == 0
    # 应只列 1 条
    lines = [ln for ln in r.output.splitlines() if ln.startswith("- score=")]
    assert len(lines) == 1


def test_cli_recall_no_query_falls_back_to_legacy_path(tmp_path: Path):
    """不带 --query 时仍走 M4.1 规则检索（行为未变）。"""
    cfg = _make_vault(tmp_path)
    r = runner.invoke(app, ["recall", "--config", str(cfg)])
    assert r.exit_code == 0
    # 旧路径输出含 "Recall ·" 与 "sort=" 标记
    assert "sort=" in r.output


def test_index_file_inside_workdir_under_dot_mindforge(tmp_path: Path):
    """索引必须落在 workdir/index/，并且 workdir 默认是 .mindforge（被 .gitignore 挡）。"""
    cfg = _make_vault(tmp_path)
    runner.invoke(app, ["index", "rebuild", "--config", str(cfg)])
    p = tmp_path / ".mindforge" / "index" / "bm25.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["schema_version"] == lx.SCHEMA_VERSION
    assert "docs" in data and len(data["docs"]) >= 2
