"""v0.4.2 — `mindforge commands` / `mindforge next` / SourceAdapter 架构稳定性测试。

学习要点
========
- ``commands`` / ``next`` 是产品体验闭环，不能调 LLM、不能读 .env、不能联网；
- ``SourceAdapter`` 架构必须保持插件化：新增 source_type 只改 registry，
  不动 scanner / processor 任何一行；
- ``SourceDocument`` 的 ``adapter_name`` 字段是 v0.4.2 新增追溯位，
  必须由 Scanner 自动回填。
"""

from __future__ import annotations

import json
import socket
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app, _dogfood_command_snippets, _normalize_post_command_global_options
from mindforge.config import load_mindforge_config
from mindforge.scanner import Scanner
from mindforge.sources.base import SourceAdapter, SourceDocument, compute_content_hash
from mindforge.sources.registry import _BUILTIN_ADAPTERS, build_active_adapters

runner = CliRunner()


# ---------------------------------------------------------------------------
# 复用 v0.3.1 的 vault 构造
# ---------------------------------------------------------------------------
def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "30-Projects").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)

    cfg = {
        "version": 0.3,
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
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "fake_alias",
                    "distill": "fake_alias",
                    "link_suggestion": "fake_alias",
                    "review_questions": "fake_alias",
                    "action_extraction": "fake_alias",
                }
            },
            "models": {
                "fake_alias": {
                    "provider": "fake_provider",
                    "type": "fake",
                    "model": "fake-model",
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


def _write_card(cards: Path, name: str, fm: dict, body: str = "## AI Summary\nx\n") -> None:
    front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items())
    (cards / f"{name}.md").write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")


# ===========================================================================
# `mindforge commands`
# ===========================================================================
def test_commands_lists_key_groups() -> None:
    """commands 输出应按用户目标组织，而不是只按内部模块名铺开。"""
    res = runner.invoke(app, ["commands"])
    assert res.exit_code == 0
    out = res.output
    for kw in [
        "第一次开始",
        "导入 / 处理资料",
        "审批 ai_draft",
        "Recall",
        "Review",
        "Backup / Doctor",
        "Debug / Safety",
    ]:
        assert kw in out, f"commands 输出缺少 group: {kw}"
    # 第一阶段命令地图不再展示 legacy scan/project/Obsidian 主路径
    for cmd in ["mindforge web", "mindforge watch add", "mindforge approve",
                "mindforge index", "mindforge recall", "mindforge review"]:
        assert cmd in out
    assert "mindforge scan" not in out
    assert "mindforge obsidian" not in out
    assert "mindforge wiki" in out
    assert "--staged-export" not in out
    assert "--write" not in out


def test_commands_does_not_leak_secrets() -> None:
    """commands 是纯静态字符串，不应包含 secret 关键字。"""
    res = runner.invoke(app, ["commands"])
    assert res.exit_code == 0
    low = res.output.lower()
    for forbidden in ["api_key", "authorization:", "bearer ", "anthropic_api_key", ".env="]:
        assert forbidden not in low


# ===========================================================================
# `mindforge next`
# ===========================================================================
def test_next_without_config_suggests_init(tmp_path: Path) -> None:
    """配置不存在时 next 应当建议 init，且不抛错。"""
    res = runner.invoke(app, ["next", "--config", str(tmp_path / "missing.yaml")])
    assert res.exit_code == 0
    assert "mindforge init" in res.output


def test_next_empty_vault_suggests_inbox_or_index(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    res = runner.invoke(app, ["next", "--config", str(cfg)])
    assert res.exit_code == 0
    # 无原料 + 无索引 → 至少一条与 inbox 或 index 相关的建议
    assert ("inbox" in res.output or "index rebuild" in res.output)


def test_next_suggests_approve_when_drafts_exist(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "draft-1", {
        "id": "draft-1", "title": "draft", "status": "ai_draft",
        "track": "agent-runtime", "value_score": 5,
    })
    res = runner.invoke(app, ["next", "--config", str(cfg)])
    assert res.exit_code == 0
    assert "approve list" in res.output
    assert f"--vault {tmp_path / 'vault'}" in res.output


def test_next_suggests_index_rebuild_when_index_missing(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "card-1", {
        "id": "card-1", "title": "x", "status": "human_approved",
        "track": "agent-runtime", "value_score": 5,
    })
    res = runner.invoke(app, ["next", "--config", str(cfg)])
    assert res.exit_code == 0
    assert "index rebuild" in res.output


def test_next_after_scan_uses_configured_state_path(tmp_path: Path) -> None:
    """v0.7.7: next 不能把已写入的 configured state 误判成缺失。

    中文学习型说明：真实 dogfooding 会把 state.workdir 放在 /tmp 或别的目录。
    这里用真实 scan CLI 先写 state，再运行 next，证明产品提示基于配置里的
    state_file，而不是硬编码 workdir/state.json。
    """
    cfg = _make_vault(tmp_path)
    inbox = tmp_path / "vault" / "00-Inbox" / "ManualNotes"
    inbox.joinpath("daily.md").write_text("# Daily\n\nbody\n", encoding="utf-8")

    scan = runner.invoke(app, ["scan", "--config", str(cfg)])
    res = runner.invoke(app, ["next", "--config", str(cfg)])

    assert scan.exit_code == 0, scan.output
    assert res.exit_code == 0, res.output
    assert "state.json 还没建立" not in res.output
    assert "process --limit" in res.output


def test_next_json_format_is_parseable(tmp_path: Path) -> None:
    cfg = _make_vault(tmp_path)
    res = runner.invoke(app, ["next", "--config", str(cfg), "--format", "json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["version"] == 2
    assert "status" in data
    assert "inbox_files" in data["status"]
    assert isinstance(data["suggestions"], list)
    assert all("command" in s and "reason" in s and "priority" in s for s in data["suggestions"])


def test_next_text_suggestions_keep_current_vault(tmp_path: Path) -> None:
    """真实 dogfood 输出的下一步命令必须保留当前 vault 上下文。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "draft-1", {
        "id": "draft-1", "title": "draft", "status": "ai_draft",
        "track": "agent-runtime", "value_score": 5,
    })
    res = runner.invoke(app, ["next", "--config", str(cfg)])
    assert res.exit_code == 0, res.output
    assert f"--vault {tmp_path / 'vault'}" in res.output


def test_today_outputs_daily_loop_status_and_next_action(tmp_path: Path) -> None:
    """v0.5.4: today 是只读每日入口，展示状态和下一步，不触发加工。

    这里用真实 CLI runner 验证输出来自 vault/state/card 文件系统事实，而不是只测
    字符串拼接。命令不能读正文、不能 approve，也不能写 Obsidian notes。
    """
    cfg = _make_vault(tmp_path)
    inbox = tmp_path / "vault" / "00-Inbox" / "ManualNotes"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "daily.md").write_text("# Daily\n\nbody\n", encoding="utf-8")
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "draft-1", {
        "id": "draft-1", "title": "draft", "status": "ai_draft",
        "track": "agent-runtime", "value_score": 5,
    })

    res = runner.invoke(app, ["today", "--config", str(cfg)])
    assert res.exit_code == 0, res.output
    assert "MindForge today" in res.output
    assert "Daily status" in res.output
    assert "ai_draft=1" in res.output
    assert "Next actions" in res.output
    assert "approve list" in res.output


def test_start_outputs_onboarding_state_and_safety(tmp_path: Path) -> None:
    """v0.6.1: start 是第一天入口，只读展示状态和安全边界。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "approved", {
        "id": "approved", "title": "approved", "status": "human_approved",
        "track": "agent-runtime", "value_score": 5,
    })
    res = runner.invoke(app, ["start", "--config", str(cfg)])
    assert res.exit_code == 0, res.output
    assert "MindForge start" in res.output
    assert "Onboarding status" in res.output
    assert "human_approved" in res.output
    assert "Next actions" in res.output
    assert "不读 .env" in res.output


def test_start_suggestions_keep_current_vault(tmp_path: Path) -> None:
    """start 是第一天入口，建议命令也必须能直接复制到同一 vault。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "draft-1", {
        "id": "draft-1", "title": "draft", "status": "ai_draft",
        "track": "agent-runtime", "value_score": 5,
    })
    res = runner.invoke(app, ["start", "--config", str(cfg)])
    assert res.exit_code == 0, res.output
    assert f"--vault {tmp_path / 'vault'}" in res.output


def test_start_missing_config_suggests_init(tmp_path: Path) -> None:
    """未 init 场景要直接指向 init，而不是抛 Python traceback。"""
    res = runner.invoke(app, ["start", "--config", str(tmp_path / "missing.yaml")])
    assert res.exit_code == 0, res.output
    assert "mindforge init --interactive" in res.output


def test_start_json_from_non_repo_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """packaged-like smoke：start 在非 repo cwd 仍可用。"""
    cfg = _make_vault(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)
    res = runner.invoke(app, ["start", "--config", str(cfg), "--format", "json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["version"] == 1
    assert data["safety"]["calls_real_llm"] is False
    assert data["safety"]["reads_env"] is False


def test_today_json_is_parseable_and_does_not_read_env_or_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """today 必须是本地只读命令：不读 .env、不联网、不调用真实 LLM。"""
    cfg = _make_vault(tmp_path)
    (tmp_path / ".env").write_text("MINDFORGE_SECRET=must-not-leak\n", encoding="utf-8")

    import socket as _socket

    def _no_socket(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("today 不应联网")

    monkeypatch.setattr(_socket, "socket", _no_socket)
    res = runner.invoke(app, ["today", "--config", str(cfg), "--format", "json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["version"] == 1
    assert "status" in data and "suggestions" in data
    assert "must-not-leak" not in res.output


def test_start_does_not_read_env_or_network_or_write_obsidian(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """start 只能是只读 onboarding，不得偷偷读 secret、联网或写 Obsidian。"""
    cfg = _make_vault(tmp_path)
    (tmp_path / ".env").write_text("SECRET=must-not-leak\n", encoding="utf-8")

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("start 不应读取 .env")

    def _blocked_socket(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("start 不应联网")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr(socket, "socket", _blocked_socket)
    res = runner.invoke(app, ["start", "--config", str(cfg)])
    assert res.exit_code == 0, res.output
    assert "must-not-leak" not in res.output
    assert not (tmp_path / "vault" / "90-System" / "MindForge" / "Staging").exists()


def test_daily_loop_empty_states_have_next_action_hints(tmp_path: Path) -> None:
    """空状态也要像产品：告诉用户下一步，而不是只输出 no match。"""
    cfg = _make_vault(tmp_path)

    approve = runner.invoke(app, ["approve", "list", "--config", str(cfg)])
    assert approve.exit_code == 0, approve.output
    assert "没有待 approve" in approve.output
    assert "profile fake" in approve.output

    recall = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "missing"])
    assert recall.exit_code == 0, recall.output
    assert "没有匹配" in recall.output
    assert "index rebuild" in recall.output

    weekly = runner.invoke(app, ["review", "weekly", "--config", str(cfg)])
    assert weekly.exit_code == 0, weekly.output
    assert "Next action" in weekly.output
    assert "approve list" in weekly.output


def test_approve_list_outputs_todo_view_without_auto_approving(tmp_path: Path) -> None:
    """v0.6.2: approve list 是待办视图，不是审批动作。

    测试用真实 CLI 读取卡片 frontmatter，并在命令后回读文件确认 status 仍是
    ai_draft；这条边界防止未来把“更顺手”误做成自动 approve。
    """
    cfg = _make_vault(tmp_path)
    card = tmp_path / "vault" / "20-Knowledge-Cards" / "draft-ux.md"
    _write_card(card.parent, "draft-ux", {
        "id": "draft-ux",
        "title": "Approve UX draft",
        "status": "ai_draft",
        "track": "agent-runtime",
        "source_title": "Demo source",
        "created_at": "2026-01-02T03:04:00",
    })

    res = runner.invoke(app, ["approve", "list", "--config", str(cfg)])

    assert res.exit_code == 0, res.output
    assert "Approve Todo" in res.output
    assert "Demo source" in res.output
    assert "2026-01-02T03:04" in res.output
    assert "不会自动 approve" in res.output
    assert "mindforge approve 1 --confirm" in res.output
    assert 'status: "ai_draft"' in card.read_text(encoding="utf-8")


def test_approve_explicit_action_mentions_human_approval_boundary(tmp_path: Path) -> None:
    """显式 approve 可以写 human_approved，但输出必须讲清这是人工动作。"""
    cfg = _make_vault(tmp_path)
    card = tmp_path / "vault" / "20-Knowledge-Cards" / "draft-approve.md"
    _write_card(card.parent, "draft-approve", {
        "id": "draft-approve",
        "title": "Draft approve",
        "status": "ai_draft",
    })

    res = runner.invoke(app, ["approve", "--config", str(cfg), "--card", str(card)])
    assert res.exit_code == 2, res.output
    assert "--confirm" in res.output
    assert "ai_draft" in card.read_text(encoding="utf-8")

    res = runner.invoke(
        app,
        ["approve", "--config", str(cfg), "--card", str(card), "--confirm"],
    )

    assert res.exit_code == 0, res.output
    assert "human_approved" in res.output
    assert "显式人工 approve" in res.output
    assert "不会让 AI 自动写入" in res.output
    assert "status: human_approved" in card.read_text(encoding="utf-8")


def test_review_weekly_outputs_learning_tasks_and_bridge(tmp_path: Path) -> None:
    """review weekly 应像学习任务清单，同时仍只读 frontmatter 安全字段。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    overdue = (datetime.now().astimezone() - timedelta(days=1)).isoformat()
    _write_card(cards, "review-card", {
        "id": "review-card",
        "title": "Review card",
        "status": "human_approved",
        "track": "agent-runtime",
        "review_after": overdue,
        "last_review_result": "partial",
    })

    res = runner.invoke(app, ["review", "weekly", "--config", str(cfg)])

    assert res.exit_code == 0, res.output
    assert "Learning tasks" in res.output
    assert "overdue" in res.output
    assert "Workflow bridge" in res.output
    assert "review 只使用 human_approved" in res.output
    assert "不**调用 LLM" in res.output


def test_recall_hit_and_no_hit_include_next_actions(tmp_path: Path) -> None:
    """recall 是只读检索，但命中/空结果都应把用户带回学习闭环。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(
        cards,
        "agent-card",
        {
            "id": "agent-card",
            "title": "Agent runtime card",
            "status": "human_approved",
            "track": "agent-runtime",
            "value_score": 7,
        },
        body="## AI Summary\nagent runtime checkpoint\n",
    )

    hit = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "agent"])
    assert hit.exit_code == 0, hit.output
    assert "review weekly" in hit.output
    assert "手动 approve" in hit.output

    miss = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "zzzz-no-hit"])
    assert miss.exit_code == 0, miss.output
    assert "index rebuild" in miss.output
    assert "approve list" in miss.output
    assert "继续 process" in miss.output


def test_approval_review_recall_no_env_network_or_obsidian_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.6.2 UX 命令只能读本地安全状态，不读 .env、不联网、不写 Obsidian。"""
    cfg = _make_vault(tmp_path)
    (tmp_path / ".env").write_text("SECRET=must-not-leak\n", encoding="utf-8")
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "draft-safe", {
        "id": "draft-safe",
        "title": "Draft safe",
        "status": "ai_draft",
    })

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("approve/review/recall 不应读取 .env")

    def _blocked_socket(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("approve/review/recall 不应联网")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr(socket, "socket", _blocked_socket)

    for args in (
        ["approve", "list", "--config", str(cfg)],
        ["review", "weekly", "--config", str(cfg)],
        ["recall", "--config", str(cfg), "--query", "agent"],
    ):
        res = runner.invoke(app, args)
        assert res.exit_code == 0, res.output
        assert "must-not-leak" not in res.output
    assert not (tmp_path / "vault" / "90-System" / "MindForge" / "Staging").exists()


def test_recall_search_ux_shows_query_rank_source_terms_and_boundary(tmp_path: Path) -> None:
    """v0.6.3: recall 命中结果要解释“搜到了什么、为什么、下一步”。

    测试通过真实 CLI 跑 BM25 路径，验证输出来自索引/卡片事实；这里不引入
    RAG/embedding，也不调用 LLM，只做本地词法检索的产品化展示。
    """
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(
        cards,
        "search-card",
        {
            "id": "search-card",
            "title": "Agent search checkpoint",
            "status": "human_approved",
            "track": "agent-runtime",
            "source_type": "plain_markdown",
        },
        body="## AI Summary\nagent checkpoint runtime\n",
    )

    res = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "agent", "--explain"])

    assert res.exit_code == 0, res.output
    assert "Search query: agent" in res.output
    assert "Index:" in res.output
    assert "rank=#1" in res.output
    assert "source=plain_markdown" in res.output
    assert "human_approved/approved knowledge" in res.output
    assert "terms=agent" in res.output
    assert "why" in res.output
    assert "review weekly" in res.output
    assert "local lexical recall only" in res.output
    assert "no RAG, no embedding, no LLM, no .env, no upload" in res.output


def test_recall_empty_state_reports_counts_and_recovery_actions(tmp_path: Path) -> None:
    """无结果时要基于本地卡片计数给出下一步，而不是只说 no match。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "approved", {
        "id": "approved",
        "title": "Approved memory",
        "status": "human_approved",
    })
    _write_card(cards, "draft", {
        "id": "draft",
        "title": "Draft memory",
        "status": "ai_draft",
    })

    res = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "zzzz-no-hit"])

    assert res.exit_code == 0, res.output
    assert "approved cards=1" in res.output
    assert "ai_draft=1" in res.output
    assert "index rebuild" in res.output
    assert "approve list" in res.output
    assert "继续 process" in res.output
    assert "换同义词" in res.output


def test_recall_missing_index_says_temporary_index_and_rebuild(tmp_path: Path) -> None:
    """索引缺失不是失败，但必须告诉用户本次用了临时索引并建议 rebuild。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "agent-card", {
        "id": "agent-card",
        "title": "Agent card",
        "status": "human_approved",
    })

    res = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "agent"])

    assert res.exit_code == 0, res.output
    assert "vault.root" in res.output
    assert "cards_dir" in res.output
    assert "temporary in-memory index" in res.output
    assert "suggest_rebuild=yes" in res.output


def test_recall_stale_disk_index_suggests_rebuild_after_card_change(tmp_path: Path) -> None:
    """approve/process 后卡片变化时，recall 要说明磁盘索引已 stale 并建议 rebuild。"""

    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "agent-card", {
        "id": "agent-card",
        "title": "Agent card",
        "status": "human_approved",
    })
    rebuild = runner.invoke(app, ["index", "rebuild", "--config", str(cfg)])
    assert rebuild.exit_code == 0, rebuild.output
    _write_card(cards, "new-agent-card", {
        "id": "new-agent-card",
        "title": "New Agent card",
        "status": "human_approved",
    })

    res = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "new"])

    assert res.exit_code == 0, res.output
    assert "source=memory-rebuilt-stale" in res.output
    assert "suggest_rebuild=yes" in res.output
    assert "index rebuild" in res.output


def test_recall_include_drafts_marks_draft_risk(tmp_path: Path) -> None:
    """--include-drafts 可以查看草稿，但输出必须标明 draft 风险。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "draft-agent", {
        "id": "draft-agent",
        "title": "Agent draft",
        "status": "ai_draft",
    })

    res = runner.invoke(
        app, ["recall", "--config", str(cfg), "--query", "agent", "--include-drafts"]
    )

    assert res.exit_code == 0, res.output
    assert "ai_draft/risky draft" in res.output
    assert "approved knowledge" not in res.output


def test_recall_search_ux_non_repo_cwd_and_no_env_or_obsidian_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """packaged-like recall smoke：显式 --config 时不依赖 repo cwd，也不读 .env。"""
    cfg = _make_vault(tmp_path)
    (tmp_path / ".env").write_text("SECRET=must-not-leak\n", encoding="utf-8")
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(cards, "agent-card", {
        "id": "agent-card",
        "title": "Agent non repo cwd",
        "status": "human_approved",
    })
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("recall 不应读取 .env")

    def _blocked_socket(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("recall 不应联网或调用远程 LLM")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr(socket, "socket", _blocked_socket)
    monkeypatch.chdir(run_dir)

    res = runner.invoke(app, ["recall", "--config", str(cfg), "--query", "agent"])

    assert res.exit_code == 0, res.output
    assert "Agent non repo cwd" in res.output
    assert "must-not-leak" not in res.output
    assert not (tmp_path / "vault" / "90-System" / "MindForge" / "Staging").exists()
    assert "RAG enabled" not in res.output
    assert "embedding enabled" not in res.output


def test_config_show_and_doctor_report_paths_and_safety(tmp_path: Path) -> None:
    """v0.6.4: config UX 要让用户知道当前会读写哪些本地路径。"""
    cfg = _make_vault(tmp_path)

    show = runner.invoke(app, ["config", "show", "--config", str(cfg)])
    assert show.exit_code == 0, show.output
    assert "MindForge config show" in show.output
    assert "vault.root" in show.output
    assert "active_provider: fake" in show.output
    assert "calls_real_llm" in show.output
    assert "False" in show.output

    doctor = runner.invoke(app, ["config", "doctor", "--config", str(cfg)])
    assert doctor.exit_code == 0, doctor.output
    assert "package assets" in doctor.output
    assert "llm policy" in doctor.output
    assert "config looks safe" in doctor.output


def test_config_missing_and_bad_yaml_are_actionable(tmp_path: Path) -> None:
    """配置缺失或 YAML 损坏时要给 next action，不输出 traceback。"""
    missing = runner.invoke(app, ["config", "doctor", "--config", str(tmp_path / "missing.yaml")])
    assert missing.exit_code == 2
    assert "config missing" in missing.output
    assert "config init" in missing.output

    bad = tmp_path / "bad.yaml"
    bad.write_text("vault: [unterminated\n", encoding="utf-8")
    res = runner.invoke(app, ["config", "doctor", "--config", str(bad)])
    assert res.exit_code == 2
    assert "config invalid" in res.output
    assert "fix YAML" in res.output


def test_config_init_defaults_real_dogfood_and_refuses_overwrite(tmp_path: Path) -> None:
    """config init 写真实 dogfood 默认配置，并默认拒绝覆盖用户文件。"""
    cfg = tmp_path / "mindforge.yaml"
    vault = tmp_path / "vault"

    dry = runner.invoke(app, ["config", "init", "--output", str(cfg), "--vault", str(vault), "--dry-run"])
    assert dry.exit_code == 0, dry.output
    assert "dry-run" in dry.output
    assert not cfg.exists()

    written = runner.invoke(app, ["config", "init", "--output", str(cfg), "--vault", str(vault)])
    assert written.exit_code == 0, written.output
    text = cfg.read_text(encoding="utf-8")
    assert "default_model: main" in text
    assert "active_profile:" not in text
    assert "profiles:" not in text
    assert "Do not put API keys in this YAML" in text
    assert str(vault.resolve()) in text

    second = runner.invoke(app, ["config", "init", "--output", str(cfg), "--vault", str(vault)])
    assert second.exit_code == 2
    assert "拒绝覆盖" in second.output


def test_setup_dry_run_and_config_show_from_non_repo_cwd_no_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """setup/config 是本地配置引导，不应读取 .env、联网或写 Obsidian。"""
    cfg = _make_vault(tmp_path)
    (tmp_path / ".env").write_text("SECRET=must-not-leak\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("config/setup 不应读取 .env")

    def _blocked_socket(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("config/setup 不应联网")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr(socket, "socket", _blocked_socket)
    monkeypatch.chdir(run_dir)

    show = runner.invoke(app, ["config", "show", "--config", str(cfg)])
    assert show.exit_code == 0, show.output
    assert "must-not-leak" not in show.output

    setup = runner.invoke(app, ["setup", "--config", str(run_dir / "new.yaml"), "--vault", str(tmp_path / "vault"), "--dry-run"])
    assert setup.exit_code == 0, setup.output
    assert "secrets stay in env/.env" in setup.output
    assert "no LLM call" in setup.output
    assert not (run_dir / "new.yaml").exists()
    assert not (tmp_path / "vault" / "90-System" / "MindForge" / "Staging").exists()


def test_dogfood_plan_lists_safe_copyable_loop() -> None:
    """v0.6.5: dogfood plan 是只读命令地图，不是自动 runner。"""
    res = runner.invoke(app, ["dogfood", "plan", "--vault", "/tmp/disposable-vault"])
    assert res.exit_code == 0, res.output
    for command, _note in _dogfood_command_snippets(Path("/tmp/disposable-vault")):
        assert command in res.output
    assert "disposable non-sensitive copy" in res.output
    assert "no .env" in res.output
    assert "no real LLM" in res.output
    assert "no Obsidian formal-note writes" in res.output
    assert "RAG enabled" not in res.output
    assert "plugin enabled" not in res.output


def test_approve_show_previews_frontmatter_without_approving_or_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """approve show 支撑 dogfooding 决策，但必须只读安全摘要。"""
    cfg = _make_vault(tmp_path)
    (tmp_path / ".env").write_text("SECRET=must-not-leak\n", encoding="utf-8")
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    card = cards / "dogfood-draft.md"
    _write_card(cards, "dogfood-draft", {
        "id": "dogfood-draft",
        "title": "Dogfood Draft",
        "status": "ai_draft",
        "source_type": "plain_markdown",
    }, body="## AI Summary\nBODY_SECRET_SHOULD_NOT_PRINT\n")

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("approve show 不应读取 .env")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    res = runner.invoke(app, ["approve", "show", "--config", str(cfg), "--card", str(card)])

    assert res.exit_code == 0, res.output
    assert "Approve preview" in res.output
    assert "Dogfood Draft" in res.output
    assert "ai_draft" in res.output
    assert "preview only" in res.output
    assert "BODY_SECRET_SHOULD_NOT_PRINT" not in res.output
    assert "must-not-leak" not in res.output
    assert 'status: "ai_draft"' in card.read_text(encoding="utf-8")


def test_dogfooding_docs_and_checklist_exist_and_keep_boundaries() -> None:
    """README-first 文档必须强调非敏感、安全边界。"""
    root = Path(__file__).resolve().parent.parent
    doc = root / "README.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    for required in [
        "non-sensitive",
        "真实 LLM 只在你配置 `MINDFORGE_LLM_API_KEY`",
        "No RAG / embedding",
        "No Obsidian plugin",
        "No automatic approve",
        "mindforge status",
        "mindforge obsidian stage",
    ]:
        assert required in text


def test_v0_6_x_readiness_doc_exists_and_keeps_scope() -> None:
    """README-first 文档不应宣称新大功能已实现。"""
    root = Path(__file__).resolve().parent.parent
    doc = root / "README.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    for boundary in (
        "Real LLM enabled by default",
        "does not print `.env` secret values",
        "No formal Obsidian note writes",
        "RAG / embedding",
        "Obsidian plugin",
    ):
        assert boundary in text
    for forbidden in (
        "RAG is implemented",
        "embedding search is implemented",
        "Obsidian plugin is implemented",
        "real LLM default path is implemented",
    ):
        assert forbidden not in text


def test_backup_export_writes_safe_files_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.5.5: backup export 只导出安全摘要，不复制正文 secret，也不覆盖旧备份。"""
    cfg = _make_vault(tmp_path)
    cards = tmp_path / "vault" / "20-Knowledge-Cards"
    _write_card(
        cards,
        "approved",
        {"id": "approved", "title": "Approved", "status": "human_approved", "track": "agent-runtime"},
        body="## AI Summary\nBODY_SECRET_SHOULD_NOT_EXPORT\n",
    )
    _write_card(
        cards,
        "draft-secret",
        {"id": "draft-secret", "title": "DRAFT_SECRET_SHOULD_NOT_EXPORT", "status": "ai_draft"},
    )
    out_dir = tmp_path / "backup"

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("backup export 不应读取 .env")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    res = runner.invoke(app, ["backup", "export", "--config", str(cfg), "--output-dir", str(out_dir)])
    assert res.exit_code == 0, res.output
    assert (out_dir / "manifest.json").exists()
    exported = "\n".join(p.read_text(encoding="utf-8") for p in out_dir.glob("*.json"))
    assert "Approved" in exported
    assert "BODY_SECRET_SHOULD_NOT_EXPORT" not in exported
    assert "DRAFT_SECRET_SHOULD_NOT_EXPORT" not in exported
    assert ".env" not in exported

    second = runner.invoke(app, ["backup", "export", "--config", str(cfg), "--output-dir", str(out_dir)])
    assert second.exit_code == 2
    assert "拒绝覆盖" in second.output


def test_backup_export_works_from_non_repo_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """packaged-like smoke：backup export 不能依赖 repo cwd。"""
    cfg = _make_vault(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)

    res = runner.invoke(app, ["backup", "export", "--config", str(cfg), "--output-dir", "backup-out"])
    assert res.exit_code == 0, res.output
    assert (run_dir / "backup-out" / "manifest.json").exists()


def test_doctor_plus_reports_recovery_actions_and_paths(tmp_path: Path) -> None:
    """doctor plus 应给恢复检查和路径边界，帮助用户判断会读写哪里。"""
    cfg = _make_vault(tmp_path)
    res = runner.invoke(app, ["doctor", "--config", str(cfg), "--paths"])
    assert res.exit_code == 0, res.output
    assert "Recovery checks" in res.output
    assert "state.json" in res.output
    assert "bm25 index" in res.output
    assert "package assets" in res.output
    assert "Data safety paths" in res.output
    assert "writes backups" in res.output
    assert "index rebuild" in res.output or "mindforge scan" in res.output


def test_doctor_plus_no_env_network_or_obsidian_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """doctor plus 只读本地状态：不读 .env、不联网、不写 Obsidian 正式 notes。"""
    cfg = _make_vault(tmp_path)
    (tmp_path / ".env").write_text("SECRET=must-not-leak\n", encoding="utf-8")

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("doctor 不应读取 .env")

    def _blocked_socket(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("doctor 不应联网")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr(socket, "socket", _blocked_socket)
    res = runner.invoke(app, ["doctor", "--config", str(cfg), "--paths"])
    assert res.exit_code == 0, res.output
    assert "must-not-leak" not in res.output
    assert not (tmp_path / "vault" / "90-System" / "MindForge" / "Staging").exists()


def test_post_command_vault_normalization_keeps_cli_boundaries() -> None:
    """v0.5.1: 自然写法只对普通命令搬动，不能偷走 init/obsidian 的局部参数。"""
    assert _normalize_post_command_global_options(
        ["mindforge", "next", "--format", "json", "--vault", "examples/demo-vault"]
    ) == [
        "mindforge",
        "--vault",
        "examples/demo-vault",
        "next",
        "--format",
        "json",
    ]

    init_argv = ["mindforge", "init", "--vault", "/tmp/vault"]
    obsidian_argv = ["mindforge", "obsidian", "scan", "--vault", "/tmp/obsidian"]
    assert _normalize_post_command_global_options(init_argv) == init_argv
    assert _normalize_post_command_global_options(obsidian_argv) == obsidian_argv


def test_next_does_not_read_env_or_call_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """next 必须无网络、无 .env 读取。"""
    cfg = _make_vault(tmp_path)
    # 写一个假 .env 但确保 next 不读它内容
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=secret-must-not-leak\n", encoding="utf-8")

    # 拦截 HTTP（通过禁用 socket）
    import socket as _socket

    def _no_socket(*a, **kw):  # pragma: no cover - 只在被违规调用时触发
        raise RuntimeError("next 不应发起 socket 调用")

    monkeypatch.setattr(_socket, "socket", _no_socket)

    res = runner.invoke(app, ["next", "--config", str(cfg)])
    assert res.exit_code == 0
    assert "secret-must-not-leak" not in res.output
    assert "ANTHROPIC_API_KEY" not in res.output


# ===========================================================================
# SourceAdapter 架构稳定性
# ===========================================================================
def test_adapter_registry_includes_all_v041_adapters() -> None:
    """v0.4.2 的 6 个内置 adapter 必须都注册。"""
    expected = {
        "CuboxMarkdownAdapter",
        "PlainMarkdownAdapter",
        "WebClipMarkdownAdapter",
        "PdfAdapter",
        "DocxAdapter",
        "ChatExportAdapter",
    }
    assert expected <= set(_BUILTIN_ADAPTERS.keys())


def test_adapter_registry_can_build_from_config(tmp_path: Path) -> None:
    cfg_path = _make_vault(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    adapters = build_active_adapters(cfg.sources)
    assert "plain_markdown" in adapters
    a = adapters["plain_markdown"]
    assert isinstance(a, SourceAdapter)
    assert a.source_type == "plain_markdown"


def test_scanner_backfills_adapter_name(tmp_path: Path) -> None:
    """Scanner 必须把 adapter_name 写到 SourceDocument 上，便于追溯。"""
    cfg_path = _make_vault(tmp_path)
    inbox = tmp_path / "vault" / "00-Inbox" / "ManualNotes"
    (inbox / "demo.md").write_text("# Demo\n\nbody\n", encoding="utf-8")

    cfg = load_mindforge_config(cfg_path)
    scanner = Scanner(cfg)
    results = scanner.scan_all()
    assert len(results) == 1
    assert results[0].ok
    doc = results[0].document
    assert doc is not None
    assert doc.adapter_name  # 已被 Scanner 回填
    assert "Adapter" in doc.adapter_name


def test_source_document_is_immutable_contract() -> None:
    """SourceDocument 是 frozen dataclass — 下游加工无法私改其内容。"""
    doc = SourceDocument(
        source_id="x",
        source_type="plain_markdown",
        source_path="/a/b.md",
        raw_text="hello",
        content_hash=compute_content_hash("hello"),
    )
    with pytest.raises(Exception):
        doc.raw_text = "tampered"  # type: ignore[misc]


def test_demo_vault_exists_and_has_minimum_assets() -> None:
    """examples/demo-vault/ 必须存在且包含最小资产，供文档与 smoke 引用。"""
    root = Path(__file__).resolve().parent.parent / "examples" / "demo-vault"
    assert root.exists(), "examples/demo-vault/ 必须存在"
    assert (root / "README.md").exists()
    assert (root / "00-Inbox" / "Cubox").is_dir()
    assert (root / "00-Inbox" / "WebClips").is_dir()
    assert (root / "00-Inbox" / "ChatExports").is_dir()
    assert (root / "30-Projects" / "my-first-agent.md").exists()
    cards = list((root / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) >= 2


def test_demo_vault_does_not_contain_secrets() -> None:
    """demo vault 必须不含任何 secret 关键字 / 真实 token / .env。"""
    root = Path(__file__).resolve().parent.parent / "examples" / "demo-vault"
    forbidden = ["sk-ant-", "sk-proj-", "Bearer ", "ANTHROPIC_API_KEY=", "OPENAI_API_KEY="]
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name == ".env":
            raise AssertionError("demo vault 不能含 .env")
        text = p.read_text(encoding="utf-8", errors="ignore")
        for f in forbidden:
            assert f not in text, f"{p} 含敏感片段 {f!r}"
