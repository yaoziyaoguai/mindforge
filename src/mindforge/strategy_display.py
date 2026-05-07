"""Strategy/provider display labels for product surfaces.

中文学习型说明：frontmatter 必须保留原始 strategy_id 以兼容旧卡，但 Web/CLI
普通产品表面不应把 ``five_stage``、``default_knowledge_card`` 这类内部实现名
直接当产品概念展示。这里集中做只读 label 映射，避免 UI 各处复制字符串判断。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyDisplay:
    label: str
    raw_id: str | None
    canonical_id: str | None
    note: str | None = None
    is_internal: bool = False
    is_legacy: bool = False


def strategy_display(raw_strategy_id: str | None) -> StrategyDisplay:
    sid = (raw_strategy_id or "").strip() or None
    if sid in {None, "", "knowledge_card", "five_stage"}:
        return StrategyDisplay(
            label="Knowledge Card Workflow",
            raw_id=sid,
            canonical_id="knowledge_card",
            note="legacy id: five_stage" if sid == "five_stage" else None,
            is_legacy=sid == "five_stage",
        )
    if sid == "default_knowledge_card":
        return StrategyDisplay(
            label="Internal/Test card",
            raw_id=sid,
            canonical_id=sid,
            note=(
                "Internal deterministic baseline; does not exercise the production "
                "prompt pipeline."
            ),
            is_internal=True,
        )
    if sid == "concept_extraction":
        return StrategyDisplay(
            label="Internal preview card",
            raw_id=sid,
            canonical_id=sid,
            note="Internal preview baseline; not a production extraction strategy.",
            is_internal=True,
        )
    return StrategyDisplay(label=sid, raw_id=sid, canonical_id=sid)


def provider_display_note(profile: str | None, provider: str | None) -> str | None:
    label = f"{profile or ''} {provider or ''}".lower()
    if "fake" in label:
        return "offline LLM test double; not a product provider"
    return None


__all__ = ["StrategyDisplay", "provider_display_note", "strategy_display"]
