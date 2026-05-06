"""v0.3.1 — 配置化 BM25 + hybrid 排序 + index doctor。

为什么这些测试必须有：
- BM25 字段权重必须能从 ``configs/mindforge.yaml`` 调整，且能被回归检测；
- 配置改动后旧索引按旧权重打分 → 必须 stale；否则用户可能拿到错误排序；
- hybrid 仍然是**纯本地规则**，不调 LLM、不读 .env、不引 embedding；
- telemetry 仍然不能记录 query 原文。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge import lexical_index as lx
from mindforge.cli import app
from mindforge.config import ConfigError, load_mindforge_config

runner = CliRunner()


# ---------------------------------------------------------------------------
# fixture（带 v0.3.1 search 块）
# ---------------------------------------------------------------------------


def _make_vault(tmp_path: Path, *, search_block: dict | None = None) -> Path:
    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "30-Projects").mkdir(parents=True)
    cards.mkdir(parents=True)

    def write(name: str, fm: dict, body: str) -> None:
        front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items())
        (cards / f"{name}.md").write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")

    write(
        "checkpoint-low-value",
        {
            "id": "checkpoint-low-value",
            "title": "checkpoint 低价值卡",
            "status": "human_approved",
            "track": "agent-runtime",
            "tags": ["checkpoint"],
            "value_score": 2,
        },
        "## AI Summary\ncheckpoint 是 agent runtime 的关键设计\n",
    )
    write(
        "checkpoint-high-value",
        {
            "id": "checkpoint-high-value",
            "title": "checkpoint 高价值卡",
            "status": "human_approved",
            "track": "agent-runtime",
            "tags": ["checkpoint", "agent"],
            "value_score": 9,
            "review_after": "2000-01-01T00:00:00+00:00",  # 已到期 → review_due_norm=1
        },
        "## AI Summary\ncheckpoint 是 agent 的核心\n",
    )
    write(
        "harness-other",
        {
            "id": "harness-other",
            "title": "Harness eval",
            "status": "human_approved",
            "track": "harness-engineering",
            "tags": ["harness"],
            "value_score": 5,
        },
        "## AI Summary\nharness 与 checkpoint 一起评估\n",
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
    if search_block is not None:
        cfg["search"] = search_block
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return cfg_path


# ---------------------------------------------------------------------------
# 1. config: defaults + 覆盖 + 校验
# ---------------------------------------------------------------------------


def test_search_config_defaults_when_missing(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    assert cfg.search.bm25.k1 == 1.5
    assert cfg.search.bm25.b == 0.75
    assert cfg.search.bm25.fields["title"] == pytest.approx(5.0)
    assert cfg.search.hybrid.weights["bm25"] == pytest.approx(0.75)


def test_search_config_user_override(tmp_path: Path):
    cfg_path = _make_vault(
        tmp_path,
        search_block={
            "bm25": {"k1": 1.2, "b": 0.5, "fields": {"title": 9.0, "tags": 0}},
            "hybrid": {"weights": {"bm25": 0.5, "value_score": 0.3, "review_due": 0.2}},
        },
    )
    cfg = load_mindforge_config(cfg_path)
    assert cfg.search.bm25.k1 == 1.2
    assert cfg.search.bm25.fields["title"] == 9.0
    assert cfg.search.bm25.fields["tags"] == 0
    fw = lx.resolve_field_weights(cfg.search.bm25.fields)
    assert fw["title"] == 9.0
    assert "tags" not in fw  # 0 → 移除
    assert "track" in fw     # 默认值保留


def test_search_config_rejects_negative_weight(tmp_path: Path):
    cfg_path = _make_vault(
        tmp_path,
        search_block={"bm25": {"fields": {"title": -1}}},
    )
    with pytest.raises(ConfigError):
        load_mindforge_config(cfg_path)


def test_search_config_rejects_bad_b(tmp_path: Path):
    cfg_path = _make_vault(tmp_path, search_block={"bm25": {"b": 1.5}})
    with pytest.raises(ConfigError):
        load_mindforge_config(cfg_path)


# ---------------------------------------------------------------------------
# 2. config_hash + index stale 检测
# ---------------------------------------------------------------------------


def test_config_hash_changes_with_weights():
    h1 = lx.compute_config_hash(field_weights={"title": 5.0}, k1=1.5, b=0.75)
    h2 = lx.compute_config_hash(field_weights={"title": 6.0}, k1=1.5, b=0.75)
    assert h1 != h2


def test_index_rebuild_writes_config_hash(tmp_path: Path):
    cfg_path = _make_vault(tmp_path, search_block={"bm25": {"fields": {"title": 7.0}}})
    res = runner.invoke(app, ["index", "rebuild", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    assert "config_hash=" in res.output

    cfg = load_mindforge_config(cfg_path)
    idx_path = lx.default_index_path(cfg.state.workdir)
    idx = lx.BM25Index.load(idx_path)
    expected = lx.compute_config_hash(
        field_weights=lx.resolve_field_weights({"title": 7.0}),
        k1=cfg.search.bm25.k1, b=cfg.search.bm25.b,
    )
    assert idx.config_hash == expected


def test_index_status_shows_stale_on_config_drift(tmp_path: Path):
    cfg_path = _make_vault(tmp_path, search_block={"bm25": {"fields": {"title": 5.0}}})
    runner.invoke(app, ["index", "rebuild", "--config", str(cfg_path)])
    # 改 yaml：把 title 权重换掉
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["search"]["bm25"]["fields"]["title"] = 9.0
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    res = runner.invoke(app, ["index", "status", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    assert "stale" in res.output
    assert "配置漂移" in res.output


# ---------------------------------------------------------------------------
# 3. recall --ranking bm25 / hybrid
# ---------------------------------------------------------------------------


def test_recall_ranking_bm25_default_unchanged(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, [
        "recall", "--config", str(cfg_path),
        "--query", "checkpoint", "--format", "json",
    ])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["ranking"] == "bm25"
    # bm25 默认下，不返回 hybrid 三路分量
    assert all("final_score" not in it for it in payload["items"])


def test_recall_ranking_hybrid_adds_components(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, [
        "recall", "--config", str(cfg_path),
        "--query", "checkpoint", "--ranking", "hybrid",
        "--format", "json",
    ])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["ranking"] == "hybrid"
    assert payload["count"] >= 2
    for it in payload["items"]:
        for k in ("bm25_score", "bm25_norm", "value_norm", "review_due_norm", "final_score"):
            assert k in it


def test_recall_hybrid_promotes_high_value_card(tmp_path: Path):
    """checkpoint-high-value（value_score=9 + review 已到期）应排在
    checkpoint-low-value（value_score=2，无 review_after）之前。"""
    cfg_path = _make_vault(
        tmp_path,
        search_block={"hybrid": {"weights": {"bm25": 0.2, "value_score": 0.5, "review_due": 0.3}}},
    )
    res = runner.invoke(app, [
        "recall", "--config", str(cfg_path),
        "--query", "checkpoint", "--ranking", "hybrid",
        "--format", "json",
    ])
    assert res.exit_code == 0, res.output
    items = json.loads(res.output)["items"]
    ids = [it["id"] for it in items]
    assert ids.index("checkpoint-high-value") < ids.index("checkpoint-low-value")


def test_recall_hybrid_explain_shows_breakdown(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, [
        "recall", "--config", str(cfg_path),
        "--query", "checkpoint", "--ranking", "hybrid", "--explain",
    ])
    assert res.exit_code == 0, res.output
    assert "hybrid" in res.output
    assert "final=" in res.output


def test_recall_invalid_ranking(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, [
        "recall", "--config", str(cfg_path),
        "--query", "checkpoint", "--ranking", "neural",
    ])
    assert res.exit_code != 0


def test_recall_hybrid_safe_when_value_score_missing(tmp_path: Path):
    """没有 value_score / review_after 的卡片，hybrid 不应崩溃，分量按 0。"""
    cfg_path = _make_vault(tmp_path)
    # 写一张完全无 value_score / review_after 的卡片
    cards_dir = cfg_path.parent / "vault" / "20-Knowledge-Cards"
    fm = {
        "id": "bare", "title": "bare checkpoint", "status": "human_approved",
        "track": "agent-runtime",
    }
    front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items())
    (cards_dir / "bare.md").write_text(
        f"---\n{front}\n---\n\n## AI Summary\ncheckpoint only\n", encoding="utf-8"
    )
    res = runner.invoke(app, [
        "recall", "--config", str(cfg_path),
        "--query", "checkpoint", "--ranking", "hybrid", "--format", "json",
    ])
    assert res.exit_code == 0, res.output
    items = json.loads(res.output)["items"]
    bare = next((i for i in items if i["id"] == "bare"), None)
    assert bare is not None
    assert bare["value_norm"] == 0.0
    assert bare["review_due_norm"] == 0.0


# ---------------------------------------------------------------------------
# 4. telemetry 安全
# ---------------------------------------------------------------------------


def test_recall_telemetry_no_query_plaintext(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    secret = "SECRET_QUERY_TOKEN_xyz"
    res = runner.invoke(app, [
        "recall", "--config", str(cfg_path),
        "--query", secret, "--ranking", "hybrid",
    ])
    assert res.exit_code == 0
    runs_dir = tmp_path / ".mindforge" / "runs"
    if runs_dir.exists():
        for f in runs_dir.glob("*.jsonl"):
            text = f.read_text(encoding="utf-8")
            assert secret not in text, f"query plaintext leaked into {f}"
            assert "ranking_mode" in text  # 但 ranking_mode 元数据应在
    else:
        pytest.skip("no runs written")


# ---------------------------------------------------------------------------
# 5. doctor 提示
# ---------------------------------------------------------------------------


def test_doctor_flags_missing_index(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, ["doctor", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    assert "BM25 索引缺失" in res.output


def test_doctor_flags_stale_index_after_config_change(tmp_path: Path):
    cfg_path = _make_vault(tmp_path, search_block={"bm25": {"fields": {"title": 5.0}}})
    runner.invoke(app, ["index", "rebuild", "--config", str(cfg_path)])
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["search"]["bm25"]["fields"]["title"] = 9.0
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    res = runner.invoke(app, ["doctor", "--config", str(cfg_path)])
    assert res.exit_code == 0
    assert "BM25 索引与 search 配置不一致" in res.output


# ---------------------------------------------------------------------------
# 6. 安全承诺：v0.3 旧测试不变（这里抽样验证）
# ---------------------------------------------------------------------------


def test_no_source_excerpt_in_hybrid_results(tmp_path: Path):
    """hybrid 路径仍然不能引入 source_excerpt / human_note。"""
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, [
        "recall", "--config", str(cfg_path),
        "--query", "checkpoint", "--ranking", "hybrid", "--format", "json",
    ])
    assert res.exit_code == 0
    payload = res.output
    assert "Source Excerpt" not in payload
    assert "Human Note" not in payload
