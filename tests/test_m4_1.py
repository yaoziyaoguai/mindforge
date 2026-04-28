"""M4.1 — recall fuzzy/sort/format & project context output/include flags 测试。

设计与 v0.2.0 一致：
- 不调用任何 LLM；
- 不读 .env；
- 不修改源文件；
- 复用 fake LLM fixture 构造 vault；
- 重点验证：M4.1 的"使用效率增强"仍处于安全召回层，不引入新泄漏路径。
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


def _setup_two_cards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, list[Path]]:
    """构造一个含 2 张 human_approved 卡的 vault，便于排序/过滤测试。

    用 fake LLM fixture 跑出第 1 张真卡，第 2 张直接复制再改字段（避免
    fake distiller 输出同名而触发 .conflict.md）。
    """
    for k in list(os.environ.keys()):
        if k.startswith("MINDFORGE_") or k.endswith("_API_KEY"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)

    cfg_path, vault, _src = _build_vault_with_fake_llm(tmp_path)
    assert runner.invoke(app, ["scan", "--config", str(cfg_path)]).exit_code == 0
    assert runner.invoke(app, _common_process_args(cfg_path)).exit_code == 0

    cards_dir = vault / "20-Knowledge-Cards" / "agent-runtime"
    first = next(cards_dir.glob("*.md"))
    # 复制一份作为第 2 张；不在 inbox 里再 process（避免 fake LLM 同名冲突）
    second = first.with_name("20260428--card-two.md")
    second.write_text(first.read_text("utf-8"), encoding="utf-8")

    cards = sorted([first, second])

    for i, card in enumerate(cards):
        runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path)])
        text = card.read_text("utf-8")
        fm_text, body = text.split("---\n", 2)[1], text.split("---\n", 2)[2]
        fm = yaml.safe_load(fm_text)
        fm["id"] = f"card-{chr(ord('a') + i)}"
        fm["title"] = (
            "Card A — Agent Runtime topic"
            if i == 0
            else "Card B — Harness trace topic"
        )
        fm["track"] = "Agent Runtime" if i == 0 else "Harness Engineering"
        fm["projects"] = ["my-first-agent"] if i == 0 else ["harness"]
        # 防止源 fixture 的 source_title 干扰 keyword 测试
        if i == 1:
            fm["source_title"] = "Harness trace export"
        fm["tags"] = ["agent", "runtime"] if i == 0 else ["harness", "trace"]
        fm["value_score"] = 9 if i == 0 else 5
        if i == 0:
            past = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(timespec="seconds")
            fm["review_after"] = past
            fm["reviewed_at"] = past
        card.write_text(
            "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
        )

    return cfg_path, vault, cards


# ===========================================================================
# (1) recall — keyword 多 token AND / ci-contains
# ===========================================================================


def test_recall_keyword_multi_token_AND(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    # 两个 token 都命中 card 0（"agent" + "runtime"）
    r = runner.invoke(
        app, ["recall", "--config", str(cfg_path), "--keyword", "Agent  Runtime",
              "--format", "json"]
    )
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["count"] == 1
    assert "Agent Runtime" in data["items"][0]["title"]


def test_recall_keyword_case_insensitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(
        app, ["recall", "--config", str(cfg_path), "--keyword", "HARNESS",
              "--format", "json"]
    )
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert data["count"] == 1
    assert data["items"][0]["track"] == "Harness Engineering"


def test_recall_keyword_does_not_match_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """keyword 仅搜白名单字段；body 中独有的 token 不应命中。"""
    cfg_path, _vault, cards = _setup_two_cards(tmp_path, monkeypatch)
    cards[0].write_text(cards[0].read_text() + "\nUNIQUE_BODY_TOKEN_M41\n")
    r = runner.invoke(
        app, ["recall", "--config", str(cfg_path), "--keyword", "UNIQUE_BODY_TOKEN_M41",
              "--format", "json"]
    )
    data = json.loads(r.output)
    assert data["count"] == 0


# ===========================================================================
# (2) recall — sort
# ===========================================================================


def test_recall_sort_by_review_after_puts_due_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(
        app, ["recall", "--config", str(cfg_path), "--sort", "review_after",
              "--format", "json"]
    )
    data = json.loads(r.output)
    assert data["count"] == 2
    # 第一张有 review_after，应排前面
    assert data["items"][0]["review_after"] is not None
    assert data["items"][1]["review_after"] is None


def test_recall_sort_by_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(
        app, ["recall", "--config", str(cfg_path), "--sort", "title", "--format", "json"]
    )
    data = json.loads(r.output)
    titles = [it["title"] for it in data["items"]]
    assert titles == sorted(titles, key=str.lower)


def test_recall_sort_by_value_score_desc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(
        app, ["recall", "--config", str(cfg_path), "--sort", "value_score",
              "--format", "json"]
    )
    data = json.loads(r.output)
    scores = [it["value_score"] for it in data["items"]]
    assert scores == sorted(scores, reverse=True)


def test_recall_sort_invalid_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(app, ["recall", "--config", str(cfg_path), "--sort", "bogus"])
    assert r.exit_code == 2


# ===========================================================================
# (3) recall — format
# ===========================================================================


def test_recall_format_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(
        app, ["recall", "--config", str(cfg_path), "--format", "markdown"]
    )
    assert r.exit_code == 0
    assert r.output.startswith("# Recall ·")
    assert "**[" in r.output  # markdown bullet 强调
    assert "`status=human_approved`" in r.output


def test_recall_format_table_smoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(
        app, ["recall", "--config", str(cfg_path), "--format", "table"]
    )
    assert r.exit_code == 0
    assert "Recall" in r.output


def test_recall_format_compact_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(app, ["recall", "--config", str(cfg_path)])
    assert r.exit_code == 0
    # 默认 compact：纯文本 - prefix
    assert "Recall" in r.output


# ===========================================================================
# (4) recall — 安全：默认仅 human_approved；不修改文件；不发 HTTP
# ===========================================================================


def test_recall_default_excludes_ai_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, cards = _setup_two_cards(tmp_path, monkeypatch)
    # 把 card 1 改回 ai_draft
    text = cards[1].read_text("utf-8")
    fm_text, body = text.split("---\n", 2)[1], text.split("---\n", 2)[2]
    fm = yaml.safe_load(fm_text)
    fm["status"] = "ai_draft"
    cards[1].write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
    )

    r = runner.invoke(app, ["recall", "--config", str(cfg_path), "--format", "json"])
    data = json.loads(r.output)
    assert all(it["status"] == "human_approved" for it in data["items"])

    r2 = runner.invoke(
        app, ["recall", "--config", str(cfg_path), "--include-drafts", "--format", "json"]
    )
    data2 = json.loads(r2.output)
    assert any(it["status"] == "ai_draft" for it in data2["items"])


def test_recall_does_not_make_http_calls_m41(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    import httpx

    def boom(*a, **kw):
        raise AssertionError("recall must not perform HTTP")

    monkeypatch.setattr(httpx.Client, "post", boom, raising=True)
    monkeypatch.setattr(httpx.Client, "send", boom, raising=True)
    for fmt in ("compact", "markdown", "table", "json"):
        r = runner.invoke(app, ["recall", "--config", str(cfg_path), "--format", fmt])
        assert r.exit_code == 0, fmt


# ===========================================================================
# (5) project context — --output / --limit / include flags
# ===========================================================================


def test_project_context_writes_output_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    out_path = tmp_path / "out" / "ctx.md"
    out_path.parent.mkdir()
    r = runner.invoke(
        app,
        ["project", "context", "my-first-agent", "--config", str(cfg_path),
         "--output", str(out_path)],
    )
    assert r.exit_code == 0, r.output
    assert out_path.exists()
    content = out_path.read_text("utf-8")
    assert "# Project Context · my-first-agent" in content
    # stdout 不应再 dump 内容
    assert "Knowledge Cards" not in r.output


def test_project_context_output_to_missing_parent_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    out_path = tmp_path / "no_such_dir" / "ctx.md"
    r = runner.invoke(
        app,
        ["project", "context", "my-first-agent", "--config", str(cfg_path),
         "--output", str(out_path)],
    )
    assert r.exit_code == 2


def test_project_context_limit_truncates_cards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r1 = runner.invoke(
        app, ["project", "context", "my-first-agent", "--config", str(cfg_path),
              "--format", "json"]
    )
    data1 = json.loads(r1.output)
    assert data1["count"] == 1  # 只有 card 0 在 my-first-agent

    # 加 harness 这个 project（card 1 含），limit=1 截断为 1
    r2 = runner.invoke(
        app, ["project", "context", "harness", "--config", str(cfg_path),
              "--limit", "1", "--format", "json"]
    )
    data2 = json.loads(r2.output)
    assert data2["count"] == 1


def test_project_context_no_actions_omits_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r1 = runner.invoke(
        app, ["project", "context", "my-first-agent", "--config", str(cfg_path)]
    )
    assert "## Action Items" in r1.output

    r2 = runner.invoke(
        app, ["project", "context", "my-first-agent", "--config", str(cfg_path),
              "--no-actions"]
    )
    assert "## Action Items" not in r2.output


def test_project_context_no_review_due_omits_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(
        app, ["project", "context", "my-first-agent", "--config", str(cfg_path),
              "--no-review-due"]
    )
    assert "## Review Due" not in r.output


def test_project_context_no_next_step_prompt_omits_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _cards = _setup_two_cards(tmp_path, monkeypatch)
    r = runner.invoke(
        app, ["project", "context", "my-first-agent", "--config", str(cfg_path),
              "--no-next-step-prompt"]
    )
    assert "Recommended Next-step Prompt" not in r.output


def test_project_context_does_not_leak_inference_or_human_note_m41(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M4.1 回归：新 include flags 与 output 写文件路径都不得泄漏 AI inference。"""
    cfg_path, _vault, cards = _setup_two_cards(tmp_path, monkeypatch)
    text = cards[0].read_text("utf-8")
    fm_text, body = text.split("---\n", 2)[1], text.split("---\n", 2)[2]
    body += (
        "\n## AI Inference (low confidence)\nLEAK_INFERENCE_TOKEN_M41\n"
        "\n## Human Note\nLEAK_HUMAN_NOTE_M41\n"
    )
    cards[0].write_text("---\n" + fm_text + "---\n" + body)

    out_path = tmp_path / "ctx.md"
    r = runner.invoke(
        app,
        ["project", "context", "my-first-agent", "--config", str(cfg_path),
         "--output", str(out_path)],
    )
    assert r.exit_code == 0, r.output
    file_content = out_path.read_text("utf-8")
    assert "LEAK_INFERENCE_TOKEN_M41" not in file_content
    assert "LEAK_HUMAN_NOTE_M41" not in file_content
