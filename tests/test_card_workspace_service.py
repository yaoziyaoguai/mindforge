"""bulk_update_cards + link_cards service tests.

需要 temp vault + cards dir + 有效 mindforge.yaml config。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mindforge.card_workspace_service import bulk_update_cards, link_cards
from mindforge.config import load_mindforge_config


def _write_config_and_vault(tmp_path: Path) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    cards_dir = vault / "20-Knowledge-Cards"
    cards_dir.mkdir(parents=True)
    inbox = vault / "00-Inbox" / "ManualNotes"
    inbox.mkdir(parents=True)

    cfg_path = tmp_path / "mindforge.yaml"
    raw = {
        "version": 9,
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
        "triage": {
            "value_score_threshold": 5,
            "default_track": "unrouted",
        },
        "llm": {
            "active": "fake",
            "providers": {
                "fake": {
                    "type": "fake",
                    "purpose": "offline_demo_ci_deterministic_tests",
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
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return cfg_path, vault


def _write_card(vault: Path, filename: str, id: str, title: str, tags: list[str] | None = None, track: str = "unrouted") -> str:
    """写入一张带 frontmatter 的卡片，返回卡片相对路径。"""
    cards_dir = vault / "20-Knowledge-Cards"
    fm: dict = {"id": id, "title": title, "status": "human_approved", "track": track}
    if tags:
        fm["tags"] = tags
    content = f"---\n{yaml.dump(fm, allow_unicode=True, default_flow_style=False)}---\n\n# {title}\n\nCard body content.\n"
    path = cards_dir / filename
    path.write_text(content, encoding="utf-8")
    rel = path.relative_to(vault)
    return str(rel)


class TestBulkUpdateCards:
    def test_bulk_update_tags(self, tmp_path: Path) -> None:
        cfg_path, vault = _write_config_and_vault(tmp_path)
        cfg = load_mindforge_config(str(cfg_path))
        _write_card(vault, "card-a.md", "card-a", "Card A", tags=["old-tag"], track="unrouted")
        _write_card(vault, "card-b.md", "card-b", "Card B", tags=["old-tag"], track="unrouted")

        updated, errors = bulk_update_cards(cfg, ["card-a", "card-b"], set_tags=["new-tag-1", "new-tag-2"])
        assert updated == 2
        assert errors == []

        # Verify frontmatter was updated
        for card_file in ["card-a.md", "card-b.md"]:
            raw = (vault / "20-Knowledge-Cards" / card_file).read_text(encoding="utf-8")
            assert "new-tag-1" in raw
            assert "new-tag-2" in raw
            assert "old-tag" not in raw
            assert "Card body content." in raw  # body preserved

    def test_bulk_update_track(self, tmp_path: Path) -> None:
        cfg_path, vault = _write_config_and_vault(tmp_path)
        cfg = load_mindforge_config(str(cfg_path))
        _write_card(vault, "card-c.md", "card-c", "Card C", track="unrouted")

        updated, errors = bulk_update_cards(cfg, ["card-c"], set_track="engineering")
        assert updated == 1
        assert errors == []
        raw = (vault / "20-Knowledge-Cards" / "card-c.md").read_text(encoding="utf-8")
        assert "track: engineering" in raw

    def test_bulk_update_unknown_card_reports_error(self, tmp_path: Path) -> None:
        cfg_path, vault = _write_config_and_vault(tmp_path)
        cfg = load_mindforge_config(str(cfg_path))
        _write_card(vault, "card-d.md", "card-d", "Card D")

        updated, errors = bulk_update_cards(cfg, ["card-d", "card-unknown"], set_tags=["tag"])
        assert updated == 1
        assert len(errors) == 1
        assert "card not found" in errors[0]

    def test_bulk_update_no_fields_returns_zero(self, tmp_path: Path) -> None:
        cfg_path, vault = _write_config_and_vault(tmp_path)
        cfg = load_mindforge_config(str(cfg_path))
        _write_card(vault, "card-e.md", "card-e", "Card E")

        updated, errors = bulk_update_cards(cfg, ["card-e"])
        assert updated == 0
        assert "no fields to update" in errors[0]


class TestLinkCards:
    def test_link_cards_creates_frontmatter_links(self, tmp_path: Path) -> None:
        cfg_path, vault = _write_config_and_vault(tmp_path)
        cfg = load_mindforge_config(str(cfg_path))
        _write_card(vault, "card-f.md", "card-f", "Card F")
        _write_card(vault, "card-g.md", "card-g", "Card G")

        ok, msg = link_cards(cfg, "card-f", "card-g", reason="see_also")
        assert ok is True
        assert msg == "ok"

        raw_f = (vault / "20-Knowledge-Cards" / "card-f.md").read_text(encoding="utf-8")
        raw_g = (vault / "20-Knowledge-Cards" / "card-g.md").read_text(encoding="utf-8")
        assert "manual_links:" in raw_f
        assert "target: card-g" in raw_f
        assert "reason: see_also" in raw_f
        assert "manual_links:" in raw_g
        assert "target: card-f" in raw_g

    def test_link_cards_dedup_prevents_duplicate(self, tmp_path: Path) -> None:
        cfg_path, vault = _write_config_and_vault(tmp_path)
        cfg = load_mindforge_config(str(cfg_path))
        _write_card(vault, "card-h.md", "card-h", "Card H")
        _write_card(vault, "card-i.md", "card-i", "Card I")

        ok, _ = link_cards(cfg, "card-h", "card-i")
        assert ok is True
        ok2, _ = link_cards(cfg, "card-h", "card-i")
        assert ok2 is True

        raw = (vault / "20-Knowledge-Cards" / "card-h.md").read_text(encoding="utf-8")
        assert raw.count("target: card-i") == 1  # not duplicated

    def test_link_cards_self_link_rejected(self, tmp_path: Path) -> None:
        cfg_path, vault = _write_config_and_vault(tmp_path)
        cfg = load_mindforge_config(str(cfg_path))
        _write_card(vault, "card-j.md", "card-j", "Card J")

        ok, msg = link_cards(cfg, "card-j", "card-j")
        assert ok is False
        assert "cannot link a card to itself" in msg

    def test_link_cards_unknown_card_rejected(self, tmp_path: Path) -> None:
        cfg_path, vault = _write_config_and_vault(tmp_path)
        cfg = load_mindforge_config(str(cfg_path))
        _write_card(vault, "card-k.md", "card-k", "Card K")

        ok, msg = link_cards(cfg, "card-k", "nonexistent")
        assert ok is False
        assert "card not found" in msg
