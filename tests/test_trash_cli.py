"""Knowledge Card Trash CLI 测试。

覆盖 trash list/show/restore/move 及其安全边界。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()


def _write_test_config(tmp_path: Path) -> tuple[Path, Path]:
    """写最小测试 config + vault，返回 (config_path, cards_dir)。"""
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
    return cfg_path, cards


def _write_card(cards_dir: Path, filename: str, status: str = "ai_draft", **extra) -> Path:
    """写一张测试 Knowledge Card。"""
    card = cards_dir / filename
    fm = {
        "id": filename.replace(".md", ""),
        "title": f"Test {filename}",
        "status": status,
        "track": "test-track",
        "tags": ["test"],
        "source_type": "plain_markdown",
        "source_path": "/tmp/test-source.md",
        "source_content_hash": "sha256:abc",
        "value_score": 5,
        "created_at": "2026-05-07",
        "strategy_id": "knowledge_card",
        "strategy_version": "0.10.0",
        "prompt_version": "distill@v1",
        "run_id": "test-run",
        **extra,
    }
    text = "---\n" + "\n".join(f"{k}: {v}" for k, v in fm.items()) + "\n---\n\nTest body content.\n"
    card.write_text(text, encoding="utf-8")
    return card


def _move_and_get_trash_path(app, cfg_path: Path, card: Path) -> str:
    """move card to trash 并从输出提取 trash path。"""
    move_result = runner.invoke(app, ["trash", "move", str(card), "--confirm", "--config", str(cfg_path)])
    assert move_result.exit_code == 0, f"move failed: {move_result.output}"
    # 输出格式: "Trash path: 90-Archive/Trash/Knowledge-Cards/xxx.md"
    for line in move_result.output.split("\n"):
        if "Trash path:" in line:
            return line.split("Trash path:")[-1].strip()
    # fallback: 从 list 中找
    list_result = runner.invoke(app, ["trash", "list", "--config", str(cfg_path)])
    for line in list_result.output.split("\n"):
        if "/Trash/Knowledge-Cards/" in line and ".md" in line:
            # 从表格行中提取路径（第一列）
            parts = line.strip().split()
            for p in parts:
                if "90-Archive/Trash" in p and p.endswith(".md"):
                    return p
    raise AssertionError(f"Could not find trash path in output: {move_result.output}")


# ============================================================================
# trash list
# ============================================================================


def test_trash_list_empty(tmp_path: Path) -> None:
    """空 Trash 友好输出。"""
    cfg_path, _cards = _write_test_config(tmp_path)
    result = runner.invoke(app, ["trash", "list", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "空" in result.output or "empty" in result.output.lower()


def test_trash_list_shows_cards(tmp_path: Path) -> None:
    """trash list 显示已 trashed 的卡片。"""
    cfg_path, cards = _write_test_config(tmp_path)

    # 先通过 CLI move a card to trash
    card = _write_card(cards, "list-me.md")
    runner.invoke(app, ["trash", "move", str(card), "--confirm", "--config", str(cfg_path)])

    result = runner.invoke(app, ["trash", "list", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "list-me" in result.output


def test_trash_list_does_not_expose_raw_key(tmp_path: Path) -> None:
    """trash list 输出不含 raw API key。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "safe.md")
    runner.invoke(app, ["trash", "move", str(card), "--confirm", "--config", str(cfg_path)])

    result = runner.invoke(app, ["trash", "list", "--config", str(cfg_path)])
    assert "sk-" not in result.output


# ============================================================================
# trash show
# ============================================================================


def test_trash_show_displays_metadata(tmp_path: Path) -> None:
    """trash show 显示 metadata 和 body preview。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "show-me.md", title="Show Me Card")
    trash_path = _move_and_get_trash_path(app, cfg_path, card)

    show_result = runner.invoke(app, ["trash", "show", trash_path, "--config", str(cfg_path)])
    assert show_result.exit_code == 0
    assert "Show Me Card" in show_result.output
    assert "Body preview" in show_result.output


def test_trash_show_nonexistent(tmp_path: Path) -> None:
    """trash show 不存在的路径报错。"""
    cfg_path, _cards = _write_test_config(tmp_path)
    result = runner.invoke(app, ["trash", "show", "nonexistent/path.md", "--config", str(cfg_path)])
    assert result.exit_code != 0


# ============================================================================
# trash restore
# ============================================================================


def test_trash_restore_requires_confirm(tmp_path: Path) -> None:
    """restore 没有 --confirm 时拒绝。"""
    cfg_path, _cards = _write_test_config(tmp_path)
    result = runner.invoke(app, ["trash", "restore", "some/path.md", "--config", str(cfg_path)])
    assert result.exit_code != 0
    assert "confirm" in result.output.lower()


def test_trash_restore_draft(tmp_path: Path) -> None:
    """restore ai_draft 后卡片回到 cards_dir。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "restore-draft.md")

    trash_path = _move_and_get_trash_path(app, cfg_path, card)
    assert not card.exists()

    result = runner.invoke(app, ["trash", "restore", trash_path, "--confirm", "--config", str(cfg_path)])
    assert result.exit_code == 0, f"restore failed: {result.output}"
    assert "restored" in result.output.lower()

    # 验证卡片回到 cards_dir
    restored = list(cards.rglob("restore-draft*.md"))
    assert len(restored) == 1

    # 验证 status 恢复为 ai_draft
    text = restored[0].read_text(encoding="utf-8")
    assert "status: ai_draft" in text
    assert "trashed_at:" not in text  # trash metadata 已清理


def test_trash_restore_approved(tmp_path: Path) -> None:
    """restore approved card 恢复 human_approved status。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "restore-approved.md", status="human_approved")

    trash_path = _move_and_get_trash_path(app, cfg_path, card)

    result = runner.invoke(app, ["trash", "restore", trash_path, "--confirm", "--config", str(cfg_path)])
    assert result.exit_code == 0, f"restore failed: {result.output}"

    restored = list(cards.rglob("restore-approved*.md"))
    assert len(restored) == 1
    text = restored[0].read_text(encoding="utf-8")
    assert "status: human_approved" in text


def test_trash_restore_preserves_source(tmp_path: Path) -> None:
    """restore 不删除 source 文件。"""
    cfg_path, cards = _write_test_config(tmp_path)
    source = tmp_path / "my-source.md"
    source.write_text("# Real source\n")

    card = _write_card(cards, "with-source.md", source_path=str(source))
    trash_path = _move_and_get_trash_path(app, cfg_path, card)

    runner.invoke(app, ["trash", "restore", trash_path, "--confirm", "--config", str(cfg_path)])
    assert source.exists()
    assert source.read_text(encoding="utf-8").startswith("# Real source")


# ============================================================================
# trash move
# ============================================================================


def test_trash_move_requires_confirm(tmp_path: Path) -> None:
    """move 没有 --confirm 时拒绝。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "needs-confirm.md")
    result = runner.invoke(app, ["trash", "move", str(card), "--config", str(cfg_path)])
    assert result.exit_code != 0
    assert "confirm" in result.output.lower()


def test_trash_move_draft(tmp_path: Path) -> None:
    """move draft card to trash --confirm 成功。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "move-me.md")

    result = runner.invoke(app, ["trash", "move", str(card), "--confirm", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "moved" in result.output.lower() or "Moved" in result.output
    assert not card.exists()  # 原卡片已移走


def test_trash_move_approved(tmp_path: Path) -> None:
    """move approved card to trash --confirm 成功。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "approved-move.md", status="human_approved")

    result = runner.invoke(app, ["trash", "move", str(card), "--confirm", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert not card.exists()


def test_trash_move_preserves_source(tmp_path: Path) -> None:
    """move to trash 不删除 source 文件。"""
    cfg_path, cards = _write_test_config(tmp_path)
    source = tmp_path / "my-source.md"
    source.write_text("# Real source\n")

    card = _write_card(cards, "with-source.md", source_path=str(source))
    result = runner.invoke(app, ["trash", "move", str(card), "--confirm", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert source.exists()


def test_trash_move_unrelated_unaffected(tmp_path: Path) -> None:
    """move 不影响其他卡片。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card_a = _write_card(cards, "a.md")
    card_b = _write_card(cards, "b.md")

    runner.invoke(app, ["trash", "move", str(card_a), "--confirm", "--config", str(cfg_path)])
    assert not card_a.exists()
    assert card_b.exists()


def test_trash_move_rejects_outside_cards(tmp_path: Path) -> None:
    """拒绝 cards_dir 外的路径。"""
    cfg_path, _cards = _write_test_config(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("---\ntitle: x\n---\nbody\n")

    result = runner.invoke(app, ["trash", "move", str(outside), "--confirm", "--config", str(cfg_path)])
    assert result.exit_code != 0


def test_trash_move_visible_after_list(tmp_path: Path) -> None:
    """move to trash 后 card 出现在 trash list 中。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "visible.md")

    runner.invoke(app, ["trash", "move", str(card), "--confirm", "--config", str(cfg_path)])
    result = runner.invoke(app, ["trash", "list", "--config", str(cfg_path)])
    assert "visible" in result.output


def test_trash_move_gone_after_restore(tmp_path: Path) -> None:
    """restore 后 card 不在 trash list 中。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "gone-card.md")

    trash_path = _move_and_get_trash_path(app, cfg_path, card)
    assert trash_path is not None

    runner.invoke(app, ["trash", "restore", trash_path, "--confirm", "--config", str(cfg_path)])

    after = runner.invoke(app, ["trash", "list", "--config", str(cfg_path)])
    # trash list 应为空（使用更具体的检查）
    assert "90-Archive/Trash" not in after.output or "空" in after.output


# ============================================================================
# Safety
# ============================================================================


def test_trash_cli_output_no_raw_key(tmp_path: Path) -> None:
    """所有 trash CLI 输出不含 raw API key。"""
    cfg_path, cards = _write_test_config(tmp_path)
    card = _write_card(cards, "no-key.md")

    results = [
        runner.invoke(app, ["trash", "list", "--config", str(cfg_path)]),
        runner.invoke(app, ["trash", "move", str(card), "--confirm", "--config", str(cfg_path)]),
        runner.invoke(app, ["trash", "list", "--config", str(cfg_path)]),
    ]
    for r in results:
        assert "sk-" not in r.output
        assert "secret" not in r.output.lower()


def test_trash_cli_nonexistent_config(tmp_path: Path) -> None:
    """不存在 config 时清晰报错。"""
    result = runner.invoke(app, ["trash", "list", "--config", str(tmp_path / "nonexistent.yaml")])
    assert result.exit_code != 0
