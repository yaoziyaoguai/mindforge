"""v0.11 StrategyRegistry Slice 2 — Red contract tests for strategy
discovery UX.

Slice 1 让 registry 能列出 ``strategy_id`` / ``strategy_version`` /
``display_name`` / ``description``，但 CLI ``strategies list`` 输出
仍偏简略，且 metadata 没有明确 strategy 是否需要真实 LLM、是否只产
``ai_draft``、用什么 envelope schema 输出。

Slice 2 主题：strategy discovery UX
====================================

目标是让用户在不调任何 LLM / .env / Cubox / Obsidian 的前提下，能够
一眼看清楚每个策略的：

- 是否离线安全（``provider_mode``：``fake_only`` / ``deterministic``
  / ``real_opt_in``）；
- 安全策略（``safety_policy``：当前所有内建策略都是 ``ai_draft_only``，
  不会自动 approve）；
- 输出 envelope schema 标识（``output_schema_id``：让消费方一眼看到
  envelope schema_version + strategy_id 组合）；
- 友好的未知策略错误提示（应主动建议 ``mindforge strategies list``，
  而不是只丢一个元组字面量）。

本切片只写 **tests / 必要 docs** —— 不改 production code。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindforge.strategies import (
    DEFAULT_STRATEGY_NAME,
    StrategyMetadata,
    available_strategies,
    list_strategies,
)


# ---------------------------------------------------------------------------
# Family A — StrategyMetadata 三项 UX 字段（Red 缺口）
# ---------------------------------------------------------------------------


REQUIRED_UX_FIELDS = (
    "provider_mode",
    "safety_policy",
    "output_schema_id",
)


@pytest.mark.parametrize("field_name", REQUIRED_UX_FIELDS)
def test_strategy_metadata_dataclass_has_ux_field(field_name: str) -> None:
    """``StrategyMetadata`` 必须新增 ``provider_mode`` /
    ``safety_policy`` / ``output_schema_id`` 三个 UX 字段。

    Red 期望：Slice 1 Green 的 StrategyMetadata 只有 4 个核心字段，
    这三个字段尚未存在 —— Slice 2 Green 必须补齐，让 CLI list 能向
    用户解释"我能在离线跑吗 / 我会自动 approve 吗 / 我吐什么 schema"。
    """

    fields = set(StrategyMetadata.__dataclass_fields__)
    assert field_name in fields, (
        f"StrategyMetadata 缺字段 {field_name!r}；"
        f"现有字段：{sorted(fields)}。"
    )


# ---------------------------------------------------------------------------
# Family B — 每个内建策略模块声明对应常量（Red 缺口）
# ---------------------------------------------------------------------------


REQUIRED_UX_CONSTANTS = (
    "STRATEGY_PROVIDER_MODE",
    "STRATEGY_SAFETY_POLICY",
    "STRATEGY_OUTPUT_SCHEMA_ID",
)


@pytest.mark.parametrize("strategy_name", ["default_knowledge_card", "five_stage"])
def test_builtin_strategy_module_exposes_ux_constants(strategy_name: str) -> None:
    """每个内建策略模块必须新增三项 UX 常量。

    Red 期望：Slice 1 Green 只补了 DISPLAY_NAME / DESCRIPTION，
    UX 三项常量尚未存在；Slice 2 Green 必须在 strategy 模块顶层
    补齐，保持"strategy 模块是元数据作者，registry 只汇总"的边界。
    """

    import importlib

    mod = importlib.import_module(f"mindforge.strategies.{strategy_name}")
    missing = [c for c in REQUIRED_UX_CONSTANTS if not hasattr(mod, c)]
    assert not missing, (
        f"strategy 模块 {strategy_name!r} 缺 UX 常量：{missing}；"
        f"Slice 2 Green 必须在 module 级补齐 {REQUIRED_UX_CONSTANTS}。"
    )

    for const in REQUIRED_UX_CONSTANTS:
        value = getattr(mod, const)
        assert isinstance(value, str) and value.strip(), (
            f"{strategy_name}.{const} 必须是非空字符串，实际：{value!r}"
        )


def test_builtin_strategy_provider_mode_values_are_in_allowed_set() -> None:
    """``STRATEGY_PROVIDER_MODE`` 取值必须落在受控集合内，
    防止 strategy 作者随手填入 free-form 字符串导致 UX 不一致。
    """

    import importlib

    allowed = {"fake_only", "deterministic", "real_opt_in"}
    for name in available_strategies():
        mod = importlib.import_module(f"mindforge.strategies.{name}")
        mode = getattr(mod, "STRATEGY_PROVIDER_MODE", None)
        assert mode in allowed, (
            f"{name}.STRATEGY_PROVIDER_MODE={mode!r} 不在允许集合 {allowed}"
        )


def test_builtin_strategy_safety_policy_is_ai_draft_only() -> None:
    """所有内建策略必须声明 ``safety_policy = "ai_draft_only"``，
    与项目硬约束（不自动 approve、不直接产 human_approved）对齐。
    """

    import importlib

    for name in available_strategies():
        mod = importlib.import_module(f"mindforge.strategies.{name}")
        policy = getattr(mod, "STRATEGY_SAFETY_POLICY", None)
        assert policy == "ai_draft_only", (
            f"{name}.STRATEGY_SAFETY_POLICY={policy!r} 必须是 'ai_draft_only'"
        )


# ---------------------------------------------------------------------------
# Family C — list_strategies 元数据通过新字段（Red 缺口）
# ---------------------------------------------------------------------------


def test_list_strategies_metadata_carries_ux_fields() -> None:
    """``list_strategies()`` 返回的每条 metadata 必须包含三项 UX 字段
    且非空 —— 这是 CLI 列表与未来文档生成器的统一数据源。
    """

    metas = list_strategies()
    assert len(metas) >= 1
    for m in metas:
        for field_name in REQUIRED_UX_FIELDS:
            value = getattr(m, field_name, None)
            assert isinstance(value, str) and value.strip(), (
                f"{m.strategy_id} metadata.{field_name} 必须是非空字符串，"
                f"实际：{value!r}"
            )


# ---------------------------------------------------------------------------
# Family D — CLI `strategies list` UX 输出（Red 缺口）
# ---------------------------------------------------------------------------


def test_cli_strategies_list_output_includes_ux_fields() -> None:
    """``mindforge strategies list`` 输出必须包含每个策略的：
    strategy_id / strategy_version / display_name / provider_mode /
    safety_policy / output_schema_id 六项可见信息。

    Red 期望：Slice 1 Green 的输出只含 id+version+display_name+description，
    未含 provider_mode / safety_policy / output_schema_id。
    """

    from mindforge.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["strategies", "list"])
    assert result.exit_code == 0, result.output

    out = result.output
    metas = list_strategies()
    for m in metas:
        assert m.strategy_id in out
        assert m.strategy_version in out
        assert m.display_name in out
        # 三项 UX 字段必须在每个策略的输出块里出现 —— 取严格 substring 检查
        assert m.provider_mode in out, (
            f"输出未含 {m.strategy_id!r} 的 provider_mode={m.provider_mode!r}"
        )
        assert m.safety_policy in out, (
            f"输出未含 {m.strategy_id!r} 的 safety_policy={m.safety_policy!r}"
        )
        assert m.output_schema_id in out, (
            f"输出未含 {m.strategy_id!r} 的 output_schema_id={m.output_schema_id!r}"
        )


def test_cli_strategies_list_does_not_construct_llm_client() -> None:
    """``mindforge strategies list`` 必须是纯查询 —— 实现源码里不能出现
    ``LLMClient(`` 构造、不能调用 ``build_strategy(`` / ``build_providers(``。

    通过对 cli.py 中 ``strategies_list`` 函数体的源码扫描守护这条边界，
    避免后续随手在 list 里加上"顺便初始化 client 检查可达性"等副作用。
    """

    src = Path("src/mindforge/cli.py").read_text(encoding="utf-8")
    # 定位 strategies_list 函数体
    marker = "def strategies_list("
    assert marker in src, "cli.py 中未找到 strategies_list 函数"
    start = src.index(marker)
    # 函数体到下一个顶层 def/@ 装饰之间
    after = src[start:]
    # 取前 2000 char 作为函数 + 紧邻区域观察窗
    window = after[:2000]
    forbidden = (
        "LLMClient(",
        "build_providers(",
        "build_strategy(",
        "load_dotenv",
        "CardWriter(",
        "approve_card(",
    )
    for token in forbidden:
        assert token not in window, (
            f"strategies_list 函数体疑似引入越界副作用：发现 {token!r}"
        )


# ---------------------------------------------------------------------------
# Family E — 未知 --strategy 错误提示包含 discovery 入口（Red 缺口）
# ---------------------------------------------------------------------------


def test_unknown_strategy_error_hints_strategies_list_command() -> None:
    """``UnknownStrategyError`` 消息必须主动建议用户运行
    ``mindforge strategies list`` 来查看可用策略，而不仅是吐出一个元组
    字面量 —— 这是 CLI 对终端用户最友好的发现入口。

    Red 期望：当前实现只在消息里附 ``available: ('default_knowledge_card',
    'five_stage')`` 元组，没有指向 CLI 命令。
    """

    from mindforge.strategies import UnknownStrategyError, build_strategy
    from mindforge.strategies.base import StrategyContext

    with pytest.raises(UnknownStrategyError) as excinfo:
        build_strategy("does_not_exist_xyz", ctx=StrategyContext())
    msg = str(excinfo.value)
    assert "strategies list" in msg, (
        "UnknownStrategyError 消息必须建议 `mindforge strategies list`，"
        f"实际消息：{msg!r}"
    )


# ---------------------------------------------------------------------------
# Family F — process --strategy 未知名错误也提示 discovery 入口（Red 缺口）
# ---------------------------------------------------------------------------


def test_cli_process_unknown_strategy_message_hints_strategies_list() -> None:
    """``mindforge process --strategy <unknown>`` 的 console 错误必须
    包含 ``mindforge strategies list`` 提示，给终端用户一条明确的下一步。

    Red 期望：当前 cli.py 把 UnknownStrategyError 翻译成
    "未知 strategy: ...; 可选: (...)"，没有 discovery 入口。
    """

    src = Path("src/mindforge/cli.py").read_text(encoding="utf-8")
    # 定位 UnknownStrategyError 翻译块
    assert "except UnknownStrategyError" in src
    after = src[src.index("except UnknownStrategyError"):]
    window = after[:600]
    assert "strategies list" in window, (
        "cli.py 中 UnknownStrategyError 翻译块未包含 `strategies list` 提示；"
        "Slice 2 Green 必须在错误消息中加入该 discovery 入口。"
    )


# ---------------------------------------------------------------------------
# Family G — Docs onboarding baseline（Red 缺口）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "strategies list",
        "default_knowledge_card",
        "five_stage",
    ],
)
def test_readme_or_docs_mentions_strategy_discovery(phrase: str) -> None:
    """README 或 docs/ROADMAP 必须提到 strategy 发现入口与两个内建策略名，
    这样新用户在没看代码前也能知道有哪些可选项。

    Red 期望：当前 README / ROADMAP 没有 ``strategies list`` 的引用。
    """

    candidates = [
        Path("README.md"),
        Path("docs/ROADMAP.md"),
    ]
    haystack = "\n".join(p.read_text(encoding="utf-8") for p in candidates if p.exists())
    assert phrase in haystack, (
        f"README + docs/ROADMAP 未提到 {phrase!r}；"
        "Slice 2 Green 必须在 README 或 ROADMAP 中加入 strategy discovery 段。"
    )


# ---------------------------------------------------------------------------
# Family H — 简单 sanity baselines（Green，锁定不退化）
# ---------------------------------------------------------------------------


def test_default_strategy_metadata_is_listable() -> None:
    """默认策略必须可以从 list_strategies 中找到。Green baseline。"""

    metas = list_strategies()
    ids = [m.strategy_id for m in metas]
    assert DEFAULT_STRATEGY_NAME in ids
