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
from .llm import LLMClient, build_providers
from .models import ItemState, StageRecord
from .processors import Pipeline
from .run_logger import (
    EVENT_SOURCE_ERROR,
    EVENT_SOURCE_SEEN,
    EVENT_SOURCE_SKIPPED_OR_UNCHANGED,
    EVENT_STATE_WRITTEN,
    EVENT_STATUS_REPORTED,
    RunLogger,
    summarize_latest_run,
)
from .scanner import Scanner
from .writer import CardWriter

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

    with RunLogger(cfg.state.runs_path, command="scan") as logger:  # type: ignore[attr-defined]
        for result in scanner.iter_results():
            seen += 1
            if not result.ok:
                failed += 1
                table.add_row(
                    result.source_type,
                    str(result.path),
                    "[red]failed[/red]",
                    result.error or "",
                )
                logger.emit(
                    EVENT_SOURCE_ERROR,
                    source_type=result.source_type,
                    adapter_name=result.adapter_name,
                    path=str(result.path),
                    error_message=result.error or "",
                )
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
            changed = before_hash != merged.content_hash or existing is None
            if changed:
                new_or_changed += 1
                label = "[green]new/changed[/green]"
                logger.emit(
                    EVENT_SOURCE_SEEN,
                    source_id=merged.source_id,
                    source_type=merged.source_type,
                    adapter_name=merged.adapter_name,
                    source_path=merged.source_path,
                    content_hash=merged.content_hash,
                    status=merged.status,
                )
            else:
                label = "unchanged"
                logger.emit(
                    EVENT_SOURCE_SKIPPED_OR_UNCHANGED,
                    source_id=merged.source_id,
                    source_type=merged.source_type,
                    adapter_name=merged.adapter_name,
                    source_path=merged.source_path,
                    content_hash=merged.content_hash,
                    status=merged.status,
                )
            table.add_row(doc.source_type, doc.source_path, label, doc.content_hash[:18] + "...")

        console.print(table)
        console.print(
            f"扫描完成：共 [bold]{seen}[/bold] 个文件，"
            f"新增/变更 [green]{new_or_changed}[/green]，失败 [red]{failed}[/red]"
        )

        if write_state:
            cp.save(active_profile=cfg.llm.active_profile)  # type: ignore[attr-defined]
            console.print(f"已写入 state.json → {cfg.state.state_path}")  # type: ignore[attr-defined]
            logger.emit(
                EVENT_STATE_WRITTEN,
                path=str(cfg.state.state_path),  # type: ignore[attr-defined]
                items_count=len(list(cp.all_items())),
            )
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
    by_status = cp.count_by_status()
    by_source = cp.count_by_source_type()

    with RunLogger(cfg.state.runs_path, command="status") as logger:  # type: ignore[attr-defined]
        logger.emit(
            EVENT_STATUS_REPORTED,
            path=str(cfg.state.state_path),  # type: ignore[attr-defined]
            items_count=len(items),
            counts={"by_status": dict(by_status), "by_source_type": dict(by_source)},
            active_profile=cp.active_profile or "",
        )

    console.print(f"[bold]MindForge status[/bold] · active_profile={cp.active_profile or '(unset)'}")
    console.print(f"state.json: {cfg.state.state_path}")  # type: ignore[attr-defined]
    console.print(f"runs dir : {cfg.state.runs_path}")  # type: ignore[attr-defined]
    console.print(f"items 总数：{len(items)}")

    # 最近一次 run 摘要（非敏感字段）
    summary = summarize_latest_run(cfg.state.runs_path)  # type: ignore[attr-defined]
    if summary is None:
        console.print("[yellow]最近一次 run：(无)[/yellow]")
    else:
        flag = "[red]failed[/red]" if summary.failed else "[green]ok[/green]"
        console.print(
            f"最近一次 run · {flag} · cmd=[bold]{summary.command or '?'}[/bold] · "
            f"run_id={summary.run_id} · events={summary.event_count} · "
            f"started={summary.started_at} · last={summary.last_event}@{summary.last_event_at}"
        )
        console.print(f"  log: {summary.path}")

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


# ---------------------------------------------------------------------------
# process — M2 主入口：跑五 stage + 写 Card
# ---------------------------------------------------------------------------


@app.command()
def process(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="只处理该单文件（绝对或相对 vault 的路径）",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="本次最多处理多少条",
    ),
    prompts_dir: Path = typer.Option(
        Path("prompts"),
        "--prompts-dir",
        help="prompts 根目录",
    ),
    tracks: Path = typer.Option(
        Path("configs/learning_tracks.yaml"),
        "--tracks",
        help="learning_tracks.yaml 路径（作为 triage prompt 的上下文）",
    ),
    template: Path = typer.Option(
        Path("templates/knowledge_card.md.j2"),
        "--template",
        help="Knowledge Card 模板路径",
    ),
) -> None:
    """对 inbox 中已 scan 的文件跑 5 stage pipeline，落地 Knowledge Card。

    硬约束：原始 source 文件不被改写；卡片默认 ``status: ai_draft``，
    必须人工修改 frontmatter 才晋升 ``human_approved``。
    """
    cfg = _load_cfg(config)
    scanner = Scanner(cfg)  # type: ignore[arg-type]
    cp = Checkpoint.load(cfg.state.state_path, backup=cfg.state.backup_state)  # type: ignore[attr-defined]

    providers = build_providers(cfg.llm)  # type: ignore[attr-defined]
    client = LLMClient(llm_config=cfg.llm, providers=providers)  # type: ignore[attr-defined]

    # 模板路径
    template_path = template
    writer = CardWriter(
        vault_root=cfg.vault.root,  # type: ignore[attr-defined]
        cards_dir=cfg.vault.cards_dir,  # type: ignore[attr-defined]
        template_path=template_path,
    )

    tracks_text = tracks.read_text("utf-8") if tracks.exists() else ""
    pipeline = Pipeline(
        client=client,
        logger=None,  # type: ignore[arg-type]  # 暂占；下面 with 块内重设
        prompts_dir=prompts_dir,
        prompt_versions=cfg.prompts,  # type: ignore[attr-defined]
        triage_threshold=cfg.triage.value_score_threshold,  # type: ignore[attr-defined]
        learning_tracks_text=tracks_text,
    )

    counts = {"processed": 0, "skipped": 0, "failed": 0, "seen": 0}

    with RunLogger(cfg.state.runs_path, command="process") as logger:  # type: ignore[attr-defined]
        pipeline.logger = logger
        for result in scanner.iter_results():
            if file is not None and Path(result.path).resolve() != file.resolve():
                continue
            counts["seen"] += 1
            if not result.ok:
                counts["failed"] += 1
                logger.emit(
                    EVENT_SOURCE_ERROR,
                    source_type=result.source_type,
                    adapter_name=result.adapter_name,
                    path=str(result.path),
                    error_message=result.error or "",
                )
                continue

            doc = result.document
            assert doc is not None

            # 把 source 登记到 checkpoint（沿用 scan 的 upsert 语义）
            candidate = ItemState(
                source_id=doc.source_id,
                source_type=doc.source_type,
                adapter_name=result.adapter_name,
                source_path=doc.source_path,
                content_hash=doc.content_hash,
                first_seen_at=datetime.now(),
            )
            item = cp.upsert_seen(candidate)

            outcome = pipeline.run(doc)

            now = datetime.now()
            item.status = outcome.status  # type: ignore[assignment]
            item.last_run_id = logger.run_id
            item.processed_at = now
            item.error_message = outcome.error_message
            for stage_name, meta in outcome.stages_meta.items():
                item.stages[stage_name] = StageRecord(
                    stage=stage_name,  # type: ignore[arg-type]
                    model_alias=meta["model_alias"],
                    provider=meta["provider"],
                    actual_model=meta["actual_model"],
                    prompt_version=meta["prompt_version"],
                    status=meta["status"],
                    processed_at=now,
                    tokens_in=meta.get("tokens_in"),
                    tokens_out=meta.get("tokens_out"),
                    latency_ms=meta.get("latency_ms"),
                )

            if outcome.status == "skipped":
                counts["skipped"] += 1
                triage_parsed = outcome.triage.parsed if outcome.triage else {}
                item.track = triage_parsed.get("track")
                item.value_score = triage_parsed.get("value_score")
                logger.emit(
                    "source_processed",
                    source_id=doc.source_id,
                    source_type=doc.source_type,
                    adapter_name=result.adapter_name,
                    source_path=doc.source_path,
                    content_hash=doc.content_hash,
                    status="skipped",
                    track=item.track or "",
                    value_score=item.value_score or 0,
                    skip_reason=outcome.skip_reason or "",
                )
                console.print(f"[yellow]skipped[/yellow] {doc.source_path} :: {outcome.skip_reason}")
            elif outcome.status == "failed":
                counts["failed"] += 1
                logger.emit(
                    "source_processed",
                    source_id=doc.source_id,
                    source_type=doc.source_type,
                    adapter_name=result.adapter_name,
                    source_path=doc.source_path,
                    content_hash=doc.content_hash,
                    status="failed",
                    stage_failed=outcome.error_stage or "",
                    error_message=outcome.error_message or "",
                )
                console.print(
                    f"[red]failed[/red] {doc.source_path} @ stage={outcome.error_stage}: {outcome.error_message}"
                )
            else:  # processed
                counts["processed"] += 1
                triage_parsed = outcome.triage.parsed if outcome.triage else {}
                item.track = triage_parsed.get("track")
                item.value_score = triage_parsed.get("value_score")
                # 渲染并写卡片
                source_dict = {
                    "source_id": doc.source_id,
                    "source_type": doc.source_type,
                    "adapter_name": result.adapter_name,
                    "source_path": doc.source_path,
                    "source_url": doc.source_url or "",
                    "title": doc.title or "",
                }
                run_dict = {
                    "created_at": now.isoformat(timespec="seconds"),
                    "prompts": {"distill_version": cfg.prompts.distill},  # type: ignore[attr-defined]
                    "profile": cfg.llm.active_profile,  # type: ignore[attr-defined]
                    "stage_models": {
                        s: {"alias": m["model_alias"], "provider": m["provider"], "model": m["actual_model"]}
                        for s, m in outcome.stages_meta.items()
                    },
                    "run_id": logger.run_id,
                }
                wr = writer.write(card_payload=outcome.card_payload or {}, source=source_dict, run=run_dict)
                item.card_path = str(wr.path.relative_to(cfg.vault.root))  # type: ignore[attr-defined]
                logger.emit(
                    "card_written",
                    output_file=str(wr.path),
                    source_id=doc.source_id,
                    source_type=doc.source_type,
                    track=item.track or "",
                    value_score=item.value_score or 0,
                    card_conflict="true" if wr.conflict else "false",
                )
                logger.emit(
                    "source_processed",
                    source_id=doc.source_id,
                    source_type=doc.source_type,
                    adapter_name=result.adapter_name,
                    source_path=doc.source_path,
                    content_hash=doc.content_hash,
                    status="processed",
                    track=item.track or "",
                    value_score=item.value_score or 0,
                    output_file=str(wr.path),
                )
                tag = "[yellow]conflict[/yellow]" if wr.conflict else "[green]processed[/green]"
                console.print(f"{tag} {doc.source_path} → {wr.path}")

            if limit is not None and counts["seen"] >= limit:
                break

        cp.save(active_profile=cfg.llm.active_profile)  # type: ignore[attr-defined]
        logger.emit(
            EVENT_STATE_WRITTEN,
            path=str(cfg.state.state_path),  # type: ignore[attr-defined]
            items_count=len(list(cp.all_items())),
        )

    console.print(
        f"\n[bold]process 完成[/bold]：seen={counts['seen']} "
        f"processed={counts['processed']} skipped={counts['skipped']} failed={counts['failed']}"
    )


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
