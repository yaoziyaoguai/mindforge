"""Strategy / prompt 只读可见性 CLI 契约。

中文学习型说明：本 milestone 要把已有 KnowledgeStrategy seam 和 prompt
assets 产品化为“可查看但不可编辑”的 UX。这里的测试刻意不构造 provider、
不读 .env、不跑 ingestion，确保 discovery 不是 execution。
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.strategies import get_strategy_metadata, list_strategies

runner = CliRunner()


def test_strategies_show_displays_single_strategy_details_without_execution() -> None:
    """show 是 strategy explain，不是 strategy run。

    输出必须足够用户判断状态、版本、安全边界和 stage/prompt 线索；planned
    策略也可以 show，但不能因此变成可执行。
    """

    result = runner.invoke(app, ["strategies", "show", "five_stage"])

    assert result.exit_code == 0, result.output
    out = result.output
    meta = get_strategy_metadata("five_stage")
    assert meta.strategy_id in out
    assert meta.strategy_version in out
    assert meta.status in out
    assert meta.provider_mode in out
    assert meta.safety_policy in out
    assert meta.output_schema_id in out
    for stage in (
        "triage",
        "distill",
        "link_suggestion",
        "review_questions",
        "action_extraction",
    ):
        assert stage in out
        assert "v1" in out
    assert "(not used by this strategy)" not in out


def test_strategies_show_planned_strategy_requires_internal_flag() -> None:
    result = runner.invoke(app, ["strategies", "show", "action_item"])

    assert result.exit_code != 0
    assert "--include-internal" in result.output

    result = runner.invoke(app, ["strategies", "show", "action_item", "--include-internal"])

    assert result.exit_code == 0, result.output
    assert "action_item" in result.output
    assert "planned" in result.output
    assert "not executable" in result.output


def test_strategies_show_unknown_strategy_fails_with_list_hint() -> None:
    result = runner.invoke(app, ["strategies", "show", "missing_strategy"])

    assert result.exit_code != 0
    assert "missing_strategy" in result.output
    assert "strategies list" in result.output


def test_prompts_list_shows_builtin_stage_versions_and_manifest_summary() -> None:
    result = runner.invoke(app, ["prompts", "list"])

    assert result.exit_code == 0, result.output
    out = result.output
    for stage in (
        "triage",
        "distill",
        "link_suggestion",
        "review_questions",
        "action_extraction",
    ):
        assert stage in out
        assert "v1" in out
    assert "description" in out


def test_prompts_show_displays_manifest_and_prompt_content_without_env_or_provider() -> None:
    result = runner.invoke(app, ["prompts", "show", "triage@v1"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "stage: triage" in out
    assert "version: v1" in out
    assert "description:" in out
    assert "{{title}}" in out or "{{ title }}" in out
    assert "api_key" not in out
    assert "MINDFORGE_" not in out


def test_prompt_cli_source_stays_read_only_and_provider_free() -> None:
    """静态守护：prompt visibility 不能偷偷初始化 provider 或读取 .env。"""

    src = Path("src/mindforge/prompt_cli.py").read_text(encoding="utf-8")
    forbidden = (
        "LLMClient(",
        "build_providers(",
        "load_dotenv",
        "Provider",
        "approve_card(",
        "CardWriter(",
    )
    for token in forbidden:
        assert token not in src


def test_strategies_list_hides_internal_by_default_and_can_include_it() -> None:
    result = runner.invoke(app, ["strategies", "list"])

    assert result.exit_code == 0, result.output
    assert "knowledge_card" in result.output
    assert "default_knowledge_card" not in result.output

    internal = runner.invoke(app, ["strategies", "list", "--include-internal"])
    assert internal.exit_code == 0, internal.output
    for meta in list_strategies():
        assert meta.strategy_id in internal.output


def test_readme_documents_card_provenance_and_prompt_visibility() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for token in (
        "mindforge strategies show knowledge_card",
        "mindforge prompts list",
        "mindforge prompts show triage@v1",
        "source content hash",
        "strategy/prompt/source/provider provenance",
        "strategy.active",
    ):
        assert token in text
