"""v0.10 Slice 5 TDD Red — five_stage envelope migration + writer/presenter compat.

设计意图（中文学习型）
======================

Slice 4 让 ``DefaultKnowledgeCardStrategy`` 输出公共 envelope，但
``five_stage`` 仍输出旧 ``{"card": {...}}`` 平坦结构，并且 ``CardWriter``
仍直接读 ``payload["card"]["track"]``。这意味着只要 default 策略真的
被 writer 消费，就会 KeyError；Slice 3 只能用 ``--dry-run`` 规避。

Slice 5 的目标是把 envelope 契约延伸到 writer/presenter 边界，让两条
策略共享同一个 envelope，并让 presenter 即便面对未知 strategy 也能给
出安全 preview。完成 Slice 5 后才允许进入 v0.11 StrategyRegistry。

为什么 Slice 5 只做 Red、不做 Green
-----------------------------------

- five_stage 真正迁移涉及 ``_build_card_payload``（pipeline.py）+ writer
  envelope 适配 + presenter 渲染；任一处先动都会破坏端到端 fake
  provider e2e 测试（``tests/test_phase1_cubox_e2e.py``）。先用 Red 把
  契约钉住，再让 Green 一次性拉齐。
- ``_build_card_payload`` 是纯函数，可以用合成 stage outputs 测试，无
  需 LLM。CardWriter 同样可以用合成 envelope 测试。Presenter helper
  尚不存在 —— Slice 5 Green 才创建。

Red 失败原因预期
----------------

1. ``_build_card_payload`` 仍返回 ``{"card": {...}}``，不含 envelope
   顶层字段；
2. ``CardWriter.write`` 直接读 ``payload["card"]["track"]``，envelope-
   shape 输入会 KeyError；
3. ``mindforge.envelope`` 模块尚不存在，``render_envelope_preview``
   helper 还没引入。

边界
====

不实现 envelope 迁移；不动 ``_build_card_payload`` / ``CardWriter`` /
``cli.py`` / ``processors/pipeline.py`` 生产代码；不创建 envelope
presenter；不调真实 LLM；不读 .env；不写 vault；不晋升已审核状态；
不实现 StrategyRegistry / custom strategy。
"""

from __future__ import annotations

from typing import Any

import pytest

from mindforge.processors.pipeline import _build_card_payload
from mindforge.sources.base import SourceDocument, compute_content_hash


# ---------------------------------------------------------------------------
# 公共信封必填字段（与 Slice 4 envelope contract 对齐）
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


def _doc(text: str = "Title: Slice 5\n\nFive stage envelope sample.") -> SourceDocument:
    return SourceDocument(
        source_id="id:slice5-fivestage-1",
        source_type="plain_markdown",
        source_path="/tmp/slice5-fivestage.md",
        title="five_stage envelope contract",
        raw_text=text,
        content_hash=compute_content_hash(text),
        adapter_name="PlainMarkdownAdapter",
        tags=["envelope"],
    )


def _stage_outputs() -> dict[str, dict[str, Any]]:
    """合成五段 stage outputs，模拟 Pipeline 在 fake provider 下的产物。

    字段名/类型与 ``Pipeline`` 内部对 ``distill`` / ``link_suggestion`` /
    ``review_questions`` / ``action_extraction`` 的消费契约一致。
    """

    distill = {
        "slug": "slice5-fivestage",
        "title": "Slice 5 Five Stage",
        "tags": ["envelope"],
        "confidence": 0.5,
        "source_excerpt": "Five stage envelope sample.",
        "ai_summary_bullets": ["bullet"],
        "ai_inference_bullets": [],
        "reusable_prompts_or_principles": [],
    }
    return {
        "distill": distill,
        "link_suggestion": {"project_hooks": [], "suggested_links": []},
        "review_questions": {"review_questions": []},
        "action_extraction": {"action_items": []},
    }


# ---------------------------------------------------------------------------
# 1. five_stage envelope migration
# ---------------------------------------------------------------------------


def test_five_stage_build_card_payload_emits_envelope() -> None:
    """``_build_card_payload`` 必须输出公共 envelope 而非 ``{"card": {...}}``。

    Red 原因：当前实现直接返回 ``{"card": {...17 字段...}}``，缺
    envelope 顶层契约。
    """
    stages = _stage_outputs()
    payload = _build_card_payload(
        doc=_doc(),
        track="learning",
        value_score=80,
        distill=stages["distill"],
        link_suggestion=stages["link_suggestion"],
        review_questions=stages["review_questions"],
        action_extraction=stages["action_extraction"],
    )
    missing = ENVELOPE_REQUIRED_KEYS - set(payload.keys())
    assert not missing, (
        f"five_stage payload 缺 envelope 字段：{sorted(missing)}\n"
        f"实际 keys：{sorted(payload.keys())}"
    )


def test_five_stage_envelope_strategy_identity() -> None:
    """envelope 必须标注用户可见 canonical ``strategy_id == "knowledge_card"``。"""
    stages = _stage_outputs()
    payload = _build_card_payload(
        doc=_doc(),
        track="learning",
        value_score=80,
        distill=stages["distill"],
        link_suggestion=stages["link_suggestion"],
        review_questions=stages["review_questions"],
        action_extraction=stages["action_extraction"],
    )
    assert payload.get("strategy_id") == "knowledge_card"
    sv = payload.get("strategy_version")
    assert isinstance(sv, str) and sv


def test_five_stage_envelope_status_is_ai_draft() -> None:
    """envelope.status == "ai_draft" —— Strategy 永不能伪造已审核状态。"""
    stages = _stage_outputs()
    payload = _build_card_payload(
        doc=_doc(),
        track="learning",
        value_score=80,
        distill=stages["distill"],
        link_suggestion=stages["link_suggestion"],
        review_questions=stages["review_questions"],
        action_extraction=stages["action_extraction"],
    )
    assert payload.get("status") == "ai_draft"


def test_five_stage_envelope_structured_payload_carries_card() -> None:
    """五段产物必须装入 ``structured_payload.card``，对外保持稳定路径。

    writer 在 Slice 5 Green 后从 ``structured_payload.card.{track,id}``
    读路径信息；structured_payload 内部 schema 由 strategy 自治。
    """
    stages = _stage_outputs()
    payload = _build_card_payload(
        doc=_doc(),
        track="learning",
        value_score=80,
        distill=stages["distill"],
        link_suggestion=stages["link_suggestion"],
        review_questions=stages["review_questions"],
        action_extraction=stages["action_extraction"],
    )
    structured = payload.get("structured_payload")
    assert isinstance(structured, dict)
    card = structured.get("card")
    assert isinstance(card, dict)
    assert card.get("track") == "learning"
    assert card.get("id") == "slice5-fivestage"


def test_five_stage_envelope_review_hints_present() -> None:
    """``review_hints.title`` 与 ``review_hints.one_line`` 用于 presenter 安全 fallback。"""
    stages = _stage_outputs()
    payload = _build_card_payload(
        doc=_doc(),
        track="learning",
        value_score=80,
        distill=stages["distill"],
        link_suggestion=stages["link_suggestion"],
        review_questions=stages["review_questions"],
        action_extraction=stages["action_extraction"],
    )
    hints = payload.get("review_hints")
    assert isinstance(hints, dict)
    assert "title" in hints
    assert "one_line" in hints


def test_five_stage_envelope_source_evidence_dict() -> None:
    """envelope.source_evidence 必须是 dict，包含 source_id 与 content_hash。"""
    stages = _stage_outputs()
    payload = _build_card_payload(
        doc=_doc(),
        track="learning",
        value_score=80,
        distill=stages["distill"],
        link_suggestion=stages["link_suggestion"],
        review_questions=stages["review_questions"],
        action_extraction=stages["action_extraction"],
    )
    evidence = payload.get("source_evidence")
    assert isinstance(evidence, dict)
    for key in ("source_id", "content_hash"):
        assert key in evidence


# ---------------------------------------------------------------------------
# 2. CardWriter envelope compatibility
# ---------------------------------------------------------------------------


def _make_envelope_payload() -> dict[str, Any]:
    """合成一个 Slice 4 envelope-shaped payload，供 writer 测试。

    五段卡片字段全部装在 structured_payload.card 内 —— writer 只应通过
    envelope 读取 track/id/template fields，不应直接读 envelope 顶层
    strategy-specific keys。
    """

    return {
        "strategy_id": "five_stage",
        "strategy_version": "0.10.0",
        "schema_version": "1",
        "status": "ai_draft",
        "source_evidence": {
            "source_id": "id:slice5-writer",
            "content_hash": "sha256:deadbeef",
        },
        "structured_payload": {
            "card": {
                "id": "slice5-writer",
                "title": "Slice 5 Writer",
                "track": "learning",
                "tags": [],
                "value_score": 80,
                "confidence": 0.5,
                "source_excerpt": "",
                "ai_summary_bullets": [],
                "ai_inference_bullets": [],
                "reusable_prompts_or_principles": [],
                "project_hooks": [],
                "review_questions": [],
                "action_items": [],
                "suggested_links": [],
                "projects": [],
            },
        },
        "review_hints": {"title": "Slice 5 Writer", "one_line": ""},
    }


def test_card_writer_accepts_envelope_payload(tmp_path) -> None:
    """``CardWriter.write`` 必须接受 envelope-shaped payload。

    Red 原因：当前实现直接 ``card_payload["card"]["track"]``，对
    envelope 输入会 KeyError('card')。Slice 5 Green 必须让 writer 通
    过 envelope 通道读取 strategy-specific card 字段。
    """
    from mindforge.writer import CardWriter

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "cards").mkdir()
    template_text = "{{ card.title }}\n{{ card.id }}\n{{ card.track }}\n"
    writer = CardWriter(
        vault_root=vault,
        cards_dir="cards",
        template_text=template_text,
    )
    payload = _make_envelope_payload()
    # 不应抛 KeyError；应能定位到 vault/cards/learning/<date>--slice5-writer.md
    result = writer.write(
        card_payload=payload,
        source={"source_id": "id:slice5-writer", "title": "Slice 5 Writer"},
        run={"run_id": "test-run", "started_at": "2026-01-01T00:00:00Z"},
    )
    assert result.path.name.endswith("slice5-writer.md")
    assert "learning" in str(result.path)


def test_card_writer_does_not_read_envelope_top_level_strategy_keys() -> None:
    """writer 模块源码不应读取 strategy-specific keys（除 ``structured_payload`` 外）。

    防止 writer 演化为多策略巨石：writer 只能消费 envelope 的
    structured_payload + 公共 routing keys，不能 hard-code "if
    strategy_id == X" 分发。本测试以源码扫描代替运行时断言（运行时
    分支不易枚举）。
    """
    from pathlib import Path as _P

    src = (_P(__file__).resolve().parent.parent / "src" / "mindforge" / "writer.py").read_text("utf-8")
    forbidden_substrings = (
        'strategy_id ==',
        'card_payload["strategy_id"]',
        "card_payload['strategy_id']",
    )
    leaks = [s for s in forbidden_substrings if s in src]
    assert not leaks, f"writer.py 不应包含 strategy 分发：{leaks}"


# ---------------------------------------------------------------------------
# 3. Presenter unknown-strategy fallback
# ---------------------------------------------------------------------------


def test_envelope_render_helper_exists() -> None:
    """v0.10 Slice 5 Green 必须提供 ``mindforge.envelope.render_envelope_preview``。

    Red 原因：模块尚不存在。Slice 5 Green 引入纯函数 helper，让
    presenter / CLI 可以对 default / five_stage / unknown 三类
    envelope 给出统一安全 preview，而不是各 presenter 各自分发。

    设计意图：helper 只读 ``review_hints`` + ``strategy_id``，对
    structured_payload 内部结构不做假设 —— 这是"未知 strategy 也能安
    全 preview"契约的根基。
    """
    try:
        from mindforge.envelope import render_envelope_preview  # type: ignore[attr-defined]
    except ImportError:
        pytest.fail(
            "mindforge.envelope.render_envelope_preview 尚未实现；"
            "Slice 5 Green 应引入此 helper"
        )
    assert callable(render_envelope_preview)


def test_envelope_render_preview_handles_unknown_strategy() -> None:
    """未知 strategy_id 也必须返回可读 preview，不抛异常。"""
    try:
        from mindforge.envelope import render_envelope_preview  # type: ignore[attr-defined]
    except ImportError:
        pytest.fail(
            "mindforge.envelope.render_envelope_preview 尚未实现"
        )
    envelope = {
        "strategy_id": "user_custom_strategy_xyz",
        "strategy_version": "0.0.1",
        "schema_version": "1",
        "status": "ai_draft",
        "source_evidence": {"source_id": "id:x", "content_hash": "sha256:0"},
        "structured_payload": {"opaque_field_unknown_to_us": [1, 2, 3]},
        "review_hints": {"title": "Custom Title", "one_line": "Custom one line."},
    }
    preview = render_envelope_preview(envelope)
    assert isinstance(preview, str)
    assert "Custom Title" in preview
    assert "user_custom_strategy_xyz" in preview


def test_envelope_render_preview_does_not_leak_human_approved_status() -> None:
    """preview helper 必须把 status 原样展示，不能伪装成已审核状态。

    helper 只读 envelope.status，不做任何状态转换；这条契约防止
    presenter 在 preview 渲染时无意中"看起来像已审核"误导用户。
    """
    try:
        from mindforge.envelope import render_envelope_preview  # type: ignore[attr-defined]
    except ImportError:
        pytest.fail("mindforge.envelope.render_envelope_preview 尚未实现")
    envelope = {
        "strategy_id": "default_knowledge_card",
        "strategy_version": "0.10.0",
        "schema_version": "1",
        "status": "ai_draft",
        "source_evidence": {"source_id": "id:y", "content_hash": "sha256:0"},
        "structured_payload": {"title": "T", "one_sentence_summary": "S"},
        "review_hints": {"title": "T", "one_line": "S"},
    }
    preview = render_envelope_preview(envelope)
    assert "ai_draft" in preview


# ---------------------------------------------------------------------------
# 4. process_service envelope passthrough (Green baseline)
# ---------------------------------------------------------------------------


def test_process_service_preserves_envelope_passthrough() -> None:
    """``ProcessItemResult.card_payload`` 必须把 strategy 的 envelope 原样透传。

    这条契约防止 ``process_service`` 在 envelope 迁移过程中悄悄变成
    "重新拼装 dict 的垃圾桶"。process_service 的职责是 use-case 编排，
    不是 schema 翻译；任何字段重塑都会让 writer/presenter 必须再次理
    解 process_service 的中间形态，违反 Information Hiding。

    本测试通过源码扫描守护：``process_service.py`` 不应 ``card_payload=``
    某个新构造的 dict（除直接传 ``outcome.card_payload``）。当前 Green
    baseline 通过；将来若有人把 envelope 拆开重组，本测试立即报警。
    """
    from pathlib import Path as _P

    src = (_P(__file__).resolve().parent.parent / "src" / "mindforge" / "process_service.py").read_text("utf-8")
    forbidden = (
        'card_payload={"',
        "card_payload={'",
        'card_payload=dict(',
    )
    leaks = [s for s in forbidden if s in src]
    assert not leaks, f"process_service 不应重塑 card_payload：{leaks}"
    # 必须存在 outcome.card_payload 透传形式
    assert "card_payload=outcome.card_payload" in src, (
        "process_service 必须保留 outcome.card_payload 透传契约"
    )
