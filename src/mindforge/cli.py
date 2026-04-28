"""mindforge — 命令行入口（typer）。

v0.1 / M1 阶段实现的命令：
- ``mindforge scan``    — 扫描 inbox，派发到 adapter，更新 state.json；不调 LLM。
- ``mindforge status``  — 打印 state.json 的状态汇总（按 status / source_type）。

M2 才会加入 ``process``。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .checkpoint import Checkpoint
from .config import ConfigError, load_mindforge_config
from .models import ItemState
from .scanner import Scanner

app = typer.Typer(
    add_completion=False,
    help="MindForge — 多源接入的本地 AI 知识加工管线（v0.1）",
)
console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_cfg(config_path: Path) -> object:
    try:
        return load_mindforge_config(config_path)
    except ConfigError as e:
        console.print(f"[red]配置错误：{e}[/red]")
        raise typer.Exit(code=2) from e


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


@app.command()
def scan(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    write_state: bool = typer.Option(
        True,
        "--write-state/--no-write-state",
        help="是否把扫描结果写入 state.json（默认写入）",
    ),
) -> None:
    """扫描 inbox 目录，把每个文件解析为 SourceDocument 并登记到 state.json。"""
    cfg = _load_cfg(config)
    scanner = Scanner(cfg)  # type: ignore[arg-type]
    cp = Checkpoint.load(cfg.state.state_path, backup=cfg.state.backup_state)  # type: ignore[attr-defined]

    seen = 0
    new_or_changed = 0
    failed = 0
    table = Table(title="MindForge scan", show_lines=False)
    table.add_column("source_type")
    table.add_column("path", overflow="fold")
    table.add_column("status")
    table.add_column("hash", overflow="fold")

    for result in scanner.iter_results():
        seen += 1
        if not result.ok:
            failed += 1
            table.add_row(result.source_type, str(result.path), "[red]failed[/red]", result.error or "")
            continue

        doc = result.document
        assert doc is not None
        candidate = ItemState(
            source_id=doc.source_id,
            source_type=doc.source_type,
            adapter_name=result.adapter_name,
            source_path=doc.source_path,
            content_hash=doc.content_hash,
            first_seen_at=datetime.now(),
        )
        existing = cp.get(doc.source_type, doc.source_path)
        before_hash = existing.content_hash if existing else None
        merged = cp.upsert_seen(candidate)
        if before_hash != merged.content_hash or existing is None:
            new_or_changed += 1
            label = "[green]new/changed[/green]"
        else:
            label = "unchanged"
        table.add_row(doc.source_type, doc.source_path, label, doc.content_hash[:18] + "...")

    console.print(table)
    console.print(
        f"扫描完成：共 [bold]{seen}[/bold] 个文件，"
        f"新增/变更 [green]{new_or_changed}[/green]，失败 [red]{failed}[/red]"
    )

    if write_state:
        cp.save(active_profile=cfg.llm.active_profile)  # type: ignore[attr-defined]
        console.print(f"已写入 state.json → {cfg.state.state_path}")  # type: ignore[attr-defined]
    else:
        console.print("[yellow]--no-write-state：state.json 未写入[/yellow]")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@app.command()
def status(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
) -> None:
    """打印 state.json 的当前状态汇总。"""
    cfg = _load_cfg(config)
    cp = Checkpoint.load(cfg.state.state_path)  # type: ignore[attr-defined]

    items = list(cp.all_items())
    console.print(f"[bold]MindForge status[/bold] · active_profile={cp.active_profile or '(unset)'}")
    console.print(f"state.json: {cfg.state.state_path}")  # type: ignore[attr-defined]
    console.print(f"items 总数：{len(items)}")

    by_status = cp.count_by_status()
    by_source = cp.count_by_source_type()

    if not items:
        console.print("[yellow]state.json 为空。先运行 `mindforge scan`。[/yellow]")
        return

    t1 = Table(title="按 status 分布")
    t1.add_column("status")
    t1.add_column("count", justify="right")
    for k in sorted(by_status):
        t1.add_row(k, str(by_status[k]))
    console.print(t1)

    t2 = Table(title="按 source_type 分布")
    t2.add_column("source_type")
    t2.add_column("count", justify="right")
    for k in sorted(by_source):
        t2.add_row(k, str(by_source[k]))
    console.print(t2)

    # ai_draft 提醒（v0.1 反污染机制）
    drafts = [i for i in items if i.status == "processed"]
    if drafts:
        console.print(
            f"[yellow]提示：{len(drafts)} 张卡片仍处于 processed (ai_draft) 状态，"
            "审核后请把 frontmatter 的 status 改为 human_approved。[/yellow]"
        )


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
