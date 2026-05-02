"""v0.12 Slice 4 — Custom Preview Registry Integration Red contract tests.

v0.12 Slice 1 锁定了 ``StrategyDefinition`` 的形状与校验，Slice 2 锁
定了从显式安全路径加载文件的边界，Slice 3 把 discovery 接入了 CLI 的
只读元数据展示。但还有一个**关键边界**没有 Red 钉死：

如果一个调用方（外部脚本 / 未来的 ``mindforge process --custom-path``
扩展 / 测试 fixture）拿到了 discovered 的 custom strategy id 并把它
传给 :func:`mindforge.strategies.build_strategy`，目前会发生什么？

**今天的行为**：``build_strategy(custom_id, ctx)`` 抛 ``UnknownStrategyError``
—— 与 v0.11 ``"action_item"`` 等 *已注册元数据但未实现* 策略给出的
``NotYetImplementedStrategyError`` 形成 UX 错配：用户在 ``strategies
list --custom-path`` 明明看见了名字，却被告知"未知"。

Slice 4 主题：custom strategy non-executable preview integration /
registry metadata merge / no runtime activation
=========================================================================

本切片只写 tests / docs / fixtures —— 不改 production code。目标是把
"custom 定义 ↔ registry execution gate"这一刀的契约用 Red 测试钉死，
让 Slice 4 Green 实现没有任何空间引入：

- custom strategy runtime；
- arbitrary Python plugin；
- shell / script strategy；
- 把 custom 自动注入 ``_FACTORIES`` 让其变可执行；
- 用真实 LLM provider 跑 custom；
- 把 custom 作为隐式默认策略；
- 在 build path 里读取 ``.env`` / 写 vault / 隐式扫描；
- 把 invalid custom 当 planned 兜底执行。

本切片明确**不**实现：

- custom strategy 真实运行；
- custom strategy 自动 approve；
- ``mindforge process --custom-path`` 的真实接入；
- 任何 plugin 注册器 / 入口扫描器。

Red 期望
========

绝大多数测试因为 production 还没有 ``build_strategy(..., custom_path=...)``
重载、还没有"custom id 走 NotYetImplemented 友好分流"、discover 还
不拒绝重复 id、docs 还没补 preview→implementation 演进路径而失败；
少量 sanity baseline 保护现有 Slice 1/2/3 行为。所有失败必须是清晰
的 production gap，而不是 import 错误 / 测试 bug / 环境问题。
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml

from mindforge.strategies import (
    NotYetImplementedStrategyError,
    StrategyContext,
    UnknownStrategyError,
    available_strategies,
    build_strategy,
    discover_strategies,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


_VALID_DICT: dict[str, object] = {
    "strategy_id": "user_concept_review",
    "strategy_version": "0.0.1",
    "display_name": "User Concept Review",
    "description": "用户自定义概念复习卡片策略（声明式，preview）。",
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


def _write_yaml(path: Path, data: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _fake_strategy_context() -> StrategyContext:
    """构造一个最小的 StrategyContext —— 不构造真实 LLMClient / 不读
    .env，仅用于 build_strategy 的负向断言。

    既有 built-in ``default_knowledge_card`` 是离线 deterministic 策略，
    不消费 ``client``；本 fixture 因此不需要 LLM 实例。
    """

    return StrategyContext(
        client=None,
        prompts_dir=Path("prompts"),
        prompt_versions={},
        learning_tracks_text="",
    )


# ---------------------------------------------------------------------------
# Family A — Metadata merge contract（Red 缺口）
# ---------------------------------------------------------------------------


def test_discover_strategies_preserves_builtins(tmp_path: Path) -> None:
    """加 custom 定义不能挤掉 built-in。"""

    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    metas = discover_strategies(custom_path=tmp_path)
    ids = {m.strategy_id for m in metas}
    for name in (
        "default_knowledge_card",
        "five_stage",
        "concept_extraction",
        "action_item",
    ):
        assert name in ids


def test_discover_strategies_custom_includes_full_metadata(
    tmp_path: Path,
) -> None:
    """custom metadata 必须填满 8 字段（与 built-in 同形）。"""

    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    metas = discover_strategies(custom_path=tmp_path)
    custom = next(m for m in metas if m.strategy_id == "user_concept_review")
    for field in (
        "strategy_id",
        "strategy_version",
        "display_name",
        "description",
        "provider_mode",
        "safety_policy",
        "output_schema_id",
        "status",
    ):
        value = getattr(custom, field)
        assert value, f"custom metadata 字段 {field!r} 为空"


def test_discover_strategies_custom_status_is_preview_or_planned(
    tmp_path: Path,
) -> None:
    """v0.11 Slice 4 planned guard 自动覆盖；custom status 必须 ∈
    {planned, preview}。"""

    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    metas = discover_strategies(custom_path=tmp_path)
    custom = next(m for m in metas if m.strategy_id == "user_concept_review")
    assert custom.status in {"planned", "preview"}


def test_discover_strategies_rejects_duplicate_strategy_id(
    tmp_path: Path,
) -> None:
    """custom 文件若声明的 ``strategy_id`` 与 built-in 撞名，必须 fail-loud
    友好错误（含两边来源），而不是悄悄覆盖或并列。
    """

    dup = dict(_VALID_DICT)
    dup["strategy_id"] = "five_stage"  # 撞 built-in
    dup["output_schema_id"] = "five_stage@1"
    _write_yaml(tmp_path / "dup.yaml", dup)
    with pytest.raises(Exception) as excinfo:
        discover_strategies(custom_path=tmp_path)
    msg = str(excinfo.value).lower()
    assert "five_stage" in msg
    assert "duplicate" in msg or "already" in msg or "conflict" in msg


def test_discover_strategies_empty_dir_returns_only_builtins(
    tmp_path: Path,
) -> None:
    """空目录 → 与不传 path 等价。Sanity baseline（应 Green）。"""

    metas = discover_strategies(custom_path=tmp_path)
    builtin = discover_strategies()
    assert {m.strategy_id for m in metas} == {m.strategy_id for m in builtin}


# ---------------------------------------------------------------------------
# Family B — Executable vs preview-only boundary（Red 缺口）
# ---------------------------------------------------------------------------


def test_build_strategy_with_discovered_custom_raises_not_yet_implemented(
    tmp_path: Path,
) -> None:
    """``build_strategy`` 必须支持把 custom_path 一并传入并对 custom id
    抛 ``NotYetImplementedStrategyError`` —— 而不是 ``UnknownStrategyError``。

    今天 build_strategy 不知道 custom path，因此 custom id 会被报为
    "unknown"；UX 与 ``strategies list --custom-path`` 已展示该名字
    严重错配。Slice 4 Green 要把这条边界统一：discovered 但未实现 →
    NotYetImplemented；未 discovered → Unknown。
    """

    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    ctx = _fake_strategy_context()
    with pytest.raises(NotYetImplementedStrategyError) as excinfo:
        build_strategy("user_concept_review", ctx, custom_path=tmp_path)  # type: ignore[call-arg]
    msg = str(excinfo.value).lower()
    assert "user_concept_review" in msg
    assert "preview" in msg or "not yet" in msg or "discovery" in msg


def test_build_strategy_with_unknown_custom_id_raises_unknown(
    tmp_path: Path,
) -> None:
    """名字既不在 built-in 也不在 custom_path 内 → 仍是
    ``UnknownStrategyError``（非 NotYetImplemented）。两类错误必须分流。
    """

    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    ctx = _fake_strategy_context()
    with pytest.raises(UnknownStrategyError):
        build_strategy("totally_made_up", ctx, custom_path=tmp_path)  # type: ignore[call-arg]


def test_build_strategy_with_custom_does_not_call_provider(
    tmp_path: Path,
) -> None:
    """即便 build_strategy 接受 custom_path，也绝不能在 custom-preview
    分支中触发 provider —— ``_DummyLLM`` 的 chat 会抛 AssertionError，
    若被调用本测试就会 fail。"""

    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    ctx = _fake_strategy_context()
    with pytest.raises(NotYetImplementedStrategyError):
        build_strategy("user_concept_review", ctx, custom_path=tmp_path)  # type: ignore[call-arg]


def test_invalid_custom_does_not_become_executable(tmp_path: Path) -> None:
    """非法 custom 文件下 build_strategy 不能因为 metadata 错配而回退到
    任何默认策略；必须抛 ``InvalidStrategyDefinitionError`` 或其子类。
    """

    bad = dict(_VALID_DICT)
    bad["safety_policy"] = "auto_approve"
    _write_yaml(tmp_path / "bad.yaml", bad)
    from mindforge.strategies.custom import InvalidStrategyDefinitionError

    ctx = _fake_strategy_context()
    with pytest.raises(InvalidStrategyDefinitionError):
        build_strategy("user_concept_review", ctx, custom_path=tmp_path)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Family C — Registry boundary（Red 缺口 + invariant）
# ---------------------------------------------------------------------------


def test_registry_factories_remains_builtin_only_after_discovery(
    tmp_path: Path,
) -> None:
    """custom discovery 不能在过程中把名字写入 ``_FACTORIES``。
    内部映射快照必须保持只含 built-in 可执行项。"""

    from mindforge.strategies import registry as reg

    before = dict(reg._FACTORIES)  # type: ignore[attr-defined]
    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    discover_strategies(custom_path=tmp_path)
    after = dict(reg._FACTORIES)  # type: ignore[attr-defined]
    assert before == after, (
        "discover_strategies 不允许把 custom 名字写进 _FACTORIES; "
        f"diff: {set(after) - set(before)}"
    )


def test_available_strategies_remains_builtin_only_after_discovery(
    tmp_path: Path,
) -> None:
    """``available_strategies()`` 是"可执行 / planned 内建"的稳定快照；
    discovery 不能把 custom 名字写进去（custom 是元数据视图，不是
    registry 注册项）。"""

    before = set(available_strategies())
    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    discover_strategies(custom_path=tmp_path)
    after = set(available_strategies())
    assert before == after


def test_registry_module_source_has_no_arbitrary_execution_tokens() -> None:
    """registry.py 必须保持 declarative 边界：不导入任意 module / 不
    执行 shell / 不构造 LLMClient / 不读 .env / 不联网。"""

    src = Path("src/mindforge/strategies/registry.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "subprocess",
        "os.system",
        "eval(",
        "exec(",
        "importlib.import_module",
        "__import__",
        "LLMClient(",
        "import requests",
        "import httpx",
        "load_dotenv",
        "Path.home(",
        "expanduser",
        ".obsidian",
    )
    for token in forbidden:
        assert token not in src, (
            f"registry.py 出现越界触点 {token!r}；registry 必须保持 "
            "declarative + non-execution 边界。"
        )


# ---------------------------------------------------------------------------
# Family D — UX / docs（Red 缺口）
# ---------------------------------------------------------------------------


def test_unknown_strategy_message_lists_implemented_alternatives() -> None:
    """``UnknownStrategyError`` 消息必须列出至少一个 implemented 替代
    （UX 上让用户立刻知道"我能跑哪些"）。"""

    ctx = _fake_strategy_context()
    with pytest.raises(UnknownStrategyError) as excinfo:
        build_strategy("totally_made_up", ctx)
    msg = str(excinfo.value).lower()
    assert (
        "five_stage" in msg
        or "default_knowledge_card" in msg
        or "implemented" in msg
    )


def test_custom_strategy_doc_explains_preview_to_implementation_path() -> None:
    """``docs/CUSTOM_STRATEGY.md`` 必须解释 preview → 未来 implementation
    的安全演进路径（即"如何把一个 preview 定义变成可执行策略"），并
    再次重申不会引入 arbitrary plugin / shell / 默认真实 LLM。
    """

    p = Path("docs/CUSTOM_STRATEGY.md")
    text = p.read_text(encoding="utf-8").lower()
    for token in (
        "preview to",
        "future implementation",
        "no arbitrary python",
        "no shell",
    ):
        assert token in text, (
            f"docs/CUSTOM_STRATEGY.md 缺 preview→implementation 演进说明 "
            f"{token!r}"
        )


def test_custom_preview_error_message_explains_discovery_only_status() -> None:
    """custom preview 被 build_strategy 拒绝时，错误消息必须包含
    "preview" 或 "discovery" 字面量（让用户立刻明白这不是 typo 而是
    "已发现但还不能跑"）。"""

    ctx = _fake_strategy_context()
    # docs check 已在上面；这里聚焦运行时错误消息。
    import tempfile

    with tempfile.TemporaryDirectory() as tdir:
        f = Path(tdir) / "u.yaml"
        _write_yaml(f, _VALID_DICT)
        try:
            build_strategy(
                "user_concept_review", ctx, custom_path=Path(tdir)
            )  # type: ignore[call-arg]
        except NotYetImplementedStrategyError as exc:
            msg = str(exc).lower()
            assert "preview" in msg or "discovery" in msg, msg
        else:
            raise AssertionError(
                "build_strategy(custom_id, ctx, custom_path=...) 未抛 "
                "NotYetImplementedStrategyError"
            )


# ---------------------------------------------------------------------------
# Family E — Sanity Green baselines
# ---------------------------------------------------------------------------


def test_v012_slice3_discover_strategies_still_works(tmp_path: Path) -> None:
    """Slice 3 Green 行为不能因为 Slice 4 Red 而回退。"""

    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    metas = discover_strategies(custom_path=tmp_path)
    assert any(m.strategy_id == "user_concept_review" for m in metas)


def test_existing_builtin_build_strategy_still_works() -> None:
    """built-in implemented 策略必须仍可构造（``default_knowledge_card``
    是离线 deterministic）。"""

    pkg = importlib.import_module("mindforge.strategies")
    ctx = _fake_strategy_context()
    s = pkg.build_strategy("default_knowledge_card", ctx)
    assert s is not None
