"""Stage 5 — basic KnowledgeStrategy seam additional boundary tests.

设计意图
========

仓库已有 ``mindforge.strategies`` seam（``KnowledgeStrategy`` Protocol +
``StrategyContext`` + ``build_strategy``）以及 9 个 strategy 测试 +
9 个 strategy boundary 测试，已覆盖 typer/rich/dotenv/run_logger/CLI/
presenter/approval/review/writer 反向 import 禁飞。

Stage 5 补齐的**新增**契约：

1. strategy 层不感知 source domain（cubox_* / source_mux / scanner /
   sources.cubox_* / obsidian）；
2. strategy 层不读取 .env / 不依赖 vault_writer / workspace；
3. strategy 通过 ``StrategyContext.client: LLMClient`` 接受**任意**
   LLMProvider（不绑定 FakeProvider）；
4. 用 FakeProvider 跑一次完整 strategy.run 不写任何磁盘文件、不打开
   任何 socket；
5. strategy 输出的 ``PipelineOutcome.card_payload`` 是 in-memory dict，
   绝不携带 ``human_approved`` 字段或 ``status: human_approved``。
"""

from __future__ import annotations

import ast
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mindforge.llm.base import LLMRequest, LLMResult
from mindforge.llm.client import LLMClient
from mindforge.sources.base import SourceDocument
from mindforge.strategies import (
    DEFAULT_STRATEGY_NAME,
    StrategyContext,
    build_strategy,
)

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "src" / "mindforge"
_STRATEGIES_DIR = _SRC / "strategies"


# ---------------------------------------------------------------------------
# 1. AST：strategy 不感知 source / vault / workspace / dotenv
# ---------------------------------------------------------------------------


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


_FORBIDDEN_FOR_STRATEGY = {
    # source-specific
    "mindforge.cubox_cli",
    "mindforge.cubox_dryrun_presenter",
    "mindforge.cubox_preview_presenter",
    "mindforge.source_mux",
    "mindforge.scanner",
    "mindforge.sources.cubox_api",
    "mindforge.sources.cubox_markdown",
    # vault / workspace / obsidian
    "mindforge.vault_writer",
    "mindforge.workspace",
    "mindforge.obsidian",
    "mindforge.obsidian_cli",
    # dotenv
    "dotenv",
    "mindforge.env_loader",
}


def test_strategy_modules_do_not_import_source_or_vault_or_dotenv() -> None:
    targets = [p for p in _STRATEGIES_DIR.glob("*.py") if p.name != "__pycache__"]
    assert targets
    for t in targets:
        leaked = _imports(t) & _FORBIDDEN_FOR_STRATEGY
        assert not leaked, f"{t.name} 不应 import：{leaked}"


# ---------------------------------------------------------------------------
# 2. StrategyContext.client 是 LLMClient（不绑定具体 provider）
# ---------------------------------------------------------------------------


def test_strategy_context_client_field_is_typed_as_llm_client() -> None:
    """StrategyContext.client 的注解必须是 LLMClient（或字符串别名），
    不应直接绑定 FakeProvider / OpenAICompatibleProvider 等具体实现。
    """
    # 注解可能是字符串 forward-ref（base.py 用 TYPE_CHECKING import LLMClient
    # 以避免循环导入）。直接比对 dataclass 原始注解字符串，避免触发 eval。
    import dataclasses

    fields = {f.name: f for f in dataclasses.fields(StrategyContext)}
    assert "client" in fields
    raw = fields["client"].type
    raw_str = raw if isinstance(raw, str) else getattr(raw, "__name__", repr(raw))
    assert "LLMClient" in raw_str, (
        f"StrategyContext.client 注解={raw_str!r}，应包含 LLMClient"
    )
    # 不应直接绑定具体 provider 类型
    for forbidden in ("FakeProvider", "OpenAICompatibleProvider", "AnthropicCompatibleProvider"):
        assert forbidden not in raw_str


# ---------------------------------------------------------------------------
# 3. 一次 fake-only strategy.run：不写磁盘、不联网
# ---------------------------------------------------------------------------


@dataclass
class _MinimalLLMConfig:
    """构造 LLMClient 需要的最小 cfg duck-type。

    LLMClient 只依赖：``resolve_stage(stage)`` 与
    ``profiles[active_profile][stage]`` 与 ``models[alias]``。
    """

    active_profile: str
    profiles: dict[str, dict[str, str]]
    models: dict[str, "_MinimalModelConfig"]

    def resolve_stage(self, stage: str) -> "_MinimalModelConfig":
        alias = self.profiles[self.active_profile][stage]
        return self.models[alias]


@dataclass
class _MinimalModelConfig:
    alias: str
    type: str
    model: str
    provider: str = "fake"
    model_env: str | None = None


def _build_fake_client() -> LLMClient:
    """复用既有 build_providers + LLMClient + bundled 配置，强制 fake profile。

    避免手搓 _MinimalModelConfig 漏掉 max_retries 等隐含字段；这与
    cubox_cli.preview-ai-draft 的构造路径一致。
    """
    from dataclasses import replace as _replace

    from mindforge.assets_runtime import asset_root
    from mindforge.config import load_mindforge_config
    from mindforge.llm import build_providers

    cfg = load_mindforge_config(
        asset_root().joinpath("configs", "mindforge.yaml")  # type: ignore[arg-type]
    )
    safe_llm = _replace(cfg.llm, active_profile="fake")
    providers = build_providers(safe_llm)
    return LLMClient(llm_config=safe_llm, providers=providers)


def _make_doc() -> SourceDocument:
    return SourceDocument(
        source_id="cubox_api:stage5-test-doc",
        source_type="cubox_api",
        source_path="memory://stage5",
        title="Stage 5 strategy seam test",
        author=None,
        source_url=None,
        created_at=None,
        captured_at=datetime.now(timezone.utc),
        tags=[],
        raw_text="A short reading note used by strategy seam smoke. " * 4,
        content_hash="stage5testhashhashhash",
    )


class _NoOpLogger:
    run_id = "stage5-noop"

    def emit(self, event: str, **fields: object) -> None:
        return None


def _build_prompt_versions():
    from mindforge.config import PromptVersions

    return PromptVersions(
        triage="v1",
        distill="v1",
        link_suggestion="v1",
        review_questions="v1",
        action_extraction="v1",
    )


def test_strategy_run_with_fake_provider_does_not_open_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("strategy + fake provider 不应建立网络连接")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)

    from mindforge.assets_runtime import asset_root

    client = _build_fake_client()
    prompts_dir = asset_root().joinpath("prompts")
    tracks_text = asset_root().joinpath(
        "configs", "learning_tracks.yaml"
    ).read_text(encoding="utf-8")

    ctx = StrategyContext(
        client=client,
        prompts_dir=prompts_dir,
        prompt_versions=_build_prompt_versions(),
        triage_threshold=0,
        learning_tracks_text=tracks_text,
        logger=None,
    )
    strat = build_strategy(DEFAULT_STRATEGY_NAME, ctx)
    strat.logger = _NoOpLogger()  # type: ignore[assignment]
    outcome = strat.run(_make_doc())
    # 不要求 processed —— fake provider 与真实 prompt versions 之间可能
    # 有 manifest 缺失等正常 skipped/failed 路径。这里只断言：
    # outcome 是合法对象，**绝不**是 human_approved。
    assert outcome.status in {"processed", "skipped", "failed"}
    if outcome.card_payload is not None:
        # card_payload 是 in-memory dict；不应包含 human_approved 字面值
        assert "human_approved" not in str(outcome.card_payload)


def test_strategy_run_does_not_write_files_under_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    from mindforge.assets_runtime import asset_root

    client = _build_fake_client()
    prompts_dir = asset_root().joinpath("prompts")
    tracks_text = asset_root().joinpath(
        "configs", "learning_tracks.yaml"
    ).read_text(encoding="utf-8")

    ctx = StrategyContext(
        client=client,
        prompts_dir=prompts_dir,
        prompt_versions=_build_prompt_versions(),
        triage_threshold=0,
        learning_tracks_text=tracks_text,
        logger=None,
    )
    strat = build_strategy(DEFAULT_STRATEGY_NAME, ctx)
    strat.logger = _NoOpLogger()  # type: ignore[assignment]
    strat.run(_make_doc())

    leaked = (
        list(tmp_path.rglob("*.md"))
        + list(tmp_path.rglob("*.jsonl"))
        + list(tmp_path.rglob("*.json"))
        + list(tmp_path.rglob("*.yaml"))
    )
    assert leaked == [], f"strategy.run 不应写任何文件：{leaked}"


# ---------------------------------------------------------------------------
# 4. KnowledgeStrategy 仅依赖 SourceDocument → PipelineOutcome 输入输出面
# ---------------------------------------------------------------------------


def test_knowledge_strategy_protocol_run_signature_only_takes_source_document() -> None:
    """``KnowledgeStrategy.run`` 的参数类型必须是 ``SourceDocument``，
    不允许引入 source-specific 子类型（如 CuboxApiDocument）。
    """
    import inspect

    from mindforge.strategies.base import KnowledgeStrategy

    sig = inspect.signature(KnowledgeStrategy.run)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    assert len(params) == 1
    p = params[0]
    # annotation 可能是字符串 forward-ref（Pipeline.run 与 Protocol.run 都用
    # ``"SourceDocument"`` 字符串以避免循环导入），inspect 在 from __future__
    # import annotations 下会返回带引号的字符串。
    ann = p.annotation
    if isinstance(ann, str):
        # 接受 ``SourceDocument`` 或 ``"SourceDocument"`` 两种文本形态
        assert "SourceDocument" in ann
    else:
        assert ann is SourceDocument


# ---------------------------------------------------------------------------
# 5. LLMRequest/LLMResult 是 strategy ↔ provider 唯一稳定接口
# ---------------------------------------------------------------------------


def test_llm_request_and_result_are_immutable_value_objects() -> None:
    """LLMRequest / LLMResult 是 strategy 与 provider 之间的稳定契约，
    必须是 frozen dataclass，避免任一侧偷偷修改对方的视图。
    """
    import dataclasses

    assert dataclasses.is_dataclass(LLMRequest)
    assert dataclasses.is_dataclass(LLMResult)
    # frozen 标记
    assert getattr(LLMRequest, "__dataclass_params__").frozen is True
    assert getattr(LLMResult, "__dataclass_params__").frozen is True
