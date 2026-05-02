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

from .base import KnowledgeStrategy, StrategyContext
from .default_knowledge_card import build_default_knowledge_card_strategy
from .five_stage import build_five_stage_strategy

DEFAULT_STRATEGY_NAME = "five_stage"


class UnknownStrategyError(ValueError):
    """请求了未注册的策略名。

    使用结构化异常而不是返回 None，让调用方在静默拿到错误策略前就 crash —
    fake-default 安全路径不允许悄悄回退。
    """


_FACTORIES: dict[str, Callable[[StrategyContext], KnowledgeStrategy]] = {
    DEFAULT_STRATEGY_NAME: build_five_stage_strategy,
    "default_knowledge_card": build_default_knowledge_card_strategy,
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
        raise UnknownStrategyError(
            f"unknown knowledge strategy: {name!r}; "
            f"available: {available_strategies()}"
        )
    return factory(ctx)
