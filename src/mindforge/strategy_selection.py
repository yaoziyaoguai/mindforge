"""Runtime strategy selection helpers.

中文学习型说明：strategy selection 与 provider selection 必须分离。
provider 负责“调用哪个模型/endpoint”，strategy 负责“如何抽取知识并组织
card envelope”。把这层放在独立 helper 中，import/process/watch/Web 都能复用
同一条规则，避免三个 CLI adapter 各写一套优先级和错误文案。
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import MindForgeConfig
from .strategies import (
    DEFAULT_STRATEGY_NAME,
    NotYetImplementedStrategyError,
    UnknownStrategyError,
    available_strategies,
    canonical_strategy_id,
    get_strategy_metadata,
)
from .strategies.registry import StrategyMetadata


@dataclass(frozen=True)
class StrategySelection:
    strategy_id: str
    source: str
    metadata: StrategyMetadata
    legacy_alias: str | None = None


class StrategySelectionError(ValueError):
    """用户选择了未知、planned 或当前不可执行的 strategy。"""


def resolve_strategy_selection(
    cfg: MindForgeConfig,
    *,
    explicit_strategy: str | None = None,
    watched_strategy: str | None = None,
) -> StrategySelection:
    """按统一优先级解析 strategy 并验证可执行性。

    优先级：``--strategy`` > watched registry strategy > ``strategy.active`` >
    built-in default ``knowledge_card``。

    中文学习型说明：测试可以注入 LLM stub response，但 active strategy 不能
    注入 deterministic baseline。否则 CI 通过的不是生产 Knowledge Card
    Strategy 路径，真实 dogfood 仍可能坏掉。
    """

    raw = explicit_strategy or watched_strategy or cfg.strategy.active or DEFAULT_STRATEGY_NAME
    selected = str(raw).strip()
    if not selected:
        selected = DEFAULT_STRATEGY_NAME
    canonical = canonical_strategy_id(selected)
    source = (
        "--strategy"
        if explicit_strategy
        else ("watched source strategy" if watched_strategy else ("strategy.active" if cfg.strategy.active else "default"))
    )
    try:
        metadata = get_strategy_metadata(canonical)
    except UnknownStrategyError as exc:
        raise StrategySelectionError(
            f"unknown strategy: {selected!r}; available: {available_strategies()}; "
            "run `mindforge strategies list` to see executable status."
        ) from exc
    if metadata.status == "planned":
        raise StrategySelectionError(
            f"strategy {selected!r} is planned and not executable; "
            "choose the production Knowledge Card Strategy (`knowledge_card`)."
        )
    if not metadata.production_ready:
        raise StrategySelectionError(
            f"strategy {selected!r} is internal/not production-ready and cannot be "
            "used as active strategy. Tests should inject LLM stub responses into "
            "`knowledge_card` instead of selecting deterministic baselines."
        )
    if metadata.status not in {"implemented", "preview"}:
        raise StrategySelectionError(
            f"strategy {selected!r} is {metadata.status!r} and cannot be executed safely."
        )
    return StrategySelection(
        strategy_id=metadata.canonical_id or canonical,
        source=source,
        metadata=metadata,
        legacy_alias=selected if selected != (metadata.canonical_id or canonical) else None,
    )


def strategy_error_from_build_error(strategy_id: str, exc: Exception) -> StrategySelectionError:
    """把 registry build 异常翻译成统一 selection 错误。

    build_strategy 仍是最终执行守门人；本 helper 只是让 CLI/service 不需要了解
    registry 内部异常树。
    """

    if isinstance(exc, NotYetImplementedStrategyError):
        return StrategySelectionError(f"strategy {strategy_id!r} is not executable: {exc}")
    if isinstance(exc, UnknownStrategyError):
        return StrategySelectionError(f"unknown strategy: {strategy_id!r}; available: {available_strategies()}")
    return StrategySelectionError(str(exc))


__all__ = [
    "StrategySelection",
    "StrategySelectionError",
    "resolve_strategy_selection",
    "strategy_error_from_build_error",
]
