"""Cubox dry-run summary presenter — 纯展示层。

职责边界（高内聚 / 低耦合 / Information Hiding）
------------------------------------------------

只做两件事：

1. 把 ``DryRunSummary`` 渲染成 **human-readable** 文本（Rich 风格但不依赖
   Rich，避免新依赖）；
2. 把同一 ``DryRunSummary`` 序列化成 **machine-readable** JSON 一行。

明确**不**承担：

- 解析 Cubox export（属于 ``CuboxApiAdapter.parse_export``）；
- 跨源去重（属于 ``SourceMux``）；
- knowledge generation / approval / vault 写入（与 dry-run 无关）；
- 读取 ``.env`` / 调用 LLM / 联网 / 调真实 Cubox API（dry-run 安全边界）；
- 暴露 token / 全文 body / 完整 url —— summary 严格只输出 sample title 与
  source_id 简短前缀，正文与凭据永远不进入展示层。

这条边界由 ``test_presenter_module_exists_and_has_no_forbidden_imports``
和 ``test_cubox_dry_run_summary_does_not_leak_token_or_body`` 守护。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class DryRunSampleItem:
    """sample 中的单条目，只暴露 title 与 source_id 简短前缀。"""

    title: str
    source_id_short: str


@dataclass(frozen=True)
class DryRunSummary:
    """Cubox dry-run 的可观测汇总，绝不携带 raw body / url / token。"""

    items_seen: int = 0
    yielded: int = 0
    deduped: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    sample: list[DryRunSampleItem] = field(default_factory=list)


def render_text(summary: DryRunSummary) -> str:
    """渲染人类可读 summary。"""

    lines = [
        "Cubox dry-run summary",
        f"  items_seen : {summary.items_seen}",
        f"  yielded    : {summary.yielded}",
        f"  deduped    : {summary.deduped}",
    ]
    if summary.by_source:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(summary.by_source.items()))
        lines.append(f"  by_source  : {parts}")
    else:
        lines.append("  by_source  : (none)")
    if summary.sample:
        lines.append("  sample:")
        for item in summary.sample:
            lines.append(f"    - {item.source_id_short}  {item.title}")
    return "\n".join(lines)


def render_json(summary: DryRunSummary) -> str:
    """渲染机器可读 JSON 一行。"""

    payload = asdict(summary)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


__all__ = ["DryRunSampleItem", "DryRunSummary", "render_text", "render_json"]
