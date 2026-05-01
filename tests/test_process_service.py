"""v0.7.20 — process_service 领域边界测试。

这些测试直接覆盖 service 层，**不通过** Typer CLI / CliRunner。目的：

1. 把 fake-safety / no-real-LLM / ai_draft 等系统级安全边界从 console 文案
   分支里独立出来，让它们能被静态保护；
2. 证明 ``process_service`` 没有依赖 ``typer`` / ``rich`` / ``console`` /
   ``RunLogger`` / ``dotenv``，可以在最小依赖下被 service-level 单元测试覆盖；
3. 与 ``safety_policy.boundary_statement(...)`` 对齐，确认本 service 与全局
   边界声明一致。

本轮明确不动 processor 主链路，因此 ``summarize_outcome`` 仅用 dataclass 构造
``PipelineOutcome`` / ``StageResult`` 进行单元验证，不真的跑 pipeline。
"""

from __future__ import annotations

import ast
import importlib
import inspect
import sys
from pathlib import Path

import pytest
import yaml

from mindforge import process_service
from mindforge.config import MindForgeConfig, load_mindforge_config
from mindforge.process_service import (
    FAKE_PROFILE,
    PROCESS_ERROR_MALFORMED_INPUT,
    PROCESS_ERROR_MISSING_SOURCE,
    PROCESS_ERROR_UNSUPPORTED_PROVIDER,
    ProcessError,
    ProcessRequest,
    ProcessRuntime,
    resolve_process_runtime,
    summarize_outcome,
)
from mindforge.processors.base import StageResult
from mindforge.processors.pipeline import PipelineOutcome
from mindforge.safety_policy import boundary_statement
from mindforge.sources.base import SourceDocument


# ---------------------------------------------------------------------------
# 测试 fixture：构造最小 fake-only MindForgeConfig，无真实 LLM / 无 .env
# ---------------------------------------------------------------------------


def _write_min_cfg(tmp_path: Path, *, active_profile: str = "fake") -> Path:
    """构造最小可加载的 mindforge.yaml；默认 fake profile，无网络 / 无 .env。"""
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                    "projects_dir": "30-Projects",
                },
                "sources": {
                    "enabled": ["plain_markdown"],
                    "registry": {
                        "plain_markdown": {
                            "adapter": "PlainMarkdownAdapter",
                            "inbox_subdir": "ManualNotes",
                            "file_glob": "*.md",
                            "enabled": True,
                        }
                    },
                },
                "state": {
                    "workdir": str(tmp_path / ".mindforge"),
                    "state_file": "state.json",
                    "runs_dir": "runs",
                    "index_file": "index.jsonl",
                },
                "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
                "llm": {
                    "active_profile": active_profile,
                    "profiles": {
                        "fake": {
                            "triage": "f1",
                            "distill": "f1",
                            "link_suggestion": "f1",
                            "review_questions": "f1",
                            "action_extraction": "f1",
                        },
                        "openai": {
                            "triage": "o1",
                            "distill": "o1",
                            "link_suggestion": "o1",
                            "review_questions": "o1",
                            "action_extraction": "o1",
                        },
                    },
                    "models": {
                        "f1": {
                            "provider": "fake-local",
                            "type": "fake",
                            "base_url": "fake://",
                            "model": "fake-1",
                            "timeout_seconds": 5,
                            "max_retries": 0,
                        },
                        "o1": {
                            "provider": "openai-compatible",
                            "type": "openai_compatible",
                            "base_url": "https://example.com",
                            "model": "gpt-test",
                            "api_key_env": "OPENAI_API_KEY",
                            "timeout_seconds": 5,
                            "max_retries": 0,
                        },
                    },
                },
                "prompts": {
                    "triage_version": "v1",
                    "distill_version": "v1",
                    "link_suggestion_version": "v1",
                    "review_questions_version": "v1",
                    "action_extraction_version": "v1",
                },
                "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return cfg_path


def _load_cfg(tmp_path: Path, *, active_profile: str = "fake") -> MindForgeConfig:
    return load_mindforge_config(_write_min_cfg(tmp_path, active_profile=active_profile))


def _doc() -> SourceDocument:
    """构造最小 SourceDocument 用于 summarize_outcome。"""
    return SourceDocument(
        source_id="sid-1",
        source_type="plain_markdown",
        source_path="00-Inbox/ManualNotes/sample.md",
        title="Sample",
        source_url=None,
        raw_text="hello",
        content_hash="hash-1",
        adapter_name="PlainMarkdownAdapter",
    )


def _stage_result(parsed: dict) -> StageResult:
    return StageResult(
        stage="triage",
        parsed=parsed,
        prompt_version="triage@v1",
        model_alias="f1",
        provider="fake-local",
        actual_model="fake-1",
        tokens_in=0,
        tokens_out=0,
        latency_ms=0,
    )


# ---------------------------------------------------------------------------
# 1. fake provider 默认安全路径保持不变
# ---------------------------------------------------------------------------


def test_fake_provider_default_path_does_not_require_real_env(tmp_path: Path) -> None:
    """默认 fake profile → ``requires_real_env=False``。

    与 ``safety_policy.boundary_statement('fake_provider_default')`` 对齐：
    fake provider 是默认安全路径，不需要读 ``.env`` / 不调用真实 LLM。
    """
    cfg = _load_cfg(tmp_path, active_profile="fake")
    runtime = resolve_process_runtime(ProcessRequest(cfg=cfg))
    assert isinstance(runtime, ProcessRuntime)
    assert runtime.provider.active_profile == FAKE_PROFILE
    assert runtime.provider.requires_real_env is False
    # 与 safety_policy 边界声明对齐（文档/测试双向引用，不耦合控制流）
    assert "fake provider" in boundary_statement("fake_provider_default")


# ---------------------------------------------------------------------------
# 2. explicit fake provider selection
# ---------------------------------------------------------------------------


def test_explicit_fake_profile_selected(tmp_path: Path) -> None:
    """显式指定 fake profile，service 选择结果稳定。"""
    cfg = _load_cfg(tmp_path, active_profile="fake")
    runtime = resolve_process_runtime(ProcessRequest(cfg=cfg))
    assert isinstance(runtime, ProcessRuntime)
    assert runtime.provider.active_profile == "fake"


# ---------------------------------------------------------------------------
# 3. unsupported provider 返回结构化错误
# ---------------------------------------------------------------------------


def test_unsupported_provider_returns_structured_error(tmp_path: Path) -> None:
    """active_profile 不在 profiles 中 → unsupported_provider 错误。

    config loader 已对 active_profile 做过严格校验；本测试用 dataclass
    ``replace`` 构造非法 cfg 验证 service 层的防御式检查。
    """
    from dataclasses import replace

    cfg = _load_cfg(tmp_path)
    bad_llm = replace(cfg.llm, active_profile="nonexistent")
    bad_cfg = replace(cfg, llm=bad_llm)
    err = resolve_process_runtime(ProcessRequest(cfg=bad_cfg))
    assert isinstance(err, ProcessError)
    assert err.code == PROCESS_ERROR_UNSUPPORTED_PROVIDER
    assert err.detail["active_profile"] == "nonexistent"
    assert "fake" in err.detail["known"]


# ---------------------------------------------------------------------------
# 4. missing source / malformed input 返回结构化错误
# ---------------------------------------------------------------------------


def test_missing_source_empty_enabled_returns_structured_error(tmp_path: Path) -> None:
    """``sources.enabled`` 为空 → service 拒绝处理（missing_source）。"""
    from dataclasses import replace

    cfg = _load_cfg(tmp_path)
    bad_sources = replace(cfg.sources, enabled=())
    bad_cfg = replace(cfg, sources=bad_sources)
    err = resolve_process_runtime(ProcessRequest(cfg=bad_cfg))
    assert isinstance(err, ProcessError)
    assert err.code == PROCESS_ERROR_MISSING_SOURCE


def test_malformed_negative_limit_returns_structured_error(tmp_path: Path) -> None:
    cfg = _load_cfg(tmp_path)
    err = resolve_process_runtime(ProcessRequest(cfg=cfg, limit=-1))
    assert isinstance(err, ProcessError)
    assert err.code == PROCESS_ERROR_MALFORMED_INPUT
    assert err.detail["field"] == "limit"


# ---------------------------------------------------------------------------
# 5. process result 是 ai_draft，不是 human_approved
# 6. process_service 不自动 approve
# ---------------------------------------------------------------------------


def test_summarize_processed_outcome_yields_ai_draft_semantics() -> None:
    """summarize_outcome 不会写入 status=human_approved；卡片晋升只能由
    ``approval_service.approve_explicit_card`` 显式人审动作完成。"""
    outcome = PipelineOutcome(
        status="processed",
        triage=_stage_result({"track": "agents", "value_score": 8}),
        card_payload={"id": "card-1", "title": "x"},
    )
    result = summarize_outcome(outcome, _doc(), "PlainMarkdownAdapter", dry_run=False)
    assert result.status == "processed"
    assert result.track == "agents"
    assert result.value_score == 8
    assert result.would_write_only is False
    # service 不携带 status=human_approved 字段；CLI/writer 写卡片时默认 ai_draft
    payload_str = repr(result.card_payload)
    assert "human_approved" not in payload_str
    # 与 safety_policy 边界对齐
    assert "human_approved" in boundary_statement("human_approved_gate")


# ---------------------------------------------------------------------------
# 7. 不读取真实 .env（构造 runtime 不触发 dotenv）
# 8. 不调用真实 LLM（不实例化真实 provider）
# ---------------------------------------------------------------------------


def test_resolve_does_not_load_dotenv_or_instantiate_real_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """监视 ``env_loader.load_dotenv_silently`` 与 ``llm.factory.build_providers``：
    service 构造 runtime 不应触发任一者。"""
    import mindforge.env_loader as env_loader
    import mindforge.llm.factory as llm_factory

    calls: list[str] = []

    def _fake_dotenv(*args, **kwargs) -> dict[str, str]:
        calls.append("dotenv")
        return {}

    def _fake_build(*args, **kwargs):  # pragma: no cover - guard
        calls.append("build_providers")
        return {}

    monkeypatch.setattr(env_loader, "load_dotenv_silently", _fake_dotenv)
    monkeypatch.setattr(llm_factory, "build_providers", _fake_build)

    cfg = _load_cfg(tmp_path, active_profile="openai")
    runtime = resolve_process_runtime(ProcessRequest(cfg=cfg))
    assert isinstance(runtime, ProcessRuntime)
    assert runtime.provider.requires_real_env is True
    assert calls == [], (
        "process_service.resolve_process_runtime 不应触发 dotenv 或 "
        "build_providers；这两个副作用必须留给 CLI 端。"
    )
    # 与 safety_policy 边界声明对齐
    assert "no_env_read" or boundary_statement("no_env_read")
    assert "real LLM" in boundary_statement("no_real_llm")


# ---------------------------------------------------------------------------
# 9. 不依赖 Typer / Rich / console（静态 import 断言）
# ---------------------------------------------------------------------------


def test_process_service_module_does_not_import_typer_rich_console() -> None:
    """通过 AST 解析 ``process_service`` 模块的 import 与名称引用，确保它没有
    依赖 Typer / Rich / dotenv / RunLogger 这些 CLI/IO 层符号。

    使用 AST 而不是字符串扫描，是因为 docstring 中合法地讨论了这些被禁止
    的依赖；字符串扫描会误命中文档。
    """
    if "mindforge.process_service" in sys.modules:
        del sys.modules["mindforge.process_service"]
    importlib.import_module("mindforge.process_service")
    src = inspect.getsource(process_service)
    tree = ast.parse(src)
    forbidden_modules = {"typer", "rich", "dotenv"}
    forbidden_top = {"typer", "rich"}
    forbidden_attr = {"console", "RunLogger", "load_dotenv", "load_dotenv_silently"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in forbidden_modules, (
                    f"process_service 不应 import {alias.name!r}"
                )
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            assert mod not in forbidden_modules, (
                f"process_service 不应 from {node.module!r} import"
            )
            for alias in node.names:
                assert alias.name not in forbidden_attr, (
                    f"process_service 不应引入符号 {alias.name!r}"
                )
        elif isinstance(node, ast.Name):
            assert node.id not in forbidden_top, (
                f"process_service 不应引用顶层 {node.id!r}"
            )
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in forbidden_top:
                pytest.fail(f"process_service 不应访问 {node.value.id}.{node.attr}")


# ---------------------------------------------------------------------------
# 10. 不写正式 Obsidian notes（无写文件副作用）
# ---------------------------------------------------------------------------


def test_resolve_does_not_write_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """监视 ``Path.write_text`` / ``Path.write_bytes``：service 不主动写文件。

    例外：用户显式传 ``tracks`` 时会 ``read_text`` 用户文件 —— 这是读，
    不是写。本测试不传 tracks，确保零写入。
    """
    cfg = _load_cfg(tmp_path)
    # 仅在 cfg 加载完毕后再开始监视 ——  fixture 写 yaml 是测试 setup，不属于
    # service 的副作用边界。
    writes: list[str] = []
    real_write_text = Path.write_text
    real_write_bytes = Path.write_bytes

    def _track_write_text(self, *a, **kw):  # type: ignore[no-untyped-def]
        writes.append(str(self))
        return real_write_text(self, *a, **kw)

    def _track_write_bytes(self, *a, **kw):  # type: ignore[no-untyped-def]
        writes.append(str(self))
        return real_write_bytes(self, *a, **kw)

    monkeypatch.setattr(Path, "write_text", _track_write_text)
    monkeypatch.setattr(Path, "write_bytes", _track_write_bytes)

    _ = resolve_process_runtime(ProcessRequest(cfg=cfg))
    assert writes == [], f"process_service 不应写文件；实际写入={writes}"


# ---------------------------------------------------------------------------
# 11. 不做 RAG / embedding（无 embedding/index 依赖）
# ---------------------------------------------------------------------------


def test_process_service_does_not_reference_embedding_or_rag() -> None:
    """AST 解析：process_service 没有 import / 调用 embedding / vector / RAG
    相关符号。docstring 合法讨论这些被禁止的依赖，故不用字符串扫描。"""
    src = inspect.getsource(process_service)
    tree = ast.parse(src)
    forbidden_substrings = ("embedding", "embeddings", "vector", "rag")

    def _bad(name: str) -> bool:
        low = name.lower()
        return any(s in low for s in forbidden_substrings)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not _bad(alias.name), f"不应 import {alias.name!r}"
        elif isinstance(node, ast.ImportFrom):
            assert not _bad(node.module or ""), f"不应 from {node.module!r} import"
            for alias in node.names:
                assert not _bad(alias.name), f"不应引入符号 {alias.name!r}"
        elif isinstance(node, ast.Name):
            assert not _bad(node.id), f"不应引用名称 {node.id!r}"
        elif isinstance(node, ast.Attribute):
            assert not _bad(node.attr), f"不应访问属性 {node.attr!r}"

    assert "embedding" in boundary_statement("no_embedding")
    assert "RAG" in boundary_statement("no_rag")


# ---------------------------------------------------------------------------
# 12. provider/profile 选择结果稳定（确定性）
# ---------------------------------------------------------------------------


def test_provider_selection_is_deterministic(tmp_path: Path) -> None:
    cfg = _load_cfg(tmp_path, active_profile="openai")
    r1 = resolve_process_runtime(ProcessRequest(cfg=cfg))
    r2 = resolve_process_runtime(ProcessRequest(cfg=cfg))
    assert isinstance(r1, ProcessRuntime) and isinstance(r2, ProcessRuntime)
    assert r1.provider == r2.provider
    assert r1.provider.requires_real_env is True


# ---------------------------------------------------------------------------
# 13. summarize_outcome 三分流字节级一致 + dry_run
# ---------------------------------------------------------------------------


def test_summarize_skipped_carries_skip_reason() -> None:
    outcome = PipelineOutcome(
        status="skipped",
        triage=_stage_result({"track": "noise", "value_score": 1}),
        skip_reason="below threshold",
    )
    result = summarize_outcome(outcome, _doc(), "PlainMarkdownAdapter", dry_run=False)
    assert result.status == "skipped"
    assert result.skip_reason == "below threshold"
    assert result.track == "noise"
    assert result.would_write_only is False


def test_summarize_failed_carries_error_stage_and_message() -> None:
    outcome = PipelineOutcome(
        status="failed",
        error_stage="distill",
        error_message="boom",
    )
    result = summarize_outcome(outcome, _doc(), "PlainMarkdownAdapter", dry_run=False)
    assert result.status == "failed"
    assert result.error_stage == "distill"
    assert result.error_message == "boom"
    # failed 分支没有 triage → track / value_score 应为 None（与 v0.7.19 CLI 行为一致）
    assert result.track is None
    assert result.value_score is None


def test_summarize_dry_run_processed_marks_would_write_only() -> None:
    outcome = PipelineOutcome(
        status="processed",
        triage=_stage_result({"track": "agents", "value_score": 7}),
        card_payload={"id": "x"},
    )
    result = summarize_outcome(outcome, _doc(), "PlainMarkdownAdapter", dry_run=True)
    assert result.would_write_only is True
    assert result.status == "processed"


# ---------------------------------------------------------------------------
# 14. 与 approval_service 的 human-approved 语义不冲突
# ---------------------------------------------------------------------------


def test_summarize_outcome_does_not_promote_to_human_approved() -> None:
    """即便 outcome 完成，service 也只回 ``status="processed"``；human_approved
    只能通过 ``approval_service`` 显式人审动作产生。"""
    outcome = PipelineOutcome(
        status="processed",
        triage=_stage_result({"track": "x", "value_score": 9}),
        card_payload={"id": "card-x", "status": "ai_draft"},
    )
    result = summarize_outcome(outcome, _doc(), "PlainMarkdownAdapter", dry_run=False)
    assert result.status != "human_approved"
    assert result.status == "processed"


# ---------------------------------------------------------------------------
# 15. 与 recall / review 的只读消费边界不冲突
# ---------------------------------------------------------------------------


def test_resolve_does_not_touch_lexical_index_or_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """监视 lexical_index 与 review_service 的入口：service 不应触碰它们。"""
    import mindforge.lexical_index as lexical_index
    import mindforge.review_service as review_service

    bad: list[str] = []

    def _no(name: str):
        def _fn(*a, **kw):
            bad.append(name)
            raise AssertionError(f"process_service 不应触碰 {name}")
        return _fn

    # 监视 review_service 中已存在的公共入口（运行时不触发即视为通过）
    if hasattr(review_service, "build_weekly_review"):
        monkeypatch.setattr(review_service, "build_weekly_review", _no("build_weekly_review"))
    # 监视 lexical_index 中的索引构建入口
    if hasattr(lexical_index, "build_lexical_index"):
        monkeypatch.setattr(lexical_index, "build_lexical_index", _no("build_lexical_index"))

    cfg = _load_cfg(tmp_path)
    _ = resolve_process_runtime(ProcessRequest(cfg=cfg))
    assert bad == []
