"""v0.10 Slice 4 TDD Red — Strategy 输出公共信封（common envelope）契约。

设计意图（中文学习型）
======================

为什么 v0.10 必须先解决 envelope，再做 v0.11 StrategyRegistry？
---------------------------------------------------------------

Slice 3 Green 测试 ``--strategy default_knowledge_card`` 时被迫使用
``--dry-run``：原因是 ``DefaultKnowledgeCardStrategy`` 输出的 10 字段
扁平 payload 与 ``CardWriter`` 期望的 ``{"card": {...track, id}}``
schema 不兼容。如果不先冻结一个跨策略稳定的 **公共信封**，未来每新增
一个内置 strategy 或自定义 strategy 都会重复遇到 writer/presenter/
review/approval 适配问题，最终把 ``CardWriter`` 或某个 presenter 拖成
"知道所有 strategy 字段" 的多策略巨石 —— 这违反 v0.11 路线锁定的
"strategy 自带 schema、registry 不重新发明字段" 原则。

公共信封契约
============

任意 strategy 的 ``PipelineOutcome.card_payload`` 必须满足：

1. **strategy_id**：当前策略名（registry 注册名），便于 audit 与
   per-strategy 渲染分发；
2. **strategy_version**：策略实现版本字符串，用于回放历史 ai_draft；
3. **schema_version**：本 envelope 模式版本，未来扩展时向后兼容；
4. **status**：必须恒为 ``"ai_draft"`` —— 任何 strategy 永远不能伪造
   已审核状态；
5. **source_evidence**：来源 provenance（至少包含 source_id /
   source_type / content_hash 三选二），用于 review 时回溯；
6. **structured_payload**：strategy-specific 字段全部装入此键，外层
   不再读 strategy-specific keys —— writer/presenter/approval 只读公
   共字段；
7. **review_hints**：review 阶段需要的最小 headline 元数据（至少
   ``title`` 与 ``one_line``）；presenter 仅消费这些字段就能产生
   "可审" 的简介，无需理解 structured_payload 内部结构。

设计原则
========

- **Strategy 自带 structured_payload schema**：writer / presenter /
  approval 不应理解 strategy-specific 字段，只应消费公共信封。
- **CardWriter 不是 StrategyRegistry**：writer 只接受公共信封 +
  approval boundary 之后的 ``human_approved`` envelope；不允许 writer
  内部 if strategy_id == X 来分发渲染。
- **Presenter 不是 StrategyRegistry**：presenter 渲染基于公共信封，
  对未知 strategy 仍能给出安全 preview（fallback 到通用模板）。
- **Approval 只接受公共信封**：``approver.approve_card`` 的输入是公
  共信封 + 显式人工动作，不接受裸 source-layer 输出。
- **dry-run 不写 workspace**：CLI ``--dry-run`` 路径下 writer 不被调
  用 —— 这是 Slice 3 已隐式依赖的契约，本测试将其显式化。
- **Strategy 不调用 CardWriter / Approval / Presenter**：Strategy 只
  emit envelope，不主动 IO。

预期 Red
========

当前两个 strategy（``five_stage`` / ``default_knowledge_card``）输出
的 payload 都不符合公共信封：

- ``five_stage`` 输出 ``{"card": {...}}``，缺 strategy_id /
  strategy_version / schema_version / source_evidence /
  structured_payload / review_hints。
- ``default_knowledge_card`` 输出扁平 10 字段，同样缺这些公共字段。

因此本文件中所有 envelope-shape 测试预期 Red。它们的失败原因是
**production 尚未实现公共信封**，不是 import error 或 fixture 问题。

不属于本 slice
==============

- 不实现 envelope（那是 Slice 4 Green / 或后续独立 milestone）；
- 不改 CardWriter；
- 不改任何 presenter；
- 不改 approval；
- 不调真实 LLM；
- 不读 .env；
- 不调真实 Cubox API；
- 不写正式 Obsidian vault；
- 不生成已审核状态；
- 不实现 StrategyRegistry / custom strategy。
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401

import pytest

from mindforge.processors.pipeline import PipelineOutcome
from mindforge.sources.base import SourceDocument, compute_content_hash
from mindforge.strategies import StrategyContext, build_strategy
from mindforge.strategies.default_knowledge_card import (
    build_default_knowledge_card_strategy,
)


# ---------------------------------------------------------------------------
# 公共信封必填字段（contract）
# ---------------------------------------------------------------------------

ENVELOPE_REQUIRED_KEYS = frozenset(
    {
        "strategy_id",
        "strategy_version",
        "schema_version",
        "status",
        "source_evidence",
        "structured_payload",
        "review_hints",
    }
)

REVIEW_HINTS_REQUIRED_KEYS = frozenset({"title", "one_line"})


def _doc(text: str = "Title: Slice 4\n\nEnvelope contract sample paragraph.") -> SourceDocument:
    return SourceDocument(
        source_id="id:slice4-envelope-1",
        source_type="plain_markdown",
        source_path="/tmp/slice4-envelope.md",
        title="envelope contract",
        raw_text=text,
        content_hash=compute_content_hash(text),
        adapter_name="PlainMarkdownAdapter",
        tags=["envelope"],
    )


def _ctx() -> StrategyContext:
    return StrategyContext()


# ---------------------------------------------------------------------------
# Red 期望：两条策略都不满足公共信封契约
# ---------------------------------------------------------------------------


def test_default_knowledge_card_payload_has_envelope_keys() -> None:
    """``DefaultKnowledgeCardStrategy`` 输出必须含公共信封字段。

    当前 production 直接吐 10 字段扁平结构，缺 envelope keys → 预期 Red。
    """
    strat = build_default_knowledge_card_strategy(_ctx())
    outcome = strat.run(_doc())
    assert isinstance(outcome, PipelineOutcome)
    assert outcome.card_payload is not None
    missing = ENVELOPE_REQUIRED_KEYS - set(outcome.card_payload.keys())
    assert not missing, (
        f"DefaultKnowledgeCardStrategy 输出缺 envelope 字段：{sorted(missing)}\n"
        f"实际 keys：{sorted(outcome.card_payload.keys())}"
    )


def test_default_knowledge_card_envelope_status_is_ai_draft() -> None:
    """envelope 顶层 ``status`` 必须为 ``"ai_draft"`` —— Strategy 永不能伪造已审核状态。"""
    strat = build_default_knowledge_card_strategy(_ctx())
    outcome = strat.run(_doc())
    assert outcome.card_payload is not None
    assert outcome.card_payload.get("status") == "ai_draft"


def test_default_knowledge_card_envelope_carries_strategy_identity() -> None:
    """envelope 必须含 strategy_id 与 strategy_version，便于 audit 与回放。"""
    strat = build_default_knowledge_card_strategy(_ctx())
    outcome = strat.run(_doc())
    assert outcome.card_payload is not None
    assert outcome.card_payload.get("strategy_id") == "default_knowledge_card"
    sv = outcome.card_payload.get("strategy_version")
    assert isinstance(sv, str) and sv, "strategy_version 必须为非空字符串"


def test_default_knowledge_card_envelope_review_hints_minimum() -> None:
    """``review_hints`` 至少包含 ``title`` 与 ``one_line``，供 presenter 安全渲染。"""
    strat = build_default_knowledge_card_strategy(_ctx())
    outcome = strat.run(_doc())
    assert outcome.card_payload is not None
    hints = outcome.card_payload.get("review_hints")
    assert isinstance(hints, dict), f"review_hints 必须是 dict，实际：{type(hints)}"
    missing = REVIEW_HINTS_REQUIRED_KEYS - set(hints.keys())
    assert not missing, f"review_hints 缺字段：{sorted(missing)}"


def test_default_knowledge_card_envelope_structured_payload_isolation() -> None:
    """strategy-specific 字段必须在 ``structured_payload`` 内，envelope 顶层不泄漏。

    例如 10 字段中的 ``key_takeaways`` / ``concepts`` /
    ``questions_for_review`` 必须在 ``structured_payload`` 里，而不是
    在 envelope 顶层；否则 writer/presenter/approval 都会被迫认识这
    些 strategy-specific 字段。
    """
    strat = build_default_knowledge_card_strategy(_ctx())
    outcome = strat.run(_doc())
    assert outcome.card_payload is not None
    structured = outcome.card_payload.get("structured_payload")
    assert isinstance(structured, dict)
    leaked = {
        "key_takeaways",
        "concepts",
        "questions_for_review",
        "limitations",
    } & set(outcome.card_payload.keys())
    assert not leaked, (
        f"strategy-specific 字段不应出现在 envelope 顶层：{sorted(leaked)}"
    )


def test_default_knowledge_card_envelope_source_evidence_present() -> None:
    """``source_evidence`` 必须含至少 ``source_id`` 与 ``content_hash``，用于 review 回溯。"""
    strat = build_default_knowledge_card_strategy(_ctx())
    outcome = strat.run(_doc())
    assert outcome.card_payload is not None
    evidence = outcome.card_payload.get("source_evidence")
    assert isinstance(evidence, dict)
    for key in ("source_id", "content_hash"):
        assert key in evidence, f"source_evidence 缺 {key}"


# ---------------------------------------------------------------------------
# Red 期望：five_stage 也必须升级到公共信封
# ---------------------------------------------------------------------------


def test_five_stage_payload_should_also_use_envelope() -> None:
    """``five_stage`` 输出也必须迁移到公共信封。

    当前 ``five_stage`` 直接吐 ``{"card": {...}}``，CardWriter 是其
    唯一已知消费者，但这条契约阻碍了 v0.11 多策略 —— writer 不能为
    每个 strategy 写一段适配代码。本测试把"公共信封覆盖所有内置策略"
    显式化。

    使用 registry by-name 派发，避免硬编码 import；如果 five_stage
    需要 LLM client，跳过测试（Slice 4 Green 实现时再决定如何在
    deterministic 路径上验证 envelope；本 Red 阶段只需暴露 gap）。
    """
    try:
        strat = build_strategy("five_stage", _ctx())
    except ValueError as exc:
        pytest.skip(f"five_stage 需要 LLM client，跳过 envelope shape 检查：{exc}")
        return  # 防御性
    outcome = strat.run(_doc())  # type: ignore[unreachable]
    assert outcome.card_payload is not None
    missing = ENVELOPE_REQUIRED_KEYS - set(outcome.card_payload.keys())
    assert not missing, (
        f"five_stage 输出缺 envelope 字段：{sorted(missing)}\n"
        f"实际 keys：{sorted(outcome.card_payload.keys())}"
    )


# ---------------------------------------------------------------------------
# Green 期望：strategy 不主动 IO（已是 Slice 1 boundary 的子集，这里冗余固化）
# ---------------------------------------------------------------------------


def test_strategy_module_does_not_import_card_writer() -> None:
    """Strategy 模块禁止 import CardWriter / approver / presenter / review_service。

    防止未来 Green 实现公共信封时，"顺便" 让 strategy 自己调 writer
    或 approval。strategy 只 emit envelope，IO 由 CLI/service 完成。
    """
    import ast

    strategy_dir = Path(__file__).resolve().parent.parent / "src" / "mindforge" / "strategies"
    forbidden = {
        "CardWriter",
        "approver",
        "approve_card",
        "approval_service",
        "review_service",
        "approve_presenter",
        "review_presenter",
        "recall_presenter",
    }
    leaks: dict[str, set[str]] = {}
    for f in strategy_dir.glob("*.py"):
        tree = ast.parse(f.read_text("utf-8"))
        seen: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    tail = node.module.rsplit(".", 1)[-1]
                    if tail in forbidden:
                        seen.add(tail)
                for alias in node.names:
                    if alias.name in forbidden:
                        seen.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    tail = alias.name.rsplit(".", 1)[-1]
                    if tail in forbidden:
                        seen.add(tail)
        if seen:
            leaks[f.name] = seen
    assert not leaks, f"strategies/ 不得 import IO/approval 模块：{leaks}"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
