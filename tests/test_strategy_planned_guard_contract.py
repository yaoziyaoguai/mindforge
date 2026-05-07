"""v0.11 StrategyRegistry Slice 4 — Red contract tests for planned-strategy
execution guard & not-yet-implemented UX.

Slice 3 把 ``status`` 字段引入 metadata，让 multi-strategy discovery 能区分
``implemented`` / ``preview`` / ``planned``。但是 status 当下只是元数据上
的 *声明*：registry 与 CLI 的 *执行边界* 完全没有为它 enforce 任何东西
—— 一个 ``status="planned"`` 的策略只要被注册，就会被 ``build_strategy()``
照常构造、被 ``mindforge process --strategy`` 照常拿去 run。这背叛了
"planned = 仅登记，不可执行" 的语义承诺，也让用户在终端无法区分 *未知策略*
（拼错名字）和 *已规划但尚未实现的策略*（名字拼对了，但功能还没做）。

Slice 4 主题：planned strategy execution guard / not-yet-implemented UX
======================================================================

Slice 4 必须在执行边界引入：

1. **registry 拒绝 build planned strategy**：``build_strategy`` 在拿到
   ``status="planned"`` 的策略名时抛 ``NotYetImplementedStrategyError``，
   而不是悄悄返回工厂构造的实例；
2. **错误类型与 unknown 严格区分**：``NotYetImplementedStrategyError``
   不能是 ``UnknownStrategyError`` 的子类 —— 否则上层 catch unknown 时
   会把 planned 一起吞掉，破坏区分；
3. **错误消息友好且可操作**：消息必须包含策略名、planned 字面量、可选
   的 implemented 替代 ID，不能是 stack trace 也不能是 Python repr；
4. **registry 必须有至少一个 planned 策略**：让 multi-strategy UX 真正
   呈现 implemented / preview / planned 三态对比，而不是停留在 metadata
   级声明；
5. **CLI process --strategy <planned> 给友好提示并退出非零**：与 unknown
   走相同的 typer.Exit code 不要紧，但消息必须不同；
6. **planned 策略仍然 listable**：``list_strategies()`` 仍返回它的元数据，
   ``mindforge strategies list`` 仍展示，让用户能看见"它存在，但还不能跑"。
7. **planned 不能偷偷 fallback** 到 default_card / five_stage 执行。

本切片只写 tests / docs / fixtures —— 不改 production code。Slice 4 Green
将通过最小改动让上述契约通过。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindforge.strategies import (
    StrategyMetadata,
    UnknownStrategyError,
    available_strategies,
    list_strategies,
)
from mindforge.strategies.base import StrategyContext


# ---------------------------------------------------------------------------
# Family A — NotYetImplementedStrategyError 类型契约（Red 缺口）
# ---------------------------------------------------------------------------


def test_not_yet_implemented_strategy_error_is_exported() -> None:
    """``mindforge.strategies`` 必须导出 ``NotYetImplementedStrategyError``。

    Red 期望：当前 strategies 包只导出 ``UnknownStrategyError``；planned
    策略与未知策略走同一类型，无法在 catch 站点区分。
    """

    import mindforge.strategies as strategies_pkg

    assert hasattr(strategies_pkg, "NotYetImplementedStrategyError"), (
        "mindforge.strategies 缺 NotYetImplementedStrategyError 导出"
    )


def test_not_yet_implemented_error_is_distinct_from_unknown_error() -> None:
    """``NotYetImplementedStrategyError`` 必须**不**是 ``UnknownStrategyError``
    的子类，否则上层 catch unknown 会把 planned 一起吞掉，破坏 UX 区分。
    """

    from mindforge.strategies import NotYetImplementedStrategyError

    assert not issubclass(NotYetImplementedStrategyError, UnknownStrategyError), (
        "NotYetImplementedStrategyError 不能继承 UnknownStrategyError"
    )
    # 但应该是 ValueError 的子类（与 UnknownStrategyError 同祖先），让顶层
    # broad catch 仍能工作。
    assert issubclass(NotYetImplementedStrategyError, ValueError), (
        "NotYetImplementedStrategyError 应继承 ValueError 以保持错误层级"
    )


# ---------------------------------------------------------------------------
# Family B — Registry 必须有至少一个 planned strategy（Red 缺口）
# ---------------------------------------------------------------------------


def test_registry_has_at_least_one_planned_strategy() -> None:
    """registry 必须包含至少一个 ``status="planned"`` 的策略。

    Red 期望：当前 3 个策略全部是 implemented/preview，没有 planned；
    multi-strategy UX 还停留在 "声明三态但只演示两态" 状态。
    """

    metas = list_strategies()
    planned = [m for m in metas if m.status == "planned"]
    assert planned, (
        f"registry 当前没有 planned 策略；现有 status："
        f"{sorted({m.status for m in metas})}"
    )


def test_planned_strategy_metadata_remains_well_formed() -> None:
    """planned 策略的元数据必须满足 Slice 1+2+3 锁定的 8 个字段契约。"""

    metas = list_strategies()
    planned = [m for m in metas if m.status == "planned"]
    assert planned, "前置：registry 至少需要一个 planned 策略"
    m = planned[0]
    assert m.strategy_id and m.strategy_version
    assert m.display_name and m.description
    assert m.provider_mode in {"fake_only", "deterministic", "real_opt_in"}
    assert m.safety_policy == "ai_draft_only"
    assert m.output_schema_id
    assert m.status == "planned"


# ---------------------------------------------------------------------------
# Family C — build_strategy 必须拒绝 planned 策略（Red 缺口）
# ---------------------------------------------------------------------------


def _first_planned_id() -> str | None:
    """辅助：找出第一个 planned 策略 ID，没有则返回 None。"""

    for m in list_strategies():
        if m.status == "planned":
            return m.strategy_id
    return None


def test_build_strategy_refuses_planned_with_dedicated_error() -> None:
    """``build_strategy(<planned_name>, ctx)`` 必须抛
    ``NotYetImplementedStrategyError``，而不是构造工厂实例。

    Red 期望：当前 build_strategy 不读 status，会照常构造。
    """

    from mindforge.strategies import NotYetImplementedStrategyError, build_strategy

    name = _first_planned_id()
    if name is None:
        pytest.skip("no planned strategy registered yet (Family B 已 Red)")
    with pytest.raises(NotYetImplementedStrategyError):
        build_strategy(name, StrategyContext())


def test_planned_strategy_error_message_is_user_actionable() -> None:
    """``NotYetImplementedStrategyError`` 消息必须包含：
    - 策略名（让用户确认拼写）；
    - "planned" / "not yet implemented" 字面量之一；
    - 至少一个 implemented 替代 ID（让用户立刻能选别的跑）。

    且**不能**包含 ``object at 0x``（Python repr 泄漏）或 ``Traceback``
    （stack trace 泄漏）。
    """

    from mindforge.strategies import NotYetImplementedStrategyError, build_strategy

    name = _first_planned_id()
    if name is None:
        pytest.skip("no planned strategy registered yet (Family B 已 Red)")

    with pytest.raises(NotYetImplementedStrategyError) as exc_info:
        build_strategy(name, StrategyContext())
    msg = str(exc_info.value)
    assert name in msg, f"消息应包含策略名 {name!r}：{msg!r}"
    assert ("planned" in msg.lower() or "not yet implemented" in msg.lower()), (
        f"消息应说明策略尚未实现：{msg!r}"
    )
    # 至少一个 implemented 策略 ID 出现在消息中（提示替代）
    implemented_ids = [m.strategy_id for m in list_strategies() if m.status == "implemented"]
    assert any(impl_id in msg for impl_id in implemented_ids), (
        f"消息应建议至少一个 implemented 替代策略；消息：{msg!r}；"
        f"implemented：{implemented_ids}"
    )
    assert "object at 0x" not in msg, f"消息泄漏 Python repr：{msg!r}"
    assert "Traceback" not in msg, f"消息泄漏 stack trace：{msg!r}"


def test_planned_strategy_does_not_silently_fallback() -> None:
    """``build_strategy(<planned>)`` 必须**抛错**而不是悄悄返回 default_card
    / five_stage 实例。这条边界是为了防止 "planned 偷偷走默认策略" 的
    fallback bug。
    """

    from mindforge.strategies import NotYetImplementedStrategyError, build_strategy

    name = _first_planned_id()
    if name is None:
        pytest.skip("no planned strategy registered yet (Family B 已 Red)")
    raised = False
    try:
        build_strategy(name, StrategyContext())
    except NotYetImplementedStrategyError:
        raised = True
    except Exception:
        # 其它异常类型也算 "没有 fallback"，但不是我们想要的契约；
        # 这条 assert 在 Slice 4 Green 后必须通过 NotYetImplementedStrategyError 路径。
        raised = True
    assert raised, (
        f"build_strategy({name!r}) 没有抛错；可能悄悄 fallback 到默认策略"
    )


# ---------------------------------------------------------------------------
# Family D — CLI 必须为 planned 策略给出友好的 not-yet-implemented 提示（Red）
# ---------------------------------------------------------------------------


def test_cli_process_planned_strategy_exits_non_zero_with_friendly_message(
    tmp_path: Path,
) -> None:
    """``mindforge process --strategy <planned_id>`` 必须以非零退出码退出，
    并打印 ``planned`` / ``not yet implemented`` 友好提示，**不能**与 unknown
    策略消息混为一谈。
    """

    from mindforge.cli import app

    name = _first_planned_id()
    if name is None:
        pytest.skip("no planned strategy registered yet (Family B 已 Red)")

    # 用最简 config + 空目录 source 让 process 能进入 build_strategy 分支
    # 而不会先在别处崩。具体 fixture 由 Slice 4 Green 视情况调整。
    cfg_path = tmp_path / "mindforge.yaml"
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    cfg_path.write_text(
        f"""
state:
  runs_path: {state_dir}/runs.jsonl
sources:
  - type: text_files
    name: t
    paths: [{src_dir}]
""".strip(),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["process", "--config", str(cfg_path), "--strategy", name],
    )
    assert result.exit_code != 0, (
        f"CLI process --strategy {name!r} 应以非零退出码退出；"
        f"实际 exit_code={result.exit_code}, output={result.output!r}"
    )
    out_lower = result.output.lower()
    assert "planned" in out_lower or "not yet implemented" in out_lower, (
        f"CLI 输出应说明策略 planned/not-yet-implemented；实际：{result.output!r}"
    )
    # 不能与 unknown 策略的措辞混淆
    assert "未知 strategy" not in result.output, (
        f"planned 策略不应被当作 unknown 策略报错：{result.output!r}"
    )


# ---------------------------------------------------------------------------
# Family E — Planned 策略仍可被 list（Green baseline + 严格不变量）
# ---------------------------------------------------------------------------


def test_planned_strategy_requires_internal_list_flag_in_cli_output() -> None:
    """planned 策略只在 developer/internal discovery 中展示。

    中文学习型说明：普通用户默认只看到生产 Knowledge Card Strategy；planned
    metadata 不该被包装成产品路线里的可选项。
    """

    from mindforge.cli import app

    name = _first_planned_id()
    if name is None:
        pytest.skip("no planned strategy registered yet (Family B 已 Red)")

    runner = CliRunner()
    result = runner.invoke(app, ["strategies", "list"])
    assert result.exit_code == 0, result.output
    assert name not in result.output

    internal = runner.invoke(app, ["strategies", "list", "--include-internal"])
    assert internal.exit_code == 0, internal.output
    assert name in internal.output
    assert "planned" in internal.output


# ---------------------------------------------------------------------------
# Family F — Docs / onboarding 解释 implemented vs preview vs planned（Red）
# ---------------------------------------------------------------------------


def test_readme_explains_strategy_lifecycle_status() -> None:
    """README 必须解释 implemented / preview / planned 三态的含义，
    让用户在跑 ``mindforge strategies list`` 看到 status 列时不会困惑。

    Red 期望：当前 README 仅在 Quick Start 提了一下 strategies list，
    没有说明三态。
    """

    p = Path("README.md")
    assert p.exists()
    text = p.read_text(encoding="utf-8").lower()
    # 三个 status 字面量都应在 README 出现，且至少其中一处应靠近"strategy"
    # 上下文（粗略检查："strategy" 与 "planned" 同时出现）
    for token in ("implemented", "preview", "planned"):
        assert token in text, f"README 缺少 status={token!r} 的说明"
    assert "strategy" in text and "planned" in text, (
        "README 应在 strategy 上下文内解释 planned 状态"
    )


# ---------------------------------------------------------------------------
# Family G — Sanity Green baselines（保护 Slice 1+2+3 已建立的契约）
# ---------------------------------------------------------------------------


def test_unknown_strategy_error_still_works() -> None:
    """不要在 Slice 4 Green 中误把 unknown 也变成 planned。"""

    from mindforge.strategies import build_strategy

    with pytest.raises(UnknownStrategyError):
        build_strategy("__definitely_not_registered__", StrategyContext())


def test_existing_implemented_strategies_still_buildable() -> None:
    """Slice 4 Green 不能让 implemented 策略被 guard 误伤。

    default_knowledge_card 是离线确定性策略，可以无 client 构造。
    five_stage 需要 client，跳过单纯构造，仅断言它仍是 implemented。
    """

    from mindforge.strategies import build_strategy, get_strategy_metadata

    inst = build_strategy("default_knowledge_card", StrategyContext())
    assert inst is not None
    assert get_strategy_metadata("five_stage").status == "implemented"


@pytest.mark.parametrize(
    "field_name",
    [
        "strategy_id",
        "strategy_version",
        "display_name",
        "description",
        "provider_mode",
        "safety_policy",
        "output_schema_id",
        "status",
    ],
)
def test_strategy_metadata_keeps_slice_1_through_3_fields(field_name: str) -> None:
    """Slice 1+2+3 锁定的 8 个字段必须全部保留。Green baseline。"""

    assert field_name in StrategyMetadata.__dataclass_fields__


def test_at_least_three_strategies_still_registered() -> None:
    """Slice 3 引入的"至少 3 个内建策略"不可在 Slice 4 Green 中回退。"""

    assert len(available_strategies()) >= 3
