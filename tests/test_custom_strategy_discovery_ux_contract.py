"""v0.12 Slice 3 — Custom Strategy Discovery UX Red contract tests.

v0.12 Slice 1 锁定了 ``StrategyDefinition`` 的形状与校验，Slice 2 锁定
了从显式安全路径加载文件的边界。但用户在终端仍只能看到 4 个内建策略
（``mindforge strategies list``）—— 即便已经把一个合法的 custom YAML
放在某个目录里，CLI 也没办法**发现** + **展示**它，更没办法在出错时
拿到对用户友好的错误。

Slice 3 主题：custom strategy discovery UX / validation error
presentation / CLI list custom definitions
============================================================

本切片只写 tests / docs / fixtures —— 不改 production code。目标是把
discovery + 展示这一刀的 UX 与边界**先用 Red 测试钉死**，让 Slice 3
Green 实现没有任何空间引入：

- 在 discovery 阶段调用 LLM / 写 vault / 读 ``.env``；
- 隐式扫描用户主目录、Obsidian vault、私人 workspace；
- 把 custom 定义自动注册成 *可执行* strategy；
- 把 invalid config 误展示为"已可执行"；
- 用 raw Python repr / Traceback 当主 UX；
- 让 ``mindforge strategies list`` 在加 custom path 时改变内建展示语义。

本切片明确**不**实现：

- custom strategy runtime；
- arbitrary Python plugin；
- shell / script strategy；
- 把 custom 定义接入 ``StrategyRegistry`` 执行路径；
- 真实 LLM 激活；
- dry-run dogfooding。

Red 期望
========

绝大多数测试因为 CLI ``--custom-path`` 选项尚不存在、discover_strategies
公开 API 尚不存在、README 尚未补 discovery UX 段落而失败；
少量 sanity baseline 测试保护现有 ``mindforge strategies list``
继续工作。所有失败必须是清晰的 production gap，而不是 import 错误 /
测试 bug / fixture 缺失 / 环境问题。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


_VALID_DICT: dict[str, object] = {
    "strategy_id": "user_concept_review",
    "strategy_version": "0.0.1",
    "display_name": "User Concept Review",
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


def _write_yaml(path: Path, data: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# Family A — CLI surface for custom discovery（Red 缺口）
# ---------------------------------------------------------------------------


def test_cli_strategies_list_accepts_custom_path_option(
    tmp_path: Path,
) -> None:
    """``mindforge strategies list --custom-path <DIR>`` 必须存在并接受
    显式 custom directory。这是 discovery 入口的*显式*开关 ——
    没传该 flag 时行为与今天完全一致（4 个 built-in），传了之后才把
    显式目录里的 declarative 定义纳入展示。
    """

    runner = CliRunner()
    f = tmp_path / "u.yaml"
    _write_yaml(f, _VALID_DICT)
    result = runner.invoke(
        app, ["strategies", "list", "--custom-path", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output


def test_cli_strategies_list_default_hides_internal_builtins() -> None:
    """默认 ``strategies list`` 是产品视图，只展示 production strategy。"""

    runner = CliRunner()
    result = runner.invoke(app, ["strategies", "list"])
    assert result.exit_code == 0, result.output
    assert "knowledge_card" in result.output
    for name in (
        "default_knowledge_card",
        "five_stage",
        "concept_extraction",
        "action_item",
    ):
        assert name not in result.output

    internal = runner.invoke(app, ["strategies", "list", "--include-internal"])
    assert internal.exit_code == 0, internal.output
    for name in ("default_knowledge_card", "five_stage", "concept_extraction", "action_item"):
        assert name in internal.output


def test_cli_strategies_list_with_custom_path_includes_custom(
    tmp_path: Path,
) -> None:
    """传 ``--custom-path`` 时输出必须额外列出该目录下的 custom 定义
    （strategy_id 必须出现在输出中）。
    """

    runner = CliRunner()
    f = tmp_path / "u.yaml"
    _write_yaml(f, _VALID_DICT)
    result = runner.invoke(
        app, ["strategies", "list", "--custom-path", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "user_concept_review" in result.output, result.output


def test_cli_strategies_list_marks_custom_distinctly(
    tmp_path: Path,
) -> None:
    """custom 定义必须在输出里有可见的"custom"标记（badge / 字面量），
    让用户立刻分辨"这是 built-in 还是 custom"，避免把 custom 误当
    project-shipped 策略。
    """

    runner = CliRunner()
    f = tmp_path / "u.yaml"
    _write_yaml(f, _VALID_DICT)
    result = runner.invoke(
        app, ["strategies", "list", "--custom-path", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "custom" in result.output.lower(), (
        f"custom 定义在输出中未被标记为 custom: {result.output!r}"
    )


def test_cli_strategies_list_marks_custom_not_executable(
    tmp_path: Path,
) -> None:
    """custom 定义必须在输出里被标记为 *not executable*（status=planned
    / preview，无可执行 factory），避免误导用户"我现在就能 mindforge
    process --strategy user_concept_review"。
    """

    runner = CliRunner()
    f = tmp_path / "u.yaml"
    _write_yaml(f, _VALID_DICT)
    result = runner.invoke(
        app, ["strategies", "list", "--custom-path", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    text = result.output.lower()
    assert ("not executable" in text) or ("preview" in text) or (
        "planned" in text
    ), f"custom 定义在输出中未被标记为不可执行: {result.output!r}"


# ---------------------------------------------------------------------------
# Family B — Validation error UX in CLI（Red 缺口）
# ---------------------------------------------------------------------------


def test_cli_invalid_custom_definition_shows_friendly_error(
    tmp_path: Path,
) -> None:
    """目录中含一个非法定义时，CLI 必须以友好错误（含文件路径）退出，
    而不是裸抛栈或静默忽略。"""

    runner = CliRunner()
    bad = tmp_path / "bad.yaml"
    _write_yaml(bad, {**_VALID_DICT, "safety_policy": "auto_approve"})
    result = runner.invoke(
        app, ["strategies", "list", "--custom-path", str(tmp_path)]
    )
    # 非 0 退出 *或* 在输出中显著标出错误（具体 UX 由 Green 定，但
    # 文件名必须出现）。
    assert "bad.yaml" in result.output, result.output
    assert "auto_approve" in result.output or "safety_policy" in result.output, (
        result.output
    )


def test_cli_invalid_custom_definition_does_not_leak_python_repr(
    tmp_path: Path,
) -> None:
    """即便加载失败，CLI 输出也不能包含 Python repr / Traceback / 对象
    地址 —— 这是面向终端用户的可读性硬约束。"""

    runner = CliRunner()
    bad = tmp_path / "bad.yaml"
    _write_yaml(bad, {**_VALID_DICT, "safety_policy": "auto_approve"})
    result = runner.invoke(
        app, ["strategies", "list", "--custom-path", str(tmp_path)]
    )
    text = result.output
    for tok in ("Traceback", "0x7f", "<object", "<class"):
        assert tok not in text, (
            f"CLI 输出出现 raw Python 调试痕迹 {tok!r}: {text!r}"
        )


def test_cli_distinguishes_invalid_config_from_planned_strategy(
    tmp_path: Path,
) -> None:
    """invalid config 与 planned strategy 必须在 UX 上可被分辨。

    invalid 是"用户输入错了请改"；planned 是"它存在但没做完，可以用
    替代"。两者错误根因不同，提示语应不同。本测试只断言"invalid"或
    "validation"等字面量出现于 invalid-config 的输出中（非 planned）。
    """

    runner = CliRunner()
    bad = tmp_path / "bad.yaml"
    _write_yaml(bad, {**_VALID_DICT, "safety_policy": "auto_approve"})
    result = runner.invoke(
        app, ["strategies", "list", "--custom-path", str(tmp_path)]
    )
    text = result.output.lower()
    assert (
        ("invalid" in text)
        or ("validation" in text)
        or ("rejected" in text)
    ), f"CLI 输出未把 invalid config 标识为校验失败: {result.output!r}"


def test_cli_invalid_custom_definition_does_not_register_as_executable(
    tmp_path: Path,
) -> None:
    """invalid custom 定义不能被悄悄注册成 executable —— 哪怕只是把
    名字加进 ``available_strategies()``。这是为了防止"列表里出现一个
    名字 → 用户尝试 process → 才发现非法"的反向 UX。
    """

    from mindforge.strategies import available_strategies

    before = set(available_strategies())
    runner = CliRunner()
    bad = tmp_path / "bad.yaml"
    _write_yaml(bad, {**_VALID_DICT, "safety_policy": "auto_approve"})
    runner.invoke(app, ["strategies", "list", "--custom-path", str(tmp_path)])
    after = set(available_strategies())
    assert before == after


# ---------------------------------------------------------------------------
# Family C — Discovery boundary（Red 缺口；行为 + source-scan）
# ---------------------------------------------------------------------------


def test_cli_strategies_list_with_custom_path_does_not_call_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``mindforge strategies list --custom-path`` 不能在内部调用任何
    provider / LLMClient / network。我们用 monkeypatch 在 LLMClient 上
    打一个 fail-loud sentinel：如果 discovery 真的去构造 LLM，立刻
    抛错。
    """

    import mindforge.cli as cli_mod

    def _explode(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "discovery must not construct LLMClient / call provider"
        )

    if hasattr(cli_mod, "LLMClient"):
        monkeypatch.setattr(cli_mod, "LLMClient", _explode)

    runner = CliRunner()
    f = tmp_path / "u.yaml"
    _write_yaml(f, _VALID_DICT)
    result = runner.invoke(
        app, ["strategies", "list", "--custom-path", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output


def test_discovery_module_source_has_no_implicit_or_execution_tokens() -> None:
    """承载 discovery 的 production 模块（``custom_loader`` 已就位；如
    Green 选择新增 ``discovery.py`` 也由本测试约束）必须保持
    declarative-only / explicit-only 边界。
    """

    candidates = [
        Path("src/mindforge/strategies/custom_loader.py"),
        Path("src/mindforge/strategies/discovery.py"),
    ]
    forbidden = (
        "Path.home(",
        "expanduser",
        "load_dotenv",
        ".obsidian",
        "subprocess",
        "os.system",
        "eval(",
        "exec(",
        "importlib.import_module",
        "__import__",
        "LLMClient(",
        "import requests",
        "import httpx",
        "cubox.app",
        "UPSTAGE_API_KEY",
        "~/.config",
        "~/.mindforge",
    )
    seen_any = False
    for p in candidates:
        if not p.exists():
            continue
        seen_any = True
        src = p.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in src, (
                f"{p} 出现越界触点 {token!r}；discovery 必须显式 + 不执行。"
            )
    assert seen_any, (
        "至少需要 custom_loader.py 或 discovery.py 之一提供 discovery 入口"
    )


# ---------------------------------------------------------------------------
# Family D — 公开 discovery API surface（Red 缺口）
# ---------------------------------------------------------------------------


def test_strategies_package_exposes_discover_strategies_api(
    tmp_path: Path,
) -> None:
    """``mindforge.strategies`` 必须暴露一个 ``discover_strategies()``
    函数，作为 CLI 与未来调用方共用的统一 discovery 入口。

    签名：``discover_strategies(custom_path: Path | None = None) ->
    tuple[StrategyMetadata, ...]``。

    - 不传 ``custom_path`` → 返回 built-in metadata；
    - 传一个目录 → 返回 built-in + 该目录下 custom 定义的 metadata；
    - custom metadata 必须满足 ``status ∈ {planned, preview}``（v0.11
      Slice 4 planned guard 自动覆盖其执行边界）。
    """

    import importlib

    pkg = importlib.import_module("mindforge.strategies")
    assert hasattr(pkg, "discover_strategies"), (
        "mindforge.strategies 缺导出 discover_strategies"
    )

    f = tmp_path / "u.yaml"
    _write_yaml(f, _VALID_DICT)
    metas = pkg.discover_strategies(custom_path=tmp_path)
    ids = {m.strategy_id for m in metas}
    # built-in 必须仍在
    for name in (
        "default_knowledge_card",
        "five_stage",
        "concept_extraction",
        "action_item",
    ):
        assert name in ids, f"discover_strategies 缺 built-in {name!r}"
    # custom 必须出现
    assert "user_concept_review" in ids
    # custom 必须被标为 planned/preview
    custom_meta = next(m for m in metas if m.strategy_id == "user_concept_review")
    assert custom_meta.status in {"planned", "preview"}


def test_discover_strategies_default_returns_only_builtins() -> None:
    """不传 ``custom_path`` 时 ``discover_strategies()`` 必须只返回
    built-in metadata，与 ``list_strategies()`` 一致。
    """

    from mindforge.strategies import (
        discover_strategies,
        list_strategies,
    )

    default = discover_strategies()
    builtin = list_strategies()
    assert {m.strategy_id for m in default} == {m.strategy_id for m in builtin}


# ---------------------------------------------------------------------------
# Family E — Docs / onboarding（Red 缺口）
# ---------------------------------------------------------------------------


def test_custom_strategy_doc_explains_discovery_ux() -> None:
    """``README.md`` 必须向用户解释 custom strategy discovery
    的关键 UX 与边界：

    - 如何用显式 ``--custom-path`` 让 CLI 看到 custom 定义；
    - discovery 不是 execution；
    - custom 定义默认 preview / 不可执行；
    - 校验错误的读法；
    - 不支持 arbitrary python plugin；
    - 不支持 shell strategy；
    - 默认不调真实 LLM。
    """

    p = Path("README.zh-CN.md")
    assert p.exists()
    text = p.read_text(encoding="utf-8").lower()
    for token in (
        "--custom-path",
        "discovery is not execution",
        "preview",
        "validation error",
        "no arbitrary python",
        "no shell",
    ):
        assert token in text, (
            f"README.md 缺 discovery 关键说明 {token!r}"
        )


# ---------------------------------------------------------------------------
# Family F — Sanity Green baselines
# ---------------------------------------------------------------------------


def test_existing_builtin_registry_still_works() -> None:
    """v0.11 + v0.12 Slice 1 + Slice 2 的 built-in 列表不受 Slice 3 Red
    影响。"""

    from mindforge.strategies import available_strategies, list_strategies

    names = available_strategies()
    assert "default_knowledge_card" in names
    assert "five_stage" in names
    assert "concept_extraction" in names
    assert "action_item" in names
    assert len(list_strategies()) >= 4


def test_v012_slice2_loader_still_works(tmp_path: Path) -> None:
    """v0.12 Slice 2 ``load_strategy_definition_from_file`` 的 happy
    path 必须继续通过 —— Slice 3 Red 不能回退 Slice 2 Green 行为。"""

    from mindforge.strategies.custom_loader import (
        load_strategy_definition_from_file,
    )

    f = tmp_path / "ok.yaml"
    _write_yaml(f, _VALID_DICT)
    d = load_strategy_definition_from_file(f)
    assert d.strategy_id == "user_concept_review"
    assert d.status == "preview"
