"""v0.4.0 — review scheduling MVP（schedule / backlog / stats）+ mark dry-run/note。

设计契约（务必通过测试守住）：
- 全程**纯本地**：不调 LLM、不读 .env、不发 HTTP、不修改卡片（schedule/backlog/stats）；
- ``review mark --dry-run`` **绝不**写文件；
- ``review mark --note`` 只能写单行 ≤200 字符的 frontmatter 字段，
  **绝不**写入 body / Source Excerpt / Human Note 区；
- JSON schema 稳定，version=1。
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


def _patch_card(vault_root: Path, name: str, **fm_updates) -> Path:
    p = vault_root / "20-Knowledge-Cards" / f"{name}.md"
    raw = p.read_text(encoding="utf-8")
    assert raw.startswith("---\n")
    end = raw.find("\n---\n", 4)
    fm = yaml.safe_load(raw[4:end])
    fm.update(fm_updates)
    new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
    p.write_text(f"---\n{new_fm}---\n{raw[end+5:]}", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. review schedule
# ---------------------------------------------------------------------------


def test_schedule_groups_by_day_markdown(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    now = datetime.now(timezone.utc).astimezone()
    _patch_card(vault, "checkpoint-low-value", review_after=(now + timedelta(days=2)).isoformat(timespec="seconds"))
    _patch_card(vault, "harness-other", review_after=(now + timedelta(days=4)).isoformat(timespec="seconds"))
    res = runner.invoke(app, ["review", "schedule", "--days", "7", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    assert "Review Schedule" in res.output
    assert "checkpoint" in res.output


def test_schedule_overdue_goes_to_today(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    # checkpoint-high-value 已设定 review_after=2000-01-01 → overdue
    res = runner.invoke(app, ["review", "schedule", "--days", "7",
                              "--format", "json", "--config", str(cfg_path)])
    assert res.exit_code == 0
    data = json.loads(res.output)
    today = datetime.now().astimezone().date().isoformat()
    days = {d["date"] for d in data["days"]}
    assert today in days


def test_schedule_excludes_ai_draft(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    _patch_card(vault, "checkpoint-low-value", status="ai_draft",
                review_after=datetime.now().astimezone().isoformat(timespec="seconds"))
    res = runner.invoke(app, ["review", "schedule", "--format", "json", "--config", str(cfg_path)])
    data = json.loads(res.output)
    titles = {it["title"] for d in data["days"] for it in d["items"]}
    assert "checkpoint 低价值卡" not in titles


def test_schedule_does_not_modify_cards(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    cards = list((vault / "20-Knowledge-Cards").glob("*.md"))
    before = {p: p.read_bytes() for p in cards}
    runner.invoke(app, ["review", "schedule", "--config", str(cfg_path)])
    for p, b in before.items():
        assert p.read_bytes() == b


def test_schedule_include_missing_review_after(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    # 清掉所有 review_after
    for p in (vault / "20-Knowledge-Cards").glob("*.md"):
        raw = p.read_text(encoding="utf-8")
        end = raw.find("\n---\n", 4)
        fm = yaml.safe_load(raw[4:end])
        fm.pop("review_after", None)
        new = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
        p.write_text(f"---\n{new}---\n{raw[end+5:]}", encoding="utf-8")
    res1 = runner.invoke(app, ["review", "schedule", "--format", "json", "--config", str(cfg_path)])
    data1 = json.loads(res1.output)
    assert data1["total"] == 0
    res2 = runner.invoke(app, ["review", "schedule", "--include-missing-review-after",
                               "--format", "json", "--config", str(cfg_path)])
    data2 = json.loads(res2.output)
    assert data2["total"] >= 1


# ---------------------------------------------------------------------------
# 2. review backlog
# ---------------------------------------------------------------------------


def test_backlog_has_four_buckets_json(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, ["review", "backlog", "--format", "json", "--config", str(cfg_path)])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert set(data["buckets"].keys()) == {"overdue", "today", "upcoming", "missing"}


def test_backlog_overdue_includes_known_card(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, ["review", "backlog", "--format", "json", "--config", str(cfg_path)])
    data = json.loads(res.output)
    overdue_titles = {it["title"] for it in data["buckets"]["overdue"]["items"]}
    assert any("高价值" in t for t in overdue_titles)


# ---------------------------------------------------------------------------
# 3. review stats
# ---------------------------------------------------------------------------


def test_stats_json_schema(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    res = runner.invoke(app, ["review", "stats", "--json", "--config", str(cfg_path)])
    assert res.exit_code == 0
    data = json.loads(res.output)
    for k in ("version", "total_human_approved", "due_today", "overdue",
              "upcoming_7_days", "missing_review_after", "reviewed_count",
              "average_review_count", "result_breakdown"):
        assert k in data
    assert set(data["result_breakdown"].keys()) == {"remembered", "partial", "forgotten"}


# ---------------------------------------------------------------------------
# 4. review mark --dry-run / --note
# ---------------------------------------------------------------------------


def test_mark_dry_run_does_not_modify(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    card = vault / "20-Knowledge-Cards" / "checkpoint-high-value.md"
    before = card.read_bytes()
    res = runner.invoke(app, [
        "review", "mark", "--card", str(card), "--result", "remembered",
        "--dry-run", "--config", str(cfg_path),
    ])
    assert res.exit_code == 0, res.output
    assert "DRY-RUN" in res.output
    assert card.read_bytes() == before


def test_mark_note_writes_single_line_field(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    card = vault / "20-Knowledge-Cards" / "checkpoint-high-value.md"
    res = runner.invoke(app, [
        "review", "mark", "--card", str(card), "--result", "partial",
        "--note", "复习时卡在 checkpoint 与 replay 的边界",
        "--config", str(cfg_path),
    ])
    assert res.exit_code == 0, res.output
    raw = card.read_text(encoding="utf-8")
    end = raw.find("\n---\n", 4)
    fm = yaml.safe_load(raw[4:end])
    assert fm["last_review_note"] == "复习时卡在 checkpoint 与 replay 的边界"
    body = raw[end + 5:]
    # note 绝不能写入 body
    assert "复习时卡在" not in body


def test_mark_note_multiline_rejected(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    card = vault / "20-Knowledge-Cards" / "checkpoint-high-value.md"
    res = runner.invoke(app, [
        "review", "mark", "--card", str(card), "--result", "partial",
        "--note", "line1\nline2", "--config", str(cfg_path),
    ])
    assert res.exit_code != 0


def test_mark_note_too_long_rejected(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    vault = Path(yaml.safe_load(cfg_path.read_text())["vault"]["root"])
    card = vault / "20-Knowledge-Cards" / "checkpoint-high-value.md"
    res = runner.invoke(app, [
        "review", "mark", "--card", str(card), "--result", "partial",
        "--note", "x" * 201, "--config", str(cfg_path),
    ])
    assert res.exit_code != 0


# ---------------------------------------------------------------------------
# 5. telemetry 仍不泄漏内容
# ---------------------------------------------------------------------------


def test_review_commands_telemetry_no_leak(tmp_path: Path):
    cfg_path = _make_vault(tmp_path)
    runner.invoke(app, ["review", "schedule", "--format", "json", "--config", str(cfg_path)])
    runner.invoke(app, ["review", "backlog", "--format", "json", "--config", str(cfg_path)])
    runner.invoke(app, ["review", "stats", "--json", "--config", str(cfg_path)])
    runs_dir = tmp_path / ".mindforge" / "runs"
    for f in runs_dir.glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            evt = json.loads(line)
            blob = json.dumps(evt, ensure_ascii=False)
            # 卡片标题 / body 不能出现在 telemetry
            assert "高价值" not in blob
            assert "AI Summary" not in blob
