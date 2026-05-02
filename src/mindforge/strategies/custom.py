"""Custom **declarative** strategy definitions（v0.12 Slice 1 Green）。

为什么是 declarative，而不是 plugin runtime？
================================================

v0.11 已经把"内建策略 + planned guard"打磨稳定，外部用户却仍只能改源码
新增策略。一个朴素的"plugin"设计会让用户能写：

- 任意 Python 模块 / callable / 入口函数；
- shell / script 字段；
- 文件系统写入 side-effect；
- 自动 approve；
- 直接输出 ``human_approved`` 状态。

任何一条都会立刻打破项目"fake-first / no-real-LLM-by-default /
ai_draft-only / explicit approve"的信任链。因此 v0.12 选择
**declarative-only**：custom strategy 是 *数据*（YAML / JSON / dict），
本模块只负责 *parse + validate*，**不**承担执行。

本模块的职责（高内聚）
========================

- 暴露 :class:`StrategyDefinition` 不可变 dataclass 作为唯一数据契约；
- 暴露 :func:`parse_strategy_definition` 把 dict 校验并转换为 dataclass；
- 暴露 :class:`InvalidStrategyDefinitionError`（``ValueError`` 子类）作为
  统一拒绝出口；
- 提供 :meth:`StrategyDefinition.to_metadata` 把自己映射到 v0.11
  :class:`mindforge.strategies.StrategyMetadata` —— 让未来的
  ``mindforge strategies list`` 能像展示内建策略一样展示 custom 的
  metadata（**仍然不能执行**，由 v0.11 Slice 4 planned guard 兜底）。

本模块明确**不**承担
====================

- 不加载文件系统（loading source 留给 v0.12 Slice 2 + Green）；
- 不注册到 ``StrategyRegistry``（执行接入留给 v0.12 Slice 3+）；
- 不调用任何 provider / LLM / network；
- 不读取 ``.env`` / 不读取 user vault；
- 不写 workspace；
- 不持有 prompt / runtime / Typer command / RunLogger。

源码安全 source-scan 契约
==========================

本文件**不允许**任何 arbitrary code execution / shell / network /
secrets / Cubox / Upstage / dotenv 触点（具体禁用 token 清单由
``test_custom_module_source_has_no_arbitrary_execution_imports``
维护，本注释刻意不列出字面量以免触发自身 source-scan）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .registry import StrategyMetadata


class InvalidStrategyDefinitionError(ValueError):
    """Custom strategy definition 校验失败。

    继承 :class:`ValueError` 与 :class:`UnknownStrategyError` /
    :class:`NotYetImplementedStrategyError` 同根，让上层 broad except
    仍能 catch；同时类身份独立，便于精确分流。
    """


# 中文学习型注释：白名单字段 = declarative-only 的硬边界。
# 任何不在此集合的 key（典型如 python_callable / shell_command /
# auto_approve）一律拒绝，从源头切断"用户在数据里夹带可执行 payload"
# 这种攻击面，而不是给禁用清单做穷举（黑名单永远漏）。
_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "strategy_id",
        "strategy_version",
        "display_name",
        "description",
        "provider_mode",
        "safety_policy",
        "output_schema_id",
        "status",
        "structured_payload_schema",
        "prompt_template",
        "real_provider_opt_in",
    }
)

_REQUIRED_FIELDS: tuple[str, ...] = (
    "strategy_id",
    "strategy_version",
    "display_name",
    "description",
    "provider_mode",
    "safety_policy",
    "output_schema_id",
    "status",
    "structured_payload_schema",
)

_ALLOWED_PROVIDER_MODES: frozenset[str] = frozenset(
    {"fake_only", "deterministic", "real_opt_in"}
)

# 中文学习型注释：custom strategy 永远只能 planned 或 preview。
# 不允许 ``implemented`` 让 v0.11 Slice 4 的 planned guard **自动覆盖**
# 所有 custom 策略的执行边界 —— 即便用户恶意把 status 写成 implemented，
# 也会在 parse 阶段就被拒，而不是悄悄进入可执行路径。
_ALLOWED_STATUSES: frozenset[str] = frozenset({"planned", "preview"})

_SAFETY_POLICY_FIXED: str = "ai_draft_only"


@dataclass(frozen=True)
class StrategyDefinition:
    """声明式自定义策略数据契约。

    与 v0.11 内建策略的 8 字段 metadata 对齐，多一个
    ``structured_payload_schema``（声明输出形状）+ 两个可选字段
    ``prompt_template`` / ``real_provider_opt_in``。

    本 dataclass 是 *数据*，不是 *代码*：任何字段都不会在 parse 阶段
    被解释为可执行 payload。frozen=True 防止 parse 后被改写。
    """

    strategy_id: str
    strategy_version: str
    display_name: str
    description: str
    provider_mode: str
    safety_policy: str
    output_schema_id: str
    status: str
    structured_payload_schema: Mapping[str, Any]
    prompt_template: str = ""
    real_provider_opt_in: bool = False

    def to_metadata(self) -> StrategyMetadata:
        """映射到 v0.11 :class:`StrategyMetadata`。

        让 ``mindforge strategies list`` 能用同一个 8 字段视图展示
        custom 策略 —— UX 一致性 + planned guard 复用。
        """

        return StrategyMetadata(
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            display_name=self.display_name,
            description=self.description,
            provider_mode=self.provider_mode,
            safety_policy=self.safety_policy,
            output_schema_id=self.output_schema_id,
            status=self.status,
        )


def _reject(msg: str) -> "InvalidStrategyDefinitionError":
    return InvalidStrategyDefinitionError(msg)


def parse_strategy_definition(data: Mapping[str, Any]) -> StrategyDefinition:
    """把 dict 校验并构造为 :class:`StrategyDefinition`。

    校验顺序（每一步都拒绝即时返回，错误消息含字段路径，便于用户修复）：

    1. 顶层必须是 mapping；
    2. 所有 key 必须在 :data:`_ALLOWED_FIELDS` 白名单；
    3. 所有必填字段必须存在；
    4. ``safety_policy`` 必须等于 ``"ai_draft_only"``；
    5. ``status`` 必须 ∈ {planned, preview}；
    6. ``provider_mode`` 必须 ∈ {fake_only, deterministic, real_opt_in}；
    7. ``provider_mode == "real_opt_in"`` 时必须显式带 ``real_provider_opt_in: True``；
    8. ``structured_payload_schema`` 必须是 mapping，且其 key 不能含
       ``human_approved`` —— 防止 custom 输出绕过 review gate。

    任何分支都不读 ``.env`` / 不调 LLM / 不写 workspace / 不执行任何
    用户提供字段的内容。
    """

    if not isinstance(data, Mapping):
        raise _reject(
            f"strategy definition must be a mapping; got {type(data).__name__}"
        )

    keys = set(data.keys())
    extras = keys - _ALLOWED_FIELDS
    if extras:
        # 中文学习型注释：白名单拒绝是 declarative-only 的最关键防线。
        # 任意 unknown key（python_callable / shell_command / auto_approve …）
        # 都会在这里被一并拦下，而不是在每个字段单独 if 判定。
        raise _reject(
            f"strategy definition contains unsupported field(s): "
            f"{sorted(extras)}; only declarative fields are allowed "
            f"({sorted(_ALLOWED_FIELDS)})."
        )

    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if missing:
        raise _reject(
            f"strategy definition missing required field(s): {missing}"
        )

    safety_policy = data["safety_policy"]
    if safety_policy != _SAFETY_POLICY_FIXED:
        raise _reject(
            f"safety_policy must be {_SAFETY_POLICY_FIXED!r}; "
            f"got {safety_policy!r}. Custom strategies cannot opt out of the "
            "ai_draft-only contract."
        )

    status = data["status"]
    if status not in _ALLOWED_STATUSES:
        raise _reject(
            f"status must be one of {sorted(_ALLOWED_STATUSES)} for custom "
            f"strategies; got {status!r}. Custom strategies cannot self-declare "
            "as 'implemented' — runnability is gated by built-in factories only."
        )

    provider_mode = data["provider_mode"]
    if provider_mode not in _ALLOWED_PROVIDER_MODES:
        raise _reject(
            f"provider_mode must be one of {sorted(_ALLOWED_PROVIDER_MODES)}; "
            f"got {provider_mode!r}."
        )

    real_opt_in_flag = bool(data.get("real_provider_opt_in", False))
    if provider_mode == "real_opt_in" and not real_opt_in_flag:
        raise _reject(
            "provider_mode='real_opt_in' requires explicit "
            "real_provider_opt_in=True in the definition; this is a second "
            "switch on top of the runtime opt-in to keep real-LLM activation "
            "deliberate."
        )

    schema = data["structured_payload_schema"]
    if not isinstance(schema, Mapping):
        raise _reject(
            "structured_payload_schema must be a mapping of field name → "
            f"declared type; got {type(schema).__name__}."
        )
    if "human_approved" in schema:
        raise _reject(
            "structured_payload_schema must not declare a 'human_approved' "
            "field — approval state is owned by the approver, never produced "
            "by a strategy."
        )

    return StrategyDefinition(
        strategy_id=str(data["strategy_id"]),
        strategy_version=str(data["strategy_version"]),
        display_name=str(data["display_name"]),
        description=str(data["description"]),
        provider_mode=str(provider_mode),
        safety_policy=str(safety_policy),
        output_schema_id=str(data["output_schema_id"]),
        status=str(status),
        structured_payload_schema=dict(schema),
        prompt_template=str(data.get("prompt_template", "")),
        real_provider_opt_in=real_opt_in_flag,
    )


__all__ = [
    "InvalidStrategyDefinitionError",
    "StrategyDefinition",
    "parse_strategy_definition",
]
