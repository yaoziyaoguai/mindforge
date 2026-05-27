"""Guided Onboarding — Sample Workspace Service tests.

中文学习型说明：测试 demo 卡片创建逻辑的幂等性、card 数量和 frontmatter 结构。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.services.sample_workspace import (
    DEMO_CARDS,
    build_sample_workspace,
    create_demo_cards,
    SampleWorkspaceResult,
)


def test_build_sample_workspace_creates_cards(tmp_path: Path) -> None:
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()

    result = build_sample_workspace(cards_dir)
    assert isinstance(result, SampleWorkspaceResult)
    assert result.created is True
    assert result.card_count == len(DEMO_CARDS)
    assert len(result.card_paths) == len(DEMO_CARDS)
    assert "Created" in result.message and "demo knowledge cards" in result.message

    # 验证文件确实写入了
    for path_str in result.card_paths:
        p = Path(path_str)
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "---" in content
        assert "status: human_approved" in content
        assert "approval_method: demo_sample" in content


def test_build_sample_workspace_idempotent(tmp_path: Path) -> None:
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()

    first = build_sample_workspace(cards_dir)
    assert first.created is True

    second = build_sample_workspace(cards_dir)
    assert second.created is False
    assert second.card_count == len(DEMO_CARDS)
    assert second.card_paths == ()
    assert "already exists" in second.message


def test_create_demo_cards_idempotent(tmp_path: Path) -> None:
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()

    paths = create_demo_cards(cards_dir)
    assert len(paths) == len(DEMO_CARDS)

    paths_second = create_demo_cards(cards_dir)
    assert paths_second == []


def test_demo_cards_have_required_fields() -> None:
    for card in DEMO_CARDS:
        assert "id" in card
        assert "title" in card
        assert "body" in card
        assert "tags" in card
        assert card["source_type"] == "demo_sample"
        assert card["quality_level"] in ("high", "medium", "low")


def test_demo_cards_frontmatter_writeable(tmp_path: Path) -> None:
    from mindforge.services.sample_workspace import (
        _card_frontmatter,
        _card_path,
    )

    card = DEMO_CARDS[0]
    fm = _card_frontmatter(card)
    assert "---\nid:" in fm
    assert "status: human_approved" in fm
    assert "approval_method: demo_sample" in fm
    assert "schema_version:" in fm

    path = _card_path(tmp_path, card["id"])
    assert path.parent.name == "demo-workspace"
