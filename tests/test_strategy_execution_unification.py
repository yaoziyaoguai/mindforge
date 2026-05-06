"""Strategy execution unification / product-path alignment regression tests.

中文学习型说明：本文件覆盖本轮 milestone 的运行时语义，而不是只测
``strategies list/show`` 的只读 seam。核心边界：

- strategy selection 与 provider selection 正交；
- active strategy / ``--strategy`` 必须进入 import/process/watch 主路径；
- 生产路径默认是 Knowledge Card Strategy（canonical id: knowledge_card）；
- deterministic baseline 是内部测试夹具，不能作为 active production strategy。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.config import load_mindforge_config
from mindforge.watch_registry import WatchRegistry

runner = CliRunner()


def _write_config(
    tmp_path: Path,
    *,
    active_provider: str = "fake",
    active_strategy: str | None = None,
) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    cfg_path = tmp_path / "configs" / "mindforge.yaml"
    cfg_path.parent.mkdir(parents=True)
    raw: dict[str, object] = {
        "version": 0.7,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
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
            "backup_state": True,
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active": active_provider,
            "providers": {
                "fake": {
                    "type": "fake",
                    "purpose": "offline_demo_ci_deterministic_tests",
                },
                "anthropic": {
                    "type": "anthropic",
                    "api_key_env": "MINDFORGE_ANTHROPIC_API_KEY",
                    "base_url_env": "MINDFORGE_ANTHROPIC_BASE_URL",
                    "model_env": "MINDFORGE_ANTHROPIC_MODEL",
                    "default_base_url": "https://api.anthropic.com",
                    "default_model": "claude-3-5-haiku-latest",
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
    }
    if active_strategy is not None:
        raw["strategy"] = {"active": active_strategy}
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return cfg_path, vault


def _write_note(vault: Path, name: str = "note.md") -> Path:
    note = vault / "00-Inbox" / "ManualNotes" / name
    note.write_text(
        "# Strategy Runtime Note\n\n"
        "This document captures a reusable production lesson about separating "
        "provider selection from extraction strategy selection while keeping the "
        "same Knowledge Card Strategy runtime path in tests. The important "
        "principle is that model responses can be stubbed, but the extraction "
        "strategy should remain the production prompt pipeline so import, "
        "process, watch, approval, and recall exercise the same architecture. "
        "Teams should preserve source provenance, prompt versions, provider "
        "metadata, and strategy identity so every ai_draft can be audited before "
        "human approval.\n",
        encoding="utf-8",
    )
    return note


def _cards(vault: Path) -> list[Path]:
    return sorted((vault / "20-Knowledge-Cards").rglob("*.md"))


def test_config_defaults_active_strategy_to_knowledge_card(tmp_path: Path) -> None:
    cfg_path, _vault = _write_config(tmp_path)

    cfg = load_mindforge_config(cfg_path)

    assert cfg.strategy.active == "knowledge_card"


def test_legacy_five_stage_active_strategy_resolves_to_knowledge_card(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """旧配置可继续写 five_stage，但运行身份必须规范化为 knowledge_card。"""

    cfg_path, vault = _write_config(tmp_path, active_strategy="five_stage")
    note = _write_note(vault)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["import", str(note), "--config", str(cfg_path), "--force"])

    assert result.exit_code == 0, result.output
    assert "processed=1 skipped=0 failed=0 seen=1" in result.output
    from mindforge.cards import read_card_frontmatter

    fm = read_card_frontmatter(_cards(vault)[0])
    assert fm["status"] == "ai_draft"
    assert fm["strategy_id"] == "knowledge_card"
    assert set(fm["prompt_versions"]) == {
        "triage",
        "distill",
        "link_suggestion",
        "review_questions",
        "action_extraction",
    }
    assert fm["source_content_hash"]


def test_import_strategy_option_accepts_knowledge_card_alias_and_does_not_change_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """``--strategy`` 只改抽取策略；``--provider`` 仍只改 LLM/provider 选择。"""

    cfg_path, vault = _write_config(tmp_path, active_strategy="knowledge_card")
    note = _write_note(vault)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "import",
            str(note),
            "--config",
            str(cfg_path),
            "--strategy",
            "five_stage",
            "--provider",
            "fake",
            "--force",
        ],
    )

    assert result.exit_code == 0, result.output
    from mindforge.cards import read_card_frontmatter

    fm = read_card_frontmatter(_cards(vault)[0])
    assert fm["strategy_id"] == "knowledge_card"
    assert fm["profile"] == "fake"


def test_internal_strategy_does_not_hide_real_provider_missing_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """不能靠 deterministic strategy 绕过 provider 缺 key 诊断。

    中文学习型说明：测试应注入 LLM stub response，而不是把 internal baseline
    配成 active strategy。这样 provider failure 不会被 fake strategy 吞掉。
    """

    cfg_path, vault = _write_config(
        tmp_path,
        active_provider="anthropic",
        active_strategy="default_knowledge_card",
    )
    note = _write_note(vault)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.import_cli.load_dotenv_silently", lambda *_a, **_k: 0)

    result = runner.invoke(app, ["import", str(note), "--config", str(cfg_path)])

    assert result.exit_code != 0
    assert "internal/not production-ready" in result.output
    assert _cards(vault) == []


def test_process_uses_config_active_strategy_knowledge_card(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, vault = _write_config(tmp_path, active_strategy="knowledge_card")
    _write_note(vault)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["process", "--config", str(cfg_path)])

    assert result.exit_code == 0, result.output
    assert "processed=1" in result.output
    from mindforge.cards import read_card_frontmatter

    fm = read_card_frontmatter(_cards(vault)[0])
    assert fm["strategy_id"] == "knowledge_card"


def test_process_strategy_option_rejects_concept_extraction_internal_baseline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """concept_extraction 是 internal preview baseline，不是产品主流程。"""

    cfg_path, vault = _write_config(tmp_path, active_strategy="five_stage")
    _write_note(vault)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["process", "--config", str(cfg_path), "--strategy", "concept_extraction"],
    )

    assert result.exit_code != 0
    assert "internal/not production-ready" in result.output
    assert _cards(vault) == []


def test_invalid_and_planned_active_strategy_fail_without_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    for strategy_id in ("missing_strategy_xyz", "action_item", "default_knowledge_card"):
        case_dir = tmp_path / strategy_id
        cfg_path, vault = _write_config(case_dir, active_strategy=strategy_id)
        note = _write_note(vault)
        monkeypatch.chdir(case_dir)

        result = runner.invoke(app, ["import", str(note), "--config", str(cfg_path)])

        assert result.exit_code != 0
        assert strategy_id in result.output
        assert _cards(vault) == []


def test_watch_add_strategy_persists_canonical_knowledge_card(tmp_path: Path, monkeypatch) -> None:
    cfg_path, vault = _write_config(tmp_path, active_strategy="knowledge_card")
    note = tmp_path / "external.md"
    note.write_text("# External Strategy Watch\n\nReusable watch source lesson.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["watch", "add", str(note), "--config", str(cfg_path), "--strategy", "five_stage"],
    )

    assert result.exit_code == 0, result.output
    registry = WatchRegistry.load(vault / ".mindforge" / "watched_sources.json")
    assert registry.sources[0].strategy_id == "knowledge_card"
    from mindforge.cards import read_card_frontmatter

    fm = read_card_frontmatter(_cards(vault)[0])
    assert fm["strategy_id"] == "knowledge_card"
