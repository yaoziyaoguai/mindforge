"""Knowledge Model v2 测试。

验证 frontmatter 解析、边界情况和 legacy fallback。
"""

from pathlib import Path

import pytest
import yaml

from mindforge.cards import _load_summary, _CardError


def _write_card(card_path: Path, frontmatter: dict, body: str = "Body text\n") -> Path:
    """写入一张测试卡片。"""
    yaml_lines = yaml.safe_dump(frontmatter, sort_keys=False).strip()
    text = f"---\n{yaml_lines}\n---\n\n{body}"
    card_path.write_text(text, encoding="utf-8")
    return card_path


# ============================================================================
# knowledge_model v2 parsing
# ============================================================================


def test_load_summary_parses_knowledge_model_v2(tmp_path: Path):
    """knowledge_type, relations, human_note 正确解析。"""
    card_path = tmp_path / "test_card.md"
    card_path.write_text(
        "---\n"
        "id: card_123\n"
        "status: human_approved\n"
        "knowledge_type: claim\n"
        "relations:\n"
        "  - type: supports\n"
        "    target_id: card_456\n"
        "human_note: This is a test note.\n"
        "---\n"
        "Body text\n",
        encoding="utf-8",
    )

    summary = _load_summary(card_path, tmp_path)

    assert summary.knowledge_type == "claim"
    assert summary.human_note == "This is a test note."
    assert len(summary.relations) == 1
    assert summary.relations[0]["type"] == "supports"
    assert summary.relations[0]["target_id"] == "card_456"


def test_load_summary_knowledge_model_fallbacks(tmp_path: Path):
    """legacy card（无 knowledge_model v2 字段）使用默认值。"""
    card_path = tmp_path / "test_card_legacy.md"
    card_path.write_text(
        "---\n"
        "id: card_legacy\n"
        "status: human_approved\n"
        "---\n"
        "Body text\n",
        encoding="utf-8",
    )

    summary = _load_summary(card_path, tmp_path)

    assert summary.knowledge_type == "concept"
    assert summary.human_note is None
    assert summary.relations == ()


# ============================================================================
# malformed YAML
# ============================================================================


def test_malformed_yaml_raises_card_error(tmp_path: Path):
    """语法错误的 YAML 导致 _CardError。"""
    card_path = tmp_path / "bad.md"
    card_path.write_text(
        "---\n"
        "id: card_1\n"
        "status human_approved\n"  # 缺少冒号
        "---\n"
        "Body\n",
        encoding="utf-8",
    )

    with pytest.raises(_CardError):
        _load_summary(card_path, tmp_path)


def test_missing_status_raises_card_error(tmp_path: Path):
    """缺 status 字段 → _CardError。"""
    card_path = tmp_path / "no_status.md"
    card_path.write_text(
        "---\n"
        "id: card_1\n"
        "title: Test\n"
        "---\n"
        "Body\n",
        encoding="utf-8",
    )

    with pytest.raises(_CardError):
        _load_summary(card_path, tmp_path)


def test_frontmatter_not_dict_raises_card_error(tmp_path: Path):
    """frontmatter 顶层不是 dict → _CardError。"""
    card_path = tmp_path / "not_dict.md"
    card_path.write_text(
        "---\n"
        "- item1\n"
        "- item2\n"
        "---\n"
        "Body\n",
        encoding="utf-8",
    )

    with pytest.raises(_CardError):
        _load_summary(card_path, tmp_path)


# ============================================================================
# knowledge_type edge cases
# ============================================================================


def test_unknown_knowledge_type_preserved(tmp_path: Path):
    """未知 knowledge_type 保持原值（不 fallback 到 concept）。"""
    card_path = tmp_path / "unknown_type.md"
    _write_card(card_path, {
        "id": "card_1",
        "status": "human_approved",
        "knowledge_type": "quantum_entanglement",  # not in known set
    })

    summary = _load_summary(card_path, tmp_path)
    # _str_or_none returns the string as-is; only empty/None falls back
    assert summary.knowledge_type == "quantum_entanglement"


def test_empty_knowledge_type_falls_back(tmp_path: Path):
    """空 knowledge_type 回退到 'concept'。"""
    card_path = tmp_path / "empty_type.md"
    _write_card(card_path, {
        "id": "card_1",
        "status": "human_approved",
        "knowledge_type": "",
    })

    summary = _load_summary(card_path, tmp_path)
    assert summary.knowledge_type == "concept"


# ============================================================================
# relations edge cases
# ============================================================================


def test_relations_not_a_list(tmp_path: Path):
    """relations 不是 list 时返回空 tuple。"""
    card_path = tmp_path / "bad_rels.md"
    _write_card(card_path, {
        "id": "card_1",
        "status": "human_approved",
        "relations": "not_a_list",
    })

    summary = _load_summary(card_path, tmp_path)
    assert summary.relations == ()


def test_relations_missing_type(tmp_path: Path):
    """relation item 缺 type → 被过滤。"""
    card_path = tmp_path / "no_type.md"
    _write_card(card_path, {
        "id": "card_1",
        "status": "human_approved",
        "relations": [
            {"target_id": "card_2"},  # no type → filtered
            {"type": "supports", "target_id": "card_3"},  # valid
        ],
    })

    summary = _load_summary(card_path, tmp_path)
    assert len(summary.relations) == 1
    assert summary.relations[0]["type"] == "supports"


def test_relations_empty_list(tmp_path: Path):
    """空 relations list → 空 tuple。"""
    card_path = tmp_path / "empty_rels.md"
    _write_card(card_path, {
        "id": "card_1",
        "status": "human_approved",
        "relations": [],
    })

    summary = _load_summary(card_path, tmp_path)
    assert summary.relations == ()


# ============================================================================
# human_note integrity
# ============================================================================


def test_human_note_is_null_when_missing(tmp_path: Path):
    """human_note 缺失时为 None。"""
    card_path = tmp_path / "no_note.md"
    _write_card(card_path, {
        "id": "card_1",
        "status": "human_approved",
    })

    summary = _load_summary(card_path, tmp_path)
    assert summary.human_note is None


def test_human_note_is_null_when_empty(tmp_path: Path):
    """human_note 为空字符串时为 None（不把空字符串当备注）。"""
    card_path = tmp_path / "empty_note.md"
    _write_card(card_path, {
        "id": "card_1",
        "status": "human_approved",
        "human_note": "",
    })

    summary = _load_summary(card_path, tmp_path)
    assert summary.human_note is None


def test_human_note_not_from_ai_text(tmp_path: Path):
    """验证 human_note 来自 frontmatter，不从未审批 body 文本伪造。"""
    card_path = tmp_path / "with_note.md"
    card_path.write_text(
        "---\n"
        "id: card_1\n"
        "status: human_approved\n"
        "human_note: Manually approved after review\n"
        "---\n"
        "## AI Summary\n\n"
        "This is AI-generated content that should not become human_note.\n"
        "## Human Note\n\n"
        "This section is in the body, not frontmatter — should not leak.\n",
        encoding="utf-8",
    )

    summary = _load_summary(card_path, tmp_path)
    # human_note should only come from frontmatter
    assert summary.human_note == "Manually approved after review"
    # body content should not contaminate human_note
    assert "AI-generated" not in (summary.human_note or "")
