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
    assert "strategy_id: \"five_stage\"" in card_text
    assert "source_content_hash:" in card_text
    assert "prompt_versions:" in card_text
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


_FORBIDDEN_STATE_FIELDS = (
    "api_key",
    "Authorization",
    "x-api-key",
    "Bearer ",
    "raw_text",
    "prompt_text",
    "completion_text",
)

_FORBIDDEN_RUN_FIELDS = (
    *_FORBIDDEN_STATE_FIELDS,
    "request_body",
    "response_body",
)

_ALLOWED_LLM_CALL_FIELDS = {
    "ts",
    "run_id",
    "event",
    "stage",
    "model_alias",
    "provider",
    "provider_type",
    "actual_model",
    "prompt_version",
    "input_file_hash",
    "status",
    "error_message",
    "tokens_in",
    "tokens_out",
    "latency_ms",
}


def _isolate_fake_cli_path(tmp_path: Path, monkeypatch) -> None:
    """隔离端到端测试环境，证明 fake process 路径不依赖真实 env 或网络。

    这里是测试架构边界：CLI 可以读传入的临时 config，但不能从开发者机器
    的 ``.env`` 或 HTTP 出口获得隐式能力。
    """
    import httpx

    for k in list(__import__("os").environ.keys()):
        if k.startswith("MINDFORGE_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)

    def _no_http(*a, **kw):  # type: ignore[no-untyped-def]
        raise AssertionError("v0.1 fake 路径绝不应该发起 HTTP 请求")

    monkeypatch.setattr(httpx.Client, "post", _no_http, raising=True)


def _run_scan_process_status(cfg_path: Path):
    """执行用户可见的 scan → process → status 闭环。"""
    r_scan = runner.invoke(app, ["scan", "--config", str(cfg_path)])
    assert r_scan.exit_code == 0, r_scan.output

    r_proc = runner.invoke(app, _common_process_args(cfg_path))
    assert r_proc.exit_code == 0, r_proc.output
    assert "processed=1" in r_proc.output

    r_stat = runner.invoke(app, ["status", "--config", str(cfg_path)])
    assert r_stat.exit_code == 0, r_stat.output
    return r_scan, r_proc, r_stat


def _assert_ai_draft_card_contract(vault: Path) -> None:
    """验证写出的 Knowledge Card 仍是 ai_draft，不能越权成人工批准态。"""
    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) == 1
    card_text = cards[0].read_text("utf-8")
    assert card_text.startswith("---\n")
    fm_text = card_text.split("---\n", 2)[1]
    fm = yaml.safe_load(fm_text)
    assert isinstance(fm, dict)
    for required in (
        "id",
        "title",
        "status",
        "track",
        "tags",
        "value_score",
        "confidence",
        "strategy_id",
        "strategy_version",
        "schema_version",
        "source_id",
        "source_type",
        "adapter_name",
        "source_path",
        "source_content_hash",
        "created_at",
        "prompt_version",
        "prompt_versions",
        "profile",
        "stage_models",
        "run_id",
    ):
        assert required in fm, f"frontmatter 缺关键字段 {required!r}"
    assert fm["status"] == "ai_draft"
    assert fm["strategy_id"] == "five_stage"
    assert fm["strategy_version"]
    assert str(fm["schema_version"]) == "1"
    assert fm["source_type"] == "plain_markdown"
    assert isinstance(fm["source_content_hash"], str)
    assert len(fm["source_content_hash"]) >= 12
    # 中文学习型说明：prompt provenance 记录 stage -> version，不记录完整
    # prompt 文本。这样新卡可追踪生成材料，同时不会把 prompt asset 塞进卡片。
    assert fm["prompt_versions"] == {
        "triage": "v1",
        "distill": "v1",
        "link_suggestion": "v1",
        "review_questions": "v1",
        "action_extraction": "v1",
    }
    assert isinstance(fm["stage_models"], dict) and len(fm["stage_models"]) == 5


def _assert_forbidden_terms_absent(text: str, forbidden_terms: tuple[str, ...], context: str) -> None:
    """统一检查持久化产物没有泄漏 prompt、completion、raw_text 或密钥字段。"""
    for forbidden in forbidden_terms:
        assert forbidden not in text, f"{context} 含禁字段 {forbidden!r}（v0.1 反泄漏约束）"


def _assert_run_log_safety(runs_dir: Path) -> None:
    """runs jsonl 只允许记录安全元数据，不保存请求/响应正文。"""
    files = list(runs_dir.glob("*.jsonl"))
    assert len(files) >= 1
    flat = "\n".join(f.read_text("utf-8") for f in files)
    _assert_forbidden_terms_absent(flat, _FORBIDDEN_RUN_FIELDS, "runs/*.jsonl")

    for f in files:
        for line in f.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") != "llm_call":
                continue
            extra = set(event) - _ALLOWED_LLM_CALL_FIELDS
            assert not extra, f"llm_call 含白名单外字段 {extra}（v0.1 反泄漏约束）"


def test_v0_1_stop_rule_safety_guarantees(
    tmp_path: Path,
    monkeypatch: "pytest.MonkeyPatch",  # noqa: F821
) -> None:
    """v0.1 收口（§7 停手规则）安全契约的端到端验证。

    本测试是 v0.1.0-rc1 的核心质量门：必须证明 fake provider 路径下整条
    pipeline 既能完整跑通（scan → process → status → 写卡 → 写 state →
    写 runs jsonl），又不会泄漏任何敏感字段、不会触发真实网络、也不需要
    任何 .env 变量。任何一条断言失败都意味着 v0.1 停手规则被破坏，
    rc1 不应发布。
    """
    _isolate_fake_cli_path(tmp_path, monkeypatch)
    cfg_path, vault, src_file = _build_vault_with_fake_llm(tmp_path)
    src_md5_before = src_file.read_text("utf-8")

    _run_scan_process_status(cfg_path)

    assert src_file.read_text("utf-8") == src_md5_before, (
        "v0.1 硬约束：原始 source 文件不可被改写"
    )
    _assert_ai_draft_card_contract(vault)

    state_text = (tmp_path / ".mindforge" / "state.json").read_text("utf-8")
    _assert_forbidden_terms_absent(state_text, _FORBIDDEN_STATE_FIELDS, "state.json")
    _assert_run_log_safety(tmp_path / ".mindforge" / "runs")
