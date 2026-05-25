"""v3.1 — 示例 workspace fixture 契约测试。

验证 sample workspace 可以被正确构建，所有卡片、源文件、配置文件格式合法。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from tests.fixtures.sample_workspace import (
    SAMPLE_CARDS,
    SAMPLE_WORKSPACE_SCHEMA_VERSION,
    build_sample_workspace,
    create_sample_cards,
    create_sample_config,
    create_sample_sources,
    create_sample_state,
)


class TestSampleWorkspace:
    """验证 build_sample_workspace 生成的数据完整性。"""

    def test_build_creates_all_directories(self, tmp_path: Path):
        ws = build_sample_workspace(tmp_path / "sample")
        assert (ws / "mindforge.yaml").exists()
        assert (ws / "vault" / "00-Inbox").is_dir()
        assert (ws / "vault" / "20-Knowledge-Cards").is_dir()
        assert (ws / ".mindforge" / "state.json").exists()
        assert (ws / "exports").is_dir()

    def test_config_is_valid_yaml(self, tmp_path: Path):
        cfg_path = create_sample_config(tmp_path)
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        assert data["version"] == 0.7
        assert "vault" in data
        assert "llm" in data

    def test_all_cards_have_required_fields(self, tmp_path: Path):
        vault = tmp_path / "vault"
        cards = create_sample_cards(vault)
        assert len(cards) == len(SAMPLE_CARDS)

        for card_path in cards:
            text = card_path.read_text(encoding="utf-8")
            assert text.startswith("---"), f"{card_path.name} 缺 frontmatter"
            parts = text.split("---", 2)
            fm = yaml.safe_load(parts[1])
            for key in ("id", "title", "status", "track", "schema_version", "quality_level"):
                assert key in fm, f"{card_path.name} 缺字段 {key}"

    def test_cards_have_body_content(self, tmp_path: Path):
        vault = tmp_path / "vault"
        cards = create_sample_cards(vault)
        for card_path in cards:
            text = card_path.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            assert len(parts) >= 3, f"{card_path.name} 缺 body"
            assert len(parts[2].strip()) > 0, f"{card_path.name} body 为空"

    def test_status_distribution_includes_all_three_states(self, tmp_path: Path):
        vault = tmp_path / "vault"
        cards = create_sample_cards(vault)
        statuses = set()
        for card_path in cards:
            text = card_path.read_text(encoding="utf-8")
            fm = yaml.safe_load(text.split("---")[1])
            statuses.add(fm["status"])
        assert "ai_draft" in statuses
        assert "human_approved" in statuses
        assert "trashed" in statuses

    def test_sources_created(self, tmp_path: Path):
        vault = tmp_path / "vault"
        sources = create_sample_sources(vault)
        assert len(sources) == 3
        for src in sources:
            assert src.suffix == ".md"

    def test_state_json_valid(self, tmp_path: Path):
        state_dir = tmp_path / ".mindforge"
        state_dir.mkdir(parents=True)
        state_path = create_sample_state(state_dir)
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == SAMPLE_WORKSPACE_SCHEMA_VERSION

    def test_schema_version_consistency(self, tmp_path: Path):
        """确保所有卡片使用统一的 schema_version。"""
        vault = tmp_path / "vault"
        cards = create_sample_cards(vault)
        for card_path in cards:
            text = card_path.read_text(encoding="utf-8")
            fm = yaml.safe_load(text.split("---")[1])
            assert fm["schema_version"] == SAMPLE_WORKSPACE_SCHEMA_VERSION, (
                f"{card_path.name} schema_version 不一致"
            )

    def test_no_real_data_leak(self, tmp_path: Path):
        """确保示例数据不含真实信息（邮箱、URL、API key 等）。"""
        ws = build_sample_workspace(tmp_path / "sample")
        all_text = ""
        for md in ws.rglob("*.md"):
            all_text += md.read_text(encoding="utf-8")
        for yf in ws.rglob("*.yaml"):
            all_text += yf.read_text(encoding="utf-8")

        assert "sk-" not in all_text, "疑似 API key 泄露"
        assert "@gmail.com" not in all_text, "疑似真实邮箱"
        assert "@anthropic.com" not in all_text
        assert "api_key" not in all_text.lower() or "fake" in all_text
