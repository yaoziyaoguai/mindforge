"""策略名 → 工厂的派发 registry。

为什么不在 ``configs/mindforge.yaml`` 立即增加 ``processing.strategy`` 字段？
==========================================================================

Phase 1 的 first cut 只引入 seam，不引入用户可见 config schema 变化。
当下只有一种策略 ``"five_stage"``，让 CLI 直接传入这个常量即可。当
未来新增策略且确认要让用户选择时，再在 config 层补字段并把它接入
:func:`build_strategy` —— 调用方代码无需调整。

这种"先用代码常量、后用 config 字段"的做法避免了"为了 seam 而提前膨胀
config schema"的过度设计。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import default_knowledge_card as _default_knowledge_card_mod
from . import concept_extraction as _concept_extraction_mod
from . import five_stage as _five_stage_mod
from .base import KnowledgeStrategy, StrategyContext
from .concept_extraction import build_concept_extraction_strategy
from .default_knowledge_card import build_default_knowledge_card_strategy
from .five_stage import build_five_stage_strategy

DEFAULT_STRATEGY_NAME = "five_stage"


def _format_unknown_strategy_message(name: str) -> str:
    """统一拼装 UnknownStrategyError 的可读消息。

    包含三段：未知名字、可选项元组、CLI discovery 入口提示
    （``mindforge strategies list``）—— 让终端用户立即拿到下一步动作。
    """

    return (
        f"unknown knowledge strategy: {name!r}; "
        f"available: {available_strategies()}; "
        "run `mindforge strategies list` to see all strategies."
    )


class UnknownStrategyError(ValueError):
    """请求了未注册的策略名。

    使用结构化异常而不是返回 None，让调用方在静默拿到错误策略前就 crash —
    fake-default 安全路径不允许悄悄回退。
    """


@dataclass(frozen=True)
class StrategyMetadata:
    """策略自描述元数据。

    本 dataclass 是 v0.11 StrategyRegistry 的"用户可见面"统一类型：
    CLI ``strategies list`` / 文档生成 / 未来 v0.12 custom strategy 都
    通过同一形状消费，避免每个消费方各自从字符串字面量去拼。

    frozen 防止调用方事后篡改，确保元数据是 strategy 模块定义的
    单一事实来源。

    UX 三字段（v0.11 Slice 2 引入）：

    - ``provider_mode``：``fake_only`` / ``deterministic`` / ``real_opt_in``，
      告诉用户该策略默认是否离线安全；
    - ``safety_policy``：固定为 ``ai_draft_only`` —— 与项目"不自动 approve"
      硬约束对齐；
    - ``output_schema_id``：``<strategy_id>@<envelope_schema_version>``，
      让消费方一眼看到 envelope schema 标识。

    生命周期字段（v0.11 Slice 3 引入）：

    - ``status``：``implemented`` / ``preview`` / ``planned`` 三态，让
      multi-strategy discovery UX 直接告诉用户某策略当前是"生产可用"、
      "可跑但语义在演化"、还是"仅登记元数据未实现"。Slice 4 将基于该
      字段在执行边界做 planned strategy guard。
    """

    strategy_id: str
    strategy_version: str
    display_name: str
    description: str
    provider_mode: str
    safety_policy: str
    output_schema_id: str
    status: str


_FACTORIES: dict[str, Callable[[StrategyContext], KnowledgeStrategy]] = {
    DEFAULT_STRATEGY_NAME: build_five_stage_strategy,
    "default_knowledge_card": build_default_knowledge_card_strategy,
    "concept_extraction": build_concept_extraction_strategy,
}


# 中文学习型注释：metadata 不在 registry 里硬编码字符串，而是从各 strategy
# 模块顶层常量按名字映射读取 —— 这样 strategy 模块仍是元数据的"作者"，
# registry 只负责"汇总展示"，避免 registry 变成 prompt / metadata 巨石。
_METADATA_MODULES = {
    DEFAULT_STRATEGY_NAME: _five_stage_mod,
    "default_knowledge_card": _default_knowledge_card_mod,
    "concept_extraction": _concept_extraction_mod,
}


def available_strategies() -> tuple[str, ...]:
    """已注册策略名的稳定快照（按名字字典序）。"""

    return tuple(sorted(_FACTORIES))


def build_strategy(name: str, ctx: StrategyContext) -> KnowledgeStrategy:
    """按名字派发策略工厂。

    未知名字会抛 :class:`UnknownStrategyError`，由调用方决定如何向用户
    呈现 —— registry 不做 console 输出。
    """

    factory = _FACTORIES.get(name)
    if factory is None:
        raise UnknownStrategyError(_format_unknown_strategy_message(name))
    return factory(ctx)


def get_strategy_metadata(name: str) -> StrategyMetadata:
    """返回单个策略的 :class:`StrategyMetadata`。

    未知名字复用 :class:`UnknownStrategyError`，保持错误类型与
    :func:`build_strategy` 一致 —— CLI 只需要 catch 一种。
    """

    mod = _METADATA_MODULES.get(name)
    if mod is None:
        raise UnknownStrategyError(_format_unknown_strategy_message(name))
    return StrategyMetadata(
        strategy_id=mod.STRATEGY_ID,
        strategy_version=mod.STRATEGY_VERSION,
        display_name=mod.STRATEGY_DISPLAY_NAME,
        description=mod.STRATEGY_DESCRIPTION,
        provider_mode=mod.STRATEGY_PROVIDER_MODE,
        safety_policy=mod.STRATEGY_SAFETY_POLICY,
        output_schema_id=mod.STRATEGY_OUTPUT_SCHEMA_ID,
        status=mod.STRATEGY_STATUS,
    )


def list_strategies() -> tuple[StrategyMetadata, ...]:
    """所有内建策略的元数据元组（顺序与 :func:`available_strategies` 一致）。

    这是 CLI ``strategies list`` 的数据源；纯查询，无副作用 —— 不会触发
    LLM、不会读 ``.env``、不会写 workspace。
    """

    return tuple(get_strategy_metadata(name) for name in available_strategies())
