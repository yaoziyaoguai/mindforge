"""v0.7.12 — Recall service 边界测试。

学习要点：recall_service 是 query-path recall 的 use-case 层，只返回结构化
结果；CLI 负责 Typer 参数、Rich/JSON/Markdown 输出和本地 RunLogger。这样
BM25/hybrid 判断可以被直接测试，而不是只能靠 CLI 输出字符串回归。
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import yaml

from mindforge.config import load_mindforge_config
from mindforge.recall_service import (
    RecallQuery,
    recall_hit_to_safe_dict,
    run_bm25_recall,
)


def _write_card(cards_dir: Path, name: str, fm: dict, body: str) -> None:
    front = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fm.items())
    (cards_dir / f"{name}.md").write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")


def _make_recall_cfg(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    cards.mkdir(parents=True)
    (vault / "00-Inbox").mkdir(parents=True)
    _write_card(
        cards,
        "agent-approved",
        {
            "id": "agent-approved",
            "title": "Agent Runtime Checkpoint",
            "status": "human_approved",
            "track": "agent-runtime",
            "tags": ["agent", "checkpoint"],
            "value_score": 8,
        },
        "## AI Summary\nagent runtime checkpoint keeps state explicit\n",
    )
    _write_card(
        cards,
        "agent-draft",
        {
            "id": "agent-draft",
            "title": "Agent Draft Memory",
            "status": "ai_draft",
            "track": "agent-runtime",
            "tags": ["agent"],
            "value_score": 5,
        },
        "## AI Summary\nagent draft should only appear with include drafts\n",
    )
    _write_card(
        cards,
        "other-approved",
        {
            "id": "other-approved",
            "title": "Cooking Notes",
            "status": "human_approved",
            "track": "life",
            "tags": ["cooking"],
            "value_score": 4,
        },
        "## AI Summary\nrecipe notes only\n",
    )
    cfg = {
        "version": 0.7,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {"enabled": [], "registry": {}},
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
            "models": {"fake_alias": {"provider": "fake", "type": "fake", "model": "fake"}},
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
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return cfg_path


def _query(**overrides) -> RecallQuery:
    base = {
        "query": "agent",
        "track": None,
        "project": None,
        "tags": (),
        "source_type": None,
        "status": "human_approved",
        "include_drafts": False,
        "since": None,
        "until": None,
        "limit": 20,
        "output_format": "compact",
        "explain": False,
        "ranking": "bm25",
        "weight_bm25": None,
        "weight_value_score": None,
        "weight_review_due": None,
    }
    base.update(overrides)
    return RecallQuery(**base)


def test_recall_service_returns_approved_card_for_query(tmp_path: Path) -> None:
    """query-path recall 应命中 human_approved 卡片，并返回结构化安全字段。"""
    cfg = load_mindforge_config(_make_recall_cfg(tmp_path))

    result = run_bm25_recall(cfg, _query())

    assert [hit.id for hit in result.hits] == ["agent-approved"]
    assert result.hits[0].status == "human_approved"
    assert "agent" in result.hits[0].matched_terms_list
    assert result.index.card_counts["human_approved"] == 2
    assert result.index.vault_root == cfg.vault.root
    assert result.index.cards_dir == cfg.vault.cards_dir


def test_recall_service_marks_disk_index_stale_when_cards_change(tmp_path: Path) -> None:
    """磁盘索引存在但卡片集合变了时，应临时重建并提示用户持久 rebuild。"""

    from mindforge import lexical_index as lx
    from mindforge.cards import iter_cards

    cfg = load_mindforge_config(_make_recall_cfg(tmp_path))
    fw = lx.resolve_field_weights(cfg.search.bm25.fields)
    old_index = lx.build_index(
        iter_cards(cfg.vault.root, cfg.vault.cards_dir).cards,
        field_weights=fw,
        k1=cfg.search.bm25.k1,
        b=cfg.search.bm25.b,
        config_hash=lx.compute_config_hash(field_weights=fw, k1=cfg.search.bm25.k1, b=cfg.search.bm25.b),
    )
    old_index.save(lx.default_index_path(cfg.state.workdir))
    _write_card(
        cfg.vault.cards_path,
        "new-agent",
        {"id": "new-agent", "title": "New Agent", "status": "human_approved"},
        "## AI Summary\nnew agent memory\n",
    )

    result = run_bm25_recall(cfg, _query(query="new"))

    assert [hit.id for hit in result.hits] == ["new-agent"]
    assert result.index.source == "memory-rebuilt-stale"
    assert result.index.stale is True
    assert result.index.suggest_rebuild is True


def test_recall_service_include_drafts_boundary(tmp_path: Path) -> None:
    """默认不返回 ai_draft；显式 include_drafts 才把草稿纳入本地词法检索。"""
    cfg = load_mindforge_config(_make_recall_cfg(tmp_path))

    approved_only = run_bm25_recall(cfg, _query(include_drafts=False))
    with_drafts = run_bm25_recall(cfg, _query(include_drafts=True))

    assert "agent-draft" not in {hit.id for hit in approved_only.hits}
    assert "agent-draft" in {hit.id for hit in with_drafts.hits}


def test_recall_service_limit_empty_query_and_stable_ranking(tmp_path: Path) -> None:
    """limit 与空 query 都在 service 层生效；排序保持由 BM25 分数和路径稳定决定。"""
    cfg = load_mindforge_config(_make_recall_cfg(tmp_path))

    limited = run_bm25_recall(cfg, _query(include_drafts=True, limit=1))
    empty = run_bm25_recall(cfg, _query(query="", include_drafts=True))

    assert len(limited.hits) == 1
    assert limited.hits[0].score >= 0
    assert empty.hits == ()


def test_recall_service_explain_safe_payload(tmp_path: Path) -> None:
    """explain 只包含 token、字段名和贡献分，不暴露 source 原文或 Human Note。"""
    cfg = load_mindforge_config(_make_recall_cfg(tmp_path))

    result = run_bm25_recall(cfg, _query(explain=True))
    payload = recall_hit_to_safe_dict(
        result.hits[0],
        explain=True,
        ranking=result.query.ranking,
        index_stale=result.index.stale,
        weight_source=result.weight_source,
    )

    assert payload["explain"]
    assert "agent" in payload["matched_terms"]
    assert "title" in payload["matched_fields"] or "body_summary" in payload["matched_fields"]
    assert "Source Excerpt" not in json.dumps(payload, ensure_ascii=False)
    assert "Human Note" not in json.dumps(payload, ensure_ascii=False)


def test_recall_service_hybrid_returns_components(tmp_path: Path) -> None:
    """hybrid 仍是本地规则排序，不是 RAG；service 返回三路分量供 CLI 展示。"""
    cfg = load_mindforge_config(_make_recall_cfg(tmp_path))

    result = run_bm25_recall(cfg, _query(ranking="hybrid", include_drafts=True, weight_bm25=0.2))

    assert result.weight_source == "cli_override"
    assert result.hits[0].final_score is not None
    assert result.hits[0].bm25_norm is not None
    assert result.active_weights is not None
    assert result.active_weights["bm25"] == 0.2


def test_recall_service_no_env_llm_network_or_file_write(tmp_path: Path, monkeypatch) -> None:
    """service 可读本地卡片，但不能读 .env、调用 LLM、联网或写 index/runs。"""
    cfg = load_mindforge_config(_make_recall_cfg(tmp_path))
    (tmp_path / ".env").write_text("MINDFORGE_LLM_API_KEY=secret\n", encoding="utf-8")

    def _blocked(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("recall_service 不应触发这个外部边界")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked)
    monkeypatch.setattr("mindforge.llm.build_providers", _blocked)
    monkeypatch.setattr(socket, "socket", _blocked)

    result = run_bm25_recall(cfg, _query(include_drafts=True))

    assert result.count >= 1
    assert not (cfg.state.workdir / "index" / "bm25.json").exists()
    assert not (cfg.state.workdir / "runs").exists()


def test_recall_service_has_no_cli_presentation_dependency() -> None:
    """service 模块不能依赖 Typer / Rich / console，避免业务判断重新耦合 CLI。"""
    source = Path("src/mindforge/recall_service.py").read_text(encoding="utf-8")

    assert "import typer" not in source
    assert "from rich" not in source
    assert "Console(" not in source
    assert "Table(" not in source
    assert "build_providers" not in source
    assert "LLMClient" not in source


def test_recall_service_uses_retrieval_port_for_index_loading(tmp_path: Path) -> None:
    """v3.6.1 关键回归：recall_service 必须通过 RetrievalPort.load_or_build_index()
    加载索引，不能绕过端口直接调用 lexical_index.BM25Index.load() 或 build_index()。

    中文学习型说明：此测试通过注入一个只记录调用的 FakeRetrievalPort，
    验证 recall_service 的索引生命周期完全走 RetrievalPort 抽象边界。
    这是 P2-04（RetrievalPort 未集成到 recall_service）的验收测试。
    """
    from mindforge.retrieval.retrieval_port import IndexLoadResult, RetrievalPort

    call_log: list[str] = []

    class FakeRetrievalPort(RetrievalPort):
        """只记录调用、不执行真实索引操作的假端口。"""

        def load_or_build_index(self, index_path, cards, *, field_weights=None, k1=1.2, b=0.75, config_hash=None):
            call_log.append("load_or_build_index")
            return IndexLoadResult(
                index=_make_fake_index(cards),
                source="memory-temp",
                used_disk=False,
                stale=False,
                warnings=(),
            )

        def search(self, index, query, **kwargs):
            call_log.append("search")
            return []

        def hybrid_search(self, index, query, **kwargs):
            call_log.append("hybrid_search")
            return []

    def _make_fake_index(cards):
        """构造一个最小可用索引对象供 search/hybrid_search 消费。"""
        from mindforge import lexical_index as lx

        fw = {"title": 2.0, "body_summary": 1.0}
        return lx.build_index(cards, field_weights=fw)

    cfg = load_mindforge_config(_make_recall_cfg(tmp_path))
    engine = FakeRetrievalPort()

    run_bm25_recall(cfg, _query(), engine=engine)

    assert "load_or_build_index" in call_log, (
        f"recall_service 未通过 RetrievalPort.load_or_build_index() 加载索引，"
        f"调用日志: {call_log}"
    )
    assert "search" in call_log or "hybrid_search" in call_log, (
        f"recall_service 未通过 RetrievalPort 执行检索，调用日志: {call_log}"
    )
