"""Cubox preview-ai-draft summary presenter — 纯展示层。

职责边界（高内聚 / 低耦合 / Information Hiding）
------------------------------------------------

只做两件事：

1. 把 ``AiDraftPreviewSummary`` 渲染成人类可读文本；
2. 把同一 summary 序列化成 machine-readable JSON 一行。

明确**不**承担：

- 调用 ``Pipeline`` / ``KnowledgeStrategy`` / 任何 LLM provider；
- approval / review / vault 写入；
- 读取 ``.env`` / 联网 / 调真实 Cubox API；
- 暴露 ai_draft 正文（``card_payload``）、token、author、url —— summary 只
  暴露 title / source_id 简短前缀 / status / track / value_score /
  ``has_card_payload`` 这些观测字段；正文与凭据**永远**不进入展示层。

边界由 ``test_preview_presenter_module_exists_and_has_no_forbidden_imports``
和 ``test_preview_does_not_print_card_body`` 守护。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class AiDraftPreviewItem:
    """单条 ai_draft 预览的可观测投影。

    字段约束：
    - ``card_payload`` 正文**不**进入此结构；只有 ``has_card_payload`` 布尔；
    - 不携带 raw_text / source_url / author / token。
    """

    title: str
    source_id_short: str
    status: str
    track: str | None = None
    value_score: int | None = None
    has_card_payload: bool = False
    skip_reason: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class AiDraftPreviewSummary:
    """Cubox preview-ai-draft 的可观测汇总。"""

    items_seen: int = 0
    yielded: int = 0
    deduped: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    outcomes: list[AiDraftPreviewItem] = field(default_factory=list)


def render_text(summary: AiDraftPreviewSummary) -> str:
    """渲染人类可读 summary。"""

    lines = [
        "Cubox ai_draft preview summary (fake provider, in-memory only)",
        f"  items_seen : {summary.items_seen}",
        f"  yielded    : {summary.yielded}",
        f"  deduped    : {summary.deduped}",
    ]
    if summary.by_status:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(summary.by_status.items()))
        lines.append(f"  by_status  : {parts}")
    else:
        lines.append("  by_status  : (none)")
    if summary.outcomes:
        lines.append("  outcomes:")
        for it in summary.outcomes:
            extras = []
            if it.track is not None:
                extras.append(f"track={it.track}")
            if it.value_score is not None:
                extras.append(f"score={it.value_score}")
            if it.has_card_payload:
                extras.append("card=yes")
            if it.skip_reason:
                extras.append(f"skip={it.skip_reason}")
            if it.error_message:
                extras.append(f"err={it.error_message}")
            tail = ("  " + " ".join(extras)) if extras else ""
            lines.append(
                f"    - [{it.status}] {it.source_id_short}  {it.title}{tail}"
            )
    return "\n".join(lines)


def render_json(summary: AiDraftPreviewSummary) -> str:
    """渲染机器可读 JSON 一行。"""

    return json.dumps(asdict(summary), ensure_ascii=False, sort_keys=True)


__all__ = [
    "AiDraftPreviewItem",
    "AiDraftPreviewSummary",
    "render_text",
    "render_json",
]
