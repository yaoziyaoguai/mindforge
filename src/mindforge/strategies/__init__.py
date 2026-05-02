"""KnowledgeStrategy seam — 知识归纳策略的可插拔扩展点（Phase 1）。

为什么要这一层？
================

MindForge 的 ``ai_draft`` 生成路径（``mindforge process``）在 v0.7.x 期间
一直只有一种实现：``processors.pipeline.Pipeline`` 中固定的五段调用链
（triage → distill → link_suggestion → review_questions → action_extraction）。
这条链路本身经过严密测试与边界保护，**不能也不应该**被重写或绕开。

但是 Phase 1 (CLI Product Shape Completion) 在 ROADMAP 中明确要求：

    "插件化、可配置的知识归纳策略 seam …… Processing Pipeline 应该依赖
    策略接口，而不是写死一种总结方式。"

未来不同来源 / 不同意图（如 Cubox 长文 reading note、Obsidian concept
card、project context、evidence append、question/claim extraction）会需要
不同的策略形状；如果调用方继续直接写 ``Pipeline(...)``，每加一种策略都
要改 CLI 与 process_service 的组合根。

本模块用最薄的 seam 解决这个问题：

- :class:`KnowledgeStrategy`（``base`` 中定义）—— 一个 ``Protocol``，结构上
  等同于 ``Pipeline.run(doc) -> PipelineOutcome``；现有 ``Pipeline`` 已经
  满足这个 Protocol，**不需要**修改 ``Pipeline`` 即可被识别为策略；
- :func:`build_strategy`（``registry`` 中定义）—— 按名字工厂派发，
  默认策略 ``"five_stage"`` 直接复用现有 ``Pipeline``；
- :class:`StrategyContext`（``base`` 中定义）—— 把策略所需的运行时材料
  （LLMClient、prompts_dir、prompt_versions、tracks_text、阈值）打包成
  一个稳定的输入面，让未来策略不必在签名上互相抄。

本 seam **不**改变行为：

- 默认策略生成的 ``ai_draft`` 与 v0.7.x byte-level 一致；
- ``human_approved`` 边界不变（仍只能由显式 approve 链路产生）；
- 不调真实 LLM、不读 ``.env``、不联网、不写正式 Obsidian notes、
  不自动 approve、不引入 RAG / embedding / Web UI / TUI / plugin。

未来扩展点
==========

- 新策略只需在 ``strategies/`` 下加一个工厂函数，并在 ``registry`` 中
  注册一个名字。``Pipeline`` 内部的五段实现完全保留为默认策略；
- 当 ``configs/mindforge.yaml`` 引入 ``processing.strategy`` 字段后，
  CLI 可直接把名字传入 :func:`build_strategy`，无需再改组合根。
"""

from pathlib import Path

from .base import KnowledgeStrategy, StrategyContext
from .concept_extraction import build_concept_extraction_strategy
from .five_stage import build_five_stage_strategy
from .registry import (
    DEFAULT_STRATEGY_NAME,
    NotYetImplementedStrategyError,
    StrategyMetadata,
    UnknownStrategyError,
    available_strategies,
    get_strategy_metadata,
    list_strategies,
)
from .registry import build_strategy as _build_builtin_strategy


def discover_strategies(
    custom_path: Path | None = None,
) -> tuple[StrategyMetadata, ...]:
    """统一的策略**发现**入口（v0.12 Slice 3 Green / Slice 4 Green）。

    职责（高内聚 / 单一）
    ====================

    把"内建策略 metadata"与"用户提供的 custom declarative metadata"
    合并成一条只读元数据流，作为 ``mindforge strategies list`` 与未来
    其它 UX 调用方的统一来源。

    本函数明确**不**承担
    ====================

    - 不构造任何 :class:`KnowledgeStrategy` 实例 → discovery 不是
      execution；
    - 不把 custom 定义注册进可执行 :data:`registry._FACTORIES` →
      v0.11 Slice 4 planned guard 顺势保护：custom metadata 的
      ``status`` 在 :func:`parse_strategy_definition` 阶段已被钉死为
      ``planned`` / ``preview``，因此即便有调用方误把名字传给
      :func:`build_strategy`，也会被 planned guard 拒绝；
    - 不读 ``.env`` / 不调 LLM / 不写 workspace / 不隐式扫描；
    - 不允许 ``custom_path`` 默认指向用户主目录或 vault —— 必须由
      调用方显式传入。

    Slice 4 Green 新增：``strategy_id`` 撞名（custom 与 built-in 同名）
    会立刻 fail-loud 抛 :class:`InvalidStrategyDefinitionError`，避免
    "悄悄覆盖"或"两个同名条目并列"造成调用方歧义 —— 见
    :func:`_reject_duplicate_strategy_ids`。

    参数
    ====

    - ``custom_path`` —— 显式 custom strategy 目录。``None`` 时只返回
      内建 metadata，与 :func:`list_strategies` 完全等价；非 ``None``
      时使用 :func:`load_strategy_definitions_from_directory` 的相同
      安全边界（白名单扩展名 / 路径穿越 / symlink-escape 全部沿用）。

    返回
    ====

    ``tuple[StrategyMetadata, ...]`` —— 顺序：先 built-in（按
    :func:`available_strategies` 字典序），再 custom（按文件名字典序）。
    """

    builtin = list(list_strategies())
    if custom_path is None:
        return tuple(builtin)

    from .custom_loader import load_strategy_definitions_from_directory

    custom_definitions = load_strategy_definitions_from_directory(custom_path)
    custom_metas = [d.to_metadata() for d in custom_definitions]
    _reject_duplicate_strategy_ids(builtin, custom_metas)
    return tuple(builtin + custom_metas)


def _reject_duplicate_strategy_ids(
    builtin: list[StrategyMetadata],
    custom: list[StrategyMetadata],
) -> None:
    """custom strategy_id 不能与 built-in 撞名，也不能彼此撞名。

    - **为什么 fail-loud**：discovery 是 *元数据合并*，调用方拿到的元
      组在 UX 与 ``build_strategy`` 中都按"名字"做唯一索引；同名条目
      会让调用方无法分辨该跑哪个，进而把 custom preview 误当 built-in
      执行。
    - **错误形态**：抛 :class:`InvalidStrategyDefinitionError`（数据级
      错误的统一根类），消息包含撞名 ``strategy_id`` 与字面量 ``duplicate
      strategy_id`` —— 让 CLI / 未来 UI 直接展示而无需自己拼装。
    """

    from .custom import InvalidStrategyDefinitionError

    builtin_ids = {m.strategy_id for m in builtin}
    seen_custom: set[str] = set()
    for meta in custom:
        if meta.strategy_id in builtin_ids:
            raise InvalidStrategyDefinitionError(
                f"duplicate strategy_id: custom definition declares "
                f"{meta.strategy_id!r} which already exists as a built-in "
                "strategy; rename the custom definition (custom strategy_id "
                "must not conflict with built-in)."
            )
        if meta.strategy_id in seen_custom:
            raise InvalidStrategyDefinitionError(
                f"duplicate strategy_id: two custom definitions declare "
                f"{meta.strategy_id!r}; rename one of them so each custom "
                "strategy_id is unique."
            )
        seen_custom.add(meta.strategy_id)


def build_strategy(
    name: str,
    ctx: StrategyContext,
    *,
    custom_path: Path | None = None,
) -> KnowledgeStrategy:
    """按名字派发策略工厂；可选地把 custom_path 一并解析为 preview-only
    友好分流（v0.12 Slice 4 Green）。

    包装 :func:`registry.build_strategy`：

    - 名字命中 built-in → 走 registry 的实现 / planned 守护路径；
    - 名字未命中 built-in 但 ``custom_path`` 给出且 custom 目录中存在
      该 strategy_id → 抛 :class:`NotYetImplementedStrategyError`，
      消息含 ``preview`` + ``discovery`` 两个字面量，让用户立刻明白
      这不是 typo，而是"已被 discovery 看到，但尚不可执行"；
    - 名字未命中 built-in 且未在 custom 目录出现 → 仍抛
      :class:`UnknownStrategyError`（与 ``custom_path=None`` 路径一致）；
    - custom 目录加载错误（非法定义 / 路径穿越 / symlink-escape） →
      :class:`InvalidStrategyDefinitionError` 子类直接传播。

    本函数**不**调 provider / 不读 ``.env`` / 不写 workspace / 不
    把 custom 注入 ``_FACTORIES``。preview-only 分流仅借助 discovery
    元数据视图判断"该名字是否被发现过"。
    """

    if custom_path is None:
        return _build_builtin_strategy(name, ctx)
    try:
        return _build_builtin_strategy(name, ctx)
    except UnknownStrategyError:
        # discovery 元数据视图查表：若该名字属于 custom preview，则
        # 改抛 NotYet 而不是 Unknown —— UX 友好分流。
        from .custom_loader import load_strategy_definitions_from_directory

        custom_metas = [
            d.to_metadata()
            for d in load_strategy_definitions_from_directory(custom_path)
        ]
        if any(m.strategy_id == name for m in custom_metas):
            raise NotYetImplementedStrategyError(
                f"strategy {name!r} was found via discovery (custom preview); "
                "discovery is not execution. Custom preview strategies are "
                "registered as metadata only and cannot be executed yet. "
                "Run `mindforge strategies list --custom-path <DIR>` to see "
                "all preview definitions; pick a built-in implemented "
                "strategy to actually run `mindforge process`."
            ) from None
        raise


__all__ = [
    "DEFAULT_STRATEGY_NAME",
    "KnowledgeStrategy",
    "NotYetImplementedStrategyError",
    "StrategyContext",
    "StrategyMetadata",
    "UnknownStrategyError",
    "available_strategies",
    "build_concept_extraction_strategy",
    "build_five_stage_strategy",
    "build_strategy",
    "discover_strategies",
    "get_strategy_metadata",
    "list_strategies",
]
