"""v0.12 Slice 2 — Custom Strategy Loading Source Red contract tests.

v0.12 Slice 1 Green 锁定了 ``StrategyDefinition`` 的 *形状* 与 *校验*，
但用户仍只能在 Python 代码里手写 dict 喂给 ``parse_strategy_definition``。
真实使用面是把声明式定义放进文件（YAML / JSON），让 mindforge 从一个
**显式安全路径**加载。

Slice 2 主题：custom strategy loading source / safe config discovery /
no execution boundary
====================================================================

本切片只写 tests / docs / fixtures —— 不改 production code。目标是把
loading 与 discovery 这一刀的安全契约**先用 Red 测试钉死**，让 Slice 2
Green 实现没有任何空间引入：

- 隐式扫描用户主目录、Obsidian vault、私人 workspace、``.env``；
- path traversal（``../../etc/passwd``）；
- symlink 越狱；
- 任意扩展名加载（``.py`` / ``.sh`` / 二进制）；
- 在 loading 阶段调用 provider / LLM / network；
- 在 loading 阶段写 workspace；
- 在 loading 阶段执行用户提供的代码；
- 把 custom 定义自动注册成可执行 strategy；
- 用 raw Python repr / stack trace 当主 UX。

本切片明确**不**实现：

- custom strategy runtime；
- arbitrary Python plugin；
- shell / script strategy；
- 把 custom 定义接入 ``StrategyRegistry`` 执行路径；
- 真实 LLM 激活；
- dry-run dogfooding。

Red 期望
========

绝大多数测试因为 ``mindforge.strategies.custom_loader`` 模块、相关符号、
docs 段落尚未存在而失败；少量 sanity baseline 测试保护 v0.11 + v0.12
Slice 1 Green 继续工作。所有失败必须是清晰的 production gap，而不是
import 错误 / 测试 bug / fixture 缺失 / 环境问题。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Family A — 模块与公开符号契约（Red 缺口）
# ---------------------------------------------------------------------------


def test_custom_loader_module_exists() -> None:
    """``mindforge.strategies.custom_loader`` 模块必须存在，承担 *loading
    source* 这唯一职责，与 ``custom.py``（parse / validate）解耦。
    """

    p = Path("src/mindforge/strategies/custom_loader.py")
    assert p.exists(), (
        "src/mindforge/strategies/custom_loader.py 尚不存在；"
        "v0.12 Slice 2 Green 必须新增此模块。"
    )


def test_custom_loader_module_exports_required_symbols() -> None:
    """``custom_loader`` 必须导出三件套：

    - ``load_strategy_definition_from_file(path) -> StrategyDefinition``
    - ``load_strategy_definitions_from_directory(path) -> tuple[StrategyDefinition, ...]``
    - ``StrategyDefinitionFileError``（继承
      :class:`InvalidStrategyDefinitionError`，让上层既有的 broad except
      仍能 catch，同时保留 file 级语义）。
    """

    import importlib

    mod = importlib.import_module("mindforge.strategies.custom_loader")
    for name in (
        "load_strategy_definition_from_file",
        "load_strategy_definitions_from_directory",
        "StrategyDefinitionFileError",
    ):
        assert hasattr(mod, name), (
            f"mindforge.strategies.custom_loader 缺导出 {name!r}"
        )


def test_loader_file_error_is_invalid_definition_subclass() -> None:
    """``StrategyDefinitionFileError`` 必须继承
    :class:`InvalidStrategyDefinitionError`，让既有"任何 custom 定义出
    问题"的 broad except 仍能覆盖 loading 失败。
    """

    from mindforge.strategies.custom import InvalidStrategyDefinitionError
    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
    )

    assert issubclass(
        StrategyDefinitionFileError, InvalidStrategyDefinitionError
    )


# ---------------------------------------------------------------------------
# Family B — Safe loading source（Red 缺口）
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
    """以最小 YAML 写法落盘（pyyaml 已是项目依赖）。"""

    import yaml  # type: ignore[import-untyped]

    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_load_valid_yaml_returns_strategy_definition(tmp_path: Path) -> None:
    """合法 YAML 文件必须能被 loader 解析为 :class:`StrategyDefinition`。"""

    from mindforge.strategies.custom import StrategyDefinition
    from mindforge.strategies.custom_loader import (
        load_strategy_definition_from_file,
    )

    f = tmp_path / "my_strategy.yaml"
    _write_yaml(f, _VALID_DICT)
    d = load_strategy_definition_from_file(f)
    assert isinstance(d, StrategyDefinition)
    assert d.strategy_id == "user_concept_review"


def test_load_valid_json_returns_strategy_definition(tmp_path: Path) -> None:
    """合法 JSON 文件必须能被 loader 解析为 :class:`StrategyDefinition`。"""

    from mindforge.strategies.custom import StrategyDefinition
    from mindforge.strategies.custom_loader import (
        load_strategy_definition_from_file,
    )

    f = tmp_path / "my_strategy.json"
    _write_json(f, _VALID_DICT)
    d = load_strategy_definition_from_file(f)
    assert isinstance(d, StrategyDefinition)
    assert d.strategy_id == "user_concept_review"


@pytest.mark.parametrize("ext", [".py", ".sh", ".txt", ".bin", ""])
def test_load_unsupported_extension_is_rejected(
    tmp_path: Path, ext: str
) -> None:
    """非 declarative 扩展名（``.py`` / ``.sh`` / ``.txt`` / 无扩展）必
    须被拒。这是 declarative-only 的边界 —— 不允许 loader 触碰任何
    *疑似可执行* 文件，即便其内容恰好可以被 YAML 解析。
    """

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        load_strategy_definition_from_file,
    )

    f = tmp_path / f"my_strategy{ext}"
    f.write_text("strategy_id: x\n", encoding="utf-8")
    with pytest.raises(StrategyDefinitionFileError):
        load_strategy_definition_from_file(f)


def test_load_nonexistent_file_is_user_friendly_error(
    tmp_path: Path,
) -> None:
    """不存在的路径必须以 :class:`StrategyDefinitionFileError` 友好提示，
    而不是裸 ``FileNotFoundError`` 直接抛到用户面前。
    """

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        load_strategy_definition_from_file,
    )

    f = tmp_path / "missing.yaml"
    with pytest.raises(StrategyDefinitionFileError):
        load_strategy_definition_from_file(f)


def test_load_malformed_yaml_returns_user_friendly_error(
    tmp_path: Path,
) -> None:
    """格式损坏的 YAML 必须返回友好错误，**不**让原始 YAMLError 直接
    冒泡，错误消息应包含文件路径以便用户定位。
    """

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        load_strategy_definition_from_file,
    )

    f = tmp_path / "broken.yaml"
    f.write_text("strategy_id: [unclosed\n", encoding="utf-8")
    with pytest.raises(StrategyDefinitionFileError) as excinfo:
        load_strategy_definition_from_file(f)
    assert "broken.yaml" in str(excinfo.value)


def test_load_directory_returns_validated_definitions(tmp_path: Path) -> None:
    """目录加载必须返回一个 ``tuple[StrategyDefinition, ...]``；每个文件
    都经过 ``parse_strategy_definition`` 验证；忽略非 declarative 扩展名。
    """

    from mindforge.strategies.custom_loader import (
        load_strategy_definitions_from_directory,
    )

    a = tmp_path / "a.yaml"
    b = tmp_path / "b.json"
    junk = tmp_path / "readme.md"
    _write_yaml(a, {**_VALID_DICT, "strategy_id": "a_strategy"})
    _write_json(b, {**_VALID_DICT, "strategy_id": "b_strategy"})
    junk.write_text("# not a strategy\n", encoding="utf-8")

    defs = load_strategy_definitions_from_directory(tmp_path)
    ids = {d.strategy_id for d in defs}
    assert ids == {"a_strategy", "b_strategy"}


def test_load_empty_directory_returns_empty_tuple(tmp_path: Path) -> None:
    """空目录必须返回 ``()`` —— 没有定义不是错误，是常态。"""

    from mindforge.strategies.custom_loader import (
        load_strategy_definitions_from_directory,
    )

    assert load_strategy_definitions_from_directory(tmp_path) == ()


def test_load_directory_invalid_definition_raises_per_file(
    tmp_path: Path,
) -> None:
    """目录中含一个非法定义时，loader 必须抛 file 级错误（包含问题文件
    名），而不是悄悄忽略 —— 静默忽略会让用户的安全字段被默默丢弃。
    """

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        load_strategy_definitions_from_directory,
    )

    bad = tmp_path / "bad.yaml"
    _write_yaml(bad, {**_VALID_DICT, "safety_policy": "auto_approve"})
    with pytest.raises(StrategyDefinitionFileError) as excinfo:
        load_strategy_definitions_from_directory(tmp_path)
    assert "bad.yaml" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Family C — Path traversal / symlink defense（Red 缺口）
# ---------------------------------------------------------------------------


def test_directory_load_rejects_symlink_escape(tmp_path: Path) -> None:
    """目录中若存在指向 *外部* 真实文件的 symlink，loader 必须拒绝该
    symlink（要么跳过、要么显式拒绝；绝不能跟随 symlink 读取目录之外
    的文件）。

    这是防止用户被诱导把"看起来在我项目里"的目录里塞一个 symlink 指
    向 ``~/.ssh/config`` 之类。
    """

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        load_strategy_definitions_from_directory,
    )

    outside = tmp_path / "outside"
    outside.mkdir()
    outside_target = outside / "target.yaml"
    _write_yaml(outside_target, _VALID_DICT)

    inside = tmp_path / "inside"
    inside.mkdir()
    link = inside / "evil.yaml"
    try:
        link.symlink_to(outside_target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")

    # 期望 v0.12 Slice 2 Green 在遇到 symlink-escape 时显式拒绝。
    with pytest.raises(StrategyDefinitionFileError):
        load_strategy_definitions_from_directory(inside)


def test_file_load_rejects_path_traversal(tmp_path: Path) -> None:
    """显式带 ``..`` 的路径必须在 loader 入口被规范化检查后拒绝（即便
    目标文件存在）。这是为了让 loader 永远只接受用户**明示**的目录树
    内的文件。
    """

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        load_strategy_definition_from_file,
    )

    base = tmp_path / "base"
    base.mkdir()
    sibling = tmp_path / "sibling.yaml"
    _write_yaml(sibling, _VALID_DICT)

    traversal = base / ".." / "sibling.yaml"
    with pytest.raises(StrategyDefinitionFileError):
        load_strategy_definition_from_file(traversal)


# ---------------------------------------------------------------------------
# Family D — 无隐式扫描（Red 缺口；source-scan）
# ---------------------------------------------------------------------------


def test_loader_source_has_no_implicit_scanning_tokens() -> None:
    """``custom_loader`` 源码不能隐式扫描用户主目录、vault、私人
    workspace、``.env``。任何 implicit discovery 都会让"用户没显式同意"
    的文件被读取。
    """

    p = Path("src/mindforge/strategies/custom_loader.py")
    assert p.exists(), (
        "src/mindforge/strategies/custom_loader.py 尚不存在；v0.12 Slice 2"
        " Green 待实现。"
    )
    src = p.read_text(encoding="utf-8")
    forbidden = (
        "Path.home(",
        "expanduser",
        "os.environ.get(\"HOME",
        "os.environ.get('HOME",
        ".obsidian",
        "load_dotenv",
        # 不应隐式硬编码任何配置目录字面量
        "~/.config",
        "~/.mindforge",
    )
    for token in forbidden:
        assert token not in src, (
            f"custom_loader.py 出现隐式扫描触点 {token!r}；loading source"
            " 必须由调用方显式传入路径。"
        )


# ---------------------------------------------------------------------------
# Family E — Loading 不执行代码 / 不调 provider / 不写 workspace（Red）
# ---------------------------------------------------------------------------


def test_loader_source_has_no_arbitrary_execution_or_network_tokens() -> None:
    """``custom_loader`` 源码不能引入 arbitrary code execution / shell /
    network / LLM / Cubox / Upstage 触点。loader 的唯一动作是 *读取* +
    *委派给 parse_strategy_definition*。
    """

    p = Path("src/mindforge/strategies/custom_loader.py")
    assert p.exists(), (
        "src/mindforge/strategies/custom_loader.py 尚不存在；v0.12 Slice 2"
        " Green 待实现。"
    )
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
        "cubox.app",
        "UPSTAGE_API_KEY",
    )
    for token in forbidden:
        assert token not in src, (
            f"custom_loader.py 出现越界触点 {token!r}；loading 必须只读 +"
            " 委派 parse_strategy_definition。"
        )


def test_loaded_definition_status_invariant_holds(tmp_path: Path) -> None:
    """loader 不允许绕过 ``status ∈ {planned, preview}`` 不变量。即便
    YAML 写 ``status: implemented``，也必须在 parse 阶段被拒（因为
    loader 委派给 parse_strategy_definition）。
    """

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        load_strategy_definition_from_file,
    )

    f = tmp_path / "evil.yaml"
    _write_yaml(f, {**_VALID_DICT, "status": "implemented"})
    with pytest.raises(StrategyDefinitionFileError):
        load_strategy_definition_from_file(f)


# ---------------------------------------------------------------------------
# Family F — Discovery without execution（Red 缺口）
# ---------------------------------------------------------------------------


def test_loaded_definition_can_be_listed_as_metadata(tmp_path: Path) -> None:
    """加载得到的定义必须能用 ``to_metadata()`` 转为 v0.11
    :class:`StrategyMetadata`，让未来 ``mindforge strategies list`` 能
    展示 custom 策略 —— **仍不可执行**，由 v0.11 Slice 4 planned guard
    兜底。
    """

    from mindforge.strategies import StrategyMetadata
    from mindforge.strategies.custom_loader import (
        load_strategy_definition_from_file,
    )

    f = tmp_path / "ok.yaml"
    _write_yaml(f, _VALID_DICT)
    d = load_strategy_definition_from_file(f)
    meta = d.to_metadata()
    assert isinstance(meta, StrategyMetadata)
    assert meta.status in {"planned", "preview"}


def test_loader_does_not_auto_register_in_strategy_registry(
    tmp_path: Path,
) -> None:
    """loader 必须**不**自动把 custom 定义注册进 ``StrategyRegistry``
    的 ``available_strategies()``。注册（或者 *被发现但仍不可执行* 的
    新 surface）是后续 slice 的事；本切片严格 loading + parse only。
    """

    from mindforge.strategies import available_strategies
    from mindforge.strategies.custom_loader import (
        load_strategy_definition_from_file,
    )

    before = set(available_strategies())
    f = tmp_path / "ok.yaml"
    _write_yaml(f, _VALID_DICT)
    load_strategy_definition_from_file(f)
    after = set(available_strategies())
    assert before == after, (
        "loader 不能在调用时改变 built-in registry；自动注册留给后续"
        " slice 显式接入。"
    )


# ---------------------------------------------------------------------------
# Family G — Validation UX（Red 缺口）
# ---------------------------------------------------------------------------


def test_loader_error_includes_offending_file_path(tmp_path: Path) -> None:
    """loader 抛 :class:`StrategyDefinitionFileError` 时必须把出错文件
    路径放进消息，便于用户即时定位。"""

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        load_strategy_definition_from_file,
    )

    f = tmp_path / "bad.yaml"
    _write_yaml(f, {**_VALID_DICT, "safety_policy": "auto_approve"})
    with pytest.raises(StrategyDefinitionFileError) as excinfo:
        load_strategy_definition_from_file(f)
    assert "bad.yaml" in str(excinfo.value)


def test_loader_error_does_not_leak_python_repr_as_primary_ux(
    tmp_path: Path,
) -> None:
    """loader 错误消息**不应**以裸 Python repr / object 地址 / Traceback
    片段为主 UX。这是面向终端用户的可读性硬约束。
    """

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        load_strategy_definition_from_file,
    )

    f = tmp_path / "bad.yaml"
    _write_yaml(f, {**_VALID_DICT, "safety_policy": "auto_approve"})
    with pytest.raises(StrategyDefinitionFileError) as excinfo:
        load_strategy_definition_from_file(f)
    msg = str(excinfo.value)
    forbidden_in_msg = ("Traceback", "0x7f", "<object", "<class")
    for tok in forbidden_in_msg:
        assert tok not in msg, (
            f"loader 错误消息出现 raw Python 调试痕迹 {tok!r}: {msg!r}"
        )


# ---------------------------------------------------------------------------
# Family H — Docs / onboarding（Red 缺口）
# ---------------------------------------------------------------------------


def test_custom_strategy_doc_explains_loading_safety() -> None:
    """``README.md`` 必须向用户解释 loading 的
    关键安全契约：

    - 仅显式路径加载；
    - loading 不是 execution；
    - 不隐式扫描主目录 / vault；
    - 不读 ``.env``；
    - 不支持 arbitrary python plugin；
    - 不支持 shell strategy。
    """

    p = Path("README.md")
    assert p.exists(), "README.md 必须存在"
    text = p.read_text(encoding="utf-8").lower()
    for token in (
        "explicit path",
        "loading is not execution",
        "no implicit",
        "no arbitrary python",
        "no shell",
    ):
        assert token in text, (
            f"README.md 缺 loading-safety 关键说明 {token!r}"
        )


# ---------------------------------------------------------------------------
# Family I — Sanity Green baselines（v0.11 + v0.12 Slice 1 不能回归）
# ---------------------------------------------------------------------------


def test_existing_builtin_registry_still_works() -> None:
    """v0.11 + v0.12 Slice 1 的 built-in 列表不受 Slice 2 Red 影响。"""

    from mindforge.strategies import available_strategies, list_strategies

    names = available_strategies()
    assert "default_knowledge_card" in names
    assert "five_stage" in names
    assert "concept_extraction" in names
    assert "action_item" in names
    assert len(list_strategies()) >= 4


def test_v012_slice1_parse_still_works() -> None:
    """v0.12 Slice 1 ``parse_strategy_definition`` 的 happy path 必须
    继续通过 —— Slice 2 Red 不能回退 Slice 1 Green 行为。"""

    from mindforge.strategies.custom import parse_strategy_definition

    d = parse_strategy_definition(_VALID_DICT)
    assert d.strategy_id == "user_concept_review"
    assert d.status == "preview"
