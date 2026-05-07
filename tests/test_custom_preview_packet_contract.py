"""v0.12 Slice 5 — Custom Strategy Dry-Run Preview Packet Red contract tests.

v0.12 Slice 1/2/3/4 锁定了 declarative 形状、安全加载、CLI discovery
与 registry 拒绝执行边界。还差最后一块拼图：当用户想"在终端确认我刚
写的 custom YAML 长什么样、字段是否合理、它会不会被误当成 ai_draft /
human_approved"时，我们需要一个 **review-only preview packet** —— 把
custom definition 的元数据 + 校验结果 打包成一个稳定的、可被 CLI /
未来 UI / 文档生成器统一消费的只读包。

Slice 5 主题：custom strategy dry-run preview packet / review-only
presentation / no approval or execution
=========================================================================

本切片只写 tests / docs / fixtures —— 不改 production code。目标是把
"preview packet 数据结构 + presenter UX + 行为边界"用 Red 测试钉死，
让 Slice 5 Green 实现没有任何空间引入：

- 把 preview packet 当 ai_draft；
- 把 preview packet 当 human_approved；
- 在 packet 构造路径上调用 LLM / 写 vault / approve / 调
  ``CardWriter`` / 调 ``ApprovalService``；
- 让 packet 字段含 ``human_approved`` 字面量；
- 让 packet 暴露 raw Python repr / Traceback；
- 让 packet 的 ``executable`` 字段为 ``True``。

本切片明确**不**实现：

- custom strategy runtime；
- 真实 LLM provider activation；
- 真实 dogfooding；
- arbitrary Python plugin；
- shell / script strategy。

Red 期望
========

production 还没有 ``mindforge.strategies.preview_packet`` 模块、还没
有 ``build_custom_preview_packet`` / ``render_custom_preview_packet``
API、docs 还没补 review-only 段落。绝大多数测试在"模块不存在 / 函数
不存在 / docs 缺 token"上失败，少量 sanity baseline 保护现有 Slice
3/4 行为。所有失败必须是清晰的 production gap，而不是 import 错误 /
测试 bug / 环境问题。
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml


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


def _load_preview_packet_module():
    """统一加载 ``mindforge.strategies.preview_packet``；不存在 → 显式 fail。"""

    return importlib.import_module("mindforge.strategies.preview_packet")


# ---------------------------------------------------------------------------
# Family A — preview packet 数据形状（Red 缺口）
# ---------------------------------------------------------------------------


def test_preview_packet_module_exists() -> None:
    """``mindforge.strategies.preview_packet`` 必须以独立模块存在。

    不在 ``custom.py`` / ``custom_loader.py`` / ``__init__.py`` 内挤
    更多职责 —— preview packet 是面向 *展示与 review* 的另一条
    use-case 切面，独立成模块以保持高内聚。
    """

    mod = _load_preview_packet_module()
    assert mod is not None


def test_build_custom_preview_packet_exists() -> None:
    """``build_custom_preview_packet`` 必须公开。"""

    mod = _load_preview_packet_module()
    assert hasattr(mod, "build_custom_preview_packet")


def test_preview_packet_includes_required_fields() -> None:
    """packet 必须含 8 字段元数据 + ``validation_status`` + ``executable``
    + ``kind`` —— 形成稳定可被消费的 schema。"""

    from mindforge.strategies.custom import parse_strategy_definition

    mod = _load_preview_packet_module()
    definition = parse_strategy_definition(_VALID_DICT)
    packet = mod.build_custom_preview_packet(definition)
    for key in (
        "strategy_id",
        "strategy_version",
        "display_name",
        "description",
        "provider_mode",
        "safety_policy",
        "output_schema_id",
        "status",
        "validation_status",
        "executable",
        "kind",
    ):
        assert key in packet, f"preview packet 缺字段 {key!r}: {packet!r}"


def test_preview_packet_marks_not_executable_and_preview_only() -> None:
    """``executable`` 必须 False，``kind`` 必须显式 preview_only。"""

    from mindforge.strategies.custom import parse_strategy_definition

    mod = _load_preview_packet_module()
    definition = parse_strategy_definition(_VALID_DICT)
    packet = mod.build_custom_preview_packet(definition)
    assert packet["executable"] is False, packet
    assert packet["kind"] == "preview_only", packet
    assert packet["status"] in {"planned", "preview"}, packet
    assert packet["validation_status"] == "valid", packet


def test_preview_packet_does_not_include_human_approved_field() -> None:
    """packet 必须**不含** ``human_approved`` 字段，避免任何 serializer
    / presenter 误把 packet 当成 approved card。
    """

    from mindforge.strategies.custom import parse_strategy_definition

    mod = _load_preview_packet_module()
    definition = parse_strategy_definition(_VALID_DICT)
    packet = mod.build_custom_preview_packet(definition)
    assert "human_approved" not in packet, packet


# ---------------------------------------------------------------------------
# Family B — 构造 packet 不能产生任何执行 / approval 副作用
# ---------------------------------------------------------------------------


def test_building_preview_packet_does_not_call_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """构造 packet 不能触发 LLMClient 构造。"""

    import mindforge.llm as llm_mod
    from mindforge.strategies.custom import parse_strategy_definition

    def _explode(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "preview packet builder must not construct LLMClient"
        )

    monkeypatch.setattr(llm_mod, "LLMClient", _explode)
    mod = _load_preview_packet_module()
    definition = parse_strategy_definition(_VALID_DICT)
    mod.build_custom_preview_packet(definition)


def test_preview_packet_module_source_has_no_execution_or_io_tokens() -> None:
    """preview_packet.py 必须保持 declarative + presentation：不构造
    LLM / 不写 vault / 不读 .env / 不联网 / 不持有 CardWriter /
    ApprovalService 引用。"""

    p = Path("src/mindforge/strategies/preview_packet.py")
    assert p.exists(), "preview_packet.py 必须存在"
    src = p.read_text(encoding="utf-8")
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
        "CardWriter(",
        "ApprovalService(",
        "approve_card(",
        "human_approved",
    )
    for token in forbidden:
        assert token not in src, (
            f"preview_packet.py 出现越界触点 {token!r}; "
            "preview packet 必须保持 declarative + presentation 边界。"
        )


def test_building_preview_packet_does_not_register_executable() -> None:
    """构造 packet 不能改 ``available_strategies()`` / ``_FACTORIES``。"""

    from mindforge.strategies import available_strategies
    from mindforge.strategies import registry as reg
    from mindforge.strategies.custom import parse_strategy_definition

    mod = _load_preview_packet_module()
    before_names = set(available_strategies())
    before_factories = dict(reg._FACTORIES)  # type: ignore[attr-defined]
    definition = parse_strategy_definition(_VALID_DICT)
    mod.build_custom_preview_packet(definition)
    assert set(available_strategies()) == before_names
    assert dict(reg._FACTORIES) == before_factories  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Family C — Presenter UX（Red 缺口）
# ---------------------------------------------------------------------------


def test_render_custom_preview_packet_exists() -> None:
    """``render_custom_preview_packet(packet) -> str`` 必须公开。"""

    mod = _load_preview_packet_module()
    assert hasattr(mod, "render_custom_preview_packet")


def test_render_custom_preview_packet_user_readable() -> None:
    """渲染输出必须 user-readable：含 strategy_id、"not executable"、
    "preview" 字面量；不含 raw repr / Traceback。"""

    from mindforge.strategies.custom import parse_strategy_definition

    mod = _load_preview_packet_module()
    definition = parse_strategy_definition(_VALID_DICT)
    packet = mod.build_custom_preview_packet(definition)
    text = mod.render_custom_preview_packet(packet)
    assert isinstance(text, str)
    lower = text.lower()
    assert "user_concept_review" in lower
    assert "not executable" in lower
    assert "preview" in lower
    for tok in ("Traceback", "0x7f", "<object", "<class"):
        assert tok not in text, (
            f"render 输出含 raw Python 调试痕迹 {tok!r}: {text!r}"
        )


def test_render_clearly_distinguishes_preview_from_ai_draft() -> None:
    """渲染必须明确区分 preview 与 ai_draft —— 必须显式包含字面量
    ``preview`` 与 ``ai_draft_only`` / ``not ai_draft`` 之一。"""

    from mindforge.strategies.custom import parse_strategy_definition

    mod = _load_preview_packet_module()
    definition = parse_strategy_definition(_VALID_DICT)
    packet = mod.build_custom_preview_packet(definition)
    text = mod.render_custom_preview_packet(packet).lower()
    assert "preview" in text
    assert ("ai_draft_only" in text) or ("not ai_draft" in text)


def test_invalid_definition_preview_packet_is_validation_error_kind(
    tmp_path: Path,
) -> None:
    """对 invalid 文件应能产出"validation error"形态的 packet，含文件
    路径 + 失败原因；不抛 raw 栈。Slice 5 Green 可以选择 (a) 单独函数
    ``build_invalid_preview_packet(path, error)`` 或 (b) 让
    ``build_custom_preview_packet`` 接受 ``InvalidStrategyDefinitionError``。
    本 Red 只断言至少一种入口可用且形态正确。
    """

    from mindforge.strategies.custom import InvalidStrategyDefinitionError
    from mindforge.strategies.custom_loader import (
        load_strategy_definition_from_file,
    )

    bad = dict(_VALID_DICT)
    bad["safety_policy"] = "auto_approve"
    f = tmp_path / "bad.yaml"
    _write_yaml(f, bad)

    try:
        load_strategy_definition_from_file(f)
    except InvalidStrategyDefinitionError as exc:
        captured_error = exc
    else:
        raise AssertionError("loader 没有抛 InvalidStrategyDefinitionError")

    mod = _load_preview_packet_module()
    builder = getattr(mod, "build_invalid_preview_packet", None) or getattr(
        mod, "build_custom_preview_packet"
    )
    if builder is mod.build_custom_preview_packet:
        packet = builder(captured_error)
    else:
        packet = builder(f, captured_error)
    assert packet["kind"] == "preview_only", packet
    assert packet["executable"] is False, packet
    assert packet["validation_status"] != "valid", packet
    text = mod.render_custom_preview_packet(packet)
    assert "bad.yaml" in text
    assert "validation" in text.lower() or "invalid" in text.lower()


# ---------------------------------------------------------------------------
# Family D — Boundary docs（Red 缺口）
# ---------------------------------------------------------------------------


def test_custom_strategy_doc_explains_preview_packet_review_only() -> None:
    """``README.md`` 必须解释 preview packet 是
    review-only / 不是 ai_draft / 不是 human_approved / future
    implementation 仍需显式 approval。
    """

    p = Path("README.md")
    text = p.read_text(encoding="utf-8").lower()
    for token in (
        "preview packet",
        "review-only",
        "not ai_draft",
        "not human_approved",
        "explicit approval",
    ):
        assert token in text, (
                f"README.md 缺 preview packet review-only 说明 "
            f"{token!r}"
        )


# ---------------------------------------------------------------------------
# Family E — Sanity Green baselines
# ---------------------------------------------------------------------------


def test_v012_slice4_discover_strategies_still_works(tmp_path: Path) -> None:
    """Slice 4 Green 行为不能因为 Slice 5 Red 而回退。"""

    from mindforge.strategies import discover_strategies

    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    metas = discover_strategies(custom_path=tmp_path)
    assert any(m.strategy_id == "user_concept_review" for m in metas)


def test_v012_slice4_build_strategy_custom_preview_still_friendly(
    tmp_path: Path,
) -> None:
    """Slice 4 Green build_strategy preview-only 拒绝路径仍 Green。"""

    from mindforge.strategies import (
        NotYetImplementedStrategyError,
        StrategyContext,
        build_strategy,
    )

    _write_yaml(tmp_path / "u.yaml", _VALID_DICT)
    ctx = StrategyContext(
        client=None,
        prompts_dir=Path("prompts"),
        prompt_versions={},
        learning_tracks_text="",
    )
    with pytest.raises(NotYetImplementedStrategyError) as excinfo:
        build_strategy("user_concept_review", ctx, custom_path=tmp_path)
    assert "preview" in str(excinfo.value).lower()
