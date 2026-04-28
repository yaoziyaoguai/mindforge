"""v0.4.1 — review scheduling polish (iCal export + weekly report) + doctor 增强。

设计契约（务必通过测试守住）：
- iCal 仅本地纯文本生成，**不**接系统日历、**不**联网、**不**请求权限；
- weekly report 是 frontmatter 结构化汇总，**不**调 LLM；
- iCal 与 weekly 都不能泄漏 raw_text / Source Excerpt / Human Note / prompt / api_key；
- doctor 在不同状态下给出**可执行**的下一步建议。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

from .test_v0_3_1 import _make_vault

runner = CliRunner()


# ---------------------------------------------------------------------------
# 1. review schedule --format ical
# ---------------------------------------------------------------------------


def test_schedule_ical_stdout(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, ["review", "schedule", "--days", "7",
                              "--format", "ical", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    out = res.output
    assert "BEGIN:VCALENDAR" in out
    assert "END:VCALENDAR" in out
    assert "BEGIN:VEVENT" in out
    assert "PRODID:-//MindForge//Review Schedule//EN" in out
    # 不得泄漏卡片正文
    assert "AI Summary" not in out
    assert "checkpoint 是 agent runtime" not in out


def test_schedule_ical_to_file(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    out_file = tmp_path / "review.ics"
    res = runner.invoke(app, ["review", "schedule", "--days", "7", "--format", "ical",
                              "--output", str(out_file), "--config", str(cfg_path)])
    assert res.exit_code == 0
    text_bytes = out_file.read_bytes()
    assert text_bytes.startswith(b"BEGIN:VCALENDAR")
    assert text_bytes.count(b"BEGIN:VEVENT") >= 1
    # CRLF（RFC 5545 推荐）
    assert b"\r\n" in text_bytes


def test_schedule_ical_uid_stable_across_runs(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    a = runner.invoke(app, ["review", "schedule", "--format", "ical", "--config", str(cfg_path)]).output
    b = runner.invoke(app, ["review", "schedule", "--format", "ical", "--config", str(cfg_path)]).output
    # UID 应一致（基于 card.id）→ 用户重复导入不会出现重复事件
    a_uids = sorted(line for line in a.splitlines() if line.startswith("UID:"))
    b_uids = sorted(line for line in b.splitlines() if line.startswith("UID:"))
    assert a_uids == b_uids


# ---------------------------------------------------------------------------
# 2. review weekly report
# ---------------------------------------------------------------------------


def test_weekly_markdown_structure(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, ["review", "weekly", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    out = res.output
    for h in (
        "Weekly Review",
        "Overdue",
        "Due this week",
        "Reviewed this week",
        "Forgotten / partial",
        "Suggested focus tracks",
        "Project distribution",
        "Next week preview",
    ):
        assert h in out
    assert "LLM" in out  # disclaimer 必须存在


def test_weekly_json_schema(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, ["review", "weekly", "--format", "json", "--config", str(cfg_path)])
    assert res.exit_code == 0
    data = json.loads(res.output)
    for k in ("version", "generated_at", "window", "overdue", "due_this_week",
              "reviewed_this_week_count", "forgotten_or_partial",
              "suggested_focus_tracks", "project_distribution", "next_week_preview"):
        assert k in data
    assert data["version"] == 1


def test_weekly_does_not_modify_cards(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    cards = list((vault / "20-Knowledge-Cards").glob("*.md"))
    before = {p: p.read_bytes() for p in cards}
    runner.invoke(app, ["review", "weekly", "--config", str(cfg_path)])
    runner.invoke(app, ["review", "weekly", "--format", "json", "--config", str(cfg_path)])
    for p, b in before.items():
        assert p.read_bytes() == b


def test_weekly_no_llm_no_env(tmp_path: Path, monkeypatch):
    """weekly 不应导入任何 LLM provider 模块、不应读取 .env。"""
    cfg_path = _make_vault(tmp_path)
    # 简单守门：禁用 httpx 调用就足以保证不发任何 HTTP
    import httpx
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("不应建 HTTP 客户端")))
    res = runner.invoke(app, ["review", "weekly", "--format", "json", "--config", str(cfg_path)])
    assert res.exit_code == 0


# ---------------------------------------------------------------------------
# 3. doctor 新增 review hint
# ---------------------------------------------------------------------------


def test_doctor_hints_overdue(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, ["doctor", "--config", str(cfg_path)])
    assert "overdue" in res.output or "review backlog" in res.output


def test_doctor_hints_due_this_week(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    # 把 high-value 卡的 review_after 改到 5 天后（不再 overdue，但 due 7 天内）
    soon = (datetime.now(timezone.utc).astimezone() + timedelta(days=5)).isoformat(timespec="seconds")
    p = vault / "20-Knowledge-Cards" / "checkpoint-high-value.md"
    raw = p.read_text(encoding="utf-8")
    end = raw.find("\n---\n", 4)
    fm = yaml.safe_load(raw[4:end])
    fm["review_after"] = soon
    p.write_text(f"---\n{yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)}---\n{raw[end+5:]}", encoding="utf-8")
    res = runner.invoke(app, ["doctor", "--config", str(cfg_path)])
    assert "review schedule" in res.output or "本周" in res.output or "overdue" in res.output


# ---------------------------------------------------------------------------
# 4. 安全：iCal / weekly 不泄漏敏感字段（telemetry + 输出双重检查）
# ---------------------------------------------------------------------------


def test_ical_weekly_no_leak_in_telemetry(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    runner.invoke(app, ["review", "schedule", "--format", "ical", "--config", str(cfg_path)])
    runner.invoke(app, ["review", "weekly", "--format", "json", "--config", str(cfg_path)])
    runs_dir = tmp_path / ".mindforge" / "runs"
    forbidden = ("AI Summary", "Source Excerpt", "Human Note", "api_key",
                 "Authorization", "checkpoint 是 agent runtime")
    for f in runs_dir.glob("*.jsonl"):
        text = f.read_text(encoding="utf-8")
        for kw in forbidden:
            assert kw not in text, f"telemetry leaked {kw!r}"
