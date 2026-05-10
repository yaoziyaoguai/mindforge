"""Scanner + registry 集成测试 + CLI 端到端冒烟测试。

构造一个临时 vault，放入 plain_markdown / cubox_markdown 文件，
跑 ``mindforge scan`` 与 ``mindforge status``，验证：
- state.json 被正确创建并包含两条记录；
- 重复 scan 同一未变更文件不会改 hash；
- status 命令能跑通且输出关键字段。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.checkpoint import Checkpoint
from mindforge.cli import app
from mindforge.config import load_mindforge_config
from mindforge.scanner import Scanner

runner = CliRunner()


def _build_vault(tmp_path: Path) -> tuple[Path, Path]:
    """创建一个临时 vault + configs/mindforge.yaml，返回 (config_path, vault_root)。"""
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox"
    (inbox / "ManualNotes").mkdir(parents=True)
    (inbox / "Cubox").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)

    (inbox / "ManualNotes" / "n1.md").write_text(
        "---\ntitle: n1\n---\nbody one\n", encoding="utf-8"
    )
    (inbox / "Cubox" / "c1.md").write_text(
        "---\ntitle: c1\nurl: https://x\n---\n# c1\nhello cubox\n",
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
            "enabled": ["cubox_markdown", "plain_markdown"],
            "registry": {
                "cubox_markdown": {
                    "adapter": "CuboxMarkdownAdapter",
                    "inbox_subdir": "Cubox",
                    "file_glob": "*.md",
                    "enabled": True,
                },
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
            "active_profile": "default",
            "profiles": {
                "default": {
                    "triage": "m",
                    "distill": "m",
                    "link_suggestion": "m",
                    "review_questions": "m",
                    "action_extraction": "m",
                }
            },
            "models": {
                "m": {
                    "provider": "p",
                    "type": "openai_compatible",
                    "base_url": "http://x",
                    "model": "m",
                    "timeout_seconds": 60,
                    "max_retries": 1,
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
    p = cfg_dir / "mindforge.yaml"
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return p, vault


def test_scanner_iterates_two_sources(tmp_path: Path) -> None:
    cfg_path, _ = _build_vault(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    scanner = Scanner(cfg)
    results = scanner.scan_all()
    assert len(results) == 2
    by_type = {r.source_type for r in results}
    assert by_type == {"cubox_markdown", "plain_markdown"}
    assert all(r.ok for r in results)


def test_scanner_handles_failed_adapter(tmp_path: Path) -> None:
    """删除文件后 adapter.load 抛 FileNotFoundError，应被收敛为 ScanResult.error。"""
    cfg_path, vault = _build_vault(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    scanner = Scanner(cfg)

    # 先扫描一遍拿到 adapter；然后构造一个不存在的路径直接调 _safe_load
    adapter = scanner.adapters["plain_markdown"]
    res = scanner._safe_load(adapter, "plain_markdown", Path("/tmp/__no__.md"))
    assert not res.ok
    assert "FileNotFoundError" in (res.error or "")


def test_cli_scan_then_status(tmp_path: Path) -> None:
    cfg_path, _ = _build_vault(tmp_path)

    # scan
    r1 = runner.invoke(app, ["scan", "--config", str(cfg_path)])
    assert r1.exit_code == 0, r1.output
    assert "扫描完成" in r1.output
    assert "新增/变更" in r1.output

    # state.json 已写入
    state_path = tmp_path / ".mindforge" / "state.json"
    assert state_path.exists()
    cp = Checkpoint.load(state_path)
    assert len(list(cp.all_items())) == 2
    assert cp.active_profile == "default"

    # 二次 scan：应全部 unchanged
    r2 = runner.invoke(app, ["scan", "--config", str(cfg_path)])
    assert r2.exit_code == 0, r2.output
    assert "新增/变更 [green]0[/green]" in r2.output or "新增/变更 0" in r2.output

    # status
    r3 = runner.invoke(app, ["status", "--config", str(cfg_path)])
    assert r3.exit_code == 0, r3.output
    assert "items 总数：2" in r3.output
    assert "raw" in r3.output
    assert "imported_file" in r3.output
    assert "plain_markdown" in r3.output
    # M1.5 新增：runs dir 与最近一次 run 摘要必须出现
    assert "runs dir" in r3.output
    assert "最近一次 run" in r3.output
    assert "run_id=" in r3.output
    assert "events=" in r3.output


def test_cli_scan_no_write_state(tmp_path: Path) -> None:
    cfg_path, _ = _build_vault(tmp_path)
    r = runner.invoke(app, ["scan", "--config", str(cfg_path), "--no-write-state"])
    assert r.exit_code == 0, r.output
    state_path = tmp_path / ".mindforge" / "state.json"
    assert not state_path.exists()


def test_cli_scan_bad_config(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("not: a valid config", encoding="utf-8")
    r = runner.invoke(app, ["scan", "--config", str(bad)])
    assert r.exit_code == 2
    assert "配置错误" in r.output


def _read_run_jsonl(runs_dir: Path) -> list[dict]:
    files = list(runs_dir.glob("*.jsonl"))
    assert files, f"no run jsonl found in {runs_dir}"
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return [json.loads(line) for line in latest.read_text("utf-8").splitlines() if line.strip()]


def test_cli_scan_writes_run_jsonl(tmp_path: Path) -> None:
    cfg_path, _ = _build_vault(tmp_path)
    runs_dir = tmp_path / ".mindforge" / "runs"

    # 第一次：两条 source_seen + 一条 state_written
    r1 = runner.invoke(app, ["scan", "--config", str(cfg_path)])
    assert r1.exit_code == 0, r1.output
    events = _read_run_jsonl(runs_dir)
    by_event = [e["event"] for e in events]
    assert by_event[0] == "run_started"
    assert by_event[-1] == "run_finished"
    assert by_event.count("source_seen") == 2
    assert by_event.count("state_written") == 1
    # 字段白名单：不应出现 raw_text / 文章正文
    flat = json.dumps(events, ensure_ascii=False)
    assert "raw_text" not in flat
    # 第一条带 command
    assert events[0]["command"] == "scan"
    # source_seen 携带必要字段
    seen = next(e for e in events if e["event"] == "source_seen")
    for f in ("source_id", "source_type", "adapter_name", "source_path", "content_hash", "status"):
        assert f in seen, f"missing field {f}"

    # 第二次：两条 source_skipped_or_unchanged
    r2 = runner.invoke(app, ["scan", "--config", str(cfg_path)])
    assert r2.exit_code == 0, r2.output
    events2 = _read_run_jsonl(runs_dir)
    by_event2 = [e["event"] for e in events2]
    assert by_event2.count("source_skipped_or_unchanged") == 2
    assert by_event2.count("source_seen") == 0


def test_cli_status_writes_run_jsonl(tmp_path: Path) -> None:
    cfg_path, _ = _build_vault(tmp_path)
    runs_dir = tmp_path / ".mindforge" / "runs"

    runner.invoke(app, ["scan", "--config", str(cfg_path)])
    r = runner.invoke(app, ["status", "--config", str(cfg_path)])
    assert r.exit_code == 0, r.output

    # 找出 command=status 的那份 jsonl（同秒生成时不能依赖排序）
    status_events: list[dict] | None = None
    for f in runs_dir.glob("*.jsonl"):
        events = [json.loads(line) for line in f.read_text("utf-8").splitlines() if line.strip()]
        if events and events[0].get("command") == "status":
            status_events = events
            break
    assert status_events is not None, "no status run jsonl found"
    statuses = [e for e in status_events if e["event"] == "status_reported"]
    assert len(statuses) == 1
    assert statuses[0]["items_count"] == 2
    assert "by_status" in statuses[0]["counts"]
    assert "by_source_type" in statuses[0]["counts"]
