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

from . import concept_extraction as _concept_extraction_mod
from . import action_item as _action_item_mod
from . import default_knowledge_card as _default_knowledge_card_mod
from . import five_stage as _five_stage_mod
from . import knowledge_card as _knowledge_card_mod
from .base import KnowledgeStrategy, StrategyContext
from .concept_extraction import build_concept_extraction_strategy
from .default_knowledge_card import build_default_knowledge_card_strategy
from .five_stage import build_five_stage_strategy

DEFAULT_STRATEGY_NAME = "knowledge_card"
LEGACY_FIVE_STAGE_ALIAS = "five_stage"
INTERNAL_STRATEGY_IDS = frozenset(
    {"default_knowledge_card", "concept_extraction", "action_item"}
)


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


def _format_planned_strategy_message(name: str) -> str:
    """统一拼装 NotYetImplementedStrategyError 的可读消息。

    包含四段：策略名、planned/not-yet-implemented 字面量、可执行替代
    （implemented 状态的 ID 列表）、CLI discovery 入口提示。让用户立刻
    知道"它存在但没做完"且"我可以用这些代替"。

    严格不放 Python repr / stack trace —— 错误消息是用户主界面的一部分，
    不能泄漏内部对象地址或调用栈。
    """

    implemented = tuple(
        m.strategy_id
        for m in list_strategies(include_internal=True)
        if m.status == "implemented" and m.production_ready
    )
    return (
        f"strategy {name!r} is planned (not yet implemented); "
        f"implemented alternatives: {implemented}; "
        "run `mindforge strategies list` to see all strategies."
    )


class UnknownStrategyError(ValueError):
    """请求了未注册的策略名。

    使用结构化异常而不是返回 None，让调用方在静默拿到错误策略前就 crash —
    fake-default 安全路径不允许悄悄回退。
    """


class NotYetImplementedStrategyError(ValueError):
    """请求执行了一个已登记元数据但 ``status="planned"`` 的策略。

    与 :class:`UnknownStrategyError` 严格区分（**不**继承它），目的是让
    上层调用站点能分别处理两种语义：

    - unknown：用户拼错了名字 → 提示拼写正确的可选项；
    - planned：用户拼对了名字，但此策略只是"已登记尚未实现" → 提示
      implemented 替代 + 解释为什么这次不能跑。

    选择继承 :class:`ValueError` 而不是新发明一棵异常树，是为了让既有
    顶层 broad except 仍能 catch；同时保证两个错误类彼此不互为子类，
    防止一个 ``except UnknownStrategyError`` 把 planned 一并吞掉。
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
    - ``output_schema_id``：``<strategy_id>@<envelope_schema_version>``,
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
    role: str = "internal_baseline"
    production_ready: bool = False
    user_recommended: bool = False
    canonical_id: str | None = None
    legacy_aliases: tuple[str, ...] = ()
    warning: str = ""

    @property
    def is_internal(self) -> bool:
        return not self.user_recommended


# 中文学习型注释：``_FACTORIES`` 只登记 *可执行* 策略；planned 策略
# **故意不**出现在这里，从源头上就没有可被偷调用的工厂。这样即便未来
# build_strategy 的 status 守护被破坏，planned 路径也不会回退到默认
# 策略 —— 因为根本不存在 factory。
_FACTORIES: dict[str, Callable[[StrategyContext], KnowledgeStrategy]] = {
    DEFAULT_STRATEGY_NAME: build_five_stage_strategy,
    LEGACY_FIVE_STAGE_ALIAS: build_five_stage_strategy,
    "default_knowledge_card": build_default_knowledge_card_strategy,
    "concept_extraction": build_concept_extraction_strategy,
}


# 中文学习型注释：metadata 不在 registry 里硬编码字符串，而是从各 strategy
# 模块顶层常量按名字映射读取 —— 这样 strategy 模块仍是元数据的"作者"，
# registry 只负责"汇总展示"，避免 registry 变成 prompt / metadata 巨石。
#
# v0.11 Slice 4：``_METADATA_MODULES`` 是策略**注册**的事实来源（包含
# planned 在内的所有可被发现的策略），而 ``_FACTORIES`` 只登记可执行
# 工厂。两者解耦让 planned 策略可以"可见但不可执行"。
_METADATA_MODULES = {
    DEFAULT_STRATEGY_NAME: _knowledge_card_mod,
    LEGACY_FIVE_STAGE_ALIAS: _five_stage_mod,
    "default_knowledge_card": _default_knowledge_card_mod,
    "concept_extraction": _concept_extraction_mod,
    "action_item": _action_item_mod,
}


def available_strategies() -> tuple[str, ...]:
    """已注册策略名的稳定快照（按名字字典序）。

    包含 implemented / preview / planned 全部三态 —— UX 上 planned 策略
    必须能被发现，否则用户根本不知道"它存在但还不能跑"。可执行性由
    :func:`build_strategy` 在调用时根据 ``status`` 守护。
    """

    return tuple(sorted(_METADATA_MODULES))


def build_strategy(name: str, ctx: StrategyContext) -> KnowledgeStrategy:
    """按名字派发策略工厂，并在 ``status="planned"`` 时礼貌拒绝。

    错误分流：

    - **未注册名** → :class:`UnknownStrategyError`，建议拼写正确的可选项；
    - **planned 状态** → :class:`NotYetImplementedStrategyError`，建议
      implemented 替代；
    - **已注册但缺工厂**（防御）→ 同样抛 NotYet，避免 silent KeyError；
    - **正常路径** → 调用工厂返回策略实例。

    任何分支都不读 ``.env``、不调 LLM、不写 workspace。
    """

    name = canonical_strategy_id(name)
    if name not in _METADATA_MODULES:
        raise UnknownStrategyError(_format_unknown_strategy_message(name))
    status = _METADATA_MODULES[name].STRATEGY_STATUS
    if status == "planned":
        raise NotYetImplementedStrategyError(
            _format_planned_strategy_message(name)
        )
    factory = _FACTORIES.get(name)
    if factory is None:
        # 防御分支：metadata 已注册但 _FACTORIES 没有对应项，且 status
        # 不是 planned —— 这是一个内部不一致。仍然拒绝执行而不是回退。
        raise NotYetImplementedStrategyError(
            _format_planned_strategy_message(name)
        )
    return factory(ctx)


def get_strategy_metadata(name: str) -> StrategyMetadata:
    """返回单个策略的 :class:`StrategyMetadata`。

    未知名字复用 :class:`UnknownStrategyError`，保持错误类型与
    :func:`build_strategy` 一致 —— CLI 只需要 catch 一种。
    """

    lookup_name = name
    mod = _METADATA_MODULES.get(lookup_name)
    if mod is None:
        raise UnknownStrategyError(_format_unknown_strategy_message(name))
    canonical_id = getattr(mod, "STRATEGY_CANONICAL_ID", mod.STRATEGY_ID)
    aliases = tuple(getattr(mod, "STRATEGY_LEGACY_ALIASES", ()))
    return StrategyMetadata(
        strategy_id=mod.STRATEGY_ID,
        strategy_version=mod.STRATEGY_VERSION,
        display_name=mod.STRATEGY_DISPLAY_NAME,
        description=mod.STRATEGY_DESCRIPTION,
        provider_mode=mod.STRATEGY_PROVIDER_MODE,
        safety_policy=mod.STRATEGY_SAFETY_POLICY,
        output_schema_id=mod.STRATEGY_OUTPUT_SCHEMA_ID,
        status=mod.STRATEGY_STATUS,
        role=getattr(mod, "STRATEGY_ROLE", _default_role(mod.STRATEGY_ID, mod.STRATEGY_STATUS)),
        production_ready=bool(getattr(mod, "STRATEGY_PRODUCTION_READY", False)),
        user_recommended=bool(getattr(mod, "STRATEGY_USER_RECOMMENDED", False)),
        canonical_id=str(canonical_id),
        legacy_aliases=aliases,
        warning=str(getattr(mod, "STRATEGY_WARNING", "")),
    )


def list_strategies(*, include_internal: bool = True) -> tuple[StrategyMetadata, ...]:
    """所有内建策略的元数据元组（顺序与 :func:`available_strategies` 一致）。

    这是 CLI ``strategies list`` 的数据源；纯查询，无副作用 —— 不会触发
    LLM、不会读 ``.env``、不会写 workspace。
    """

    metas = tuple(get_strategy_metadata(name) for name in available_strategies())
    if include_internal:
        return metas
    return tuple(m for m in metas if m.user_recommended and m.strategy_id == m.canonical_id)


def public_strategies() -> tuple[StrategyMetadata, ...]:
    """普通用户可见 strategy 列表。

    中文学习型说明：测试替身可以存在于 registry 中，但默认 discovery 不能把
    它们包装成产品能力。CLI/Web 默认只消费这个 public view。
    """

    return list_strategies(include_internal=False)


def canonical_strategy_id(name: str) -> str:
    """把 legacy/internal alias 规范化成可落盘的 canonical id。"""

    text = str(name or "").strip()
    if text == LEGACY_FIVE_STAGE_ALIAS:
        return DEFAULT_STRATEGY_NAME
    return text


def _default_role(strategy_id: str, status: str) -> str:
    if status == "planned":
        return "planned"
    if strategy_id == "concept_extraction":
        return "preview_internal"
    return "internal_baseline"
