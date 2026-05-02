"""Cubox command adapter — `mindforge cubox ...` 子命令。

中文学习型说明
==============

本模块是 **CLI adapter**，不是 service。它持有 Typer/Rich，因为职责就是
定义子命令、解析参数、调用既有 ``CuboxApiAdapter.parse_export`` 与
``SourceMux``、并把结果交给 ``cubox_dryrun_presenter`` 渲染。

为什么独立成文件而不放进 ``cli.py``
-----------------------------------

``cli.py`` 是 thin orchestrator，与 ``processor / pipeline / scanner /
source_mux`` 之间有明确的反向依赖守护（见
``test_core_modules_do_not_hardcode_cubox`` /
``test_cli_does_not_import_mux_in_default_path``）。Cubox dry-run 是一个
**新的 opt-in use-case 入口**，它合法地需要 import ``cubox_api`` 与
``source_mux`` —— 把它放在独立 adapter 模块，可以让既有 AST 边界继续
守护 ``cli.py`` 的"默认路径无 source-specific 依赖"约定，而不必松动它。

设计原则
--------

- **薄 adapter**：只编排 ``parse_export`` + ``SourceMux.feed`` + presenter；
- **复用既有结构**：mapping 走 adapter，去重走 mux，不重写；
- **零网络/零 .env/零 LLM/零 vault 写入**：本命令永远不调真实 Cubox API、
  不读 ``.env``、不生成 ai_draft / human_approved、不写 Obsidian。
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from .cubox_dryrun_presenter import (
    DryRunSampleItem,
    DryRunSummary,
    render_json,
    render_text,
)
from .scanner import ScanResult
from .source_mux import SourceMux
from .sources.cubox_api import CuboxApiAdapter

console = Console()

cubox_app = typer.Typer(
    add_completion=False,
    help="Cubox 本地 export 预检（不联网、不调 API、不写 vault）",
)


@cubox_app.command("dry-run")
def cubox_dry_run(
    export: Path = typer.Option(
        ..., "--export", help="本地 Cubox JSON export 文件路径"
    ),
    limit: int = typer.Option(3, "--limit", help="sample 标题最多展示条数", min=0),
    json_out: bool = typer.Option(False, "--json", help="输出机器可读 JSON 一行"),
) -> None:
    """对一个本地 Cubox JSON export 文件做去重预检，仅打印 summary。

    永不调用真实 Cubox API、不读 .env、不调 LLM、不写 Obsidian vault、
    不生成 ai_draft、不生成 human_approved。
    """

    if not export.exists():
        console.print(f"[red]Cubox export 文件不存在：{export}[/red]")
        raise typer.Exit(code=2)

    adapter = CuboxApiAdapter()
    try:
        docs = adapter.parse_export(export)
    except json.JSONDecodeError as exc:
        console.print(
            f"[red]Cubox export JSON 解析失败：{export}"
            f"（{exc.msg} @ line {exc.lineno}）[/red]"
        )
        raise typer.Exit(code=2) from exc
    except ValueError as exc:
        console.print(f"[red]Cubox export 内容非法：{exc}[/red]")
        raise typer.Exit(code=2) from exc

    mux = SourceMux()
    yielded_docs = []
    by_source: dict[str, int] = {}
    for d in docs:
        kept = mux.feed(
            ScanResult(
                source_type=d.source_type,
                adapter_name=adapter.name,
                path=export,
                document=d,
            )
        )
        if kept is not None and kept.document is not None:
            yielded_docs.append(kept.document)
            by_source[kept.source_type] = by_source.get(kept.source_type, 0) + 1

    sample = [
        DryRunSampleItem(
            title=d.title,
            source_id_short=d.source_id.split(":", 1)[-1][:12],
        )
        for d in yielded_docs[:limit]
    ]
    summary = DryRunSummary(
        items_seen=len(docs),
        yielded=len(yielded_docs),
        deduped=mux.stats.deduped,
        by_source=by_source,
        sample=sample,
    )

    if json_out:
        typer.echo(render_json(summary))
    else:
        typer.echo(render_text(summary))


__all__ = ["cubox_app"]
