"""Privacy contract / future gate documentation assertions.

历史 privacy/gate/proposal 文档已经合并进 canonical docs；这里钉住关键
token，防止语义反转。
"""

from __future__ import annotations

from pathlib import Path

import pytest

PRIVACY = Path("docs/SECURITY.md")
PROPOSAL = Path("docs/IMPLEMENTATION.md")
GATES = Path("docs/ROADMAP.md")


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
    assert "review-only" in text
    assert "not `human_approved`" in text
    # 关键约束: 提案不得隐含允许 human_approved 自动产生
    assert "human_approved" in text


def test_proposal_lists_artifact_kinds():
    text = PROPOSAL.read_text(encoding="utf-8")
    for kind in [
        "preview packets",
        "readiness checks",
        "real smoke",
    ]:
        assert kind in text, f"missing artifact kind: {kind}"


def test_deferred_gates_exists():
    assert GATES.exists()


@pytest.mark.parametrize(
    "token",
    [
        "sample folder",
        "no-persist",
        "dry-run",
        "human_approved",
        "diff preview",
        "backup",
    ],
)
def test_deferred_gates_token(token: str):
    assert token in GATES.read_text(encoding="utf-8"), f"missing: {token}"
