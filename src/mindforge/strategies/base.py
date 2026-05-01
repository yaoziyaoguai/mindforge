"""KnowledgeStrategy Protocol 与 StrategyContext。

设计要点（学习型说明）
======================

为什么用 ``typing.Protocol`` 而不是 ABC？
-----------------------------------------

现有 ``processors.pipeline.Pipeline`` 已经有 ``run(doc) -> PipelineOutcome``
方法。如果改成继承 ABC，会强制修改 ``Pipeline`` 类签名 —— 这违反"不重写
现有模块"的原则，且会污染 ``Pipeline`` 的独立性。

``Protocol`` 是 PEP 544 的 structural typing：``Pipeline`` 不需要任何修改
即被识别为 ``KnowledgeStrategy`` 的实现。这正是"补 seam，不重写"的范式。

为什么把 logger 设为可变字段？
------------------------------

CLI 在构造 ``Pipeline`` 时传入 ``logger=None``，然后在 ``with RunLogger(...)``
作用域内对实例属性 ``pipeline.logger = logger`` 赋值。这是 v0.7.x 之前就
有的契约，本 seam 必须保持兼容，因此 Protocol 显式声明 ``logger`` 为可变
属性。

为什么 StrategyContext 不强制所有字段？
---------------------------------------

第一版只覆盖 five_stage 策略的实际依赖。未来策略若需要额外材料（如
template 引用、source-specific config），可以以新可选字段加入；不影响
已有调用方。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover - 仅静态类型；运行时不导入避免循环依赖
    from ..llm import LLMClient
    from ..processors.pipeline import PipelineOutcome
    from ..run_logger import RunLogger
    from ..sources.base import SourceDocument


@dataclass
class StrategyContext:
    """策略工厂所需的运行时材料。

    字段语义与 ``Pipeline.__init__`` 一一对应，但是把"策略选择"与"策略
    构造材料"显式分离 —— 调用方组装一次 context，可被多个策略工厂消费。
    """

    client: "LLMClient"
    prompts_dir: Any
    prompt_versions: Any
    triage_threshold: int
    learning_tracks_text: str
    logger: "RunLogger | None" = None


@runtime_checkable
class KnowledgeStrategy(Protocol):
    """ai_draft 生成策略的最小契约。

    任何策略实现只需提供 ``run(doc)`` 与可写的 ``logger`` 字段即可。
    现有 ``processors.pipeline.Pipeline`` 已结构性满足；新策略可以是任何
    形状，只要保持同一输入面（``SourceDocument``）与同一输出面
    （``PipelineOutcome``）。
    """

    logger: "RunLogger | None"

    def run(self, doc: "SourceDocument") -> "PipelineOutcome": ...
