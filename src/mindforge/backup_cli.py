"""Local backup CLI adapter.

导出只包含 human_approved card metadata、state counters 与 review schedule；
不读取 .env、不复制 source 原文、不上传 telemetry。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import typer

from .checkpoint import Checkpoint
from .cli_cards import card_to_safe_dict as _card_to_safe_dict
from .cli_cards import write_json as _write_json
from .cli_runtime import console, load_cfg

backup_app = typer.Typer(add_completion=False, help="本地备份 / 导出 / 恢复检查（不上传、不读 .env）")

# ---------------------------------------------------------------------------
# backup — v0.5.5 local export / recovery safety
# ---------------------------------------------------------------------------


@backup_app.command("export")
def backup_export(
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="备份输出目录；默认 .mindforge/backups/<timestamp>。",
    ),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """导出本地安全备份：已审核卡片摘要、state summary、review schedule。

    中文学习型说明：v0.5.5 的 backup/export 是恢复辅助，不是云同步。它只导出
    Knowledge Card frontmatter 白名单摘要和本地状态计数，不读取 `.env`，不复制
    source 原文、不上传 telemetry，也不会覆盖已存在备份目录。
    """
    from .cards import filter_cards, iter_cards

    cfg = load_cfg(config, read_env=False)
    now = datetime.now().astimezone()
    if output_dir is None:
        safe_ts = now.isoformat(timespec="seconds").replace(":", "-")
        target = cfg.state.workdir / "backups" / f"mindforge-backup-{safe_ts}"
    else:
        target = output_dir.expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target
    target = target.resolve()
    if target.exists():
        console.print(f"[red]✗ 备份目录已存在，拒绝覆盖：{target}[/red]")
        console.print("[dim]下一步：换一个 --output-dir，或先人工检查旧备份。[/dim]")
        raise typer.Exit(code=2)
    target.mkdir(parents=True)

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved = filter_cards(scan.cards, status="human_approved")
    cards_payload = [_card_to_safe_dict(card) for card in approved]

    state_payload: dict[str, object]
    if cfg.state.state_path.exists():
        try:
            cp = Checkpoint.load(cfg.state.state_path, backup=False)
            state_payload = {
                "state_path": str(cfg.state.state_path),
                "exists": True,
                "count_by_status": cp.count_by_status(),
                "count_by_source_type": cp.count_by_source_type(),
            }
        except Exception as e:  # noqa: BLE001 - 只导出错误类别，不输出原始 state 内容
            state_payload = {
                "state_path": str(cfg.state.state_path),
                "exists": True,
                "error": f"{type(e).__name__}: {e}",
            }
    else:
        state_payload = {"state_path": str(cfg.state.state_path), "exists": False}

    schedule_payload = _build_review_schedule_export(approved, generated_at=now, days=7)
    manifest = {
        "version": 1,
        "generated_at": now.isoformat(timespec="seconds"),
        "vault_root": str(cfg.vault.root),
        "files": {
            "human_approved_cards": "human_approved_cards.json",
            "state_summary": "state_summary.json",
            "review_schedule": "review_schedule.json",
        },
        "safety": {
            "contains_env": False,
            "contains_source_raw_text": False,
            "contains_prompt_or_completion": False,
            "uploads_telemetry": False,
        },
    }

    _write_json(target / "manifest.json", manifest)
    _write_json(target / "human_approved_cards.json", {"count": len(cards_payload), "items": cards_payload})
    _write_json(target / "state_summary.json", state_payload)
    _write_json(target / "review_schedule.json", schedule_payload)
    (target / "README.md").write_text(
        "# MindForge Local Backup\n\n"
        "This backup contains safe summaries only: human_approved card metadata, "
        "state counters, and a local review schedule. It does not contain `.env`, "
        "source raw text, prompt/completion logs, telemetry upload data, or Obsidian formal-note writes.\n",
        encoding="utf-8",
    )

    console.print(f"[green]✓ backup exported[/green] {target}")
    console.print(f"  human_approved cards: {len(cards_payload)}")
    console.print("  files: manifest.json, human_approved_cards.json, state_summary.json, review_schedule.json")
    console.print("[dim]说明：未读取 .env，未上传 telemetry，未修改 Obsidian notes。[/dim]")


def _build_review_schedule_export(cards: list, *, generated_at: datetime, days: int) -> dict[str, object]:
    """构建安全 review schedule 导出，不写系统日历、不读取正文。"""
    horizon = generated_at + timedelta(days=days)
    by_day: dict[str, list[dict[str, object]]] = {}
    for card in cards:
        if card.review_after is None:
            continue
        due_at = card.review_after if card.review_after.tzinfo else card.review_after.replace(tzinfo=generated_at.tzinfo)
        if due_at <= generated_at:
            key = generated_at.date().isoformat()
        elif due_at <= horizon:
            key = due_at.date().isoformat()
        else:
            continue
        by_day.setdefault(key, []).append(_card_to_safe_dict(card))
    return {
        "version": 1,
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "horizon_days": days,
        "total": sum(len(items) for items in by_day.values()),
        "days": [{"date": day, "count": len(items), "items": items} for day, items in sorted(by_day.items())],
    }
