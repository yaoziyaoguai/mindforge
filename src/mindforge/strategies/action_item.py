"""ActionItemStrategy — v0.11 Slice 4 planned built-in strategy.

为什么这是一个 *仅元数据* 模块
==============================

v0.11 Slice 3 把 ``status`` 字段引入策略 metadata，让 registry 能向用户
表达 ``implemented`` / ``preview`` / ``planned`` 三态。Slice 4 必须让
**至少一个内建策略真的处于 planned 状态**，否则 multi-strategy UX 永远
只能演示 implemented + preview 两态，三态契约只是字面上的承诺。

``action_item`` 是 ROADMAP §v0.11+ 早就规划过的方向之一（"从素材中抽取
可执行行动项"），但它的 *语义模型* 仍在讨论：抽取力度 / 是否带 due-date
推断 / 是否与已有 review_service due-tracking 结合 / 输出粒度。在这些
设计未敲定前，**先不**给它一个能跑的 KnowledgeStrategy 实现 —— 让它在
registry 里以 ``status="planned"`` 存在，但**没有 build_xxx 工厂**：

- ``mindforge strategies list`` 仍能展示它（Slice 4 Red Family E
  契约）—— 用户看见"我有这个策略，但它还不能跑"；
- ``build_strategy("action_item", ctx)`` 必须抛
  ``NotYetImplementedStrategyError``（Slice 4 Red Family C 契约）——
  registry 在 status check 阶段就拒绝，不会进 factory 分支；
- 永远不会**偷偷 fallback** 到 ``default_knowledge_card`` 或 ``five_stage``
  执行（Slice 4 Red Family C 第三条契约）；
- 不调 LLM、不读 ``.env``、不联网、不写 vault —— 因为根本没有可执行
  代码路径会做这些事。

把"仅 metadata"的 planned 策略落到一个独立模块（而不是塞在 registry 内
hardcode），是为了让未来 Slice 4+1 / v0.12 真正实现 action_item 时，
只需要在本模块加一个工厂、把 ``STRATEGY_STATUS`` 改成 ``preview`` 或
``implemented``、并在 registry 的 ``_FACTORIES`` 表注册一行 —— 调用方与
其他 strategy 模块都不需要动。这正是"先把 planned 元数据骨架立起来"
的 Information Hiding 收益。
"""

from __future__ import annotations


STRATEGY_ID = "action_item"
STRATEGY_VERSION = "0.0.0"
ENVELOPE_SCHEMA_VERSION = "1"
STRATEGY_DISPLAY_NAME = "Action Item Extraction (Planned)"
STRATEGY_DESCRIPTION = (
    "规划中策略：从素材抽取可执行行动项。语义模型（抽取力度 / due-date "
    "推断 / 与 review_service due-tracking 协作）尚未敲定，本版本仅在 "
    "registry 中登记元数据，不可执行；调用 build_strategy 会抛 "
    "NotYetImplementedStrategyError。"
)
STRATEGY_PROVIDER_MODE = "deterministic"
STRATEGY_SAFETY_POLICY = "ai_draft_only"
STRATEGY_OUTPUT_SCHEMA_ID = f"{STRATEGY_ID}@{ENVELOPE_SCHEMA_VERSION}"
# v0.11 Slice 4：planned = 仅登记元数据，execute 路径会被 registry 在
# build_strategy 入口拒绝；UX 上仍可被 list 出来让用户感知它存在。
STRATEGY_STATUS = "planned"
STRATEGY_ROLE = "planned"
STRATEGY_PRODUCTION_READY = False
STRATEGY_USER_RECOMMENDED = False
STRATEGY_CANONICAL_ID = STRATEGY_ID
STRATEGY_LEGACY_ALIASES: tuple[str, ...] = ()
STRATEGY_WARNING = "planned metadata only; not executable."


__all__ = [
    "ENVELOPE_SCHEMA_VERSION",
    "STRATEGY_DESCRIPTION",
    "STRATEGY_DISPLAY_NAME",
    "STRATEGY_ID",
    "STRATEGY_OUTPUT_SCHEMA_ID",
    "STRATEGY_PROVIDER_MODE",
    "STRATEGY_SAFETY_POLICY",
    "STRATEGY_STATUS",
    "STRATEGY_VERSION",
]
