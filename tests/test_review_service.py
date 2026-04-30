"""v0.7.18 — review_service 领域边界测试。

这些测试直接覆盖 weekly review service，而不是通过 CLI 输出间接判断。目标是让
review 的核心业务规则可独立验证：只聚合 `human_approved` 卡片，绝不把
`ai_draft` 当成正式复习材料，也不改变 approval 状态。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

import mindforge.review_service as review_service
from mindforge.approval_service import approve_explicit_card
from mindforge.config import MindForgeConfig, load_mindforge_config
from mindforge.review_service import build_weekly_review, calculate_weekly_review_window


def _write_card(cards_dir: Path, name: str, frontmatter: dict[str, object]) -> Path:
    """写最小测试卡片；review_service 只能读取 frontmatter 安全摘要。"""

    front = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in frontmatter.items()
    )
    path = cards_dir / f"{name}.md"
    path.write_text(f"---\n{front}\n---\n\nBODY_SECRET_SHOULD_NOT_MATTER\n", encoding="utf-8")
    return path


def _make_cfg(tmp_path: Path) -> tuple[MindForgeConfig, Path, Path]:
    """创建隔离 vault/config，不读取真实 `.env`，不连接真实 LLM。"""

    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    projects = vault / "30-Projects"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    cards.mkdir(parents=True)
    projects.mkdir(parents=True)
    formal_note = projects / "formal-note.md"
    formal_note.write_text("# formal note\n", encoding="utf-8")

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
    return load_mindforge_config(cfg_path), cards, formal_note


def test_weekly_review_window_calculation() -> None:
    """窗口计算可用固定 now 独立测试，避免 CLI 当前时间导致断言漂移。"""

    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    window = calculate_weekly_review_window(now)

    assert window.generated_at == now
    assert window.week_start == now - timedelta(days=7)
    assert window.due_end == now + timedelta(days=7)
    assert window.preview_end == now + timedelta(days=14)


def test_weekly_aggregates_only_human_approved_cards(tmp_path: Path) -> None:
    """approved 卡片进入 review 聚合；ai_draft 即使到期也必须排除。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    _write_card(
        cards,
        "approved-overdue",
        {
            "id": "approved-overdue",
            "title": "Approved overdue",
            "status": "human_approved",
            "track": "agent-runtime",
            "projects": ["alpha"],
            "review_after": (now - timedelta(days=1)).isoformat(),
            "last_review_result": "partial",
        },
    )
    _write_card(
        cards,
        "draft-overdue",
        {
            "id": "draft-overdue",
            "title": "Draft overdue",
            "status": "ai_draft",
            "track": "agent-runtime",
            "projects": ["alpha"],
            "review_after": (now - timedelta(days=2)).isoformat(),
            "last_review_result": "forgotten",
        },
    )

    result = build_weekly_review(cfg, now=now)

    assert [card.id for card in result.approved_cards] == ["approved-overdue"]
    assert [card.id for card in result.overdue] == ["approved-overdue"]
    assert [card.id for card in result.forgotten_or_partial] == ["approved-overdue"]
    assert result.draft_cards_count == 1
    assert "draft-overdue" not in {card.id for card in result.overdue}


def test_weekly_due_recent_preview_focus_and_project_distribution(tmp_path: Path) -> None:
    """service 负责 weekly 数据结构，CLI 后续只负责把这些结构渲染出去。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    _write_card(
        cards,
        "due",
        {
            "id": "due",
            "status": "human_approved",
            "track": "agent-runtime",
            "projects": ["alpha"],
            "review_after": (now + timedelta(days=3)).isoformat(),
            "reviewed_at": (now - timedelta(days=2)).isoformat(),
        },
    )
    _write_card(
        cards,
        "preview",
        {
            "id": "preview",
            "status": "human_approved",
            "track": "stock-analysis",
            "projects": ["beta"],
            "review_after": (now + timedelta(days=10)).isoformat(),
        },
    )
    _write_card(
        cards,
        "ignored-future",
        {
            "id": "ignored-future",
            "status": "human_approved",
            "track": "other",
            "review_after": (now + timedelta(days=30)).isoformat(),
        },
    )

    result = build_weekly_review(cfg, now=now)

    assert [card.id for card in result.due_this_week] == ["due"]
    assert [card.id for card in result.reviewed_this_week] == ["due"]
    assert [card.id for card in result.next_week_preview] == ["preview"]
    assert [(item.track, item.score) for item in result.suggested_focus_tracks] == [
        ("agent-runtime", 1)
    ]
    assert [(item.project, item.card_count) for item in result.project_distribution] == [
        ("alpha", 1),
        ("beta", 1),
    ]


def test_empty_review_state_is_structured(tmp_path: Path) -> None:
    """没有 weekly work 时返回结构化 empty_state，由 CLI 决定用户可见文案。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    _write_card(cards, "draft", {"id": "draft", "status": "ai_draft"})

    result = build_weekly_review(cfg, now=datetime(2026, 4, 30, tzinfo=timezone.utc))

    assert result.has_weekly_work is False
    assert result.empty_state is not None
    assert result.empty_state.reason == "only_ai_draft_cards"
    assert result.empty_state.approved_card_count == 0
    assert result.empty_state.has_draft_cards is True


def test_malformed_card_is_reported_without_blocking_valid_cards(tmp_path: Path) -> None:
    """损坏卡片进入 scan_errors，不能让 valid human_approved 聚合失败。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    _write_card(cards, "valid", {"id": "valid", "status": "human_approved"})
    (cards / "bad.md").write_text("---\nstatus: ai_draft\n  bad: : :\n---\nbody\n", encoding="utf-8")

    result = build_weekly_review(cfg, now=datetime(2026, 4, 30, tzinfo=timezone.utc))

    assert [card.id for card in result.approved_cards] == ["valid"]
    assert len(result.scan_errors) == 1
    assert result.scan_errors[0].rel_path.endswith("bad.md")


def test_review_service_does_not_env_llm_rich_typer_or_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """review_service 是本地只读聚合：不读 env、不发 HTTP、不写正式 notes、不改 status。"""

    cfg, cards, formal_note = _make_cfg(tmp_path)
    tmp_path.joinpath(".env").write_text("SECRET=must-not-read\n", encoding="utf-8")
    draft = _write_card(cards, "draft", {"id": "draft", "status": "ai_draft"})
    approved = _write_card(cards, "approved", {"id": "approved", "status": "human_approved"})
    before = {path: path.read_text(encoding="utf-8") for path in (draft, approved, formal_note)}

    def _blocked_env(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("review_service 不应读取 .env")

    def _blocked_http(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("review_service 不应调用 LLM/HTTP")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr("httpx.Client.post", _blocked_http)

    result = build_weekly_review(cfg, now=datetime(2026, 4, 30, tzinfo=timezone.utc))

    assert [card.id for card in result.approved_cards] == ["approved"]
    assert {path: path.read_text(encoding="utf-8") for path in before} == before
    assert not hasattr(review_service, "typer")
    assert not hasattr(review_service, "console")


def test_review_service_does_not_conflict_with_approval_service(tmp_path: Path) -> None:
    """review 不会自动 approve；显式 approval_service approve 后才进入 review。"""

    cfg, cards, _note = _make_cfg(tmp_path)
    draft = _write_card(cards, "draft", {"id": "draft", "status": "ai_draft"})
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)

    before = build_weekly_review(cfg, now=now)
    approved = approve_explicit_card(cfg, draft)
    after = build_weekly_review(cfg, now=now)

    assert before.approved_cards == ()
    assert approved.error is None
    assert [card.id for card in after.approved_cards] == ["draft"]
