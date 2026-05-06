"""Strategy execution unification regression tests.

中文学习型说明：本文件覆盖本轮 milestone 的运行时语义，而不是只测
``strategies list/show`` 的只读 seam。核心边界：

- strategy selection 与 provider selection 正交；
- active strategy / ``--strategy`` 必须进入 import/process/watch 主路径；
- 非 five_stage strategy 通过 normalized card envelope 统一落盘；
- planned/custom strategy 不能半通执行或静默 fallback。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cards import read_card_frontmatter
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
        "This note captures a reusable operating lesson about separating provider "
        "selection from extraction strategy selection. The same source document "
        "should produce an ai_draft through deterministic strategies without "
        "constructing a real LLM provider.\n",
        encoding="utf-8",
    )
    return note


def _cards(vault: Path) -> list[Path]:
    return sorted((vault / "20-Knowledge-Cards").rglob("*.md"))


def test_config_defaults_active_strategy_to_five_stage(tmp_path: Path) -> None:
    cfg_path, _vault = _write_config(tmp_path)

    cfg = load_mindforge_config(cfg_path)

    assert cfg.strategy.active == "five_stage"


def test_import_uses_config_active_strategy_default_knowledge_card(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """active strategy 是运行时选择，不需要用户每次传 ``--strategy``。"""

    cfg_path, vault = _write_config(tmp_path, active_strategy="default_knowledge_card")
    note = _write_note(vault)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["import", str(note), "--config", str(cfg_path)])

    assert result.exit_code == 0, result.output
    assert "processed=1 skipped=0 failed=0 seen=1" in result.output
    card = _cards(vault)[0]
    fm = read_card_frontmatter(card)
    assert fm["status"] == "ai_draft"
    assert fm["strategy_id"] == "default_knowledge_card"
    assert fm["prompt_versions"] == {}
    assert fm["stage_models"] == {}
    assert fm["source_content_hash"]


def test_import_strategy_option_overrides_config_and_does_not_change_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """``--strategy`` 只改抽取策略；``--provider`` 仍只改 LLM/provider 选择。"""

    cfg_path, vault = _write_config(tmp_path, active_strategy="five_stage")
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
            "default_knowledge_card",
            "--provider",
            "fake",
        ],
    )

    assert result.exit_code == 0, result.output
    fm = read_card_frontmatter(_cards(vault)[0])
    assert fm["strategy_id"] == "default_knowledge_card"
    assert fm["profile"] == "fake"


def test_deterministic_strategy_does_not_require_real_provider_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """deterministic strategy 不构造真实 provider，缺 key 也不应挡住离线执行。"""

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

    assert result.exit_code == 0, result.output
    assert "processed=1 skipped=0 failed=0 seen=1" in result.output
    fm = read_card_frontmatter(_cards(vault)[0])
    assert fm["strategy_id"] == "default_knowledge_card"
    assert fm["profile"] == "anthropic"


def test_process_uses_config_active_strategy_and_writes_non_five_stage_card(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path, vault = _write_config(tmp_path, active_strategy="default_knowledge_card")
    _write_note(vault)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["process", "--config", str(cfg_path)])

    assert result.exit_code == 0, result.output
    assert "processed=1" in result.output
    fm = read_card_frontmatter(_cards(vault)[0])
    assert fm["strategy_id"] == "default_knowledge_card"
    assert fm["prompt_versions"] == {}


def test_process_strategy_option_renders_concept_extraction_card(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """preview 但可执行的 built-in strategy 也必须走同一写卡边界。"""

    cfg_path, vault = _write_config(tmp_path, active_strategy="five_stage")
    _write_note(vault)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["process", "--config", str(cfg_path), "--strategy", "concept_extraction"],
    )

    assert result.exit_code == 0, result.output
    fm = read_card_frontmatter(_cards(vault)[0])
    assert fm["status"] == "ai_draft"
    assert fm["strategy_id"] == "concept_extraction"
    assert fm["prompt_versions"] == {}
    assert fm["stage_models"] == {}


def test_invalid_and_planned_active_strategy_fail_without_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    for strategy_id in ("missing_strategy_xyz", "action_item"):
        case_dir = tmp_path / strategy_id
        cfg_path, vault = _write_config(case_dir, active_strategy=strategy_id)
        note = _write_note(vault)
        monkeypatch.chdir(case_dir)

        result = runner.invoke(app, ["import", str(note), "--config", str(cfg_path)])

        assert result.exit_code != 0
        assert strategy_id in result.output
        assert _cards(vault) == []


def test_watch_add_strategy_is_persisted_in_registry(tmp_path: Path, monkeypatch) -> None:
    cfg_path, vault = _write_config(tmp_path, active_strategy="five_stage")
    note = tmp_path / "external.md"
    note.write_text("# External Strategy Watch\n\nReusable watch source lesson.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["watch", "add", str(note), "--config", str(cfg_path), "--strategy", "default_knowledge_card"],
    )

    assert result.exit_code == 0, result.output
    registry = WatchRegistry.load(vault / ".mindforge" / "watched_sources.json")
    assert registry.sources[0].strategy_id == "default_knowledge_card"
    fm = read_card_frontmatter(_cards(vault)[0])
    assert fm["strategy_id"] == "default_knowledge_card"
