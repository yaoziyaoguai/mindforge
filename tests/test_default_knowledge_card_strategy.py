"""DefaultKnowledgeCardStrategy contract tests — v0.10 KnowledgeStrategy Slice 1 (TDD Red).

为什么有这个文件
================

v0.9.x KnowledgeStrategy Customization Readiness 已经把
``DefaultKnowledgeCardStrategy`` 的 10 字段 payload contract 已收敛为
README-first 文档中的策略边界说明。
v0.10 Slice 1 的工作就是**先用测试把这个 contract 钉死**，确保
Slice 2 实现时只能产出符合契约的 payload —— 而不是边写边改 schema。

本文件**只写 tests**，不写生产代码。Slice 1 期望全部 **Red**，因为
``mindforge.strategies.default_knowledge_card`` 模块尚未存在；Slice 2
的最小实现负责把它们一次性翻绿。

设计边界（由测试守护）
======================

- strategy 必须以 ``SourceDocument`` 为唯一输入面；
- strategy 必须输出 ``PipelineOutcome`` 且 ``card_payload`` 含且仅含
  10 个 contract 字段；
- ``status`` 字段恒为 ``"ai_draft"``；
- payload 不得携带 ``human_approved`` / ``approved_by`` /
  ``approved_at`` / 任何 Obsidian 路径；
- 调用 ``run(doc)`` 不得开 socket、不得在 repo 根写文件。

任何"借实现 Slice 2 的便利顺手把这些规则放松"的修改，都会被这一组
测试拒掉。
"""

from __future__ import annotations

import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mindforge.sources.base import SourceDocument, compute_content_hash


# ---------------------------------------------------------------------------
# 10 字段 contract（与 README-first 策略边界对齐）
# ---------------------------------------------------------------------------


CARD_PAYLOAD_KEYS: frozenset[str] = frozenset({
    "title",
    "one_sentence_summary",
    "key_takeaways",
    "concepts",
    "questions_for_review",
    "source_evidence",
    "tags",
    "confidence",
    "limitations",
    "status",
})


# ---------------------------------------------------------------------------
# fixture 工厂
# ---------------------------------------------------------------------------


def _doc(text: str = "Title: Sample\n\nThis is a paragraph about agent runtimes.") -> SourceDocument:
    """构造最小合法 SourceDocument。raw_text 决定 content_hash。"""
    return SourceDocument(
        source_id="id:slice1-fixture",
        source_type="plain_markdown",
        source_path="/tmp/fixture.md",
        title="Sample title",
        raw_text=text,
        content_hash=compute_content_hash(text),
        adapter_name="PlainMarkdownAdapter",
        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=["fixture"],
    )


def _strategy_context():
    """构造一个最小 StrategyContext。

    本策略不消费 ``client`` / ``prompts_dir`` / ``prompt_versions`` /
    ``learning_tracks_text``。``StrategyContext`` 在 v0.10 中已把 ``client``
    定义为 ``Optional`` 并默认 ``None`` —— 无 LLM 策略不再需要发明占位
    LLMClient，这是 fake-first seam 的明确形态。
    """
    from mindforge.strategies.base import StrategyContext

    return StrategyContext()


# ---------------------------------------------------------------------------
# 1. 模块/类/工厂存在 —— Slice 1 期望 Red（ImportError）
# ---------------------------------------------------------------------------


def test_default_knowledge_card_module_importable() -> None:
    """``mindforge.strategies.default_knowledge_card`` 必须存在。

    **预期 Red**：模块尚未创建，Slice 2 的工作就是把它创建出来。
    """
    import importlib

    importlib.import_module("mindforge.strategies.default_knowledge_card")


def test_strategy_class_exists() -> None:
    """模块必须导出 ``DefaultKnowledgeCardStrategy`` 类。"""
    from mindforge.strategies import default_knowledge_card as mod

    assert hasattr(mod, "DefaultKnowledgeCardStrategy")


def test_factory_exists() -> None:
    """模块必须导出 ``build_default_knowledge_card_strategy`` 工厂。"""
    from mindforge.strategies import default_knowledge_card as mod

    assert hasattr(mod, "build_default_knowledge_card_strategy")
    assert callable(mod.build_default_knowledge_card_strategy)


def test_registry_lists_default_knowledge_card() -> None:
    """``registry.available_strategies()`` 必须包含新策略名。

    Slice 2 在 ``registry.py`` 注册新名后此条转绿。当前产品语义下，
    ``DEFAULT_STRATEGY_NAME`` 必须是 production ``"knowledge_card"``；
    ``default_knowledge_card`` 仅作为 internal deterministic baseline 保留。
    """
    from mindforge.strategies.registry import (
        DEFAULT_STRATEGY_NAME,
        available_strategies,
    )

    assert "default_knowledge_card" in available_strategies()
    assert DEFAULT_STRATEGY_NAME == "knowledge_card"


# ---------------------------------------------------------------------------
# 2. 行为 contract：10 字段 payload + status="ai_draft"
# ---------------------------------------------------------------------------


def test_run_returns_pipeline_outcome_with_card_payload() -> None:
    from mindforge.strategies.default_knowledge_card import (
        build_default_knowledge_card_strategy,
    )
    from mindforge.processors.pipeline import PipelineOutcome

    strat = build_default_knowledge_card_strategy(_strategy_context())
    outcome = strat.run(_doc())
    assert isinstance(outcome, PipelineOutcome)
    assert outcome.card_payload is not None


def test_card_payload_structured_payload_has_exactly_10_contract_keys() -> None:
    """v0.10 Slice 4 起 10 字段 schema 装入 envelope 的 ``structured_payload``。

    Envelope 顶层（strategy_id / strategy_version / schema_version / status /
    source_evidence / structured_payload / review_hints）由
    ``test_card_payload_envelope_contract.py`` 守护；本测试守护
    strategy-specific 的 10 字段 schema 不变（不增不减）。
    """
    from mindforge.strategies.default_knowledge_card import (
        build_default_knowledge_card_strategy,
    )

    strat = build_default_knowledge_card_strategy(_strategy_context())
    outcome = strat.run(_doc())
    assert outcome.card_payload is not None
    structured = outcome.card_payload.get("structured_payload")
    assert isinstance(structured, dict)
    actual_keys = set(structured.keys())
    assert actual_keys == set(CARD_PAYLOAD_KEYS), (
        f"missing: {CARD_PAYLOAD_KEYS - actual_keys}; "
        f"extra: {actual_keys - CARD_PAYLOAD_KEYS}"
    )


def test_status_is_ai_draft() -> None:
    """``status`` 字段必须是常量 ``"ai_draft"`` —— AI 永远不能伪造 human_approved。"""
    from mindforge.strategies.default_knowledge_card import (
        build_default_knowledge_card_strategy,
    )

    strat = build_default_knowledge_card_strategy(_strategy_context())
    outcome = strat.run(_doc())
    assert outcome.card_payload["status"] == "ai_draft"  # type: ignore[index]


# ---------------------------------------------------------------------------
# 3. payload 禁止字段
# ---------------------------------------------------------------------------


def test_payload_does_not_carry_human_approved_fields() -> None:
    """payload 永远不得携带 approval / vault path 字段。"""
    from mindforge.strategies.default_knowledge_card import (
        build_default_knowledge_card_strategy,
    )

    strat = build_default_knowledge_card_strategy(_strategy_context())
    outcome = strat.run(_doc())
    payload = outcome.card_payload or {}
    for forbidden in (
        "human_approved",
        "approved_by",
        "approved_at",
        "obsidian_path",
        "vault_path",
        "workspace_path",
    ):
        assert forbidden not in payload, (
            f"strategy 不得在 payload 中携带 {forbidden!r}"
        )
    # status 也不得是 human_approved（即使写错也要拒掉）
    assert payload.get("status") != "human_approved"


# ---------------------------------------------------------------------------
# 4. 副作用 contract：不开 socket / 不在 repo 根写文件
# ---------------------------------------------------------------------------


def test_run_does_not_open_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindforge.strategies.default_knowledge_card import (
        build_default_knowledge_card_strategy,
    )

    def _no_socket(*a: object, **kw: object) -> object:
        raise AssertionError("strategy.run 不得开 socket")

    monkeypatch.setattr(socket, "socket", _no_socket)
    strat = build_default_knowledge_card_strategy(_strategy_context())
    strat.run(_doc())  # 不应抛 AssertionError


def test_run_does_not_write_repo_root_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """strategy.run 不得在 repo 根（cwd）创建文件。"""
    from mindforge.strategies.default_knowledge_card import (
        build_default_knowledge_card_strategy,
    )

    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    strat = build_default_knowledge_card_strategy(_strategy_context())
    strat.run(_doc())
    after = set(tmp_path.iterdir())
    assert before == after, f"strategy 在 cwd 写入了文件：{after - before}"
