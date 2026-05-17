"""Knowledge Health CLI tests.

中文学习型说明：CLI health 是 M5 的用户可见入口。测试必须确认它只读生成报告，
不会把 ai_draft 自动 approve，也不会修改 human_approved frontmatter。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cards import read_card_frontmatter
from mindforge.cli import app

runner = CliRunner()


def _write_config(tmp_path: Path) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    cards.mkdir(parents=True)
    cfg = tmp_path / "mindforge.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                },
                "llm": {
                    "active": "fake",
                    "providers": {"fake": {"type": "fake", "purpose": "test"}},
                },
                "telemetry": {"enabled": True, "local_only": True},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg, vault


def test_health_cli_reports_issues_without_mutating_cards(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    cards = vault / "20-Knowledge-Cards"
    approved = cards / "approved.md"
    draft = cards / "draft.md"
    approved.write_text(
        """---
id: approved-1
title: Approved Missing Provenance
status: human_approved
---

tiny
""",
        encoding="utf-8",
    )
    draft.write_text(
        """---
id: draft-1
title: Draft
status: ai_draft
source_id: src
source_type: txt
source_path: note.txt
source_content_hash: sha256:test
adapter_name: TxtAdapter
---

draft
""",
        encoding="utf-8",
    )
    before = approved.read_text(encoding="utf-8")

    result = runner.invoke(app, ["health", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "MindForge Knowledge Health" in result.output
    assert "missing_provenance" in result.output
    assert approved.read_text(encoding="utf-8") == before
    assert read_card_frontmatter(draft)["status"] == "ai_draft"


def test_health_cli_json_includes_issue_reason_and_suggested_action(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    (vault / "20-Knowledge-Cards" / "approved.md").write_text(
        """---
id: approved-1
title: Approved Missing Provenance
status: human_approved
---

tiny
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["health", "--config", str(cfg), "--json"])

    assert result.exit_code == 0, result.output
    assert '"code": "missing_provenance"' in result.output
    assert '"reason":' in result.output
    assert '"suggested_action":' in result.output
