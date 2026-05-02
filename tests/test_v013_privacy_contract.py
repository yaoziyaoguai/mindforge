"""v0.13 Stage 1 — 隐私契约 / 提案 / deferred gates 文档断言。

钉死 3 份 canonical 文档的关键 token, 防止以后被静默修改、复制漂移
或字段语义反转。
"""

from __future__ import annotations

from pathlib import Path

import pytest

PRIVACY = Path("docs/LOCAL_FIRST_PRIVACY_CONTRACT.md")
PROPOSAL = Path("docs/PROPOSAL_REVIEWABLE_ARTIFACT.md")
GATES = Path("docs/V0_13_REAL_INGESTION_DEFERRED_GATES.md")


def test_privacy_contract_exists():
    assert PRIVACY.exists()


@pytest.mark.parametrize(
    "token",
    [
        "fake-default",
        "real-opt-in",
        "human_approved",
        "active_profile",
        "secret",
        "Cubox",
        "Obsidian",
        "Real ≠ Approved",
        "Human Decision Gate Map",
    ],
)
def test_privacy_contract_token(token: str):
    assert token in PRIVACY.read_text(encoding="utf-8"), f"missing: {token}"


def test_proposal_exists_and_marked_unauthorized():
    text = PROPOSAL.read_text(encoding="utf-8")
    assert "proposal-only" in text or "proposal only" in text.lower()
    assert "NOT authorized" in text or "未授权" in text
    # 关键约束: 提案不得隐含允许 human_approved 自动产生
    assert "human_approved" in text


def test_proposal_lists_artifact_kinds():
    text = PROPOSAL.read_text(encoding="utf-8")
    for kind in [
        "preview_packet",
        "ai_draft_preview",
        "readiness_report",
        "real_smoke_result",
    ]:
        assert kind in text, f"missing artifact kind: {kind}"


def test_deferred_gates_exists():
    assert GATES.exists()


@pytest.mark.parametrize(
    "token",
    [
        "测试账号",
        "sample folder",
        "no-persist",
        "dry-run",
        "human_approved",
        "--allow-real",
        "--allow-write",
        "Path.home()",
    ],
)
def test_deferred_gates_token(token: str):
    assert token in GATES.read_text(encoding="utf-8"), f"missing: {token}"
