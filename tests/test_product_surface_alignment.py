"""产品表面与测试替身隔离契约。

中文学习型说明：MindForge 的端到端测试应该替身化 LLM 返回，而不是把
``fake provider`` 或 deterministic strategy 包装成用户能力。本文件只锁定
用户可见语义：正式 production workflow 是 Knowledge Card Workflow；
``five_stage`` 是 legacy/internal pipeline alias；deterministic baselines 默认
隐藏，不能作为 production active_strategy。
"""

from __future__ import annotations

from pathlib import Path
import tomllib

import pytest
from rich.console import Console
from typer.testing import CliRunner

from mindforge.assets_runtime import asset_root
from mindforge.cli import app
from mindforge.config import MindForgeConfig, StrategyConfig, load_mindforge_config
from mindforge.llm import LLMResult, ResolvedModel, StageCallResult
from mindforge.process_service import ProcessAssets, ProcessRuntime, ProviderSelection
from mindforge.processors.pipeline import _build_card_payload
from mindforge.process_executor import build_pipeline
from mindforge.presenters.local_status import render_local_status
from mindforge.services.doctor import compute_doctor_hints, config_doctor_rows
from mindforge.services.local_status import LocalStatusSnapshot
from mindforge.sources.base import SourceDocument, compute_content_hash
from mindforge.strategies import DEFAULT_STRATEGY_NAME, get_strategy_metadata
from mindforge.strategy_selection import (
    StrategySelectionError,
    resolve_strategy_selection,
)


runner = CliRunner()


def test_full_test_environment_installs_readable_source_extras() -> None:
    """完整测试环境必须安装 PDF/DOCX extras，而不是跳过可读文档测试。

    中文学习型说明：DOCX/PDF 是 optional runtime dependency，但 CI 跑的是完整
    pytest，里面会用 synthetic fixture 覆盖 Web DOCX dedup 和 adapter smoke。
    这里锁定 packaging/docs 口径，避免 CI 只安装 dev extras 导致测试环境漂移。
    """

    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = project["project"]["optional-dependencies"]

    assert "pypdf>=4.0" in extras["pdf"]
    assert "python-docx>=1.0" in extras["docx"]

    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    testing_doc = Path("docs/dev/testing.md").read_text(encoding="utf-8")
    assert ".[dev,pdf,docx]" in ci
    assert ".[dev,pdf,docx]" in testing_doc


def test_default_public_strategy_is_knowledge_card() -> None:
    assert DEFAULT_STRATEGY_NAME == "knowledge_card"
    meta = get_strategy_metadata("knowledge_card")
    assert meta.display_name == "Knowledge Card Workflow"
    assert meta.production_ready is True
    assert meta.user_recommended is True


def test_strategies_list_hides_internal_baselines_by_default() -> None:
    result = runner.invoke(app, ["strategies", "list"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "knowledge_card" in out
    assert "Knowledge Card Workflow" in out
    assert "default_knowledge_card" not in out
    assert "concept_extraction" not in out
    assert "action_item" not in out


def test_strategies_list_include_internal_shows_debug_fixtures() -> None:
    result = runner.invoke(app, ["strategies", "list", "--include-internal"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "knowledge_card" in out
    assert "default_knowledge_card" in out
    assert "concept_extraction" in out
    assert "action_item" in out
    assert "internal_baseline" in out
    assert "fake-first" not in out
    assert "回退路径" not in out
    assert "默认离线可跑" not in out
    assert "fake provider 默认" not in out


def test_strategies_show_legacy_alias_explains_canonical_strategy() -> None:
    result = runner.invoke(app, ["strategies", "show", "five_stage"])

    assert result.exit_code == 0, result.output
    assert "legacy alias" in result.output.lower()
    assert "knowledge_card" in result.output
    assert "Knowledge Card Strategy" in result.output
    assert "(not used by this strategy)" not in result.output


def test_internal_strategy_show_requires_include_internal() -> None:
    result = runner.invoke(app, ["strategies", "show", "default_knowledge_card"])

    assert result.exit_code != 0
    assert "--include-internal" in result.output


def test_active_strategy_default_and_legacy_alias_resolve_to_canonical(
) -> None:
    cfg = _bundled_config()
    assert cfg.strategy.active == "knowledge_card"

    legacy_cfg = _replace_strategy(cfg, "five_stage")
    selected = resolve_strategy_selection(legacy_cfg)
    assert selected.strategy_id == "knowledge_card"
    assert selected.metadata.canonical_id == "knowledge_card"
    assert selected.legacy_alias == "five_stage"


@pytest.mark.parametrize("strategy_id", ["default_knowledge_card", "concept_extraction", "action_item"])
def test_internal_strategy_cannot_be_active_without_dev_mode(
    strategy_id: str,
) -> None:
    cfg = _replace_strategy(_bundled_config(), strategy_id)

    with pytest.raises(StrategySelectionError, match="internal|not production|planned"):
        resolve_strategy_selection(cfg)


def test_knowledge_card_pipeline_writes_canonical_strategy_id() -> None:
    """新生成 card provenance 应写用户可见 canonical id，而不是内部 pipeline 名。

    大模型可以在测试里 stub，但 strategy runtime path 不能替换成
    deterministic strategy；这里直接测生产 pipeline envelope 的身份字段。
    """

    payload = _build_card_payload(
        doc=_source_doc(),
        track="agent-runtime",
        value_score=8,
        distill={
            "slug": "production-path-alignment",
            "title": "Production Path Alignment",
            "tags": ["strategy"],
            "confidence": 0.7,
            "source_excerpt": "Tests should stub LLM responses, not strategy.",
            "ai_summary_bullets": ["Use production strategy with injected LLM stubs."],
            "ai_inference_bullets": [],
            "reusable_prompts_or_principles": ["Fake model output, not strategy runtime."],
        },
        link_suggestion={"suggested_links": [], "project_hooks": []},
        review_questions={"review_questions": []},
        action_extraction={"action_items": []},
    )

    assert payload["strategy_id"] == "knowledge_card"
    assert payload["review_hints"]["title"] == "Production Path Alignment"


def test_knowledge_card_strategy_can_run_with_injected_stub_llm() -> None:
    """测试替身化 LLM response，而不是替换 strategy runtime path。

    中文学习型说明：这是 production/test path alignment 的核心。大模型返回可以
    stub，但仍应构造 Knowledge Card Workflow，并走 triage/distill/link/review/
    action 五段 prompt pipeline，最后得到 canonical ``knowledge_card`` envelope。
    """

    cfg = _bundled_config()
    pipeline = build_pipeline(
        cfg=cfg,
        runtime=_bundled_runtime(),
        strategy="knowledge_card",
        llm_client=_StubLLMClient(),
    )
    pipeline.logger = _NoOpLogger()  # type: ignore[attr-defined]

    outcome = pipeline.run(_source_doc())

    assert outcome.status == "processed"
    assert outcome.card_payload is not None
    assert outcome.card_payload["strategy_id"] == "knowledge_card"
    assert set(outcome.stages_meta) == {
        "triage",
        "distill",
        "link_suggestion",
        "review_questions",
        "action_extraction",
    }


def test_readme_main_path_does_not_recommend_fake_or_internal_strategies() -> None:
    text = Path("README.zh-CN.md").read_text(encoding="utf-8")
    main, _, _ = text.partition("## 文档导航")

    for token in ("mindforge demo", "fake", "Cubox", "cubox", "dogfood", "active_profile", "profiles"):
        assert token not in main, f"{token!r} must not appear in the user-facing README path"
    assert "--provider fake" not in main
    assert "default_knowledge_card" not in main
    assert "concept_extraction" not in main
    assert "Knowledge Card Workflow" in main


def test_example_config_does_not_contain_legacy_tokens() -> None:
    """configs/mindforge_example.yaml 不包含 legacy 配置标记。"""
    text = Path("configs/mindforge_example.yaml").read_text(encoding="utf-8")
    forbidden = ["active_profile", "profiles:", "fake_fast", "fake_strong",
                 "api_key_env", "base_url_env", "model_env", "anthropic_coding_plan",
                 "all_local", "active_profile: fake"]
    for token in forbidden:
        assert token not in text, f"forbidden token {token!r} found in example config"


def test_example_config_routing_refs_valid_models() -> None:
    """example config 的 routing 和 wiki.model 都引用 llm.models 中存在的 model id。"""
    import yaml
    data = yaml.safe_load(Path("configs/mindforge_example.yaml").read_text(encoding="utf-8"))
    models = set(data["llm"]["models"].keys())
    for step, model_id in data["llm"]["routing"].items():
        assert model_id in models, f"routing.{step}={model_id!r} not in models {models}"
    if "wiki" in data and "model" in data["wiki"]:
        assert data["wiki"]["model"] in models, f"wiki.model not in models {models}"


def test_readme_references_example_config() -> None:
    """README 以 workspace 为用户主概念；example config 仍存在于磁盘供 CI/部署。"""
    text = Path("README.zh-CN.md").read_text(encoding="utf-8")
    # 磁盘上的 example config 是 CI/部署产物，仍然存在
    assert Path("configs/mindforge_example.yaml").is_file()
    # README 不再让用户把它当主概念——workspace 是用户唯一需要理解的概念
    assert "workspace" in text
    assert "无需关心内部 config 文件路径" in text


def test_llm_provider_doc_references_example_config() -> None:
    """docs/zh-CN/model-setup.md 引用了 mindforge_example.yaml。"""
    text = Path("docs/zh-CN/model-setup.md").read_text(encoding="utf-8")
    assert "mindforge_example.yaml" in text


def test_llm_provider_doc_hides_legacy_and_internal_paths() -> None:
    """LLM 配置文档也必须以 Web Setup + real model 为主路径。"""

    text = Path("docs/zh-CN/model-setup.md").read_text(encoding="utf-8")
    for token in (
        "fake",
        "dogfood",
        "Cubox",
        "cubox",
        "active_profile",
        "profiles",
        "api_key_env",
        "base_url_env",
        "model_env",
        ".env",
    ):
        assert token not in text, f"{token!r} leaked into LLM provider docs"


def test_readme_first_stage_dogfood_contract_is_explicit() -> None:
    """README 锁定第一阶段 dogfood 表面，避免重新漂回 legacy/provider 文案。

    中文学习型说明：这不是业务逻辑测试，而是产品承诺测试。README 是 GitHub
    新用户的第一入口，必须把本地配置、secret store、路径和 Wiki 手动边界说清楚。
    """

    text = Path("README.zh-CN.md").read_text(encoding="utf-8")
    main, _, _ = text.partition("## 文档导航")

    assert "configs/mindforge.yaml" in text
    assert "本地 runtime config" in text
    assert "workspace" in text
    assert "自动记住" in text
    assert "secret store" in text
    assert ".mindforge/secrets.json" in text
    assert "默认不联网" in text
    assert "默认不调用真实 LLM/API" in text
    assert "显式配置 provider/API key" in text
    assert "不上传 telemetry" in text
    assert "environment files" in text
    assert "Web Add Source" in text
    assert "必须绝对路径" in text
    assert "anthropic" in text
    assert "anthropic_compatible" in text
    assert "openai" in text
    assert "openai_compatible" in text
    assert "LLM synthesis 必须由用户在 Wiki 页面或 CLI 手动触发" in text
    assert "not RAG / not embedding / no vector DB" in text
    assert "source_location_neighbor" in text
    assert "当前没有独立全局 Graph 页面" in text
    assert "vault/" in text
    assert "本地知识库" in text
    assert "不提交" in text
    assert "支持相对路径" in text
    assert "解析为绝对路径" in text

    for token in ("active_profile", "profiles", "fake_fast", "fake_strong", "mindforge demo", "Cubox", "dogfood"):
        assert token not in main, f"{token!r} must not appear in the user-facing README path"

    assert _  # reference section boundary exists.


def test_cli_primary_help_hides_internal_demo_cubox_env_profile_surfaces() -> None:
    """普通用户 CLI 主 help 只能展示第一阶段真实主路径。

    中文学习型说明：fake/demo/Cubox/env/profile 可以继续作为测试或开发内部实现
    存在，但不能再出现在 root help 里作为普通用户入口。
    """
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0, result.output
    out = result.output
    for token in (
        "demo",
        "dogfood",
        "cubox",
        "Cubox",
        "fake",
        "profile",
        "active_profile",
        "profiles",
        ".env",
        "env",
        "provider readiness",
        "profile_only",
    ):
        assert token not in out, f"{token!r} leaked into root help"
    for token in ("web", "status", "doctor", "watch", "import", "approve", "library", "trash", "wiki", "prompts", "recall"):
        assert token in out


def test_cli_commands_map_hides_internal_demo_cubox_env_profile_surfaces() -> None:
    """``mindforge commands`` 是普通用户命令地图，不列开发/测试 fixture。"""
    result = runner.invoke(app, ["commands"])

    assert result.exit_code == 0, result.output
    out = result.output
    for token in ("demo", "dogfood", "cubox", "Cubox", "fake", "profile", "active_profile", "profiles", ".env", "env"):
        assert token not in out, f"{token!r} leaked into commands map"
    assert "mindforge web" in out
    assert "mindforge watch add" in out
    assert "mindforge approve list" in out
    # 中文学习型说明：recall 的 ranking/explain 只在 --query 路径生效。
    # 命令地图里的示例必须可直接 copy-paste，不能生成缺 query 会失败的命令。
    assert 'mindforge recall --query "..." --ranking hybrid --explain' in out
    assert "mindforge recall --ranking hybrid --explain" not in out


def test_cli_direct_help_does_not_expose_retired_mode_surfaces() -> None:
    """隐藏入口的 help 也不能成为第二套产品说明书。

    中文学习型说明：Typer 的 ``hidden=True`` 只会从 root help 移除命令，
    但用户仍可能直达 ``command --help``。第一阶段产品语义必须统一到
    real model setup / local secret store / source import-watch / background
    processing / review-approve，不能通过隐藏 help 继续教授旧模式。
    """

    checks = [
        ["demo", "--help"],
        ["cubox", "--help"],
        ["dogfood", "--help"],
        ["provider", "--help"],
        ["llm", "--help"],
        ["process", "--help"],
        ["watch", "add", "--help"],
        ["import", "--help"],
    ]

    for args in checks:
        result = runner.invoke(app, args)
        out = result.output
        for token in (
            "fake-default",
            "fake provider",
            "dogfooding",
            "Cubox 本地",
            "Cubox JSON",
            "active_profile",
            "legacy profiles",
            "provider/profile",
            ".env",
            "env presence",
        ):
            assert token not in out, f"{token!r} leaked from {' '.join(args)}"


def test_cli_status_presenter_hides_legacy_provider_env_and_source_labels() -> None:
    """status 输出是普通用户入口，只展示模型设置和通用 source 类别。

    中文学习型说明：service 层为了兼容历史状态仍可能携带 profile/env/Cubox
    元数据；presenter 必须在用户主路径把它们翻译成第一阶段产品语义。
    """

    snapshot = LocalStatusSnapshot(
        config_path="/tmp/mindforge/configs/mindforge.yaml",
        vault={
            "path": "/tmp/mindforge/vault",
            "exists": True,
            "readable": True,
            "looks_like_mindforge": True,
            "is_real_environment": False,
        },
        workspace={
            "state_item_count": 1,
            "runs_path": "/tmp/mindforge/.mindforge/runs",
            "state_counts": {"ai_draft": 1},
            "source_counts": {"cubox_markdown": 1},
        },
        provider={
            "active_profile": "legacy",
            "opt_in_state": "profile_only",
            "network_called": False,
        },
        cubox={"token_present": True},
        env_keys=[{"name": "SECRET_TOKEN", "configured": True, "sources": ["process"]}],
        sources=[],
        cards={"total": 1, "by_status": {"ai_draft": 1}, "scan_error_count": 0},
        recall={"mode": "local lexical recall", "index_exists": False, "approved_card_count": 0},
        safety={
            "vault_path": "/tmp/mindforge/vault",
            "provider_state": "profile_only",
            "write_mode": "explicit_approval_required",
            "pending_drafts": 1,
        },
        next_actions=["mindforge approve list"],
        warnings=["Model setup may need review; status checks still do not call LLM."],
    )

    console = Console(record=True, width=120)
    render_local_status(console, snapshot)
    out = console.export_text()

    assert "model setup=needs setup" in out
    assert "imported_file" in out
    for token in ("active_profile", "profile_only", "Cubox", "cubox_markdown", ".env", "SECRET_TOKEN"):
        assert token not in out


def test_status_empty_state_does_not_recommend_approve_show_without_drafts() -> None:
    """没有 ai_draft 时，status 不能引导用户去空的 approve show。"""

    snapshot = LocalStatusSnapshot(
        config_path="/tmp/mindforge/configs/mindforge.yaml",
        vault={
            "path": "/tmp/mindforge/vault",
            "exists": True,
            "readable": True,
            "looks_like_mindforge": True,
            "is_real_environment": False,
        },
        workspace={
            "state_item_count": 0,
            "runs_path": "/tmp/mindforge/.mindforge/runs",
            "state_counts": {},
            "source_counts": {},
        },
        provider={
            "active_profile": "__model_routing__",
            "opt_in_state": "needs_setup",
            "network_called": False,
        },
        cubox={},
        env_keys=[],
        sources=[],
        cards={"total": 0, "by_status": {}, "scan_error_count": 0},
        recall={"mode": "local lexical recall", "index_exists": False, "approved_card_count": 0},
        safety={
            "vault_path": "/tmp/mindforge/vault",
            "provider_state": "needs_setup",
            "write_mode": "explicit_approval_required",
            "pending_drafts": 0,
        },
        next_actions=["mindforge watch add <file-or-folder>", "complete model setup in Web Setup"],
        warnings=[],
    )

    console = Console(record=True, width=120)
    render_local_status(console, snapshot)
    out = console.export_text()

    assert "approve show" not in out
    assert "mindforge watch add" in out


def test_status_cli_hides_old_setup_words_when_no_drafts(tmp_path: Path) -> None:
    """status 是 read/query 主路径：无 draft 时不给空 approve show，也不泄漏旧词。"""

    project = tmp_path / "project"
    vault = project / "vault"
    for subdir in ("00-Inbox", "20-Knowledge-Cards", "30-Projects"):
        (vault / subdir).mkdir(parents=True, exist_ok=True)
    cfg = project / "configs" / "mindforge.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        """
version: 0.7
vault:
  root: "vault"
llm:
  default_model: main
  models:
    main:
      type: openai_compatible
      base_url: "https://provider.example.com/v1"
      model: "model-name"
  routing:
    triage: main
    distill: main
    link_suggestion: main
    review_questions: main
    action_extraction: main
telemetry:
  enabled: true
  local_only: true
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["status", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    # 中文学习型说明：status 输出被 Rich 在不同终端宽度下折叠换行，
    # 换行点若落在空格处（如 "model " 在一行末尾、"setup=needs setup"
    # 在下一行开头），replace("\n", " ") 会引入多余空格。用 split+join
    # 归一化所有空白序列为单空格，确保 product surface 断言不被 Rich
    # 换行行为破坏。
    flat = " ".join(result.output.split())
    assert "model setup=needs setup" in flat
    assert "mindforge watch add" in result.output or "mindforge import" in result.output
    assert "approve show" not in result.output
    for token in ("fake", ".env", " env", "demo", "profile", "Cubox", "api_key_env"):
        assert token not in result.output


def test_doctor_logic_hides_demo_env_and_profile_hints() -> None:
    """doctor 的建议必须指向真实 Setup，而不是历史 demo/profile 路径。"""

    cfg = _bundled_config()
    out = "\n".join(
        [" ".join(row) for row in config_doctor_rows(cfg)]
        + [f"{priority} {message}" for priority, message in compute_doctor_hints(cfg, [])]
    )

    assert "model setup" in out
    for token in ("mindforge demo", "demo vault", "active_profile", ".env", "dogfood", "fake"):
        assert token not in out


def test_readme_quickstart_documents_clean_clone_bootstrap() -> None:
    """README Quick Start 以 workspace 为用户主概念，说明 init 后自动记住 workspace。"""

    text = Path("README.zh-CN.md").read_text(encoding="utf-8")
    quickstart = text.split("## 快速开始", 1)[1].split("\n## ", 1)[0]

    assert "mindforge web" in quickstart
    assert "首次运行" in quickstart or "查看 first-run" in quickstart
    assert "workspace" in quickstart
    assert "自动记住" in quickstart
    assert "无需关心内部 config 文件路径" in quickstart
    assert "local secret store" in text
    assert "API key 不写 YAML" in text


def test_readme_quickstart_uses_async_cli_main_path_and_hides_legacy_terms() -> None:
    """Quick Start 必须从 clean clone 到 async processing，而不是 Web-only 或旧同步路径。"""

    text = Path("README.zh-CN.md").read_text(encoding="utf-8")
    quickstart = text.split("## 快速开始", 1)[1].split("\n## ", 1)[0]

    for token in (
        "mindforge init",
        "mindforge start",
        "mindforge status",
        "mindforge watch add",
        "mindforge import",
        "mindforge runs list",
        "mindforge runs show",
        "mindforge approve list",
        "Library",
        "Wiki",
    ):
        assert token in quickstart
    for forbidden in (
        "Cubox",
        "cubox",
        "fake",
        "demo",
        "profile",
        ".env",
        "environment variable",
        "mindforge scan",
        "mindforge process",
        "scan && process",
    ):
        assert forbidden not in quickstart


def _source_doc() -> SourceDocument:
    raw = "A normal synthetic document about production/test path alignment."
    return SourceDocument(
        source_id="plain_markdown:alignment",
        source_type="plain_markdown",
        source_path="/tmp/alignment.md",
        title="Production Path Alignment",
        raw_text=raw,
        content_hash=compute_content_hash(raw),
        adapter_name="PlainMarkdownAdapter",
    )


def _bundled_config() -> MindForgeConfig:
    return load_mindforge_config(asset_root().joinpath("configs", "mindforge.yaml"))  # type: ignore[arg-type]


def _bundled_runtime() -> ProcessRuntime:
    prompts_root = asset_root().joinpath("prompts")
    tracks_text = asset_root().joinpath("configs", "learning_tracks.yaml").read_text(encoding="utf-8")  # type: ignore[union-attr]
    return ProcessRuntime(
        provider=ProviderSelection(active_profile="stub", requires_real_env=False),
        assets=ProcessAssets(
            prompts_dir=prompts_root,
            tracks_text=tracks_text,
            template_path=None,
            template_text=None,
        ),
        bypass_triage_gate=False,
    )


class _StubLLMClient:
    def resolve_model_for_stage(self, stage: str) -> ResolvedModel:
        return ResolvedModel(
            stage=stage,
            model_alias="stub_alias",
            provider="stub",
            actual_model="stub-model",
            type="stub",
        )

    def generate(self, *, stage: str, prompt: str, options=None) -> StageCallResult:  # type: ignore[no-untyped-def]
        payloads = {
            "triage": {
                "track": "agent-runtime",
                "value_score": 8,
                "should_process": True,
                "reason": "stubbed production-path triage",
                "topic_keywords": ["strategy", "testing"],
            },
            "distill": {
                "title": "Production Path Alignment",
                "slug": "production-path-alignment",
                "tags": ["strategy", "testing"],
                "confidence": 0.75,
                "source_excerpt": "Tests should stub LLM responses, not strategy runtime.",
                "ai_summary_bullets": ["Stub the model, keep the Knowledge Card Strategy."],
                "ai_inference_bullets": [],
                "reusable_prompts_or_principles": ["Fake model output, not strategy runtime."],
            },
            "link_suggestion": {"suggested_links": [], "project_hooks": []},
            "review_questions": {
                "review_questions": [
                    {
                        "angle": "architecture",
                        "question": "Why should tests stub LLM responses instead of strategy?",
                        "expected_points": ["same runtime path"],
                    }
                ]
            },
            "action_extraction": {"action_items": []},
        }
        import json

        return StageCallResult(
            resolved=self.resolve_model_for_stage(stage),
            result=LLMResult(
                text=json.dumps(payloads[stage], ensure_ascii=False),
                tokens_in=max(1, len(prompt) // 8),
                tokens_out=16,
                latency_ms=0,
                raw={"stub": True},
            ),
        )


class _NoOpLogger:
    run_id = "stubbed-production-path"

    def emit(self, event: str, **fields: object) -> None:
        return None


# ---------------------------------------------------------------------------
# Wiki LLM-first 产品语义 characterization tests
# ---------------------------------------------------------------------------


def test_commands_map_shows_wiki_rebuild_as_llm_first_not_deterministic() -> None:
    """``mindforge commands`` 中 wiki rebuild 不展示 --mode deterministic 作为主路径。

    设计意图：Wiki 主路径是 LLM synthesis，deterministic 只在 Advanced/Troubleshooting
    回退中暴露。命令地图是用户发现入口，必须展示 LLM-first 语义。
    """
    result = runner.invoke(app, ["commands"])

    assert result.exit_code == 0, result.output
    out = result.output

    # LLM-first wiki rebuild 命令存在
    assert "mindforge wiki rebuild" in out
    assert "LLM synthesis" in out or "LLM" in out

    # 主路径命令地图不展示 --mode deterministic
    assert "--mode deterministic" not in out


def test_llm_provider_doc_yaml_example_uses_llm_mode_not_deterministic() -> None:
    """docs/zh-CN/model-setup.md 的 YAML 示例必须推荐 mode: llm（非 deterministic）。

    LLM-first 产品承诺：普通用户看到的配置示例应该以 LLM synthesis 为默认路径。
    """
    text = Path("docs/zh-CN/model-setup.md").read_text(encoding="utf-8")

    # YAML 示例中 wiki.mode 推荐 llm
    assert "mode: llm" in text, "LLM provider doc 应包含 mode: llm 注释说明"

    # 不推荐 mode: deterministic 作为默认
    assert "mode: deterministic" not in text, (
        "LLM provider doc 不应推荐 mode: deterministic；llm 是主路径"
    )

    # 注释解释 LLM-first 语义
    assert "LLM-first" in text, "应在注释中说明 LLM-first synthesis 是推荐路径"


def test_llm_provider_doc_deterministic_only_in_troubleshooting_context() -> None:
    """deterministic 只在 Troubleshooting/回退上下文中出现，不作为并列选项。

    验证：docs/zh-CN/model-setup.md 中所有 deterministic 出现位置均
    在回退说明或 Troubleshooting 上下文中，而非 YAML 配置示例或推荐路径。
    """
    text = Path("docs/zh-CN/model-setup.md").read_text(encoding="utf-8")

    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "deterministic" in line.lower():
            # 收集周围上下文（上下各 3 行）
            start = max(0, i - 3)
            end = min(len(lines), i + 4)
            context = " ".join(lines[start:end]).lower()

            troubleshooting_words = (
                "troubleshooting", "回退", "fallback", "advanced",
                "不推荐", "不是推荐", "not the recommended",
            )
            assert any(w in context for w in troubleshooting_words), (
                f"line {i}: 'deterministic' 出现在非回退上下文中: {line.strip()}"
            )


def test_llm_provider_doc_auto_rebuild_explains_llm_safety() -> None:
    """auto_rebuild_on_approve 的说明必须包含 LLM synthesis 安全语义。

    不应暗示只运行 deterministic rebuild。应明确说明使用 wiki.mode 指定的方式，
    LLM synthesis 需要已配置模型和 API key。
    """
    text = Path("docs/zh-CN/model-setup.md").read_text(encoding="utf-8")

    assert "auto_rebuild_on_approve" in text

    # 新语义：使用 wiki.mode 指定的方式
    assert "wiki.mode" in text or "mode" in text

    # 不应暗示只运行 deterministic
    assert "只运行 deterministic" not in text
    assert "也只运行 deterministic" not in text

    # 应提到需要模型配置
    assert ("模型" in text) or ("model" in text.lower() and "api" in text.lower()), (
        "auto_rebuild_on_approve 说明应提到模型配置要求"
    )


def test_readme_wiki_section_does_not_expose_deterministic_as_primary() -> None:
    """README Wiki 章节不暴露 deterministic 作为主路径。

    Wiki 是 LLM-first synthesis；deterministic 仅在 Advanced/Troubleshooting 中出现。
    """
    text = Path("README.zh-CN.md").read_text(encoding="utf-8")

    # 找到 Wiki 相关内容
    wiki_start = text.find("Wiki")
    assert wiki_start >= 0, "README 应包含 Wiki 内容"

    # 在 Wiki 相关内容区域（前后各 200 字符）
    region = text[max(0, wiki_start - 200):wiki_start + 2000]

    # LLM-first 描述
    assert "LLM-first synthesis" in region or "LLM synthesis" in region

    # Wiki rebuild 命令不展示 --mode deterministic
    assert "wiki rebuild\"" not in region or "--mode deterministic" not in region

    # deterministic 只应在 Advanced 或 Troubleshooting 上下文
    if "deterministic" in region:
        idx = region.index("deterministic")
        nearby = region[max(0, idx - 50):idx + 100]
        assert any(w in nearby.lower() for w in ("advanced", "troubleshooting", "回退", "fallback", "not recommended")), (
            "README 中 deterministic 只应在 Advanced/Troubleshooting 上下文出现"
        )


def _replace_strategy(cfg: MindForgeConfig, active: str) -> MindForgeConfig:
    return MindForgeConfig(
        version=cfg.version,
        vault=cfg.vault,
        sources=cfg.sources,
        state=cfg.state,
        triage=cfg.triage,
        llm=cfg.llm,
        prompts=cfg.prompts,
        logging=cfg.logging,
        review=cfg.review,
        telemetry=cfg.telemetry,
        obsidian=cfg.obsidian,
        search=cfg.search,
        strategy=StrategyConfig(active=active),
        raw=cfg.raw,
    )


# —— wiki rebuild LLM-first 边界测试 ——


def test_wiki_config_default_mode_is_llm() -> None:
    """WikiConfig 默认 mode 必须是 llm，不是 deterministic。

    deterministic 仅保留为内部兼容回退，不在普通用户配置默认中暴露。
    """
    from mindforge.config import WikiConfig

    cfg = WikiConfig()
    assert cfg.mode == "llm", f"WikiConfig 默认 mode 应为 llm，实际为 {cfg.mode!r}"


def test_wiki_parse_defaults_to_llm() -> None:
    """_parse_wiki 缺失 mode 字段时应默认 llm，不是 deterministic。"""
    from mindforge.config import _parse_wiki

    wiki = _parse_wiki({})
    assert wiki.mode == "llm", f"缺失 mode 时应默认 llm，实际为 {wiki.mode!r}"

    wiki_none = _parse_wiki(None)
    assert wiki_none.mode == "llm", f"raw=None 时应默认 llm，实际为 {wiki_none.mode!r}"


def test_wiki_parse_rejects_unknown_mode_with_llm_first_message() -> None:
    """_parse_wiki 错误消息应优先推荐 llm。"""
    from mindforge.config import ConfigError, _parse_wiki

    with pytest.raises(ConfigError) as exc:
        _parse_wiki({"mode": "gpt5"})
    msg = str(exc.value)
    assert "llm" in msg, f"错误消息应包含 llm: {msg}"
    assert msg.index("llm") < msg.index("deterministic"), (
        f"错误消息中 llm 应在 deterministic 之前: {msg}"
    )


def test_wiki_rebuild_help_hides_mode_option(tmp_path: Path) -> None:
    """wiki rebuild --help 不应展示 --mode deterministic 选项给普通用户。

    --mode 选项标记为 hidden=True，只在显式 --help 不展示。
    """
    import yaml

    vault = tmp_path / "vault"
    (vault / "00-Inbox").mkdir(parents=True)
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {"root": str(vault)},
                "llm": {
                    "default_model": "main",
                    "models": {
                        "main": {"type": "anthropic_compatible", "base_url": "https://x.example.com", "model": "m1"},
                    },
                },
                "wiki": {"mode": "llm"},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["wiki", "rebuild", "--help", "--config", str(cfg_path)])

    assert result.exit_code == 0, result.output
    # --mode 不应出现在帮助文本中
    assert "--mode" not in result.output, (
        "wiki rebuild --help 不应展示 --mode 选项，实际输出包含 --mode"
    )
    # 不应展示 deterministic 作为选项
    assert "deterministic" not in result.output, (
        f"wiki rebuild --help 不应展示 deterministic，实际输出: {result.output}"
    )


def test_wiki_rebuild_requires_model_setup(
    tmp_path: Path, monkeypatch
) -> None:
    """wiki rebuild 在 model setup incomplete 时必须报错，不能静默 fallback 到 deterministic。

    LLM-first 原则：没有模型配置时，wiki rebuild 应明确提示需要 model setup，
    而不是走 deterministic template rebuild 作为静默主路径。
    """
    import yaml

    vault = tmp_path / "vault"
    (vault / "00-Inbox").mkdir(parents=True)
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
                    "archive_dir": "90-Archive",
                },
                "sources": {
                    "enabled": ["plain_markdown"],
                    "registry": {
                        "plain_markdown": {
                            "adapter": "PlainMarkdownAdapter",
                            "inbox_subdir": "00-Inbox",
                            "file_glob": "*.md",
                            "enabled": True,
                        },
                    },
                },
                "state": {
                    "workdir": ".mindforge",
                    "state_file": "state.json",
                    "runs_dir": "runs",
                    "index_file": "index.jsonl",
                    "backup_state": True,
                },
                "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
                "llm": {
                    "default_model": None,
                    "models": {},
                    "routing": {},
                },
                "wiki": {"mode": "llm"},
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
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(vault)

    result = runner.invoke(app, ["wiki", "rebuild", "--config", str(cfg_path)])

    assert result.exit_code != 0, (
        f"model setup incomplete 时 wiki rebuild 应报错退出，实际 exit_code=0: {result.output}"
    )
    assert "model setup" in result.output.lower(), (
        f"错误消息应包含 model setup，实际: {result.output}"
    )
    assert "deterministic" not in result.output.lower(), (
        f"model setup incomplete 时不应建议 deterministic 作为替代方案: {result.output}"
    )


def test_llm_first_readme_wiki_rebuild_not_deterministic() -> None:
    """README 中 wiki rebuild 命令描述不应暗示 deterministic 为主路径。"""
    text = Path("README.zh-CN.md").read_text(encoding="utf-8")

    # 找到 wiki rebuild 相关上下文
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "wiki rebuild" in line.lower() and "deterministic" not in line.lower():
            # 检查周围 5 行，不应有将 deterministic 作为主路径的描述
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            context = " ".join(lines[start:end]).lower()
            assert "deterministic" not in context, (
                f"line {i}: wiki rebuild 上下文不应出现 deterministic: {line.strip()}"
            )


def test_mindforge_commands_wiki_rebuild_is_llm_first() -> None:
    """mindforge commands 输出中 wiki rebuild 应描述为 LLM synthesis。"""
    result = runner.invoke(app, ["commands"])

    assert result.exit_code == 0, result.output
    # wiki rebuild 描述应包含 LLM synthesis
    assert ("LLM synthesis" in result.output or "LLM" in result.output), (
        f"commands 中 wiki rebuild 应描述为 LLM synthesis，实际: {result.output}"
    )
    # 不应将 deterministic 作为可见命令选项
    assert "deterministic" not in result.output, (
        f"commands 输出不应包含 deterministic: {result.output}"
    )
