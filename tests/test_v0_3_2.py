"""v0.3.2 — recall UX polish + index info JSON + doctor 增强。

为什么这些测试必须有：
- ``--weight-*`` CLI override **绝不**应写回 yaml；只影响本次排序；
- 非法权重（负数 / 全 0）必须 fail-fast，不能静默回退；
- ``recall --explain --format json`` 必须输出 ``why_this_matched`` / ``weight_source`` /
  ``active_weights`` 等机器可读字段，便于调试和回归；
- ``index info --json`` 必须给出**稳定 schema**（version=1），供脚本/doctor 消费；
- doctor 必须在"没有 human_approved 卡片"等场景下给出可执行 hint；
- 所有这些行为仍然是**纯本地排序 / 纯 frontmatter 计算**，不调 LLM、不读 .env、不引 embedding。
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

from .test_v0_3_1 import _make_vault  # 复用 fixture，避免重复样板

runner = CliRunner()


# ---------------------------------------------------------------------------
# 1. recall --weight-* override
# ---------------------------------------------------------------------------


def _build_index(cfg_path: Path) -> None:
    res = runner.invoke(app, ["index", "rebuild", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output


def test_recall_weight_override_applies_and_does_not_modify_yaml(tmp_path: Path):
    cfg_path = _make_vault(
        tmp_path,
        search_block={"hybrid": {"weights": {"bm25": 0.5, "value_score": 0.3, "review_due": 0.2}}},
    )
    _build_index(cfg_path)
    yaml_before = cfg_path.read_text(encoding="utf-8")
    res = runner.invoke(
        app,
        [
            "recall", "--query", "checkpoint",
            "--ranking", "hybrid",
            "--weight-bm25", "1.0",
            "--weight-value-score", "0.0",
            "--weight-review-due", "0.0",
            "--config", str(cfg_path),
        ],
    )
    assert res.exit_code == 0, res.output
    assert "weights=cli_override" in res.output
    # yaml 不能被修改
    assert cfg_path.read_text(encoding="utf-8") == yaml_before


def test_recall_weight_override_negative_rejected(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    _build_index(cfg_path)
    res = runner.invoke(
        app,
        ["recall", "--query", "checkpoint", "--ranking", "hybrid",
         "--weight-bm25", "-0.1", "--config", str(cfg_path)],
    )
    assert res.exit_code != 0


def test_recall_weight_override_all_zero_rejected(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    _build_index(cfg_path)
    res = runner.invoke(
        app,
        ["recall", "--query", "checkpoint", "--ranking", "hybrid",
         "--weight-bm25", "0", "--weight-value-score", "0",
         "--weight-review-due", "0", "--config", str(cfg_path)],
    )
    assert res.exit_code != 0


# ---------------------------------------------------------------------------
# 2. recall --explain JSON 增强字段
# ---------------------------------------------------------------------------


def test_recall_explain_json_has_v032_fields(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    _build_index(cfg_path)
    res = runner.invoke(
        app,
        ["recall", "--query", "checkpoint", "--ranking", "hybrid",
         "--explain", "--format", "json", "--config", str(cfg_path)],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["version"] == 1
    assert data["weight_source"] in ("config", "cli_override")
    assert "active_weights" in data
    assert "index_stale" in data
    assert data["items"], "应至少召回一条"
    item = data["items"][0]
    assert "why_this_matched" in item
    assert "matched_fields" in item or "matched_terms" in item
    assert item.get("ranking_mode") == "hybrid"


def test_recall_explain_json_no_query_leak_in_telemetry(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    _build_index(cfg_path)
    res = runner.invoke(
        app,
        ["recall", "--query", "checkpoint", "--ranking", "hybrid",
         "--weight-bm25", "1.0", "--explain", "--format", "json",
         "--config", str(cfg_path)],
    )
    assert res.exit_code == 0
    runs = list((tmp_path / ".mindforge" / "runs").glob("*.jsonl"))
    assert runs
    for line in runs[0].read_text(encoding="utf-8").splitlines():
        evt = json.loads(line)
        # query 原文不能写到 telemetry
        assert "checkpoint" not in json.dumps(evt, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 3. index info / status --json 稳定 schema
# ---------------------------------------------------------------------------


def test_index_info_json_schema_when_present(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    _build_index(cfg_path)
    res = runner.invoke(app, ["index", "info", "--json", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    for key in (
        "version", "index_path", "exists", "stale", "card_count",
        "last_built_at", "config_hash", "current_config_hash",
        "field_weights", "ranking_defaults", "hybrid_weights", "tokenizer",
    ):
        assert key in data, f"missing {key}"
    assert data["version"] == 1
    assert data["exists"] is True


def test_index_status_json_when_missing(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, ["index", "status", "--json", "--config", str(cfg_path)])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["exists"] is False
    assert data["stale"] is True
    assert data["last_built_at"] is None


# ---------------------------------------------------------------------------
# 4. doctor 新 hint
# ---------------------------------------------------------------------------


def test_doctor_hints_no_approved_when_only_drafts(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    # 把所有卡片改成 ai_draft，模拟"全是草稿"
    cards_dir = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"]) / "20-Knowledge-Cards"
    for p in cards_dir.glob("*.md"):
        p.write_text(p.read_text().replace("human_approved", "ai_draft"), encoding="utf-8")
    res = runner.invoke(app, ["doctor", "--config", str(cfg_path)])
    assert res.exit_code in (0, 1)  # doctor 可能基于 hint 返回 1
    assert "include-drafts" in res.output or "ai_draft" in res.output
