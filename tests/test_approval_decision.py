"""Bundle B — first-class ApprovalDecision seam tests.

本测试文件守护以下不变量，避免后续添加 reject/defer/merge/link/split/
append-as-evidence 时退化：

1. ``ApprovalDecision`` enum 必须穷举 Roadmap 已声明的 7 种用户决定。
2. ``apply_decision`` dispatcher 必须对**每一个** enum 成员都有显式分支
   （AST 静态保证，不依赖运行期覆盖率）。
3. 当前版本只有 ``APPROVE`` 接通既有 ``approve_card`` 行为；其余 6 个分支
   必须 raise ``NotImplementedDecisionError``，**绝不能**静默返回 None
   或假装成功 —— 否则会破坏 ``ai_draft → human_approved`` 边界。
4. ``ApprovalEffect`` 是 ``ApprovalOutcome`` 的新名字（同对象），历史
   import 路径仍可用，便于平滑迁移。
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

from mindforge.approver import (
    ApprovalDecision,
    ApprovalEffect,
    ApprovalError,
    ApprovalOutcome,
    ApprovalRequest,
    NotImplementedDecisionError,
    apply_decision,
    approve_card,
)
from mindforge.config import MindForgeConfig, load_mindforge_config


# ---------------------------------------------------------------------------
# 1. enum 形状 / 历史别名
# ---------------------------------------------------------------------------


_REQUIRED_DECISIONS = {
    "APPROVE",
    "REJECT",
    "DEFER",
    "APPEND_AS_EVIDENCE",
    "LINK_TO_EXISTING",
    "MERGE_CANDIDATE",
    "SPLIT",
}


def test_approval_decision_enum_lists_all_seven_first_class_outcomes() -> None:
    """7 种 first-class outcome 必须全部建模为 enum 成员。

    Roadmap 在 Phase 1 完成标准里明确列出这 7 种用户决定；本测试是该需求
    的领域模型快照。新增决定必须先扩 enum，再扩 dispatcher，不能反过来。
    """

    actual = {member.name for member in ApprovalDecision}
    assert actual == _REQUIRED_DECISIONS, (
        f"ApprovalDecision 成员漂移：缺 {_REQUIRED_DECISIONS - actual}，"
        f"多 {actual - _REQUIRED_DECISIONS}"
    )


def test_approval_decision_values_are_stable_strings() -> None:
    """枚举 value 用于 JSON / 日志序列化，必须是稳定的 snake_case 字符串。"""

    expected = {
        ApprovalDecision.APPROVE: "approve",
        ApprovalDecision.REJECT: "reject",
        ApprovalDecision.DEFER: "defer",
        ApprovalDecision.APPEND_AS_EVIDENCE: "append_as_evidence",
        ApprovalDecision.LINK_TO_EXISTING: "link_to_existing",
        ApprovalDecision.MERGE_CANDIDATE: "merge_candidate",
        ApprovalDecision.SPLIT: "split",
    }
    for member, value in expected.items():
        assert member.value == value


def test_approval_outcome_is_alias_of_approval_effect() -> None:
    """历史名 ``ApprovalOutcome`` 必须仍指向新名 ``ApprovalEffect``。

    保留别名是为了让未受控的下游脚本 / 文档示例不会一夜之间炸掉；本仓库
    内部一律使用 ``ApprovalEffect``。
    """

    assert ApprovalOutcome is ApprovalEffect


# ---------------------------------------------------------------------------
# 2. dispatcher AST fitness：必须穷举所有 enum 成员
# ---------------------------------------------------------------------------


def test_apply_decision_dispatcher_handles_every_enum_member() -> None:
    """``apply_decision`` 函数体必须显式提及每一个 ``ApprovalDecision`` 成员。

    用 AST 静态扫描函数源码，找所有形如 ``ApprovalDecision.<NAME>`` 的
    Attribute 节点。新增 enum 成员但忘记接 dispatcher 时，本测试会立刻
    红灯，避免出现"用户做了决定但系统静默无视"的隐性 bug。
    """

    src = inspect.getsource(apply_decision)
    tree = ast.parse(src)
    referenced: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "ApprovalDecision"
        ):
            referenced.add(node.attr)
    missing = _REQUIRED_DECISIONS - referenced
    assert not missing, (
        f"apply_decision dispatcher 漏处理决定：{missing}；"
        f"新增 enum 成员后必须同时在 dispatcher 中加一个分支"
    )


# ---------------------------------------------------------------------------
# 3. 行为：APPROVE 路径与既有 approve_card 字节一致；其余分支 NotImplemented
# ---------------------------------------------------------------------------


def _write_card(cards_dir: Path, name: str, frontmatter: dict[str, object]) -> Path:
    front = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in frontmatter.items()
    )
    path = cards_dir / f"{name}.md"
    path.write_text(f"---\n{front}\n---\n\nbody\n", encoding="utf-8")
    return path


def _make_cfg(tmp_path: Path) -> tuple[MindForgeConfig, Path]:
    """复用 test_approval_service 的最小 vault/config 形态；不读 .env、不接真实 LLM。"""

    import yaml

    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    projects = vault / "30-Projects"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    cards.mkdir(parents=True)
    projects.mkdir(parents=True)

    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                    "projects_dir": "30-Projects",
                },
                "sources": {
                    "enabled": ["plain_markdown"],
                    "registry": {
                        "plain_markdown": {
                            "adapter": "PlainMarkdownAdapter",
                            "inbox_subdir": "ManualNotes",
                            "file_glob": "*.md",
                            "enabled": True,
                        }
                    },
                },
                "state": {
                    "workdir": str(tmp_path / ".mindforge"),
                    "state_file": "state.json",
                    "runs_dir": "runs",
                    "index_file": "index.jsonl",
                },
                "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
                "llm": {
                    "active_profile": "fake",
                    "profiles": {
                        "fake": {
                            "triage": "f1",
                            "distill": "f1",
                            "link_suggestion": "f1",
                            "review_questions": "f1",
                            "action_extraction": "f1",
                        }
                    },
                    "models": {
                        "f1": {
                            "provider": "fake-local",
                            "type": "fake",
                            "base_url": "fake://",
                            "model": "fake-1",
                            "timeout_seconds": 5,
                            "max_retries": 0,
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
        ),
        encoding="utf-8",
    )
    return load_mindforge_config(cfg_path), cards


def test_approve_decision_dispatches_to_existing_approve_card_behavior(
    tmp_path: Path,
) -> None:
    """APPROVE 分支必须复用既有 ``approve_card``，行为字节一致。

    用同一张 ai_draft 卡片分别走两条路径，比较返回的 ``ApprovalEffect``
    关键字段：保证 dispatcher 没有偷偷改变晋升语义。
    """

    cfg, cards = _make_cfg(tmp_path)
    card_a = _write_card(cards, "a", {"id": "a", "status": "ai_draft"})
    card_b = _write_card(cards, "b", {"id": "b", "status": "ai_draft"})

    direct = approve_card(card_a, cfg=cfg)
    via_seam = apply_decision(
        ApprovalRequest(card_path=card_b, decision=ApprovalDecision.APPROVE),
        cfg=cfg,
    )

    assert direct.kind == via_seam.kind == "approved"
    assert direct.prev_status == via_seam.prev_status == "ai_draft"
    assert direct.new_status == via_seam.new_status == "human_approved"
    assert direct.approval_method == via_seam.approval_method


@pytest.mark.parametrize(
    "decision",
    [
        ApprovalDecision.REJECT,
        ApprovalDecision.DEFER,
        ApprovalDecision.APPEND_AS_EVIDENCE,
        ApprovalDecision.LINK_TO_EXISTING,
        ApprovalDecision.MERGE_CANDIDATE,
        ApprovalDecision.SPLIT,
    ],
)
def test_unimplemented_decisions_raise_explicit_not_implemented(
    tmp_path: Path,
    decision: ApprovalDecision,
) -> None:
    """6 个未实现分支必须显式 raise，错误消息提到 decision 名字。

    显式爆炸而非静默忽略，是为了：
    - 任何上层误用都会被立刻发现，不会"假装成功"
    - 卡片状态绝不会因为意图未实现而被悄悄改写
    - 后续 Bundle 接通某分支时，移除这条 raise 即可，调用方零改动
    """

    cfg, cards = _make_cfg(tmp_path)
    card = _write_card(cards, "x", {"id": "x", "status": "ai_draft"})
    before = card.read_text(encoding="utf-8")

    with pytest.raises(NotImplementedDecisionError) as exc_info:
        apply_decision(
            ApprovalRequest(card_path=card, decision=decision),
            cfg=cfg,
        )

    assert exc_info.value.decision is decision
    assert decision.value in str(exc_info.value)
    # 关键：未实现分支绝不能改卡片状态
    assert card.read_text(encoding="utf-8") == before
    # 继承自 ApprovalError，CLI 既有错误处理可以兜住
    assert isinstance(exc_info.value, ApprovalError)


def test_not_implemented_decision_error_uses_ex_usage_exit_code() -> None:
    """exit_code 复用 EX_USAGE(64)；不与既有业务错误码（2/3/4）冲突。"""

    err = NotImplementedDecisionError(ApprovalDecision.REJECT)
    assert err.exit_code == 64
