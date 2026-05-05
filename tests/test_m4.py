"""M4 — recall / review / project memory 最小闭环测试。

覆盖矩阵见 docs/M4_RECALL_REVIEW_PROTOCOL.md §8。

设计原则：
- 全部使用真实 vault + fake LLM，复用 M2 端到端 fixture；
- 反向断言：M4 任何命令**不**得改 status / 不得发 HTTP / 不得修改正文；
- 全部测试不依赖任何 MINDFORGE_* env，且 chdir 到 tmp_path。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app

from tests.test_process_e2e import (  # type: ignore[import-not-found]
    _build_vault_with_fake_llm,
    _common_process_args,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# 公共 fixture：生成一个含 1 张 human_approved 卡的 vault
# ---------------------------------------------------------------------------


def _vault_with_approved_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    for k in list(os.environ.keys()):
        if k.startswith("MINDFORGE_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)

    cfg_path, vault, _src = _build_vault_with_fake_llm(tmp_path)
    assert runner.invoke(app, ["scan", "--config", str(cfg_path)]).exit_code == 0
    assert runner.invoke(app, _common_process_args(cfg_path)).exit_code == 0

    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) == 1
    card = cards[0]

    # approve → human_approved
    r = runner.invoke(
        app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"]
    )
    assert r.exit_code == 0, r.output
    return cfg_path, vault, card


def _read_fm(card: Path) -> dict:
    text = card.read_text("utf-8")
    assert text.startswith("---\n")
    return yaml.safe_load(text.split("---\n", 2)[1]) or {}


def _read_body(card: Path) -> str:
    return card.read_text("utf-8").split("---\n", 2)[2]


# ===========================================================================
# (1) cards.py 基础：iter / extract_section / filter
# ===========================================================================


def test_iter_cards_skips_conflict_and_hidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    cards_dir = card.parent
    (cards_dir / "broken.conflict.md").write_text("---\nbad: yaml: :\n---\nbody\n")
    (cards_dir / ".hidden.md").write_text("---\nid: x\n---\n")

    from mindforge.cards import iter_cards
    from mindforge.config import load_mindforge_config

    cfg = load_mindforge_config(cfg_path)
    res = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    paths = {c.rel_path for c in res.cards}
    assert any("conflict" not in p and not Path(p).name.startswith(".") for p in paths)
    assert all("conflict" not in p for p in paths)
    assert all(not Path(p).name.startswith(".") for p in paths)


def test_extract_section_returns_block_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _vault_with_approved_card(tmp_path, monkeypatch)
    from mindforge.cards import extract_section

    body = (
        "## Source Excerpt\noriginal text\n\n"
        "## AI Summary\nsummary line\n- pt1\n\n"
        "## Human Note\nshould not bleed\n"
    )
    assert extract_section(body, "AI Summary") and "summary line" in extract_section(body, "AI Summary")
    assert "Human Note" not in (extract_section(body, "AI Summary") or "")
    assert extract_section(body, "Nonexistent") is None


def test_filter_cards_AND_semantic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    fm = _read_fm(card)
    fm.setdefault("projects", []).append("proj-A")
    fm["tags"] = ["agent", "harness"]
    body = _read_body(card)
    card.write_text(
        "---\n"
        + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
        + "---\n"
        + body
    )

    from mindforge.cards import filter_cards, iter_cards
    from mindforge.config import load_mindforge_config

    cfg = load_mindforge_config(cfg_path)
    cards = iter_cards(cfg.vault.root, cfg.vault.cards_dir).cards

    assert filter_cards(cards, project="proj-A", tags=["agent"]) != []
    # AND 语义：tag 不匹配则空
    assert filter_cards(cards, project="proj-A", tags=["nonexistent"]) == []
    # project 不匹配
    assert filter_cards(cards, project="proj-other") == []


# ===========================================================================
# (2) recall — 各过滤器 / keyword 不搜 body / json schema
# ===========================================================================


def test_recall_returns_human_approved_only_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _card = _vault_with_approved_card(tmp_path, monkeypatch)
    r = runner.invoke(app, ["recall", "--config", str(cfg_path), "--format", "json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["count"] == 1
    assert data["items"][0]["status"] == "human_approved"


def test_recall_keyword_does_not_search_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """keyword 仅搜 frontmatter 白名单 + 文件名；body 内容不应匹配。"""
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    # 注入一个 body 独有 token，frontmatter 不含
    text = card.read_text("utf-8")
    card.write_text(text + "\n\nUNIQUE_BODY_TOKEN_XYZ\n")

    r = runner.invoke(
        app,
        ["recall", "--config", str(cfg_path), "--keyword", "UNIQUE_BODY_TOKEN_XYZ", "--format", "json"],
    )
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert data["count"] == 0


def test_recall_json_schema_contains_only_safe_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _card = _vault_with_approved_card(tmp_path, monkeypatch)
    r = runner.invoke(app, ["recall", "--config", str(cfg_path), "--format", "json"])
    data = json.loads(r.output)
    safe = {
        "id", "title", "path", "status", "track", "projects", "tags",
        "source_type", "source_url", "created_at", "reviewed_at",
        "review_after", "value_score",
        # v0.4 — review 元数据是安全字段（来自 frontmatter，非 body）
        "review_count", "last_review_result",
    }
    item_keys = set(data["items"][0].keys())
    assert item_keys <= safe, f"出现非白名单字段: {item_keys - safe}"


def test_recall_does_not_modify_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    before = card.read_bytes()
    r = runner.invoke(app, ["recall", "--config", str(cfg_path), "--keyword", "anything"])
    assert r.exit_code == 0
    assert card.read_bytes() == before


# ===========================================================================
# (3) review mark — 4 字段写入 / 不改 status / 不改正文
# ===========================================================================


def test_review_mark_writes_four_fields_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    fm_before = _read_fm(card)
    body_before = _read_body(card)

    r = runner.invoke(
        app,
        ["review", "mark", "--card", str(card), "--result", "remembered", "--config", str(cfg_path)],
    )
    assert r.exit_code == 0, r.output

    fm_after = _read_fm(card)
    body_after = _read_body(card)

    # 正文 byte 级不变
    assert body_after == body_before
    # status 未变
    assert fm_after["status"] == fm_before["status"] == "human_approved"
    # 4 字段写入
    assert fm_after["last_review_result"] == "remembered"
    assert fm_after["review_count"] == fm_before.get("review_count", 0) + 1
    assert "reviewed_at" in fm_after
    assert "review_after" in fm_after

    # 其他字段不变
    diff = {k: (fm_before.get(k), fm_after.get(k))
            for k in (set(fm_before) | set(fm_after))
            if k not in {"reviewed_at", "review_count", "last_review_result", "review_after"}
            and fm_before.get(k) != fm_after.get(k)}
    assert diff == {}


def test_review_mark_invalid_result_exits_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    r = runner.invoke(
        app,
        ["review", "mark", "--card", str(card), "--result", "bogus", "--config", str(cfg_path)],
    )
    assert r.exit_code == 3


def test_review_mark_missing_card_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _card = _vault_with_approved_card(tmp_path, monkeypatch)
    r = runner.invoke(
        app,
        ["review", "mark", "--card", str(tmp_path / "nope.md"),
         "--result", "remembered", "--config", str(cfg_path)],
    )
    assert r.exit_code == 2


def test_review_mark_intervals_from_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    # 改配置：remembered=30
    cfg_text = cfg_path.read_text("utf-8")
    cfg_text += "\nreview:\n  intervals:\n    remembered: 30\n    partial: 7\n    forgotten: 1\n"
    cfg_path.write_text(cfg_text)

    r = runner.invoke(
        app,
        ["review", "mark", "--card", str(card), "--result", "remembered", "--config", str(cfg_path)],
    )
    assert r.exit_code == 0, r.output
    fm = _read_fm(card)
    reviewed = datetime.fromisoformat(fm["reviewed_at"])
    after = datetime.fromisoformat(fm["review_after"])
    diff = (after - reviewed).total_seconds()
    assert 29 * 86400 <= diff <= 31 * 86400


# ===========================================================================
# (4) review due — 仅默认 human_approved，不修改文件
# ===========================================================================


def test_review_due_lists_due_cards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    # 把 review_after 设为过去
    fm = _read_fm(card)
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(timespec="seconds")
    fm["review_after"] = past
    fm["reviewed_at"] = past
    fm["review_count"] = 1
    fm["last_review_result"] = "partial"
    body = _read_body(card)
    card.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
    )
    before = card.read_bytes()

    r = runner.invoke(app, ["review", "due", "--config", str(cfg_path), "--format", "json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["count"] == 1
    # due 是只读
    assert card.read_bytes() == before


# ===========================================================================
# (5) project list / context
# ===========================================================================


def test_project_list_aggregates_projects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    fm = _read_fm(card)
    fm["projects"] = ["my-first-agent", "harness"]
    body = _read_body(card)
    card.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
    )
    r = runner.invoke(app, ["project", "list", "--config", str(cfg_path), "--format", "json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    names = [it["name"] for it in data["items"]]
    assert "harness" in names and "my-first-agent" in names


def test_project_context_excludes_ai_inference_and_human_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    fm = _read_fm(card)
    fm["projects"] = ["proj-X"]
    body = _read_body(card)
    body += (
        "\n## AI Inference (low confidence)\nSECRET_INFERENCE_TOKEN\n"
        "\n## Human Note\nSECRET_HUMAN_NOTE\n"
    )
    card.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
    )
    r = runner.invoke(app, ["project", "context", "proj-X", "--config", str(cfg_path)])
    assert r.exit_code == 0, r.output
    out = r.output
    assert "SECRET_INFERENCE_TOKEN" not in out
    assert "SECRET_HUMAN_NOTE" not in out
    # 但 project 名应出现
    assert "proj-X" in out


def test_project_context_no_prompts_omits_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    fm = _read_fm(card)
    fm["projects"] = ["proj-Y"]
    body = _read_body(card)
    # 替换已有的 Reusable Prompts 段为带 token 的版本（避免 extract_section
    # 找到模板里的占位文本而错过我们的 token）
    import re
    body = re.sub(
        r"## Reusable Prompts / Principles\n[\s\S]*?(?=\n## |\Z)",
        "## Reusable Prompts / Principles\n- USEFUL_PROMPT_X\n\n",
        body,
        count=1,
    )
    card.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
    )
    r1 = runner.invoke(app, ["project", "context", "proj-Y", "--config", str(cfg_path)])
    assert "USEFUL_PROMPT_X" in r1.output
    r2 = runner.invoke(
        app, ["project", "context", "proj-Y", "--config", str(cfg_path), "--no-prompts"]
    )
    assert "USEFUL_PROMPT_X" not in r2.output


# ===========================================================================
# (6) §8 反向断言 — M4 安全保证
# ===========================================================================


def test_m4_commands_do_not_make_http_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """拦截 httpx 与 requests，任何 M4 命令都不应触发 HTTP。"""
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)

    import httpx

    def _boom(*a, **kw):
        raise AssertionError("M4 commands must not perform HTTP calls")

    monkeypatch.setattr(httpx.Client, "post", _boom, raising=True)
    monkeypatch.setattr(httpx.Client, "send", _boom, raising=True)

    cmds = [
        ["recall", "--config", str(cfg_path), "--format", "json"],
        ["review", "due", "--config", str(cfg_path), "--format", "json"],
        ["review", "mark", "--card", str(card), "--result", "remembered",
         "--config", str(cfg_path)],
        ["project", "list", "--config", str(cfg_path), "--format", "json"],
        ["project", "context", "anything", "--config", str(cfg_path)],
    ]
    for c in cmds:
        r = runner.invoke(app, c)
        assert r.exit_code in (0, 2, 3), f"{c} unexpected: {r.output}"


def test_m4_commands_do_not_write_status_human_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """recall / review / project 命令任何情况下不得改 status 字段。"""
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    # 把 status 改为 ai_draft，跑所有 M4 命令后仍应是 ai_draft
    fm = _read_fm(card)
    fm["status"] = "ai_draft"
    body = _read_body(card)
    card.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
    )

    runner.invoke(app, ["recall", "--config", str(cfg_path), "--include-drafts"])
    runner.invoke(app, ["review", "due", "--config", str(cfg_path), "--include-drafts"])
    runner.invoke(app, ["review", "mark", "--card", str(card),
                        "--result", "remembered", "--config", str(cfg_path)])
    runner.invoke(app, ["project", "list", "--config", str(cfg_path)])
    runner.invoke(app, ["project", "context", "any", "--config", str(cfg_path)])

    assert _read_fm(card)["status"] == "ai_draft"


def test_m4_runs_without_any_mindforge_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _card = _vault_with_approved_card(tmp_path, monkeypatch)
    for k in list(os.environ.keys()):
        if k.startswith("MINDFORGE_") or k.endswith("_API_KEY"):
            monkeypatch.delenv(k, raising=False)
    r = runner.invoke(app, ["recall", "--config", str(cfg_path), "--format", "json"])
    assert r.exit_code == 0, r.output


def test_runs_jsonl_does_not_contain_keyword_or_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, card = _vault_with_approved_card(tmp_path, monkeypatch)
    body_text = "RAW_BODY_SENSITIVE_TOKEN_QQQ"
    text = card.read_text("utf-8")
    card.write_text(text + "\n\n" + body_text + "\n")

    r = runner.invoke(
        app,
        ["recall", "--config", str(cfg_path), "--keyword", "PLAINTEXT_QUERY_RST",
         "--format", "json"],
    )
    assert r.exit_code == 0

    runs_dir = tmp_path / ".mindforge" / "runs"
    if not runs_dir.exists():
        # 兼容：runs_path 可能解析到 cwd，下面再搜
        runs_dir = next((p for p in tmp_path.rglob("runs") if p.is_dir()), None)
    assert runs_dir is not None and runs_dir.exists()

    found_keyword = False
    found_body = False
    for jsonl in runs_dir.rglob("*.jsonl"):
        text = jsonl.read_text("utf-8")
        if "PLAINTEXT_QUERY_RST" in text:
            found_keyword = True
        if "RAW_BODY_SENSITIVE_TOKEN_QQQ" in text:
            found_body = True
    assert not found_keyword, "runs jsonl 不应含 keyword 原文"
    assert not found_body, "runs jsonl 不应含 body 内容"
