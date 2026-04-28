"""v0.2.3 — multi-project context / evidence block / telemetry 测试。

延续 v0.2.2 的安全准则：
- 不调用真实 LLM（fake provider）；
- 不读 .env；
- 不修改 Knowledge Cards；
- 不写远程 sink；
- 关键反向断言：所有输出（markdown / json / runs jsonl / telemetry jsonl）都不
  含 sk-... / Bearer ... / 卡片正文 / SECRET。

为什么 multi-project context 仍然不是 RAG：
- 数据源仍然只是 cards frontmatter + project profile frontmatter；
- 没有 embedding、没有相似度计算、没有 LLM；
- "联合"只是按用户给出的 project 列表做集合并 + path 去重。

为什么 evidence block 必须幂等：
- 同样的 cards 输入 + 同一项目，多次运行不能让区块越长越多；
- 替换发生在 START/END marker 之间；marker 之外的人手内容一字不改。

为什么 telemetry 只能记元数据：
- 任何卡片正文 / prompt / completion / api_key / .env 都是潜在敏感数据；
- telemetry 默认本地 + 永不上传，但即便如此也要严格白名单。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.evidence import (
    END_MARKER,
    START_MARKER,
    EvidenceError,
    update_evidence_block,
    write_evidence_update,
)
from mindforge.telemetry import (
    ALLOWED_FIELDS,
    TelemetryConfig,
    measure,
    read_events,
    record_event,
    summarize,
    telemetry_path,
)

from tests.test_process_e2e import (  # type: ignore[import-not-found]
    _build_vault_with_fake_llm,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# 辅助：复用 M5.3 的 fixture 思路，再扩展成多项目
# ---------------------------------------------------------------------------


def _setup_vault_with_two_approved_cards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path, Path]:
    """构造含 2 张 human_approved 卡的 vault（一张归 a，一张归 a+b）。

    为绕开 fake LLM 在同一天生成同名卡片的冲突，本 fixture 直接把卡片
    手写到 ``20-Knowledge-Cards/agent-runtime/``，跳过 scan/process。
    """
    for k in list(os.environ.keys()):
        if k.startswith("MINDFORGE_") or k.endswith("_API_KEY"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)

    cfg_path, vault, _src = _build_vault_with_fake_llm(tmp_path)

    cards_dir = vault / "20-Knowledge-Cards" / "agent-runtime"
    cards_dir.mkdir(parents=True, exist_ok=True)
    card_a = cards_dir / "card-a.md"
    card_b = cards_dir / "card-b.md"
    _write_synthetic_card(card_a, id_="card-a", title="Card A", projects=["a"])
    _write_synthetic_card(
        card_b, id_="card-b", title="Card B (shared)", projects=["a", "b"]
    )
    return cfg_path, vault, card_a, card_b


def _write_synthetic_card(
    p: Path, *, id_: str, title: str, projects: list[str],
) -> None:
    fm = {
        "id": id_,
        "title": title,
        "status": "human_approved",
        "track": "agent-runtime",
        "projects": projects,
        "tags": [],
        "source_type": "manual_note",
        "source_title": title,
        "source_url": f"http://example.com/{id_}",
        "value_score": 7,
        "principles": [f"{id_} 原则: 看 trace 再改"],
        "known_risks": [f"{id_} 风险: 不要捏造日志"],
    }
    body = (
        "## Source Excerpt\n\n摘要片段（合成）\n\n"
        "## AI Summary\n\n这是 {id} 的合成 AI 摘要。\n\n"
        "## Action Items\n\n- 跟进 {id} 的 follow-up\n"
    ).format(id=id_)
    p.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n" + body,
        "utf-8",
    )


def _write_profile(
    vault: Path,
    project_name: str,
    *,
    default_target: str | None = None,
    description: str = "",
    principles: list[str] | None = None,
    known_risks: list[str] | None = None,
    preferred_workflow: list[str] | None = None,
) -> Path:
    pdir = vault / "30-Projects"
    pdir.mkdir(parents=True, exist_ok=True)
    fm: dict = {"project": project_name, "description": description or f"{project_name} desc"}
    if default_target is not None:
        fm["default_target"] = default_target
    fm["principles"] = principles or [f"项目 [{project_name}] 原则 1"]
    fm["known_risks"] = known_risks or [f"项目 [{project_name}] 风险 1"]
    fm["preferred_workflow"] = preferred_workflow or ["先做只读诊断", "再做最小补丁"]
    p = pdir / f"{project_name}.md"
    p.write_text(
        "---\n"
        + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
        + "---\n\n# "
        + project_name
        + "\n\n这里是项目笔记正文，**不应被 mindforge 读取**。SECRET=sk-multi-leak-test\n",
        "utf-8",
    )
    return p


_LEAK_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9]+"),
    re.compile(r"_API_KEY="),
    re.compile(r"Authorization:"),
    re.compile(r'"raw_response"'),
    re.compile(r'"completion"'),
]


# ===========================================================================
# 1. 单 project 行为兼容（v0.2.2 schema 不变）
# ===========================================================================


def test_single_project_context_still_uses_single_renderer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    _write_profile(vault, "a", default_target="claude-code")

    res = runner.invoke(app, ["project", "context", "a", "--config", str(cfg)])
    assert res.exit_code == 0, res.stdout
    out = res.stdout

    # 单项目固定 9 段标题（v0.2.2）
    assert out.startswith("# Project Context · a")
    assert "## Project Profile" in out
    assert "## Project-Level Principles" in out
    assert "## Card-Level Principles (supplementary)" in out
    assert "## Suggested Prompt for claude-code" in out
    # 多项目专属标题不应出现
    assert "## Cross-project Principles" not in out
    assert "Multi-Project Context" not in out


# ===========================================================================
# 2. 多 project：分组 + 去重 + suggested prompt 多项目语
# ===========================================================================


def test_multi_project_context_groups_and_dedups(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    _write_profile(vault, "a", default_target="claude-code")
    _write_profile(vault, "b")

    res = runner.invoke(
        app, ["project", "context", "a", "b", "--config", str(cfg)]
    )
    assert res.exit_code == 0, res.stdout
    out = res.stdout

    # 9 个固定段
    for h in (
        "# Multi-Project Context · a · b",
        "## Source Notice",
        "## Project Profiles",
        "## Cross-project Learning Tracks",
        "## Cross-project Principles",
        "## Cross-project Known Risks",
        "## Project-specific Cards",
        "## Shared Action Items",
        "## Review Due",
        "## Excluded Content (safety guarantee)",
    ):
        assert h in out, f"missing section: {h}"

    # 项目级原则按来源标注
    assert "from project [a]:" in out
    assert "from project [b]:" in out

    # 卡片去重：card-b 同时归 a 与 b，但 a 在前，所以 b 的 cards 列表里不会再出现
    cards_segment = out.split("## Project-specific Cards", 1)[1].split("## Shared Action Items", 1)[0]
    a_idx = cards_segment.index("### a (")
    b_idx = cards_segment.index("### b (")
    a_section = cards_segment[a_idx:b_idx]
    b_section = cards_segment[b_idx:]
    assert "card-a" in a_section
    assert "card-b" in a_section
    assert "card-b" not in b_section, "card-b 应被去重，仅出现在 a 项目下"

    # multi-project suggested prompt
    assert "multi-project context pack" in out
    assert "MindForge 不自动裁决冲突" in out


def test_multi_project_context_target_cli_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    _write_profile(vault, "a", default_target="claude-code")
    _write_profile(vault, "b", default_target="copilot")

    res = runner.invoke(
        app, ["project", "context", "a", "b", "--target", "codex", "--config", str(cfg)]
    )
    assert res.exit_code == 0
    assert "## Suggested Prompt for codex" in res.stdout
    assert "如发现 root cause" in res.stdout


def test_multi_project_context_missing_one_profile_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    _write_profile(vault, "a")  # 故意不写 b

    res = runner.invoke(
        app, ["project", "context", "a", "b", "--config", str(cfg)]
    )
    assert res.exit_code == 0, res.stdout
    out = res.stdout
    # a 找到、b 没找到，但命令仍然成功
    assert "a: project_profile_found=true" in out
    assert "b: project_profile_found=false" in out
    assert "(no profile configured)" in out


def test_multi_project_context_json_v2_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    _write_profile(vault, "a", default_target="claude-code")
    _write_profile(vault, "b")

    res = runner.invoke(
        app, ["project", "context", "a", "b", "--format", "json", "--config", str(cfg)]
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)

    assert payload["version"] == 2
    assert payload["mode"] == "multi_project"
    assert payload["projects"] == ["a", "b"]
    assert payload["project_count"] == 2
    assert payload["target"] == "claude-code"
    assert payload["total_unique_cards"] >= 1
    # 项目 profile 列表
    profs = {p["project"]: p for p in payload["project_profiles"]}
    assert profs["a"]["found"] is True
    assert profs["b"]["found"] is True
    # 跨项目 principles 来源
    sources = {(p["source_kind"], p["source_id"]) for p in payload["cross_project_principles"]}
    assert ("project", "a") in sources
    assert ("project", "b") in sources
    # 项目级 cards 分组
    by_proj = {x["project"]: x for x in payload["project_specific_cards"]}
    a_ids = {it["id"] for it in by_proj["a"]["items"]}
    b_ids = {it["id"] for it in by_proj["b"]["items"]}
    assert "card-a" in a_ids
    assert "card-b" in a_ids  # 去重归到第一个匹配项目
    assert "card-b" not in b_ids


def test_multi_project_context_no_secret_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    _write_profile(vault, "a")
    _write_profile(vault, "b")

    md = runner.invoke(app, ["project", "context", "a", "b", "--config", str(cfg)])
    js = runner.invoke(app, ["project", "context", "a", "b", "--format", "json", "--config", str(cfg)])
    assert md.exit_code == 0 and js.exit_code == 0
    blob = md.stdout + "\n" + js.stdout
    assert "sk-multi-leak-test" not in blob
    for pat in _LEAK_PATTERNS:
        assert not pat.search(blob), f"leak: {pat.pattern}"

    # runs / telemetry 同样不能含 SECRET / 卡片正文
    runs_dir = tmp_path / ".mindforge" / "runs"
    runs_blob = "\n".join(p.read_text("utf-8") for p in runs_dir.glob("*.jsonl"))
    assert "sk-multi-leak-test" not in runs_blob
    tele = (tmp_path / ".mindforge" / "telemetry.jsonl").read_text("utf-8")
    assert "sk-multi-leak-test" not in tele
    # 项目笔记正文 / 卡片正文都不应进 runs / telemetry
    assert "项目 [a] 原则" not in runs_blob
    assert "card-a 原则" not in runs_blob
    assert "项目 [a] 原则" not in tele


def test_multi_project_context_dedup_input_keeps_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """重复传入 a a b 等价于 a b。"""
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    _write_profile(vault, "a")
    _write_profile(vault, "b")

    res = runner.invoke(
        app, ["project", "context", "a", "a", "b", "--config", str(cfg)]
    )
    assert res.exit_code == 0
    assert "Multi-Project Context · a · b" in res.stdout


# ===========================================================================
# 3. update-evidence
# ===========================================================================


def test_update_evidence_dry_run_does_not_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    profile = _write_profile(vault, "a")
    before = profile.read_text("utf-8")

    res = runner.invoke(
        app,
        ["project", "update-evidence", "a", "--dry-run", "--config", str(cfg)],
    )
    assert res.exit_code == 0, res.stdout
    assert "dry-run" in res.stdout
    assert START_MARKER in res.stdout
    assert END_MARKER in res.stdout
    # 文件未变
    assert profile.read_text("utf-8") == before


def test_update_evidence_creates_block_then_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    profile = _write_profile(vault, "a")

    # 第 1 次：追加块
    res1 = runner.invoke(
        app, ["project", "update-evidence", "a", "--config", str(cfg)]
    )
    assert res1.exit_code == 0, res1.stdout
    text1 = profile.read_text("utf-8")
    assert START_MARKER in text1
    assert END_MARKER in text1
    assert "## MindForge Evidence" in text1
    assert text1.count(START_MARKER) == 1
    assert text1.count(END_MARKER) == 1
    # 卡片信息只含元数据
    assert "Card A" in text1
    assert "Card B" in text1
    assert "status: human_approved" in text1
    # 永不出现卡片正文 / SECRET（block 内部检查；profile 正文有 SECRET 是人手内容，不归我们管）
    block1 = text1.split(START_MARKER)[1].split(END_MARKER)[0]
    assert "sk-multi-leak-test" not in block1
    assert "card-a 原则" not in block1, "卡片正文不应进入 evidence block"

    # 第 2 次：内容应等同（除时间戳），且不重复追加
    res2 = runner.invoke(
        app, ["project", "update-evidence", "a", "--config", str(cfg)]
    )
    assert res2.exit_code == 0
    text2 = profile.read_text("utf-8")
    assert text2.count(START_MARKER) == 1
    assert text2.count(END_MARKER) == 1
    # 区块外内容一字不变
    pre1 = text1.split(START_MARKER)[0]
    pre2 = text2.split(START_MARKER)[0]
    assert pre1 == pre2
    post1 = text1.split(END_MARKER)[1]
    post2 = text2.split(END_MARKER)[1]
    assert post1 == post2

    # 第 3 次：与第 2 次 byte-for-byte 一致（同一 fixture，时间戳由 update 函数注入；
    # 这里用 evidence 模块直接调用、传入固定 now，断言完全相同）
    from datetime import datetime, timezone
    from mindforge.cards import filter_cards, iter_cards
    from mindforge.config import load_mindforge_config

    cfg_obj = load_mindforge_config(cfg)
    cards = filter_cards(
        iter_cards(cfg_obj.vault.root, cfg_obj.vault.cards_dir).cards,
        project="a", status="human_approved", include_drafts=False,
    )
    fixed_now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    u1 = update_evidence_block(profile, "a", cards, cards_dir_rel=cfg_obj.vault.cards_dir, now=fixed_now)
    write_evidence_update(u1)
    snapshot = profile.read_text("utf-8")
    u2 = update_evidence_block(profile, "a", cards, cards_dir_rel=cfg_obj.vault.cards_dir, now=fixed_now)
    assert u2.will_change is False
    write_evidence_update(u2)
    assert profile.read_text("utf-8") == snapshot


def test_update_evidence_missing_profile_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, _vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    # 故意不写 30-Projects/a.md
    res = runner.invoke(
        app, ["project", "update-evidence", "a", "--config", str(cfg)]
    )
    assert res.exit_code == 2
    assert "本命令故意不自动创建" in res.stdout


def test_update_evidence_does_not_modify_cards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, card_a, card_b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    _write_profile(vault, "a")
    before_a = card_a.read_text("utf-8")
    before_b = card_b.read_text("utf-8")

    res = runner.invoke(
        app, ["project", "update-evidence", "a", "--config", str(cfg)]
    )
    assert res.exit_code == 0
    assert card_a.read_text("utf-8") == before_a
    assert card_b.read_text("utf-8") == before_b


def test_update_evidence_drafts_only_when_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """默认仅 human_approved；--include-drafts 才包含 ai_draft。"""
    cfg, vault, card_a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    profile = _write_profile(vault, "a")

    # 把 card_a 改回 ai_draft 状态
    text = card_a.read_text("utf-8")
    parts = text.split("---\n", 2)
    fm = yaml.safe_load(parts[1])
    fm["status"] = "ai_draft"
    card_a.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + parts[2],
        "utf-8",
    )

    # 默认运行：card-a 不应入块
    res1 = runner.invoke(
        app, ["project", "update-evidence", "a", "--config", str(cfg)]
    )
    assert res1.exit_code == 0
    text1 = profile.read_text("utf-8")
    block1 = text1.split(START_MARKER)[1].split(END_MARKER)[0]
    assert "Card A" not in block1
    assert "Card B" in block1

    # --include-drafts：card-a 入块
    res2 = runner.invoke(
        app,
        ["project", "update-evidence", "a", "--include-drafts", "--config", str(cfg)],
    )
    assert res2.exit_code == 0
    text2 = profile.read_text("utf-8")
    block2 = text2.split(START_MARKER)[1].split(END_MARKER)[0]
    assert "Card A" in block2
    assert "ai_draft" in block2


def test_update_evidence_unit_path_traversal_rejected(tmp_path: Path) -> None:
    """validate 路径名 — 与 project_profile 同一道防御。"""
    res = runner.invoke(
        app,
        ["project", "update-evidence", "../etc/passwd"],
    )
    assert res.exit_code != 0


def test_evidence_block_append_when_marker_missing(tmp_path: Path) -> None:
    """profile 文件无 marker → 追加到末尾。"""
    p = tmp_path / "x.md"
    p.write_text("---\nproject: x\n---\n\n# x\n\n人手内容\n", "utf-8")
    upd = update_evidence_block(p, "x", [], cards_dir_rel="20-Knowledge-Cards")
    assert upd.block_existed_before is False
    assert START_MARKER in upd.new_text
    assert END_MARKER in upd.new_text
    write_evidence_update(upd)
    text = p.read_text("utf-8")
    assert "人手内容" in text
    # 第二次：marker 已存在 → 替换，不再追加
    upd2 = update_evidence_block(p, "x", [], cards_dir_rel="20-Knowledge-Cards")
    assert upd2.block_existed_before is True
    write_evidence_update(upd2)
    text2 = p.read_text("utf-8")
    assert text2.count(START_MARKER) == 1


# ===========================================================================
# 4. Telemetry
# ===========================================================================


def test_telemetry_record_event_writes_only_whitelisted(tmp_path: Path) -> None:
    cfg = TelemetryConfig(enabled=True)
    record_event(
        tmp_path, cfg,
        event_name="command_completed", command="recall",
        success=True, duration_ms=12, result_count=3,
    )
    p = telemetry_path(tmp_path)
    assert p.exists()
    rec = json.loads(p.read_text("utf-8").strip())
    # 所有字段必须在白名单
    for k in rec.keys():
        assert k in ALLOWED_FIELDS, f"unexpected field: {k}"
    assert rec["command"] == "recall"
    assert rec["success"] is True


def test_telemetry_disabled_writes_nothing(tmp_path: Path) -> None:
    cfg = TelemetryConfig(enabled=False)
    record_event(
        tmp_path, cfg,
        event_name="command_completed", command="recall", success=True,
    )
    assert not telemetry_path(tmp_path).exists()


def test_telemetry_measure_records_duration_and_failure(tmp_path: Path) -> None:
    cfg = TelemetryConfig(enabled=True)
    with pytest.raises(ValueError):
        with measure(tmp_path, cfg, "x-cmd") as h:
            h.set_counts(card_count=0)
            raise ValueError("boom")
    rec = json.loads(telemetry_path(tmp_path).read_text("utf-8").strip())
    assert rec["success"] is False
    assert rec["error_code"] == "ValueError"
    assert "duration_ms" in rec
    assert rec["command"] == "x-cmd"


def test_telemetry_status_and_summary_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, _vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    # 跑两次 project context，制造 telemetry 记录
    runner.invoke(app, ["project", "context", "a", "--config", str(cfg)])
    runner.invoke(app, ["project", "context", "a", "b", "--config", str(cfg)])

    status_res = runner.invoke(app, ["telemetry", "status", "--config", str(cfg)])
    assert status_res.exit_code == 0
    assert "enabled: True" in status_res.stdout
    assert "telemetry.jsonl" in status_res.stdout

    sum_res = runner.invoke(app, ["telemetry", "summary", "--config", str(cfg)])
    assert sum_res.exit_code == 0
    assert "total:" in sum_res.stdout
    assert "project-context" in sum_res.stdout

    json_res = runner.invoke(
        app, ["telemetry", "summary", "--format", "json", "--config", str(cfg)]
    )
    assert json_res.exit_code == 0
    payload = json.loads(json_res.stdout)
    assert payload["total"] >= 2
    assert "project-context" in payload["by_command"]
    assert payload["success"] >= 2


def test_telemetry_disabled_via_config_skips_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, _vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    # 给 fake fixture 的 config 注入 telemetry: enabled: false
    raw = yaml.safe_load(cfg.read_text("utf-8"))
    raw["telemetry"] = {"enabled": False, "local_only": True}
    cfg.write_text(yaml.safe_dump(raw, allow_unicode=True), "utf-8")

    res = runner.invoke(app, ["project", "context", "a", "--config", str(cfg)])
    assert res.exit_code == 0

    # 文件可能根本未创建
    p = tmp_path / ".mindforge" / "telemetry.jsonl"
    if p.exists():
        # 如存在（其它测试创建过），至少本次不应新增 project-context 记录
        events = read_events(tmp_path / ".mindforge")
        # 由于本测试 tmp_path 是隔离的，应该为空
        assert all(e.get("command") != "project-context" for e in events)


def test_telemetry_summary_recent_errors(tmp_path: Path) -> None:
    cfg = TelemetryConfig(enabled=True)
    record_event(tmp_path, cfg, event_name="command_completed", command="x", success=True, duration_ms=10)
    record_event(tmp_path, cfg, event_name="command_completed", command="y", success=False, duration_ms=20, error_code="ValueError")
    record_event(tmp_path, cfg, event_name="command_completed", command="z", success=False, duration_ms=30, error_code="OSError")
    summary = summarize(read_events(tmp_path), recent_errors=10)
    assert summary.total == 3
    assert summary.success == 1
    assert summary.failure == 2
    assert summary.by_command == {"x": 1, "y": 1, "z": 1}
    assert {e["error_code"] for e in summary.recent_errors} == {"ValueError", "OSError"}


def test_telemetry_never_contains_credentials_or_card_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _a, _b = _setup_vault_with_two_approved_cards(tmp_path, monkeypatch)
    _write_profile(vault, "a")
    runner.invoke(app, ["project", "context", "a", "--config", str(cfg)])
    runner.invoke(
        app, ["project", "update-evidence", "a", "--config", str(cfg)]
    )

    tele = (tmp_path / ".mindforge" / "telemetry.jsonl").read_text("utf-8")
    for pat in _LEAK_PATTERNS:
        assert not pat.search(tele), f"telemetry leak: {pat.pattern}"
    assert "sk-multi-leak-test" not in tele
    assert "项目 [a] 原则" not in tele
    assert "card-a 原则" not in tele

    # 字段层面：解析每行确认所有 key 都在白名单
    for line in tele.splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        for k in rec.keys():
            assert k in ALLOWED_FIELDS, f"unexpected telemetry field: {k}"


# ===========================================================================
# 5. update-evidence 的 evidence 模块单元测试
# ===========================================================================


def test_update_evidence_block_raises_on_missing_profile(tmp_path: Path) -> None:
    with pytest.raises(EvidenceError):
        update_evidence_block(
            tmp_path / "missing.md", "x", [], cards_dir_rel="20-Knowledge-Cards"
        )
