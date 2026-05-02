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
    build_strategy,
    get_strategy_metadata,
    list_strategies,
)


def discover_strategies(
    custom_path: Path | None = None,
) -> tuple[StrategyMetadata, ...]:
    """统一的策略**发现**入口（v0.12 Slice 3 Green）。

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

    metas: list[StrategyMetadata] = list(list_strategies())
    if custom_path is not None:
        from .custom_loader import load_strategy_definitions_from_directory

        for definition in load_strategy_definitions_from_directory(custom_path):
            metas.append(definition.to_metadata())
    return tuple(metas)


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
