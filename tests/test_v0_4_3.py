"""v0.4.3 — CLI onboarding polish.

本组测试只覆盖产品化入口：interactive init、doctor/next 输出契约、错误信息收口。
不调真实 LLM、不读 .env、不发 HTTP。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

from .test_v0_4_2 import _make_vault, _write_card

runner = CliRunner()


def test_init_interactive_creates_vault_and_rewrites_choices(tmp_path: Path) -> None:
    target = tmp_path / "InteractiveVault"
    res = runner.invoke(
        app,
        ["init", "--interactive", "--project-root", str(tmp_path)],
        input=f"{target}\ny\nmain\n",
    )
    assert res.exit_code == 0, res.output
    assert (target / "00-Inbox").is_dir()
    # first-run 不预建分类子目录
    for sub in ("ManualNotes", "WebClips", "ChatExports", "PDFs", "Docs"):
        assert not (target / "00-Inbox" / sub).exists()
    assert not (tmp_path / ".env").exists()

    cfg_path = tmp_path / "configs" / "mindforge.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert cfg["vault"]["root"] == str(target.resolve())
    assert cfg["telemetry"]["enabled"] is True
    assert cfg["telemetry"]["local_only"] is True
    assert cfg["llm"]["default_model"] == "main"
    assert "active" not in cfg["llm"]
    assert "active_profile" not in cfg["llm"]


def test_init_interactive_rejects_existing_non_vault_dir(tmp_path: Path) -> None:
    target = tmp_path / "not-vault"
    target.mkdir()
    (target / "notes.md").write_text("user content\n", encoding="utf-8")

    res = runner.invoke(
        app,
        ["init", "--interactive", "--project-root", str(tmp_path)],
        input=f"{target}\n",
    )
    assert res.exit_code == 2
    assert "请选择空目录" in res.output
    assert not (tmp_path / "configs").exists()


def test_next_json_v2_limits_to_five_and_adds_priority(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox" / "ManualNotes"
    inbox.joinpath("note.md").write_text("# note\n\nbody\n", encoding="utf-8")
    cards = vault / "20-Knowledge-Cards"
    _write_card(cards, "draft-1", {"id": "draft-1", "title": "d", "status": "ai_draft"})
    _write_card(
        cards,
        "approved-1",
        {
            "id": "approved-1",
            "title": "a",
            "status": "human_approved",
            "review_after": "2000-01-01T00:00:00+00:00",
        },
    )
    (vault / "30-Projects" / "p.md").write_text("---\nproject_name: p\n---\n", encoding="utf-8")

    res = runner.invoke(app, ["next", "--config", str(cfg), "--format", "json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["version"] == 2
    assert len(data["suggestions"]) <= 5
    assert all(s["priority"] in {"critical", "recommended", "info"} for s in data["suggestions"])
    assert data["suggestions"][0]["priority"] in {"critical", "recommended"}


def test_doctor_has_sections_and_optional_installs(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    res = runner.invoke(app, ["doctor", "--config", str(cfg)])
    assert res.exit_code == 0, res.output
    for expected in ("Runtime", "Vault", "Optional installs", "Safety"):
        assert expected in res.output
    assert "pypdf" in res.output
    assert "python-docx" in res.output
