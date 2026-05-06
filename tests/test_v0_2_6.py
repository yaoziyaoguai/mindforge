"""v0.2.6 — mindforge init / approve workflow polish / doctor 增强 测试。

为什么 init 必须幂等：用户多次执行不能破坏已存在的内容（详见 init_cmd.py）。
为什么 approve --all 默认拒绝：批量 approve 是把 ai_draft 升级为长期记忆的危险动作。
为什么 doctor 给可操作建议：用户大多数时候只想知道"现在哪里坏了 + 怎么修"。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_min_cfg(tmp_path: Path) -> Path:
    """创建一个最小 vault + cfg + 几张卡片，用于 approve list 测试。"""
    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "30-Projects").mkdir(parents=True)
    cards.mkdir(parents=True)

    def card(name: str, **fm) -> Path:
        front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items())
        p = cards / f"{name}.md"
        p.write_text(
            f"---\n{front}\n---\n\n# {fm.get('title', name)}\n\nbody\n",
            encoding="utf-8",
        )
        return p

    card(
        "c1",
        id="c1",
        title="Draft A",
        status="ai_draft",
        track="agent-runtime",
        projects=["alpha"],
        source_type="webclip_markdown",
    )
    card(
        "c2",
        id="c2",
        title="Draft B",
        status="ai_draft",
        track="stock-analysis",
        projects=[],
        source_type="cubox_markdown",
    )
    card(
        "c3",
        id="c3",
        title="Approved C",
        status="human_approved",
        track="agent-runtime",
        projects=["alpha"],
        source_type="plain_markdown",
    )

    cfg = {
        "version": 0.1,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
            "projects_dir": "30-Projects",
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
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "f1",
                    "distill": "f1",
                    "link_suggestion": "f1",
                    "review_questions": "f1",
                    "action_extraction": "f1",
                }
            },
            "models": {
                "f1": {
                    "provider": "fake-local",
                    "type": "fake",
                    "base_url": "fake://",
                    "model": "fake-1",
                    "timeout_seconds": 5,
                    "max_retries": 0,
                }
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
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return cfg_path


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def test_init_dry_run_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "newvault"
    res = runner.invoke(
        app,
        [
            "init",
            "--vault",
            str(target),
            "--project-root",
            str(tmp_path),
            "--dry-run",
        ],
    )
    assert res.exit_code == 0, res.output
    assert "--dry-run" in res.output
    assert not target.exists()
    assert not (tmp_path / "configs").exists()


def test_init_creates_vault_and_configs(tmp_path: Path) -> None:
    target = tmp_path / "newvault"
    res = runner.invoke(
        app,
        ["init", "--vault", str(target), "--project-root", str(tmp_path)],
    )
    assert res.exit_code == 0, res.output
    # vault 必备目录
    for d in (
        "00-Inbox/Cubox",
        "00-Inbox/WebClips",
        "00-Inbox/ChatExports",
        "00-Inbox/PDFs",
        "00-Inbox/Docs",
        "20-Knowledge-Cards",
        "30-Projects",
        "80-Reviews",
        "90-System",
    ):
        assert (target / d).is_dir(), f"missing {d}"
    # configs
    assert (tmp_path / "configs" / "mindforge.yaml").exists()
    assert (tmp_path / "configs" / "learning_tracks.yaml").exists()
    # .env.example 而非 .env
    assert (tmp_path / ".env.example").exists()
    assert not (tmp_path / ".env").exists()
    # next steps 提示
    assert "Next steps" in res.output


def test_init_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "vlt"
    args = ["init", "--vault", str(target), "--project-root", str(tmp_path)]
    runner.invoke(app, args)
    # 在 vault 内新增"用户文件"
    user_file = target / "30-Projects" / "my-personal-note.md"
    user_file.write_text("# my hand-written\n", encoding="utf-8")
    cfg_text_before = (tmp_path / "configs" / "mindforge.yaml").read_text("utf-8")

    # 第二次 init 不应破坏任何东西
    res2 = runner.invoke(app, args)
    assert res2.exit_code == 0
    assert user_file.read_text("utf-8") == "# my hand-written\n"
    assert (tmp_path / "configs" / "mindforge.yaml").read_text("utf-8") == cfg_text_before
    assert "skip" in res2.output.lower() or "keep" in res2.output.lower()


def test_init_force_overwrites_template_only(tmp_path: Path) -> None:
    target = tmp_path / "vlt"
    args = ["init", "--vault", str(target), "--project-root", str(tmp_path)]
    runner.invoke(app, args)
    # 篡改模板文件
    cfg_file = tmp_path / "configs" / "mindforge.yaml"
    cfg_file.write_text("# user modified\n", encoding="utf-8")
    # 用户文件不应被动
    user_file = target / "30-Projects" / "user.md"
    user_file.write_text("# keep me\n", encoding="utf-8")

    res = runner.invoke(app, args + ["--force"])
    assert res.exit_code == 0
    # 模板被覆盖
    assert cfg_file.read_text("utf-8") != "# user modified\n"
    # 用户文件仍在
    assert user_file.read_text("utf-8") == "# keep me\n"


# ---------------------------------------------------------------------------
# approve workflow
# ---------------------------------------------------------------------------


def test_approve_card_requires_confirm_for_real_write(tmp_path: Path) -> None:
    cfg_path = _make_min_cfg(tmp_path)
    card = tmp_path / "vault" / "20-Knowledge-Cards" / "c1.md"
    res = runner.invoke(app, ["approve", "--card", str(card), "--config", str(cfg_path)])
    assert res.exit_code == 2, res.output
    assert "--confirm" in res.output
    assert "human_approved" not in card.read_text("utf-8")

    res = runner.invoke(
        app,
        ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"],
    )
    assert res.exit_code == 0, res.output
    assert "approved" in res.output.lower()
    # 真的被改了
    assert "human_approved" in card.read_text("utf-8")


def test_approve_list_default_ai_draft(tmp_path: Path) -> None:
    cfg_path = _make_min_cfg(tmp_path)
    res = runner.invoke(app, ["approve", "list", "--config", str(cfg_path)])
    assert res.exit_code == 0, res.output
    assert "Draft A" in res.output
    assert "Draft B" in res.output
    assert "Approved C" not in res.output  # 已批准的不显示


def test_approve_list_filters_by_project_and_track(tmp_path: Path) -> None:
    cfg_path = _make_min_cfg(tmp_path)
    res = runner.invoke(
        app,
        ["approve", "list", "--project", "alpha", "--config", str(cfg_path)],
    )
    assert res.exit_code == 0
    assert "Draft A" in res.output
    assert "Draft B" not in res.output

    res2 = runner.invoke(
        app,
        ["approve", "list", "--track", "stock-analysis", "--config", str(cfg_path)],
    )
    assert res2.exit_code == 0
    assert "Draft B" in res2.output
    assert "Draft A" not in res2.output


def test_approve_list_json_format_safe_fields_only(tmp_path: Path) -> None:
    cfg_path = _make_min_cfg(tmp_path)
    res = runner.invoke(
        app,
        ["approve", "list", "--format", "json", "--config", str(cfg_path)],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["count"] == 2
    item = data["items"][0]
    # 白名单字段
    assert set(item.keys()) == {
        "title",
        "path",
        "status",
        "track",
        "projects",
        "source_type",
        "created_at",
        "value_score",
    }
    # 严禁 raw_text / body / api_key
    text = res.output.lower()
    for forbidden in ("raw_text", "api_key", "bearer", "authorization", "completion"):
        assert forbidden not in text


def test_approve_all_dry_run_writes_nothing(tmp_path: Path) -> None:
    cfg_path = _make_min_cfg(tmp_path)
    card1 = tmp_path / "vault" / "20-Knowledge-Cards" / "c1.md"
    before = card1.read_text("utf-8")
    res = runner.invoke(
        app,
        ["approve", "--all", "--dry-run", "--config", str(cfg_path)],
    )
    assert res.exit_code == 0
    assert "Draft A" in res.output
    # 文件未变
    assert card1.read_text("utf-8") == before


def test_approve_all_without_confirm_refuses(tmp_path: Path) -> None:
    cfg_path = _make_min_cfg(tmp_path)
    card1 = tmp_path / "vault" / "20-Knowledge-Cards" / "c1.md"
    before = card1.read_text("utf-8")
    res = runner.invoke(app, ["approve", "--all", "--config", str(cfg_path)])
    assert res.exit_code == 2
    assert "--confirm" in res.output
    assert card1.read_text("utf-8") == before


def test_approve_all_with_confirm_and_limit(tmp_path: Path) -> None:
    cfg_path = _make_min_cfg(tmp_path)
    res = runner.invoke(
        app,
        ["approve", "--all", "--confirm", "--limit", "1", "--config", str(cfg_path)],
    )
    assert res.exit_code == 0, res.output
    # 仅一张被升级
    cards_dir = tmp_path / "vault" / "20-Knowledge-Cards"
    upgraded = sum(
        1
        for p in cards_dir.glob("*.md")
        if "human_approved" in p.read_text("utf-8")
    )
    # c3 原本就是 human_approved + 现在多一张 → 2
    assert upgraded == 2


def test_approve_source_id_resolves_card(tmp_path: Path) -> None:
    """通过 state.json 里的 source_id 反查 card_path 再 approve。"""
    cfg_path = _make_min_cfg(tmp_path)
    # 手工写一个 state.json 关联 c1.md
    from mindforge.checkpoint import Checkpoint
    from mindforge.config import load_mindforge_config
    from mindforge.models import ItemState
    from datetime import datetime, timezone

    cfg = load_mindforge_config(cfg_path)
    cp = Checkpoint.load(cfg.state.state_path)
    item = ItemState(
        source_id="sha1:fake-c1",
        source_type="plain_markdown",
        adapter_name="PlainMarkdownAdapter",
        source_path="00-Inbox/ManualNotes/c1-src.md",
        content_hash="sha256:y",
        status="processed",
        track="agent-runtime",
        value_score=8,
        card_path="agent-runtime/c1.md",
        last_run_id="r1",
        first_seen_at=datetime.now(timezone.utc),
        processed_at=datetime.now(timezone.utc),
    )
    cp.items[f"plain_markdown::{item.source_path}"] = item
    cp.save()
    # 把 c1 移动到 agent-runtime 子目录以匹配 card_path
    src = tmp_path / "vault" / "20-Knowledge-Cards" / "c1.md"
    sub = tmp_path / "vault" / "20-Knowledge-Cards" / "agent-runtime"
    sub.mkdir(parents=True, exist_ok=True)
    target = sub / "c1.md"
    target.write_text(src.read_text("utf-8"), encoding="utf-8")
    src.unlink()

    res = runner.invoke(
        app,
        ["approve", "--source-id", "sha1:fake-c1", "--config", str(cfg_path), "--confirm"],
    )
    assert res.exit_code == 0, res.output
    assert "human_approved" in target.read_text("utf-8")


def test_approve_no_args_friendly_hint(tmp_path: Path) -> None:
    cfg_path = _make_min_cfg(tmp_path)
    res = runner.invoke(app, ["approve", "--config", str(cfg_path)])
    assert res.exit_code == 0
    assert "Approve Todo" in res.output
    assert "mindforge approve 1 --confirm" in res.output
    card = tmp_path / "vault" / "20-Knowledge-Cards" / "c1.md"
    assert 'status: "ai_draft"' in card.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# doctor 增强
# ---------------------------------------------------------------------------


def test_doctor_action_items_for_drafts(tmp_path: Path) -> None:
    cfg_path = _make_min_cfg(tmp_path)
    import os

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        res = runner.invoke(app, ["doctor", "--config", str(cfg_path)])
    finally:
        os.chdir(cwd)
    assert res.exit_code == 0, res.output
    assert "Action items" in res.output
    assert "approve list" in res.output


def test_doctor_action_items_when_uninitialized(tmp_path: Path) -> None:
    """vault 缺目录时给出 init 建议。"""
    # 写一个 cfg 指向不存在的 vault
    cfg = {
        "version": 0.1,
        "vault": {
            "root": str(tmp_path / "missing_vault"),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
            "projects_dir": "30-Projects",
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
        "state": {"workdir": str(tmp_path / ".mindforge"), "state_file": "state.json",
                  "runs_dir": "runs", "index_file": "index.jsonl"},
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {"fake": {"triage": "f1", "distill": "f1", "link_suggestion": "f1",
                                  "review_questions": "f1", "action_extraction": "f1"}},
            "models": {"f1": {"provider": "fake", "type": "fake", "base_url": "fake://",
                              "model": "fake-1", "timeout_seconds": 5, "max_retries": 0}},
        },
        "prompts": {f"{s}_version": "v1" for s in (
            "triage", "distill", "link_suggestion", "review_questions", "action_extraction"
        )},
        "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
    }
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    res = runner.invoke(app, ["doctor", "--config", str(cfg_path)])
    assert res.exit_code == 0
    # vault dir 缺失 → 应给出 init 提示
    assert "mindforge init" in res.output
