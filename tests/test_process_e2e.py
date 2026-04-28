"""M2 端到端：mindforge process 把 inbox → Knowledge Card 写到 vault。

不依赖网络：用 fake provider 跑通五个 stage。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.checkpoint import Checkpoint
from mindforge.cli import app

runner = CliRunner()

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
TEMPLATE_PATH = REPO_ROOT / "templates" / "knowledge_card.md.j2"
TRACKS_PATH = REPO_ROOT / "configs" / "learning_tracks.yaml"


def _build_vault_with_fake_llm(tmp_path: Path) -> tuple[Path, Path, Path]:
    """构造 tmp vault + 配置（active_profile=fake），返回 (cfg, vault, source_file)。"""
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox"
    (inbox / "ManualNotes").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)

    src_file = inbox / "ManualNotes" / "n1.md"
    src_file.write_text(
        "---\ntitle: Agent Runtime 札记\ntags: [agent, runtime]\n---\n\n"
        "## 笔记正文\n\n这里写一些关于 agent runtime 的理解，包括 tool calling 与 checkpoint。\n",
        encoding="utf-8",
    )

    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    cfg = {
        "version": 0.1,
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
                },
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
    cfg_path = cfg_dir / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return cfg_path, vault, src_file


def _common_process_args(cfg_path: Path) -> list[str]:
    return [
        "process",
        "--config",
        str(cfg_path),
        "--prompts-dir",
        str(PROMPTS_DIR),
        "--tracks",
        str(TRACKS_PATH),
        "--template",
        str(TEMPLATE_PATH),
    ]


def test_process_writes_card_state_and_run_log(tmp_path: Path) -> None:
    cfg_path, vault, src_file = _build_vault_with_fake_llm(tmp_path)
    src_before = src_file.read_text("utf-8")

    r = runner.invoke(app, _common_process_args(cfg_path))
    assert r.exit_code == 0, r.output
    assert "processed=1" in r.output

    # ── 卡片落地到 vault/20-Knowledge-Cards/<track>/<...>.md ──
    cards_dir = vault / "20-Knowledge-Cards"
    cards = list(cards_dir.rglob("*.md"))
    assert len(cards) == 1, f"expected 1 card, got {cards}"
    card_text = cards[0].read_text("utf-8")
    # 默认 ai_draft，必须人工晋升 human_approved
    assert "status: ai_draft" in card_text
    # 关键 frontmatter 字段
    assert "source_id:" in card_text
    assert "source_type: plain_markdown" in card_text
    assert "adapter_name: PlainMarkdownAdapter" in card_text
    assert "prompt_version:" in card_text
    assert "run_id:" in card_text
    # 不能把 raw_text 整段塞进来；body 应来自 distill 的 source_excerpt（fake 占位）
    assert "[fake] excerpt placeholder" in card_text

    # ── 原始 source 文件 100% 不被改写 ──
    assert src_file.read_text("utf-8") == src_before

    # ── state.json 已写入并含 stages ──
    cp = Checkpoint.load(tmp_path / ".mindforge" / "state.json")
    items = list(cp.all_items())
    assert len(items) == 1
    item = items[0]
    assert item.status == "processed"
    assert item.track  # 应被填入
    assert item.value_score is not None
    assert item.card_path is not None and item.card_path.startswith("20-Knowledge-Cards/")
    assert item.last_run_id is not None
    assert set(item.stages) == {
        "triage",
        "distill",
        "link_suggestion",
        "review_questions",
        "action_extraction",
    }
    for sr in item.stages.values():
        assert sr.model_alias == "f1"
        assert sr.provider == "fake-local"
        assert sr.actual_model == "fake-1"
        assert sr.status == "ok"

    # ── runs/*.jsonl 含 5 条 llm_call + card_written + source_processed ──
    runs_dir = tmp_path / ".mindforge" / "runs"
    files = list(runs_dir.glob("*.jsonl"))
    assert len(files) == 1
    events = [json.loads(line) for line in files[0].read_text("utf-8").splitlines() if line.strip()]
    by_event = [e["event"] for e in events]
    assert by_event[0] == "run_started"
    assert by_event[-1] == "run_finished"
    assert by_event.count("llm_call") == 5
    assert by_event.count("card_written") == 1
    assert by_event.count("source_processed") == 1

    # ── 每条 llm_call 字段齐全且不含 raw_text ──
    llm_calls = [e for e in events if e["event"] == "llm_call"]
    for c in llm_calls:
        for f in (
            "stage",
            "model_alias",
            "provider",
            "actual_model",
            "prompt_version",
            "input_file_hash",
            "status",
        ):
            assert f in c, f"llm_call missing {f}"
        assert c["status"] == "ok"
    flat = json.dumps(events, ensure_ascii=False)
    assert "raw_text" not in flat
    # 不应把笔记正文（"checkpoint" 三字虽然是关键词但 fake 也产出 "checkpoint" 是无关的）
    # 这里检查：raw_text key 不应出现作为字段名
    for e in events:
        assert "raw_text" not in e


def test_process_filter_by_file(tmp_path: Path) -> None:
    cfg_path, vault, src_file = _build_vault_with_fake_llm(tmp_path)
    # 再加一份不会被处理的文件
    other = vault / "00-Inbox" / "ManualNotes" / "n2.md"
    other.write_text("---\ntitle: another\n---\nbody\n", encoding="utf-8")

    r = runner.invoke(
        app,
        _common_process_args(cfg_path) + ["--file", str(src_file)],
    )
    assert r.exit_code == 0, r.output
    assert "processed=1" in r.output
    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) == 1


def test_process_second_run_writes_conflict_file(tmp_path: Path) -> None:
    """同一 source 二次 process：run_id/created_at 不同 → 渲染内容不同 → 写 .conflict.md，
    原卡片不被覆盖。"""
    cfg_path, vault, _src = _build_vault_with_fake_llm(tmp_path)
    runner.invoke(app, _common_process_args(cfg_path))
    cards1 = sorted((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards1) == 1
    text1 = cards1[0].read_text("utf-8")

    runner.invoke(app, _common_process_args(cfg_path))
    # 原卡片内容保持不变
    assert cards1[0].read_text("utf-8") == text1
    # 多出一个 .conflict.md
    conflicts = list((vault / "20-Knowledge-Cards").rglob("*.conflict.md"))
    assert len(conflicts) == 1


def test_process_skipped_when_threshold_too_high(tmp_path: Path) -> None:
    cfg_path, vault, _ = _build_vault_with_fake_llm(tmp_path)
    # 把阈值改高到 fake 评分（7）以上
    raw = yaml.safe_load(cfg_path.read_text("utf-8"))
    raw["triage"]["value_score_threshold"] = 9
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    r = runner.invoke(app, _common_process_args(cfg_path))
    assert r.exit_code == 0, r.output
    assert "skipped=1" in r.output
    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert cards == []
    cp = Checkpoint.load(tmp_path / ".mindforge" / "state.json")
    item = next(iter(cp.all_items()))
    assert item.status == "skipped"
    assert "triage" in item.stages and item.stages["triage"].status == "ok"
