"""公共 envelope 工具 —— v0.10 Slice 5 引入。

为什么需要独立 envelope 模块
============================

v0.10 Slice 4/5 把所有 strategy 的 ``PipelineOutcome.card_payload`` 统
一为公共 envelope（``strategy_id`` / ``strategy_version`` /
``schema_version`` / ``status`` / ``source_evidence`` /
``structured_payload`` / ``review_hints``）。

写入侧（``CardWriter``）通过 ``structured_payload.card`` 读取 strategy-
specific 字段；展示侧（presenter / CLI preview）需要一个**仅依赖
envelope 公共字段**的渲染入口，否则每个 presenter 都会被迫"认识每种
strategy 的 structured_payload 内部结构"，迅速演化为多策略巨石。

本模块只暴露最小一个纯函数 ``render_envelope_preview``：

- 仅读 ``review_hints.title`` / ``review_hints.one_line`` /
  ``strategy_id`` / ``status``；
- 不读 ``structured_payload`` 内部任何字段；
- 不接触 IO、provider、approver、CardWriter；
- 对未知 ``strategy_id`` / 缺字段都给出可读 fallback，不抛异常 ——
  这是"自定义策略也能安全 preview"契约的根基。

边界
====

- 不修改 envelope；不晋升 ``status``；不接收 approval action；不写文件。
- 不依赖 LLM / .env / Cubox / Obsidian。
- 不感知 strategy 数量（registry-agnostic）—— 任何新策略只要产出公共
  envelope 即可被本 helper 渲染。
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = ["render_envelope_preview"]


def _safe_str(value: Any, *, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def render_envelope_preview(envelope: Mapping[str, Any]) -> str:
    """渲染任意公共 envelope 的安全 preview 文本。

    输出形式（保持稳定，便于上层 presenter 嵌入）::

        [<status>] <title>
        strategy: <strategy_id>@<strategy_version>
        <one_line>

    设计要点：

    - ``status`` 原样展示，不做语义转换 —— 即便上游策略错误地把
      ``status`` 填成非标准值，preview 也只是显示，不伪造已审核状态；
    - ``review_hints`` 字段缺失时回落到 ``"<no title>"`` /
      ``"<no summary>"``，不抛异常；
    - 未知 ``strategy_id`` 也直接展示，让用户立刻看到"这是哪种策略产
      出的 ai_draft"，而不是隐藏在堆栈里。
    """

    if not isinstance(envelope, Mapping):
        raise TypeError("envelope 必须是 Mapping（dict 形态的公共信封）")

    status = _safe_str(envelope.get("status"), fallback="unknown")
    strategy_id = _safe_str(envelope.get("strategy_id"), fallback="unknown_strategy")
    strategy_version = _safe_str(envelope.get("strategy_version"), fallback="unknown")

    hints = envelope.get("review_hints")
    if isinstance(hints, Mapping):
        title = _safe_str(hints.get("title"), fallback="<no title>")
        one_line = _safe_str(hints.get("one_line"), fallback="<no summary>")
    else:
        title = "<no title>"
        one_line = "<no summary>"

    return (
        f"[{status}] {title}\n"
        f"strategy: {strategy_id}@{strategy_version}\n"
        f"{one_line}"
    )
