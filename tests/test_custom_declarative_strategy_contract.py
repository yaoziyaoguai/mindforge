"""v0.12 Custom Declarative Strategy Architecture — Red contract tests.

v0.11 完成了 built-in multi-strategy（Slice 3）+ planned guard（Slice 4），
现在用户在终端能看到 4 个内建策略，能区分 implemented / preview / planned，
也能在调用 planned 策略时拿到友好的 NotYetImplementedStrategyError。但
multi-strategy seam 仍只对**项目内置**模块开放：所有策略都必须由 mindforge
源码包提供，外部用户无法在不改源码的前提下加入新策略。

v0.12 主题：custom declarative strategy definition architecture
================================================================

让用户能用 **数据**（YAML / JSON / dict）声明一个自定义策略，而不是写
Python 代码。这是项目"安全边界优先"的核心架构选择 —— 任何允许用户写
任意 Python / shell 的"插件"机制都会立刻打破：

- no real LLM by default；
- no .env reads；
- no workspace writes；
- no auto approval；
- no ``human_approved`` literal sneak-in；
- no RAG / embedding / semantic merge；
- 整个 fake-first / ai_draft-only / explicit-approve 信任链。

因此 v0.12 的 *第一刀* 必须把"什么是合法的 custom strategy 声明"这条
契约**先用 Red 测试钉死**，让 Green 实现没有任何空间引入：

- arbitrary Python callable / module path 字段；
- shell / script 字段；
- filesystem write side-effect 字段；
- provider activation 字段（除非显式 opt-in 标志，且仍只能在未来真实
  LLM 路径打开时才生效）；
- 自我宣称 ``status="implemented"`` 的能力（custom strategies 默认只能
  ``planned`` 或 ``preview``，让 v0.11 Slice 4 的 planned guard 自动覆盖
  它们的执行边界）；
- ``human_approved`` 输出字段（直接绕过 review gate）；
- auto-approve 字段。

Slice plan (v0.12)
==================

- v0.12 Slice 1 = 本文件：Red contract for **declarative-only**
  StrategyDefinition + 严格 validation + registry-side planning hooks。
- v0.12 Slice 2 (未来)：Green —— 实现 ``StrategyDefinition`` /
  ``parse_strategy_definition`` / ``InvalidStrategyDefinitionError``，
  并把 custom 策略以 metadata-only 形式接入 registry，复用 v0.11 Slice 4
  的 planned guard 拒绝执行。
- v0.12 Slice 3+ (未来)：Custom 策略的 *安全* runtime（如纯 prompt-template
  执行 + 严格 schema 校验输出 + ai_draft-only），**不**在本 Red 锁定
  范围。

本切片只写 tests / docs / fixtures —— 不改 production code。
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Family A — 模块与公开符号契约（Red 缺口）
# ---------------------------------------------------------------------------


def test_custom_strategy_module_exists() -> None:
    """``mindforge.strategies.custom`` 模块必须存在，承担"declarative
    custom strategy"的唯一边界。Red 期望：当前根本没有这个模块文件。
    """

    p = Path("src/mindforge/strategies/custom.py")
    assert p.exists(), (
        "src/mindforge/strategies/custom.py 尚不存在；"
        "v0.12 Slice 2 Green 必须新增此模块。"
    )


def test_custom_strategy_module_exports_required_symbols() -> None:
    """``mindforge.strategies.custom`` 必须导出 ``StrategyDefinition`` /
    ``parse_strategy_definition`` / ``InvalidStrategyDefinitionError``
    三件套，作为 declarative custom strategy 的稳定 API 面。
    """

    import importlib

    mod = importlib.import_module("mindforge.strategies.custom")
    for name in (
        "StrategyDefinition",
        "parse_strategy_definition",
        "InvalidStrategyDefinitionError",
    ):
        assert hasattr(mod, name), (
            f"mindforge.strategies.custom 缺导出 {name!r}"
        )


def test_invalid_definition_error_is_value_error_subclass() -> None:
    """``InvalidStrategyDefinitionError`` 必须继承 ``ValueError``，与项目
    其它策略层错误（UnknownStrategyError / NotYetImplementedStrategyError）
    保持同一根类，让上层 broad catch 仍能覆盖。
    """

    from mindforge.strategies.custom import InvalidStrategyDefinitionError

    assert issubclass(InvalidStrategyDefinitionError, ValueError)


# ---------------------------------------------------------------------------
# Family B — StrategyDefinition data shape（Red 缺口）
# ---------------------------------------------------------------------------


def _valid_definition_dict() -> dict[str, object]:
    """合法的 declarative strategy definition 样例。

    这里**不含**任何 ``python_callable`` / ``python_path`` / ``shell_command``
    / ``script_path`` / ``filesystem_write`` / ``auto_approve`` 字段，
    完全是数据声明。
    """

    return {
        "strategy_id": "user_concept_review",
        "strategy_version": "0.0.1",
        "display_name": "User Concept Review (Custom)",
        "description": "用户自定义概念复习卡片策略（声明式）。",
        "provider_mode": "deterministic",
        "safety_policy": "ai_draft_only",
        "output_schema_id": "user_concept_review@1",
        "status": "preview",
        "structured_payload_schema": {
            "title": "string",
            "concepts": "list[string]",
        },
        "prompt_template": "Extract concepts from: {raw_text}",
    }


def test_parse_valid_definition_returns_strategy_definition() -> None:
    """``parse_strategy_definition`` 接受合法 dict 返回 ``StrategyDefinition``
    实例（结构化对象，而非保留 raw dict）。
    """

    from mindforge.strategies.custom import (
        StrategyDefinition,
        parse_strategy_definition,
    )

    d = parse_strategy_definition(_valid_definition_dict())
    assert isinstance(d, StrategyDefinition)


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
        "structured_payload_schema",
    ],
)
def test_strategy_definition_has_required_fields(field_name: str) -> None:
    """``StrategyDefinition`` 必须至少包含上述字段（与 v0.11 内建策略的
    8 字段 metadata 对齐 + 多一个 ``structured_payload_schema``）。
    """

    from mindforge.strategies.custom import StrategyDefinition

    fields = set(getattr(StrategyDefinition, "__dataclass_fields__", {}))
    assert field_name in fields, (
        f"StrategyDefinition 缺字段 {field_name!r}；现有：{sorted(fields)}"
    )


# ---------------------------------------------------------------------------
# Family C — Validation: 拒绝缺字段 / 非法值（Red 缺口）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    [
        "strategy_id",
        "output_schema_id",
        "safety_policy",
        "structured_payload_schema",
        "provider_mode",
    ],
)
def test_missing_required_field_is_rejected(missing_field: str) -> None:
    """缺关键字段必须抛 ``InvalidStrategyDefinitionError`` —— 而不是悄悄
    用默认值补全（默认值会让安全字段被绕过）。
    """

    from mindforge.strategies.custom import (
        InvalidStrategyDefinitionError,
        parse_strategy_definition,
    )

    data = _valid_definition_dict()
    data.pop(missing_field, None)
    with pytest.raises(InvalidStrategyDefinitionError):
        parse_strategy_definition(data)


def test_safety_policy_must_be_ai_draft_only() -> None:
    """``safety_policy`` 字段不允许除 ``ai_draft_only`` 之外的取值。
    任何 ``auto_approve`` / ``write_vault`` 之类的值都必须被拒。
    """

    from mindforge.strategies.custom import (
        InvalidStrategyDefinitionError,
        parse_strategy_definition,
    )

    data = _valid_definition_dict()
    data["safety_policy"] = "auto_approve"
    with pytest.raises(InvalidStrategyDefinitionError):
        parse_strategy_definition(data)


def test_status_implemented_is_rejected_for_custom_definition() -> None:
    """Custom strategy **不允许**自我宣称 ``status="implemented"``。

    这条契约让 v0.11 Slice 4 的 planned guard 自动覆盖所有 custom 策略
    的执行边界 —— 用户即便恶意把 status 写成 implemented，也会在 parse
    阶段被拒，而不是悄悄进入可执行路径。

    custom 默认只能是 ``planned`` 或 ``preview``。
    """

    from mindforge.strategies.custom import (
        InvalidStrategyDefinitionError,
        parse_strategy_definition,
    )

    data = _valid_definition_dict()
    data["status"] = "implemented"
    with pytest.raises(InvalidStrategyDefinitionError):
        parse_strategy_definition(data)


def test_real_opt_in_provider_mode_requires_explicit_flag() -> None:
    """``provider_mode="real_opt_in"`` 必须配合显式
    ``real_provider_opt_in: True`` 字段；缺该字段必须拒绝。

    这是为了让"真实 LLM 路径"在 declarative 层有一道额外的显式开关，
    而不是 provider_mode 字符串单独决定。
    """

    from mindforge.strategies.custom import (
        InvalidStrategyDefinitionError,
        parse_strategy_definition,
    )

    data = _valid_definition_dict()
    data["provider_mode"] = "real_opt_in"
    # 故意不加 real_provider_opt_in 字段
    with pytest.raises(InvalidStrategyDefinitionError):
        parse_strategy_definition(data)


# ---------------------------------------------------------------------------
# Family D — Validation: 拒绝 arbitrary code / shell / FS write 字段（Red）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "python_callable",
        "python_path",
        "module_path",
        "shell_command",
        "script_path",
        "exec",
        "command",
        "filesystem_write",
        "vault_write",
        "auto_approve",
    ],
)
def test_arbitrary_code_or_shell_field_is_rejected(forbidden_field: str) -> None:
    """任何 arbitrary Python / shell / FS write 字段出现在 custom 定义里
    都必须被 ``parse_strategy_definition`` 拒绝。

    这是 declarative-only 契约的核心：用户提供的策略只能是 *数据*，
    不能携带可执行 payload —— 即便是字符串形式的 shell command 也不行。
    """

    from mindforge.strategies.custom import (
        InvalidStrategyDefinitionError,
        parse_strategy_definition,
    )

    data = _valid_definition_dict()
    data[forbidden_field] = "anything"
    with pytest.raises(InvalidStrategyDefinitionError):
        parse_strategy_definition(data)


def test_human_approved_literal_in_schema_is_rejected() -> None:
    """``structured_payload_schema`` 内部出现 ``human_approved`` 字段名
    必须被拒绝 —— 否则 custom 策略可以输出已审核状态字段，绕过
    approver 显式 review gate。
    """

    from mindforge.strategies.custom import (
        InvalidStrategyDefinitionError,
        parse_strategy_definition,
    )

    data = _valid_definition_dict()
    data["structured_payload_schema"] = {
        "title": "string",
        "human_approved": "bool",
    }
    with pytest.raises(InvalidStrategyDefinitionError):
        parse_strategy_definition(data)


# ---------------------------------------------------------------------------
# Family E — Registry-side planning hooks（Red 缺口）
# ---------------------------------------------------------------------------


def test_parsed_definition_can_become_strategy_metadata() -> None:
    """``StrategyDefinition`` 必须能被无损地映射为 v0.11 ``StrategyMetadata``
    （8 字段子集），让 ``mindforge strategies list`` 在未来 v0.12 Green
    中能像展示 built-in 一样展示 custom 策略。
    """

    from mindforge.strategies import StrategyMetadata
    from mindforge.strategies.custom import (
        StrategyDefinition,
        parse_strategy_definition,
    )

    d = parse_strategy_definition(_valid_definition_dict())
    assert isinstance(d, StrategyDefinition)
    # 期望 v0.12 Green 提供 to_metadata() 或等价适配函数。
    assert hasattr(d, "to_metadata"), (
        "StrategyDefinition 应提供 to_metadata() 适配到 v0.11 StrategyMetadata"
    )
    meta = d.to_metadata()
    assert isinstance(meta, StrategyMetadata)
    assert meta.strategy_id == "user_concept_review"
    assert meta.safety_policy == "ai_draft_only"
    # custom 永远不能自我宣称 implemented；至少是 planned/preview
    assert meta.status in {"planned", "preview"}


# ---------------------------------------------------------------------------
# Family F — 模块源码安全 source-scan（Red 缺口）
# ---------------------------------------------------------------------------


def test_custom_module_source_has_no_arbitrary_execution_imports() -> None:
    """``mindforge.strategies.custom`` 模块源码不能引入任何 arbitrary code
    execution / shell / .env / network / LLM / Cubox 触点。

    Red 期望：模块文件尚不存在；FileNotFoundError 即视为 expected Red。
    """

    p = Path("src/mindforge/strategies/custom.py")
    assert p.exists(), (
        "src/mindforge/strategies/custom.py 尚不存在；v0.12 Green 待实现。"
    )
    src = p.read_text(encoding="utf-8")
    forbidden = (
        "subprocess",
        "os.system",
        "eval(",
        "exec(",
        "importlib.import_module",
        "__import__",
        "load_dotenv",
        "LLMClient(",
        "import requests",
        "import httpx",
        "cubox.app",
        "UPSTAGE_API_KEY",
    )
    for token in forbidden:
        assert token not in src, (
            f"custom.py 出现越界引用 {token!r}；declarative-only 必须避免任何"
            " arbitrary execution / network / secrets 触点。"
        )


# ---------------------------------------------------------------------------
# Family G — Docs / onboarding（Red 缺口）
# ---------------------------------------------------------------------------


def test_custom_strategy_doc_exists_and_explains_declarative_safety() -> None:
    """``README.zh-CN.md`` 必须向用户解释关键安全契约：

    - declarative 才被支持；
    - 不支持 arbitrary Python plugin；
    - 不支持 shell/script strategy；
    - 默认 fake/deterministic、real provider 只能 explicit opt-in；
    - ai_draft 永远只是 ai_draft；最终人审动作由 approver 单独执行。
    """

    p = Path("README.zh-CN.md")
    assert p.exists(), "README.zh-CN.md 尚不存在"
    text = p.read_text(encoding="utf-8").lower()
    for token in (
        "declarative",
        "no arbitrary python",
        "no shell",
        "ai_draft",
        "explicit opt-in",
    ):
        assert token in text, f"README.zh-CN.md 缺关键说明 {token!r}"


# ---------------------------------------------------------------------------
# Family H — Sanity Green baselines（保护 v0.11 已建立的契约）
# ---------------------------------------------------------------------------


def test_existing_builtin_registry_still_works() -> None:
    """v0.12 Red **不能**让 v0.11 built-in registry 出现回归。"""

    from mindforge.strategies import available_strategies, list_strategies

    names = available_strategies()
    assert "default_knowledge_card" in names
    assert "five_stage" in names
    assert "concept_extraction" in names
    assert "action_item" in names
    assert len(list_strategies()) >= 4


def test_existing_planned_guard_still_works() -> None:
    """v0.11 Slice 4 planned guard 不能被 v0.12 Red 回退。"""

    from mindforge.strategies import (
        NotYetImplementedStrategyError,
        build_strategy,
    )
    from mindforge.strategies.base import StrategyContext

    with pytest.raises(NotYetImplementedStrategyError):
        build_strategy("action_item", StrategyContext())
