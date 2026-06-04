"""Main Wiki service 测试。

v0.5: llm_rebuild_wiki 和 rebuild_main_wiki 已废弃。
Wiki 现在是 runtime View（TopicPresenter），不再通过 LLM synthesis 或
deterministic template 生成持久化 Markdown。
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import pytest
import yaml

from mindforge.config import load_mindforge_config
from mindforge.wiki_service import (
    WikiError,
    get_wiki_status,
    llm_rebuild_wiki,
    read_main_wiki,
    rebuild_main_wiki,
)


def _write_test_config(tmp_path: Path) -> Path:
    """写最小测试 config。"""
    vault = tmp_path / "test-vault"
    cards = vault / "20-Knowledge-Cards"
    cards.mkdir(parents=True)
    wiki_dir = vault / "30-Wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump({
            "version": 0.7,
            "vault": {
                "root": str(vault),
                "inbox_root": "00-Inbox",
                "cards_dir": "20-Knowledge-Cards",
                "archive_dir": "90-Archive/Skipped",
            },
            "llm": {
                "default_model": "test",
                "models": {
                    "test": {"type": "fake", "base_url": "fake://", "model": "fake"},
                },
            },
        }, sort_keys=False),
        encoding="utf-8",
    )
    return cfg_path


def _write_card(cards_dir: Path, filename: str, status: str = "human_approved", **extra) -> Path:
    """写一张测试 Knowledge Card。"""
    card = cards_dir / filename
    fm = {
        "id": filename.replace(".md", ""),
        "title": f"Test {filename.replace('.md', '')}",
        "status": status,
        "track": "test-track",
        "tags": ["test", "wiki"],
        "source_type": "plain_markdown",
        "source_path": "/tmp/test-source.md",
        "source_title": "Test Source",
        "source_content_hash": "sha256:abc",
        "value_score": 5,
        "created_at": "2026-05-10",
        "strategy_id": "knowledge_card",
        "strategy_version": "0.10.0",
        "prompt_version": "distill@v1",
        "prompt_versions": {"triage": "v1", "distill": "v1"},
        "run_id": "test-run",
        **extra,
    }
    body = "\n## AI Summary\n\nThis is an AI summary for testing.\n\n## Action Items\n\n- [ ] Test action item\n"
    text = "---\n" + "\n".join(f"{k}: {v}" for k, v in fm.items()) + "\n---\n\n" + body
    card.write_text(text, encoding="utf-8")
    return card


# ============================================================================
# rebuild_main_wiki — deprecated
# ============================================================================


def test_rebuild_main_wiki_raises_deprecation_error(tmp_path: Path) -> None:
    """rebuild_main_wiki 在 v0.5 已废弃，调用时抛出 WikiError。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    with pytest.raises(WikiError) as excinfo:
        rebuild_main_wiki(cfg)
    assert "deprecated" in str(excinfo.value).lower()


def test_rebuild_main_wiki_does_not_write_wiki_file(tmp_path: Path) -> None:
    """废弃的 rebuild_main_wiki 不会生成 Wiki 文件。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    wiki_path = cfg.vault.root / "30-Wiki" / "Main-Wiki.md"
    assert not wiki_path.exists()

    try:
        rebuild_main_wiki(cfg)
    except WikiError:
        pass

    assert not wiki_path.exists()


# ============================================================================
# llm_rebuild_wiki — deprecated
# ============================================================================


def test_llm_rebuild_wiki_raises_deprecation_error(tmp_path: Path) -> None:
    """llm_rebuild_wiki 在 v0.5 已废弃，调用时抛出 WikiError。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    with pytest.raises(WikiError) as excinfo:
        llm_rebuild_wiki(cfg)
    assert "deprecated" in str(excinfo.value).lower()


def test_llm_rebuild_wiki_does_not_write_wiki_file(tmp_path: Path) -> None:
    """废弃的 llm_rebuild_wiki 不会生成 Wiki 文件。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    wiki_path = cfg.vault.root / "30-Wiki" / "Main-Wiki.md"
    assert not wiki_path.exists()

    try:
        llm_rebuild_wiki(cfg)
    except WikiError:
        pass

    assert not wiki_path.exists()


# ============================================================================
# Wiki status
# ============================================================================


def test_wiki_status_missing(tmp_path: Path) -> None:
    """Wiki 不存在时 status 正确报告。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    status = get_wiki_status(cfg)
    assert status.exists is False


def test_wiki_status_exists(tmp_path: Path) -> None:
    """Wiki 存在时 status 正确报告。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    wiki_path = cfg.vault.root / "30-Wiki" / "Main-Wiki.md"
    wiki_path.write_text("# Main Wiki\n\nTest content.\n", encoding="utf-8")

    status = get_wiki_status(cfg)
    assert status.exists is True


# ============================================================================
# Wiki read
# ============================================================================


def test_read_wiki_missing(tmp_path: Path) -> None:
    """Wiki 不存在返回 None。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    assert read_main_wiki(cfg) is None


def test_read_wiki_content(tmp_path: Path) -> None:
    """Wiki 存在返回内容。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    wiki_path = cfg.vault.root / "30-Wiki" / "Main-Wiki.md"
    wiki_path.write_text("# Main Wiki\n\nTest content.\n", encoding="utf-8")

    content = read_main_wiki(cfg)
    assert content is not None
    assert "Test content" in content


# ============================================================================
# CLI rebuild — deprecated
# ============================================================================


def test_cli_wiki_rebuild_prints_deprecation_notice(tmp_path: Path) -> None:
    """CLI wiki rebuild 命令打印 deprecation notice，exit 0。"""
    from mindforge.wiki_cli import wiki_app

    cfg_path = _write_test_config(tmp_path)
    runner = CliRunner()
    result = runner.invoke(wiki_app, ["rebuild", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "废弃" in result.stdout or "deprecated" in result.stdout.lower()
