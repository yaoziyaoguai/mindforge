"""v0.11 StrategyRegistry Slice 3 — Red contract tests for built-in
multi-strategy skeleton & lifecycle status.

Slice 1 让 registry 暴露 metadata；Slice 2 让 metadata 携带 UX 维度
（provider_mode / safety_policy / output_schema_id）。但用户至今只能
看到两个内建策略：``default_knowledge_card``（deterministic）与
``five_stage``（real_opt_in）。

Slice 3 主题：built-in multi-strategy skeleton
================================================

ROADMAP §v0.11+ 已经规划了多个内建策略形态（concept_extraction /
action_item / question_bank / project_context / reading_note）。让
registry 真正承担"我能做哪些归纳"这条 UX 之前，必须先在 metadata
层引入两个能力：

1. **生命周期状态**（``status``）—— 每个内建策略必须自报
   ``implemented`` / ``preview`` / ``planned``，避免 "登记的策略其实
   还跑不了" 这种隐性 bug 沿调用栈传播；
2. **第三个 deterministic skeleton 内建策略**（``concept_extraction``）——
   作为 "deterministic skeleton" 的最小演示载体，让 multi-strategy
   discovery 的 UX 在 v0.12 custom strategy 之前先成立。本文件**只**
   通过 Red 测试登记这条契约；具体 strategy 模块由 Slice 3 Green 实现。

本切片只写 tests / docs —— 不改 production code。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindforge.strategies import (
    StrategyMetadata,
    available_strategies,
    list_strategies,
)


# ---------------------------------------------------------------------------
# Family A — StrategyMetadata.status field（Red 缺口）
# ---------------------------------------------------------------------------


def test_strategy_metadata_dataclass_has_status_field() -> None:
    """``StrategyMetadata`` 必须新增 ``status`` 字段。

    Red 期望：Slice 2 Green 的 StrategyMetadata 含 7 个字段
    （strategy_id / strategy_version / display_name / description /
    provider_mode / safety_policy / output_schema_id），尚无 ``status``。
    """

    fields = set(StrategyMetadata.__dataclass_fields__)
    assert "status" in fields, (
        f"StrategyMetadata 缺 status 字段；现有字段：{sorted(fields)}。"
    )


def test_each_builtin_strategy_module_exposes_status_constant() -> None:
    """每个内建策略模块必须新增 ``STRATEGY_STATUS`` 常量。

    Red 期望：当前 default_knowledge_card / five_stage 模块均无该常量。
    """

    import importlib

    missing = []
    for name in available_strategies():
        mod = importlib.import_module(f"mindforge.strategies.{name}")
        if not hasattr(mod, "STRATEGY_STATUS"):
            missing.append(name)
    assert not missing, (
        f"以下 strategy 模块缺 STRATEGY_STATUS 常量：{missing}"
    )


def test_strategy_status_values_in_allowed_set() -> None:
    """``STRATEGY_STATUS`` 取值必须落在受控集合内（implemented /
    preview / planned），防止 free-form 字符串导致 UX 不一致。
    """

    import importlib

    allowed = {"implemented", "preview", "planned"}
    for name in available_strategies():
        mod = importlib.import_module(f"mindforge.strategies.{name}")
        status = getattr(mod, "STRATEGY_STATUS", None)
        assert status in allowed, (
            f"{name}.STRATEGY_STATUS={status!r} 不在 {allowed}"
        )


def test_existing_two_builtin_strategies_remain_implemented() -> None:
    """已经实际跑通的两个 strategies 必须保持 ``status='implemented'``，
    避免 Slice 3 Green 不小心把它们降级成 preview/planned。
    """

    import importlib

    for name in ("default_knowledge_card", "five_stage"):
        mod = importlib.import_module(f"mindforge.strategies.{name}")
        status = getattr(mod, "STRATEGY_STATUS", None)
        assert status == "implemented", (
            f"{name}.STRATEGY_STATUS={status!r} 必须是 'implemented'"
        )


# ---------------------------------------------------------------------------
# Family B — concept_extraction skeleton built-in（Red 缺口）
# ---------------------------------------------------------------------------


def test_registry_includes_concept_extraction_skeleton_strategy() -> None:
    """registry 必须包含一个名为 ``concept_extraction`` 的内建策略。

    Red 期望：当前 _FACTORIES 只注册 default_knowledge_card / five_stage。
    Slice 3 Green 必须新增一个 deterministic skeleton 模块并注册之，
    作为 multi-strategy discovery UX 的最小演示载体（status 可以是
    ``preview`` 或 ``implemented``，但必须可被 list/get 查询到）。
    """

    assert "concept_extraction" in available_strategies(), (
        "registry 未注册 concept_extraction；"
        f"当前注册：{available_strategies()}"
    )


def test_concept_extraction_strategy_metadata_is_listable() -> None:
    """``list_strategies()`` 必须返回 concept_extraction 的元数据，
    且该元数据满足 Slice 1+2 已锁定的字段契约。
    """

    metas = list_strategies()
    by_id = {m.strategy_id: m for m in metas}
    assert "concept_extraction" in by_id, (
        f"list_strategies 缺 concept_extraction；返回：{sorted(by_id)}"
    )
    m = by_id["concept_extraction"]
    assert m.strategy_version, "strategy_version 必须非空"
    assert m.display_name, "display_name 必须非空"
    assert m.description, "description 必须非空"
    assert m.provider_mode in {"fake_only", "deterministic", "real_opt_in"}
    assert m.safety_policy == "ai_draft_only"
    assert m.output_schema_id, "output_schema_id 必须非空"


def test_concept_extraction_is_deterministic_or_fake_only() -> None:
    """concept_extraction 作为 "deterministic skeleton" 必须是离线安全策略 ——
    其 ``provider_mode`` 不能是 ``real_opt_in``，否则就违背了"先用纯
    deterministic skeleton 让 multi-strategy UX 先成立"的设计意图。
    """

    metas = {m.strategy_id: m for m in list_strategies()}
    m = metas.get("concept_extraction")
    assert m is not None
    assert m.provider_mode in {"fake_only", "deterministic"}, (
        f"concept_extraction.provider_mode={m.provider_mode!r} "
        "必须是离线安全（fake_only / deterministic）。"
    )


def test_concept_extraction_module_does_not_call_llm_or_read_env() -> None:
    """``mindforge.strategies.concept_extraction`` 模块源码不应出现
    ``LLMClient`` 构造、``load_dotenv``、``requests.``、``httpx.``、
    Cubox URL 等真实 LLM / 网络 / 私人资料触点。

    Red 期望：模块文件尚不存在，FileNotFoundError 即视为 expected Red。
    """

    p = Path("src/mindforge/strategies/concept_extraction.py")
    assert p.exists(), (
        "src/mindforge/strategies/concept_extraction.py 尚不存在；"
        "Slice 3 Green 必须新增此模块并保持离线安全。"
    )
    src = p.read_text(encoding="utf-8")
    forbidden = (
        "LLMClient(",
        "load_dotenv",
        "import requests",
        "import httpx",
        "cubox.app",
        "UPSTAGE_API_KEY",
        "human_approved",
    )
    for token in forbidden:
        assert token not in src, (
            f"concept_extraction.py 出现越界引用 {token!r}"
        )


# ---------------------------------------------------------------------------
# Family C — Multi-strategy discovery UX（Red 缺口）
# ---------------------------------------------------------------------------


def test_cli_strategies_list_hides_internal_builtins_by_default() -> None:
    """普通 discovery 只展示生产策略，internal built-ins 需显式 opt-in。

    中文学习型说明：多策略 registry 可以保留 internal metadata，但默认 CLI UX
    不能让用户以为 deterministic baseline 是正式产品策略。
    """

    from mindforge.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["strategies", "list"])
    assert result.exit_code == 0, result.output
    assert "knowledge_card" in result.output
    assert "default_knowledge_card" not in result.output

    internal = runner.invoke(app, ["strategies", "list", "--include-internal"])
    assert internal.exit_code == 0, internal.output
    metas = list_strategies(include_internal=True)
    assert len(metas) >= 4
    for m in metas:
        assert m.strategy_id in internal.output


def test_cli_strategies_list_include_internal_output_includes_status_label() -> None:
    """``--include-internal`` 输出必须包含每个 strategy 的 status。"""

    from mindforge.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["strategies", "list", "--include-internal"])
    assert result.exit_code == 0, result.output
    for m in list_strategies():
        # status 字面量必须出现在输出某处（不一定贴近 strategy_id，但
        # 至少作为可见字段呈现）
        assert m.status in result.output, (
            f"输出未包含 {m.strategy_id!r} 的 status={m.status!r}"
        )


# ---------------------------------------------------------------------------
# Family D — Sanity Green baselines
# ---------------------------------------------------------------------------


def test_existing_two_builtin_strategies_still_listed() -> None:
    """Slice 3 Red 不能让 Slice 1/2 的 default_knowledge_card / five_stage
    从 registry 中消失。Green baseline。
    """

    names = available_strategies()
    assert "default_knowledge_card" in names
    assert "five_stage" in names


@pytest.mark.parametrize(
    "field_name",
    ["strategy_id", "strategy_version", "display_name", "description",
     "provider_mode", "safety_policy", "output_schema_id"],
)
def test_strategy_metadata_keeps_slice_1_and_2_fields(field_name: str) -> None:
    """Slice 1 + Slice 2 锁定的 7 个字段必须全部保留。Green baseline。"""

    assert field_name in StrategyMetadata.__dataclass_fields__
