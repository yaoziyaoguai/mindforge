"""Knowledge Card Trash service 测试。

覆盖 move_to_trash / list_trashed / restore_trashed 及其安全边界。
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from mindforge.config import load_mindforge_config
from mindforge.trash_service import (
    TrashError,
    move_card_to_trash,
    list_trashed_cards,
    read_trashed_card,
    restore_trashed_card,
)


def _write_test_config(tmp_path: Path) -> Path:
    """写一个最小测试 config，返回 config_path。"""
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


def _write_draft(cards_dir: Path, filename: str, **extra_fm) -> Path:
    """写一张 ai_draft 测试卡片。"""
    card = cards_dir / filename
    fm = {
        "id": filename.replace(".md", ""),
        "title": f"Test {filename}",
        "status": "ai_draft",
        "track": "test-track",
        "tags": ["test", "draft"],
        "source_type": "plain_markdown",
        "source_path": "/tmp/test-source.md",
        "source_content_hash": "sha256:abc",
        "value_score": 5,
        "created_at": "2026-05-07",
        "strategy_id": "knowledge_card",
        "strategy_version": "0.10.0",
        "prompt_version": "distill@v1",
        "run_id": "test-run",
        **extra_fm,
    }
    text = "---\n" + "\n".join(f"{k}: {v}" for k, v in fm.items()) + "\n---\n\nTest body content.\n"
    card.write_text(text, encoding="utf-8")
    return card


# ============================================================================
# Move to Trash
# ============================================================================


def test_move_ai_draft_to_trash(tmp_path: Path) -> None:
    """ai_draft move to trash 只移动卡片，不删除 source。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_draft(cards, "test-draft.md")
    source = tmp_path / "test-source.md"
    source.write_text("# Source content\n")

    result = move_card_to_trash(cfg, card)
    assert result.previous_status == "ai_draft"
    assert result.original_path  # 有原路径记录
    assert not card.exists()  # 原卡片已移走
    assert source.exists()  # source 文件仍在

    # 验证 trash 目录中有文件
    trash_dir = cfg.vault.root / "90-Archive" / "Trash" / "Knowledge-Cards"
    trashed = list(trash_dir.rglob("*.md"))
    assert len(trashed) == 1
    text = trashed[0].read_text(encoding="utf-8")
    assert "trashed_at:" in text
    assert "previous_status: ai_draft" in text
    assert "original_path:" in text


def test_move_approved_card_to_trash(tmp_path: Path) -> None:
    """approved card move to trash 只移动卡片，source 不动。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_draft(cards, "approved-card.md", status="human_approved")
    source = tmp_path / "test-source.md"
    source.write_text("# Source\n")

    result = move_card_to_trash(cfg, card)
    assert result.previous_status == "human_approved"
    assert source.exists()


def test_move_to_trash_preserves_metadata(tmp_path: Path) -> None:
    """move 后 metadata 正确记录。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_draft(cards, "meta-card.md")
    result = move_card_to_trash(cfg, card)

    assert result.trashed_at  # 有时间戳
    assert "20-Knowledge-Cards/meta-card.md" in result.original_path


def test_move_to_trash_rejects_path_outside_cards(tmp_path: Path) -> None:
    """拒绝 cards_dir 外的路径。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    outside = tmp_path / "outside.md"
    outside.write_text("---\ntitle: x\n---\nbody\n")

    with pytest.raises(TrashError, match="不在当前 vault cards_dir"):
        move_card_to_trash(cfg, outside)


def test_move_to_trash_rejects_nonexistent(tmp_path: Path) -> None:
    """拒绝不存在的文件。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    ghost = cfg.vault.cards_path / "ghost.md"
    with pytest.raises(TrashError, match="不存在"):
        move_card_to_trash(cfg, ghost)


def test_move_to_trash_rejects_double_trash(tmp_path: Path) -> None:
    """拒绝将已在 Trash 的文件再次 move。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_draft(cards, "once.md")
    move_card_to_trash(cfg, card)

    trash_dir = cfg.vault.root / "90-Archive" / "Trash" / "Knowledge-Cards"
    trashed = list(trash_dir.rglob("*.md"))[0]
    with pytest.raises(TrashError, match="已在 Trash"):
        move_card_to_trash(cfg, trashed)


def test_move_to_trash_with_reason(tmp_path: Path) -> None:
    """带 reason 的 move。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_draft(cards, "reason-card.md")
    move_card_to_trash(cfg, card, reason="test cleanup")

    trash_dir = cfg.vault.root / "90-Archive" / "Trash" / "Knowledge-Cards"
    trashed = list(trash_dir.rglob("*.md"))[0]
    text = trashed.read_text(encoding="utf-8")
    assert 'trash_reason: "test cleanup"' in text


def test_filename_conflict_in_trash(tmp_path: Path) -> None:
    """同名文件移入 Trash 时生成唯一文件名。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    # 先在 trash 里放同名文件
    trash_dir = cfg.vault.root / "90-Archive" / "Trash" / "Knowledge-Cards"
    trash_dir.mkdir(parents=True)
    (trash_dir / "same-name.md").write_text("---\ntitle: old\n---\nold\n")

    card = _write_draft(cards, "same-name.md")
    result = move_card_to_trash(cfg, card)

    # 应有冲突安全文件名
    assert result.trash_rel_path != "90-Archive/Trash/Knowledge-Cards/same-name.md"
    assert "--trashed-" in result.trash_rel_path


# ============================================================================
# List Trash
# ============================================================================


def test_list_trashed_cards(tmp_path: Path) -> None:
    """list_trashed_cards 返回所有 trashed cards。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    _write_draft(cards, "card-a.md")
    _write_draft(cards, "card-b.md", status="human_approved")

    move_card_to_trash(cfg, cards / "card-a.md")
    move_card_to_trash(cfg, cards / "card-b.md")

    trashed = list_trashed_cards(cfg)
    assert len(trashed) == 2
    statuses = {t.previous_status for t in trashed}
    assert statuses == {"ai_draft", "human_approved"}


def test_list_trashed_empty(tmp_path: Path) -> None:
    """空 Trash 返回空列表。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    assert list_trashed_cards(cfg) == []


# ============================================================================
# Read Trash
# ============================================================================


def test_read_trashed_card(tmp_path: Path) -> None:
    """read_trashed_card 返回 frontmatter 和 body。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_draft(cards, "read-me.md", title="Read Me Card")
    result = move_card_to_trash(cfg, card)

    fm, body = read_trashed_card(cfg, result.trash_rel_path)
    assert fm["title"] == "Read Me Card"
    assert fm["previous_status"] == "ai_draft"
    assert "Test body content" in body


def test_read_trashed_rejects_path_traversal(tmp_path: Path) -> None:
    """read_trashed_card 拒绝 path traversal。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    with pytest.raises(TrashError, match="不在 Trash 目录"):
        read_trashed_card(cfg, "../../etc/passwd")


# ============================================================================
# Restore
# ============================================================================


def test_restore_ai_draft(tmp_path: Path) -> None:
    """Restore ai_draft 回到 cards_dir。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_draft(cards, "restore-me.md")
    result = move_card_to_trash(cfg, card)

    restored = restore_trashed_card(cfg, result.trash_rel_path)
    assert restored.previous_status == "ai_draft"

    # 文件回到 cards_dir
    restored_path = cfg.vault.root / restored.restored_path
    assert restored_path.exists()

    # 状态恢复为 ai_draft
    from mindforge.cards import read_card_frontmatter
    fm = read_card_frontmatter(restored_path)
    assert fm["status"] == "ai_draft"

    # trash metadata 已清理
    text = restored_path.read_text(encoding="utf-8")
    assert "trashed_at:" not in text
    assert "previous_status:" not in text


def test_restore_approved_card(tmp_path: Path) -> None:
    """Restore approved card 恢复 human_approved 状态。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_draft(cards, "approved-restore.md", status="human_approved")
    result = move_card_to_trash(cfg, card)

    restored = restore_trashed_card(cfg, result.trash_rel_path)
    assert restored.previous_status == "human_approved"

    from mindforge.cards import read_card_frontmatter
    fm = read_card_frontmatter(cfg.vault.root / restored.restored_path)
    assert fm["status"] == "human_approved"


def test_restore_conflict_safe(tmp_path: Path) -> None:
    """原路径已占用时生成冲突安全文件名。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card = _write_draft(cards, "conflict.md")
    result = move_card_to_trash(cfg, card)

    # 在原位置放一个同名文件
    (cards / "conflict.md").write_text("---\ntitle: blocker\n---\nblocker\n")

    restored = restore_trashed_card(cfg, result.trash_rel_path)
    assert restored.conflict_resolved
    assert "--restored-" in restored.restored_path


def test_restore_rejects_path_traversal(tmp_path: Path) -> None:
    """restore 拒绝 path traversal。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    with pytest.raises(TrashError, match="不在 Trash 目录"):
        restore_trashed_card(cfg, "../../etc/passwd")


def test_source_file_always_preserved(tmp_path: Path) -> None:
    """全程不删除 source 文件。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    source = tmp_path / "my-source.md"
    source.write_text("# Real source\nThis must stay.\n")

    card = _write_draft(cards, "with-source.md", source_path=str(source))
    result = move_card_to_trash(cfg, card)
    assert source.exists()
    assert source.read_text(encoding="utf-8").startswith("# Real source")

    restore_trashed_card(cfg, result.trash_rel_path)
    assert source.exists()
    assert source.read_text(encoding="utf-8").startswith("# Real source")


def test_unrelated_cards_unaffected(tmp_path: Path) -> None:
    """move to trash 不影响其他卡片。"""
    cfg_path = _write_test_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    cards = cfg.vault.cards_path

    card_a = _write_draft(cards, "a.md")
    card_b = _write_draft(cards, "b.md")

    move_card_to_trash(cfg, card_a)
    assert not card_a.exists()
    assert card_b.exists()
    assert card_b.read_text(encoding="utf-8").startswith("---")
