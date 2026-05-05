"""M3 — `mindforge approve` 反 AI 污染闸门测试。

覆盖矩阵对应 docs/SECURITY.md 的 explicit approval boundary。要点：
- ai_draft 可晋升、human_approved 幂等、其他 status 拒绝；
- approve 不调 LLM、不需要 .env、不改正文、不改源文件；
- runs jsonl 字段全在白名单；
- pipeline 端到端跑完，所有卡片初始 status 必为 ai_draft（结构上证明
  AI 永远不会自动晋升 human_approved）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.checkpoint import Checkpoint
from mindforge.cli import app

# 复用 M2 fake-LLM 端到端 fixture：能把一个真卡片落到 vault
from tests.test_process_e2e import (  # type: ignore[import-not-found]
    _build_vault_with_fake_llm,
    _common_process_args,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# 公共 fixture：跑一遍 process 得到一张 ai_draft 卡片
# ---------------------------------------------------------------------------


def _setup_vault_with_one_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path, Path]:
    """返回 (cfg_path, vault, src_file, card_path)。卡片处于 ai_draft。"""
    # 防御：清掉 MINDFORGE_* 并 chdir 到 tmp，避免误读真实 .env
    for k in list(os.environ.keys()):
        if k.startswith("MINDFORGE_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)

    cfg_path, vault, src_file = _build_vault_with_fake_llm(tmp_path)
    r_scan = runner.invoke(app, ["scan", "--config", str(cfg_path)])
    assert r_scan.exit_code == 0, r_scan.output
    r_proc = runner.invoke(app, _common_process_args(cfg_path))
    assert r_proc.exit_code == 0, r_proc.output

    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) == 1
    return cfg_path, vault, src_file, cards[0]


def _read_fm(card: Path) -> dict:
    text = card.read_text("utf-8")
    assert text.startswith("---\n")
    fm_text = text.split("---\n", 2)[1]
    fm = yaml.safe_load(fm_text)
    assert isinstance(fm, dict)
    return fm


def _read_body(card: Path) -> str:
    text = card.read_text("utf-8")
    return text.split("---\n", 2)[2]


# ---------------------------------------------------------------------------
# (1) ai_draft → approve 成功；frontmatter / state 同步
# ---------------------------------------------------------------------------


def test_approve_promotes_ai_draft_to_human_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _vault, _src, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    fm0 = _read_fm(card)
    assert fm0["status"] == "ai_draft"

    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 0, r.output
    fm1 = _read_fm(card)
    assert fm1["status"] == "human_approved"
    assert fm1["approval_method"] == "explicit_cli"
    assert isinstance(fm1["approved_at"], str) and "T" in fm1["approved_at"]

    # state.json 同步
    cp = Checkpoint.load(tmp_path / ".mindforge" / "state.json")
    items = list(cp.all_items())
    assert len(items) == 1
    item = items[0]
    assert item.status == "human_approved"
    assert item.approval_method == "explicit_cli"
    assert item.approved_at is not None


# ---------------------------------------------------------------------------
# (2) approve 不修改正文
# ---------------------------------------------------------------------------


def test_approve_preserves_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, _s, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    body_before = _read_body(card)
    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 0
    assert _read_body(card) == body_before


# ---------------------------------------------------------------------------
# (3) approve 不修改源文件
# ---------------------------------------------------------------------------


def test_approve_does_not_touch_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, src, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    src_bytes = src.read_bytes()
    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 0
    assert src.read_bytes() == src_bytes


# ---------------------------------------------------------------------------
# (4) approve 零 env
# ---------------------------------------------------------------------------


def test_approve_works_with_zero_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, _s, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    # 再次清环境，确保 approve 这一调用本身不依赖任何 env
    for k in list(os.environ.keys()):
        if k.startswith("MINDFORGE_") or k.startswith("OPENAI"):
            monkeypatch.delenv(k, raising=False)
    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 0, r.output


# ---------------------------------------------------------------------------
# (5) approve 不调 LLM（任何 HTTP post 都应当 fail，但 approve 仍 exit 0）
# ---------------------------------------------------------------------------


def test_approve_never_calls_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, _s, card = _setup_vault_with_one_card(tmp_path, monkeypatch)

    import httpx

    def _no_http(*a, **kw):  # type: ignore[no-untyped-def]
        raise AssertionError("approve 路径绝不应该发起 HTTP 请求")

    monkeypatch.setattr(httpx.Client, "post", _no_http, raising=True)
    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 0, r.output


# ---------------------------------------------------------------------------
# (6) human_approved 幂等
# ---------------------------------------------------------------------------


def test_approve_is_idempotent_on_human_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, _s, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    r1 = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r1.exit_code == 0
    fm1 = _read_fm(card)
    text1 = card.read_text("utf-8")

    r2 = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r2.exit_code == 0
    fm2 = _read_fm(card)
    text2 = card.read_text("utf-8")

    # 卡片字节级不变；timestamp 没刷新
    assert text1 == text2
    assert fm1["approved_at"] == fm2["approved_at"]


# ---------------------------------------------------------------------------
# (7) 非 ai_draft / 非 human_approved 状态拒绝
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_status", ["raw", "triaged", "skipped", "failed", "weird"])
def test_approve_rejects_non_promotable_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_status: str
) -> None:
    cfg_path, _v, _s, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    text = card.read_text("utf-8")
    text2 = text.replace("status: ai_draft", f"status: {bad_status}", 1)
    assert text2 != text
    card.write_text(text2, encoding="utf-8")

    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 4, r.output
    # 卡片完全没变
    assert card.read_text("utf-8") == text2


# ---------------------------------------------------------------------------
# (8) frontmatter 损坏 → exit 3
# ---------------------------------------------------------------------------


def test_approve_rejects_corrupt_frontmatter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, _s, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    # 写一个明显非法的 YAML
    card.write_text("---\nstatus: ai_draft\n  bad: : :\n---\nbody\n", encoding="utf-8")
    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 3, r.output


def test_approve_rejects_missing_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, _s, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    card.write_text("---\ntitle: X\n---\nbody\n", encoding="utf-8")
    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 3, r.output


# ---------------------------------------------------------------------------
# (9) 卡片不存在 → exit 2
# ---------------------------------------------------------------------------


def test_approve_rejects_missing_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, _s, _card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    r = runner.invoke(
        app,
        ["approve", "--card", str(tmp_path / "no-such-card.md"), "--config", str(cfg_path)],
    )
    assert r.exit_code == 2, r.output


# ---------------------------------------------------------------------------
# (10) runs jsonl 字段在白名单 + 卡审计事件齐全
# ---------------------------------------------------------------------------


def test_approve_runs_jsonl_uses_whitelisted_fields_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, _s, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    runs_dir = tmp_path / ".mindforge" / "runs"
    before = {p.name for p in runs_dir.glob("*.jsonl")}

    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 0

    after_files = [p for p in runs_dir.glob("*.jsonl") if p.name not in before]
    assert len(after_files) == 1
    events = [json.loads(line) for line in after_files[0].read_text("utf-8").splitlines() if line.strip()]
    names = [e["event"] for e in events]
    assert "approval_started" in names
    assert "approval_completed" in names
    # completed 含关键审计字段
    completed = next(e for e in events if e["event"] == "approval_completed")
    assert completed["status"] == "human_approved"
    assert completed["approval_method"] == "explicit_cli"
    assert "approved_at" in completed and completed["approved_at"]
    # 不得泄漏正文 / source 内容
    text = after_files[0].read_text("utf-8")
    for forbidden in ("Agent Runtime 札记", "raw_text", "prompt_text", "completion_text", "api_key"):
        assert forbidden not in text, f"runs jsonl 含禁字段 {forbidden!r}"


# ---------------------------------------------------------------------------
# (11) state.json round-trip：含新字段且无敏感内容
# ---------------------------------------------------------------------------


def test_state_json_round_trip_with_approval_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _v, _s, card = _setup_vault_with_one_card(tmp_path, monkeypatch)
    r = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"])
    assert r.exit_code == 0

    state_path = tmp_path / ".mindforge" / "state.json"
    state_text = state_path.read_text("utf-8")
    assert "approved_at" in state_text
    assert "approval_method" in state_text
    assert "explicit_cli" in state_text
    for forbidden in ("api_key", "Authorization", "Bearer ", "raw_text", "prompt_text", "completion_text"):
        assert forbidden not in state_text, f"state.json 泄漏禁字段 {forbidden!r}"

    # round-trip：load 后字段保留
    cp = Checkpoint.load(state_path)
    item = next(iter(cp.all_items()))
    assert item.status == "human_approved"
    assert item.approval_method == "explicit_cli"
    assert item.approved_at is not None


# ---------------------------------------------------------------------------
# (12) 反向断言：process 跑完，卡片初始 status 必为 ai_draft —— AI 永远不
# 会自动写 human_approved
# ---------------------------------------------------------------------------


def test_process_pipeline_never_writes_human_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for k in list(os.environ.keys()):
        if k.startswith("MINDFORGE_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)

    cfg_path, vault, _src = _build_vault_with_fake_llm(tmp_path)
    r_scan = runner.invoke(app, ["scan", "--config", str(cfg_path)])
    assert r_scan.exit_code == 0
    r_proc = runner.invoke(app, _common_process_args(cfg_path))
    assert r_proc.exit_code == 0

    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert cards, "至少应产出一张卡片"
    for c in cards:
        text = c.read_text("utf-8")
        assert "status: human_approved" not in text, (
            f"卡片 {c} 在 process 后 status 已是 human_approved — "
            "M3 协议被破坏：AI 不应自动晋升人审核状态"
        )
        # state.json 同样不该出现
    state_text = (tmp_path / ".mindforge" / "state.json").read_text("utf-8")
    assert "human_approved" not in state_text, (
        "state.json 在 process 后含 human_approved — pipeline 不应触发该状态"
    )
