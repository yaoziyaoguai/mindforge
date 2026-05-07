"""Main Wiki service 测试。验证 deterministic rebuild、provenance、Trash 过滤等。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mindforge.config import load_mindforge_config
from mindforge.trash_service import move_card_to_trash, restore_trashed_card
from mindforge.wiki_service import (
    get_wiki_status,
    read_main_wiki,
    rebuild_main_wiki,
)


def _write_test_config(tmp_path: Path) -> Path:
    """写最小测试 config。"""
    vault = tmp_path / "test-vault"
    cards = vault / "20-Knowledge-Cards"
    cards.mkdir(parents=True)
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
# Wiki rebuild
# ============================================================================


def test_rebuild_empty_cards(tmp_path: Path) -> None:
    """空 approved cards → 生成有效空 Wiki。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    result = rebuild_main_wiki(cfg)
    assert result.included_cards == 0
    assert Path(result.wiki_path).exists()


def test_rebuild_one_card(tmp_path: Path) -> None:
    """一张 approved card → Wiki 包含对应 section。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    _write_card(cards, "card-one.md")

    result = rebuild_main_wiki(cfg)
    assert result.included_cards == 1

    wiki_text = Path(result.wiki_path).read_text(encoding="utf-8")
    assert "Test card-one" in wiki_text
    assert "WIKI_SECTION_START" in wiki_text
    assert "WIKI_SECTION_END" in wiki_text
    assert "ai summary" in wiki_text.lower()


def test_rebuild_excludes_ai_draft(tmp_path: Path) -> None:
    """ai_draft 不进入 Wiki。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    _write_card(cards, "approved.md", status="human_approved")
    _write_card(cards, "draft.md", status="ai_draft")

    result = rebuild_main_wiki(cfg)
    assert result.included_cards == 1

    wiki_text = Path(result.wiki_path).read_text(encoding="utf-8")
    assert "Test approved" in wiki_text
    assert "Test draft" not in wiki_text


def test_rebuild_excludes_trashed_approved_card(tmp_path: Path) -> None:
    """trashed approved card 不进入 Wiki。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    _write_card(cards, "keep.md", status="human_approved")
    trashed = _write_card(cards, "trash-me.md", status="human_approved")
    move_card_to_trash(cfg, trashed)

    result = rebuild_main_wiki(cfg)
    assert result.included_cards == 1

    wiki_text = Path(result.wiki_path).read_text(encoding="utf-8")
    assert "Test keep" in wiki_text
    assert "Test trash-me" not in wiki_text


def test_rebuild_includes_restored_card(tmp_path: Path) -> None:
    """Restore 后 rebuild → card 回到 Wiki。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_card(cards, "restored.md", status="human_approved")
    trash_result = move_card_to_trash(cfg, card)
    restore_trashed_card(cfg, trash_result.trash_rel_path)

    result = rebuild_main_wiki(cfg)
    assert result.included_cards == 1

    wiki_text = Path(result.wiki_path).read_text(encoding="utf-8")
    assert "Test restored" in wiki_text


def test_rebuild_provenance_present(tmp_path: Path) -> None:
    """Wiki section 包含 provenance。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    _write_card(cards, "provenance-test.md", source_title="My Original Source")

    result = rebuild_main_wiki(cfg)
    wiki_text = Path(result.wiki_path).read_text(encoding="utf-8")
    assert "Source card" in wiki_text or "Card path" in wiki_text
    assert "Original source" in wiki_text
    assert "My Original Source" in wiki_text


def test_rebuild_deterministic(tmp_path: Path) -> None:
    """同一输入 produce 稳定输出（除时间戳外）。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path
    _write_card(cards, "a.md")

    r1 = rebuild_main_wiki(cfg)
    r2 = rebuild_main_wiki(cfg)

    assert r1.included_cards == r2.included_cards

    t1 = Path(r1.wiki_path).read_text(encoding="utf-8")
    t2 = Path(r2.wiki_path).read_text(encoding="utf-8")
    # 除时间戳外，内容应一致
    t1_no_ts = t1.replace(r1.last_rebuilt_at, "TS")
    t2_no_ts = t2.replace(r2.last_rebuilt_at, "TS")
    assert t1_no_ts == t2_no_ts


def test_rebuild_no_secret_leak(tmp_path: Path) -> None:
    """Wiki 不包含 secret 模式。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path
    _write_card(cards, "safe.md")

    result = rebuild_main_wiki(cfg)
    wiki_text = Path(result.wiki_path).read_text(encoding="utf-8")
    assert "sk-" not in wiki_text


def test_atomic_write_preserves_old_on_failure(tmp_path: Path, monkeypatch) -> None:
    """写入失败时旧 Wiki 保持不变。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path
    _write_card(cards, "first.md")

    # 第一次 rebuild 成功
    result = rebuild_main_wiki(cfg)
    old_text = Path(result.wiki_path).read_text(encoding="utf-8")

    # 模拟写入失败：让 os.replace 抛异常
    import os as _os
    original_replace = _os.replace

    def _fake_replace(src, dst):
        if "Main-Wiki" in str(dst):
            raise OSError("simulated write failure")
        return original_replace(src, dst)

    monkeypatch.setattr(_os, "replace", _fake_replace)

    try:
        rebuild_main_wiki(cfg)
    except OSError:
        pass

    # 旧 Wiki 应保持不变
    current = Path(result.wiki_path).read_text(encoding="utf-8")
    assert current == old_text


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
    cards = cfg.vault.cards_path
    _write_card(cards, "s1.md")

    rebuild_main_wiki(cfg)
    status = get_wiki_status(cfg)
    assert status.exists is True
    assert status.wiki_card_count == 1


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
    cards = cfg.vault.cards_path
    _write_card(cards, "read-test.md")

    rebuild_main_wiki(cfg)
    content = read_main_wiki(cfg)
    assert content is not None
    assert "Test read-test" in content
