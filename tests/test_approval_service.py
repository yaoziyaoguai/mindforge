"""v0.7.17 — approval_service 领域边界测试。

这些测试直接覆盖 service 层，而不是通过 Typer CLI 绕一圈。目的不是降低
`cli.py` 行数，而是确认 approve workflow 的核心判断能独立验证：只有明确
的人审动作可以把 `ai_draft` 晋升为 `human_approved`，列表/预览/查找都不能
顺手自动 approve。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import mindforge.approval_service as approval_service
from mindforge.approval_service import (
    ApprovalListQuery,
    approve_explicit_card,
    list_approval_candidates,
    preview_approval_card,
    resolve_candidate_by_card_id,
)
from mindforge.config import MindForgeConfig, load_mindforge_config


def _write_card(cards_dir: Path, name: str, frontmatter: dict[str, object], body: str = "body") -> Path:
    """写测试卡片；正文里放敏感哨兵时，service 只能通过文件内容断言未泄漏。"""

    front = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in frontmatter.items()
    )
    path = cards_dir / f"{name}.md"
    path.write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")
    return path


def _make_cfg(tmp_path: Path) -> tuple[MindForgeConfig, Path, Path]:
    """创建最小 vault/config；不创建 `.env`，不接真实 LLM 或 Obsidian vault。"""

    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    projects = vault / "30-Projects"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    cards.mkdir(parents=True)
    projects.mkdir(parents=True)
    projects.joinpath("official-note.md").write_text("# formal note\n", encoding="utf-8")

    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
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
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return load_mindforge_config(cfg_path), cards, projects / "official-note.md"


def test_list_pending_ai_draft_and_empty_state(tmp_path: Path) -> None:
    """候选列表只收 `ai_draft`；没有草稿时返回空结构，不自动选择替代卡片。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    _write_card(cards, "draft", {"id": "draft", "title": "Draft", "status": "ai_draft"})
    _write_card(
        cards,
        "approved",
        {"id": "approved", "title": "Approved", "status": "human_approved"},
    )

    result = list_approval_candidates(cfg)

    assert [card.id for card in result.candidates] == ["draft"]
    assert result.statuses == ("ai_draft",)
    cards.joinpath("draft.md").write_text(
        cards.joinpath("draft.md").read_text(encoding="utf-8").replace(
            '"ai_draft"', '"human_approved"'
        ),
        encoding="utf-8",
    )
    assert list_approval_candidates(cfg).candidates == ()


def test_list_filters_use_safe_frontmatter_fields_only(tmp_path: Path) -> None:
    """project/track 过滤只依赖 CardSummary 白名单字段，不需要读取正文。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    _write_card(
        cards,
        "agent",
        {
            "id": "agent",
            "title": "Agent Draft",
            "status": "ai_draft",
            "track": "agent-runtime",
            "projects": ["alpha"],
        },
        body="BODY_SECRET_SHOULD_NOT_BE_NEEDED",
    )
    _write_card(
        cards,
        "stock",
        {
            "id": "stock",
            "title": "Stock Draft",
            "status": "ai_draft",
            "track": "stock-analysis",
            "projects": ["beta"],
        },
    )

    result = list_approval_candidates(
        cfg,
        ApprovalListQuery(project="alpha", track="agent-runtime", limit=10),
    )

    assert [card.id for card in result.candidates] == ["agent"]


def test_approve_requires_explicit_target_and_promotes_only_that_card(tmp_path: Path) -> None:
    """显式 approve 只晋升传入卡片，不会越权修改其他 cards 或正式 notes。"""

    cfg, cards, formal_note = _make_cfg(tmp_path)
    target = _write_card(cards, "draft", {"id": "draft", "status": "ai_draft"})
    other = _write_card(cards, "other", {"id": "other", "status": "ai_draft"})
    other_before = other.read_text(encoding="utf-8")
    note_before = formal_note.read_text(encoding="utf-8")

    missing = approve_explicit_card(cfg, None)
    assert missing.error is not None
    assert missing.error.kind == "missing_card"

    result = approve_explicit_card(cfg, target)

    assert result.error is None
    assert result.outcome is not None
    assert result.outcome.new_status == "human_approved"
    assert "status: human_approved" in target.read_text(encoding="utf-8")
    assert other.read_text(encoding="utf-8") == other_before
    assert formal_note.read_text(encoding="utf-8") == note_before


def test_human_approved_card_is_idempotent_not_reapproved(tmp_path: Path) -> None:
    """已 human_approved 的卡片可幂等返回，但不能刷新 approved_at 或重复写入。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    card = _write_card(
        cards,
        "approved",
        {
            "id": "approved",
            "status": "human_approved",
            "approved_at": "2026-01-01T00:00:00+00:00",
            "approval_method": "explicit_cli",
        },
    )
    before = card.read_text(encoding="utf-8")

    result = approve_explicit_card(cfg, card)

    assert result.outcome is not None
    assert result.outcome.kind == "already_approved"
    assert card.read_text(encoding="utf-8") == before


def test_card_id_lookup_returns_structured_errors(tmp_path: Path) -> None:
    """card id 查找只返回路径或结构化错误，不把找不到误解成批量 approve。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    card = _write_card(cards, "draft", {"id": "draft-id", "status": "ai_draft"})

    missing_id = resolve_candidate_by_card_id(cfg, None)
    nonexistent = resolve_candidate_by_card_id(cfg, "no-such-id")
    found = resolve_candidate_by_card_id(cfg, "draft-id")

    assert missing_id.error is not None
    assert missing_id.error.kind == "missing_card_id"
    assert nonexistent.error is not None
    assert nonexistent.error.kind == "card_id_not_found"
    assert found.card_path == card.resolve()


def test_malformed_card_returns_structured_error(tmp_path: Path) -> None:
    """frontmatter 损坏时 service 返回结构化错误，不写入 human_approved。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    card = cards / "bad.md"
    card.write_text("---\nstatus: ai_draft\n  bad: : :\n---\nbody\n", encoding="utf-8")

    preview = preview_approval_card(cfg, card)
    result = approve_explicit_card(cfg, card)

    assert preview.error is not None
    assert preview.error.kind == "frontmatter_unreadable"
    assert result.error is not None
    assert result.error.exit_code == 3
    assert "human_approved" not in card.read_text(encoding="utf-8")


def test_preview_and_list_do_not_auto_approve(tmp_path: Path) -> None:
    """只读动作不能把 ai_draft 偷偷晋升为 human_approved。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    card = _write_card(cards, "draft", {"id": "draft", "status": "ai_draft"})
    before = card.read_text(encoding="utf-8")

    listed = list_approval_candidates(cfg)
    preview = preview_approval_card(cfg, card)

    assert [candidate.id for candidate in listed.candidates] == ["draft"]
    assert preview.error is None
    assert preview.fields["status"] == "ai_draft"
    assert card.read_text(encoding="utf-8") == before


def test_service_no_env_llm_rich_typer_or_obsidian_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """service 边界不读 `.env`、不调 LLM、不依赖 CLI 展示层、不写正式 notes。"""

    cfg, cards, formal_note = _make_cfg(tmp_path)
    tmp_path.joinpath(".env").write_text("SECRET=must-not-read\n", encoding="utf-8")
    card = _write_card(cards, "draft", {"id": "draft", "status": "ai_draft"})
    note_before = formal_note.read_text(encoding="utf-8")

    def _blocked_env(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("approval_service 不应读取 .env")

    def _blocked_http(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("approval_service 不应调用真实 LLM/HTTP")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr("httpx.Client.post", _blocked_http)

    result = approve_explicit_card(cfg, card)

    assert result.error is None
    assert formal_note.read_text(encoding="utf-8") == note_before
    assert not hasattr(approval_service, "typer")
    assert not hasattr(approval_service, "console")
