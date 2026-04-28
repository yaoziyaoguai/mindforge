"""mindforge — 命令行入口（typer）。

v0.1 当前命令：
- ``mindforge scan``    — 扫描 inbox，派发到 adapter，更新 state.json；不调 LLM。
- ``mindforge process`` — 跑 5 stage pipeline，写入 Knowledge Card。
- ``mindforge status``  — 打印 state.json 的状态汇总（按 status / source_type）。
- ``mindforge llm ping``— 只校验 active_profile 涉及的模型 env 是否齐全，不发 HTTP。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .checkpoint import Checkpoint
from .config import ConfigError, MindForgeConfig, load_mindforge_config
from .env_loader import load_dotenv_silently
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
llm_app = typer.Typer(add_completion=False, help="LLM provider 工具子命令（不触发业务 pipeline）")
app.add_typer(llm_app, name="llm")
console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_cfg(config_path: Path) -> MindForgeConfig:
    # 入口处加载 .env（静默，不打印 value，env > dotfile）
    load_dotenv_silently(Path.cwd())
    try:
        return load_mindforge_config(config_path)
    except ConfigError as e:
        console.print(f"[red]配置错误：{e}[/red]")
        raise typer.Exit(code=2) from e


def _override_active_profile(cfg: MindForgeConfig, profile: str | None) -> MindForgeConfig:
    """如果 CLI 传了 --profile，就基于现有 cfg 派生一份临时 LLMConfig。

    不修改 yaml；只影响本次进程。失败时友好报错。
    """
    if not profile:
        return cfg
    if profile not in cfg.llm.profiles:
        console.print(
            f"[red]--profile {profile!r} 不在 llm.profiles 中；"
            f"已知：{sorted(cfg.llm.profiles)}[/red]"
        )
        raise typer.Exit(code=2)
    from dataclasses import replace
    new_llm = replace(cfg.llm, active_profile=profile)
    return replace(cfg, llm=new_llm)


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
# approve — M3 反 AI 污染闸门：显式人工把 ai_draft 卡片晋升为 human_approved
# 详见 docs/M3_HUMAN_APPROVAL_PROTOCOL.md
# ---------------------------------------------------------------------------


@app.command()
def approve(
    card: Path = typer.Option(
        ...,
        "--card",
        help="要晋升的 Knowledge Card 文件路径（必须是 ai_draft 状态）",
    ),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
) -> None:
    """显式人工把一张 Knowledge Card 从 ai_draft 晋升为 human_approved。

    硬约束：
    - 不调用 LLM、不需要 .env、不读 active_profile；
    - 不修改卡片正文，不改写源文件；
    - 仅 ai_draft 可晋升；human_approved 幂等；其他状态拒绝。
    """
    from .approver import (  # 局部导入：approver 不应被 process 路径间接 import
        ApprovalError,
        approve_card,
    )

    cfg = _load_cfg(config)
    with RunLogger(cfg.state.runs_path, command="approve") as logger:  # type: ignore[attr-defined]
        logger.emit("approval_started", card_path=str(card))
        try:
            outcome = approve_card(card, cfg=cfg)
        except ApprovalError as e:
            logger.emit(
                "approval_failed",
                card_path=str(card),
                error_message=str(e),
                prev_status=e.prev_status or "",
            )
            console.print(f"[red]approve 失败：{e}[/red]")
            raise typer.Exit(code=e.exit_code) from e

        completed_fields: dict[str, object] = {
            "card_path": str(outcome.card_path),
            "status": outcome.new_status,
            "prev_status": outcome.prev_status,
            "approval_method": outcome.approval_method,
            "idempotent": outcome.kind == "already_approved",
        }
        if outcome.approved_at is not None:
            completed_fields["approved_at"] = outcome.approved_at.isoformat()
        if outcome.state_missing:
            completed_fields["state_missing"] = True
        logger.emit("approval_completed", **completed_fields)

    if outcome.kind == "already_approved":
        console.print(f"[yellow]已是 human_approved（幂等）：{outcome.card_path}[/yellow]")
    else:
        console.print(
            f"[green]✔ approved[/green] {outcome.card_path}  "
            f"(prev={outcome.prev_status} → {outcome.new_status}, "
            f"method={outcome.approval_method})"
        )
        if outcome.state_missing:
            console.print(
                "[yellow]注意：state.json 中找不到对应 item，仅更新了卡片文件。[/yellow]"
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
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="临时覆盖 llm.active_profile（仅本次进程，不改 yaml）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="跑完整 pipeline 但不写卡片、不写 state.json；仅 runs/*.jsonl 留痕",
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
    cfg = _override_active_profile(cfg, profile)
    if dry_run:
        console.print("[yellow]--dry-run：不会写卡片、不会写 state.json[/yellow]")
    console.print(f"active_profile = [bold]{cfg.llm.active_profile}[/bold]")

    scanner = Scanner(cfg)
    cp = Checkpoint.load(cfg.state.state_path, backup=cfg.state.backup_state)

    providers = build_providers(cfg.llm)
    client = LLMClient(llm_config=cfg.llm, providers=providers)

    template_path = template
    writer = CardWriter(
        vault_root=cfg.vault.root,
        cards_dir=cfg.vault.cards_dir,
        template_path=template_path,
    )

    tracks_text = tracks.read_text("utf-8") if tracks.exists() else ""
    pipeline = Pipeline(
        client=client,
        logger=None,  # type: ignore[arg-type]
        prompts_dir=prompts_dir,
        prompt_versions=cfg.prompts,
        triage_threshold=cfg.triage.value_score_threshold,
        learning_tracks_text=tracks_text,
    )

    counts = {"processed": 0, "skipped": 0, "failed": 0, "seen": 0}

    with RunLogger(cfg.state.runs_path, command="process") as logger:
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
                if dry_run:
                    console.print(
                        f"[cyan]dry-run[/cyan] would-write {doc.source_path}"
                        f" → {cfg.vault.cards_path / (item.track or 'unrouted')}"
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
                    )
                else:
                    wr = writer.write(card_payload=outcome.card_payload or {}, source=source_dict, run=run_dict)
                    item.card_path = str(wr.path.relative_to(cfg.vault.root))
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

        if not dry_run:
            cp.save(active_profile=cfg.llm.active_profile)
            logger.emit(
                EVENT_STATE_WRITTEN,
                path=str(cfg.state.state_path),
                items_count=len(list(cp.all_items())),
            )

    console.print(
        f"\n[bold]process 完成[/bold]：seen={counts['seen']} "
        f"processed={counts['processed']} skipped={counts['skipped']} failed={counts['failed']}"
    )


# ---------------------------------------------------------------------------
# llm ping — 只校验 active_profile 涉及的 env，不发 HTTP
# ---------------------------------------------------------------------------


@llm_app.command("ping")
def llm_ping(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="临时覆盖 active_profile",
    ),
) -> None:
    """校验当前 active_profile 涉及的所有模型 env 是否齐全。

    本命令**不发任何 HTTP 请求**，不消耗配额。它只回答：
    - active_profile 涉及哪些 alias / provider / type / 真实 model 名
    - 每个模型需要哪些 env，是否已 set（不打印 value！只报告 set / unset）
    """
    import os
    cfg = _load_cfg(config)
    cfg = _override_active_profile(cfg, profile)

    profile_map = cfg.llm.profiles[cfg.llm.active_profile]
    aliases_used = sorted(set(profile_map.values()))

    console.print(f"active_profile = [bold]{cfg.llm.active_profile}[/bold]")
    table = Table(title="LLM Provider 校验（不发 HTTP）", show_lines=True)
    table.add_column("alias")
    table.add_column("provider")
    table.add_column("type")
    table.add_column("model (resolved)")
    table.add_column("env required")
    table.add_column("env status")

    all_ok = True
    for alias in aliases_used:
        mc = cfg.llm.models[alias]
        actual_model = mc.model
        if mc.model_env and os.environ.get(mc.model_env):
            actual_model = os.environ[mc.model_env]

        env_reqs: list[tuple[str, str, bool]] = []
        if mc.base_url_env:
            env_reqs.append(("base_url", mc.base_url_env, not bool(mc.base_url)))
        if mc.api_key_env:
            env_reqs.append(("api_key", mc.api_key_env, not mc.api_key_optional))
        if mc.version_env:
            env_reqs.append(("version", mc.version_env, False))
        if mc.model_env:
            env_reqs.append(("model", mc.model_env, False))

        status_lines: list[str] = []
        for label, var, required in env_reqs:
            present = bool(os.environ.get(var))
            mark = "[green]set[/green]" if present else (
                "[red]MISSING[/red]" if required else "[yellow]unset (optional)[/yellow]"
            )
            status_lines.append(f"{label}={var} {mark}")
            if required and not present:
                all_ok = False

        env_required_summary = "\n".join(
            f"{lbl} ← {var}{' (required)' if req else ' (optional)'}"
            for lbl, var, req in env_reqs
        ) or "(none)"
        env_status_summary = "\n".join(status_lines) or "(none)"

        table.add_row(
            alias,
            mc.provider,
            mc.type,
            actual_model or "(empty)",
            env_required_summary,
            env_status_summary,
        )

    console.print(table)
    if all_ok:
        console.print("[green]✓ 所需 env 全部齐备；可以进行 smoke test。[/green]")
    else:
        console.print("[red]✗ 有必填 env 未设置。请在 .env 或 shell export 后重试。[/red]")
        raise typer.Exit(code=1)


# ===========================================================================
# M4 — review / recall / project memory
# ===========================================================================
#
# 设计原则（详见 docs/M4_RECALL_REVIEW_PROTOCOL.md）：
# - 五个命令全部不调 LLM、不读 .env、不改源文件、不写 state.json
# - review mark 是唯一允许写卡片 review 字段的命令（沿用 M3 "审计入口必须
#   唯一" 原则）
# - recall / project context 默认只看 status=human_approved；--include-drafts
#   显式打开

review_app = typer.Typer(add_completion=False, help="复习候选与标记（M4）")
project_app = typer.Typer(add_completion=False, help="项目记忆与上下文（M4）")
app.add_typer(review_app, name="review")
app.add_typer(project_app, name="project")


def _hash_keyword(kw: str | None) -> tuple[bool, str]:
    if not kw:
        return False, ""
    import hashlib

    return True, hashlib.sha256(kw.encode("utf-8")).hexdigest()[:8]


def _filters_dict(**kwargs: object) -> dict[str, object]:
    return {k: v for k, v in kwargs.items() if v not in (None, (), [])}


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError as e:
        console.print(f"[red]日期解析失败：{s!r}: {e}[/red]")
        raise typer.Exit(code=2) from e


# ---------------------------------------------------------------------------
# review due
# ---------------------------------------------------------------------------


@review_app.command("due")
def review_due(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    limit: int = typer.Option(10, "--limit"),
    track: str | None = typer.Option(None, "--track"),
    project: str | None = typer.Option(None, "--project"),
    include_drafts: bool = typer.Option(False, "--include-drafts"),
    include_missing_review_after: bool = typer.Option(
        False,
        "--include-missing-review-after",
        help="把从未 review 过的卡片也列入候选",
    ),
    output_format: str = typer.Option(
        "markdown", "--format", help="markdown | json"
    ),
) -> None:
    """列出到期 / 接近到期的复习候选（默认仅 human_approved）。"""
    from .cards import filter_cards, iter_cards

    cfg = _load_cfg(config)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    base = filter_cards(
        scan.cards,
        track=track,
        project=project,
        status="human_approved",
        include_drafts=include_drafts,
    )
    now = datetime.now().astimezone()
    due: list = []
    for c in base:
        if c.review_after is None:
            if include_missing_review_after:
                due.append(c)
            continue
        # 比较时统一用 timezone-aware
        ra = c.review_after
        if ra.tzinfo is None:
            ra = ra.replace(tzinfo=now.tzinfo)
        if ra <= now:
            due.append(c)
    # 排序
    def _k(c):  # type: ignore[no-untyped-def]
        has_after = 0 if c.review_after is not None else 1
        ra = c.review_after or datetime.max.replace(tzinfo=now.tzinfo)
        return (has_after, ra, -(c.value_score or 0), c.id or c.path.name)

    due.sort(key=_k)
    due = due[:limit]

    with RunLogger(cfg.state.runs_path, command="review-due") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "review_due_listed",
            count=len(due),
            filters=_filters_dict(
                track=track,
                project=project,
                include_drafts=include_drafts,
                include_missing_review_after=include_missing_review_after,
                limit=limit,
            ),
            output_format=output_format,
        )

    if output_format == "json":
        import json as _json

        console.print(_json.dumps(
            {
                "version": 1,
                "count": len(due),
                "items": [_card_to_safe_dict(c) for c in due],
            },
            ensure_ascii=False,
            indent=2,
        ))
        return

    if not due:
        console.print("[yellow]当前没有到期复习候选。[/yellow]")
        return
    console.print(f"[bold]Review Due[/bold] · {len(due)} 项")
    for c in due:
        console.print(
            f"- [{c.id or c.path.stem}] {c.title or '(untitled)'} · "
            f"track={c.track or '-'} · review_after={_safe_date(c.review_after)} · "
            f"value_score={c.value_score if c.value_score is not None else '-'}"
        )


# ---------------------------------------------------------------------------
# review mark
# ---------------------------------------------------------------------------


@review_app.command("mark")
def review_mark(
    card: Path = typer.Option(..., "--card"),
    result: str = typer.Option(..., "--result", help="remembered | partial | forgotten"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """记录一次 review 结果到卡片 frontmatter（4 字段写入）。"""
    from .reviewer import ReviewError, mark_card_review

    cfg = _load_cfg(config)
    with RunLogger(cfg.state.runs_path, command="review-mark") as logger:  # type: ignore[attr-defined]
        logger.emit("review_mark_started", card_path=str(card), result=result)
        try:
            outcome = mark_card_review(card, result, cfg=cfg)
        except ReviewError as e:
            logger.emit(
                "review_mark_failed",
                card_path=str(card),
                error_message=str(e),
                result=result,
            )
            console.print(f"[red]review mark 失败：{e}[/red]")
            raise typer.Exit(code=e.exit_code) from e
        logger.emit(
            "review_mark_completed",
            card_path=str(outcome.card_path),
            result=outcome.result,
            prev_review_count=outcome.prev_review_count,
            new_review_count=outcome.new_review_count,
            review_after=outcome.review_after.isoformat(),
        )
    console.print(
        f"[green]✔ reviewed[/green] {outcome.card_path}  "
        f"(result={outcome.result}, count: {outcome.prev_review_count} → "
        f"{outcome.new_review_count}, next_review_after={_safe_date(outcome.review_after)})"
    )


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------


@app.command()
def recall(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    track: str | None = typer.Option(None, "--track"),
    project: str | None = typer.Option(None, "--project"),
    tag: list[str] = typer.Option([], "--tag", help="可重复，AND 语义"),
    keyword: str | None = typer.Option(
        None, "--keyword",
        help="多 token AND；ci-contains；仅匹配 frontmatter 白名单 + 文件名",
    ),
    source_type: str | None = typer.Option(None, "--source-type"),
    status: str = typer.Option(
        "human_approved", "--status", help="human_approved | ai_draft | all"
    ),
    include_drafts: bool = typer.Option(False, "--include-drafts"),
    since: str | None = typer.Option(None, "--since", help="YYYY-MM-DD"),
    until: str | None = typer.Option(None, "--until", help="YYYY-MM-DD"),
    limit: int = typer.Option(20, "--limit"),
    sort: str = typer.Option(
        "default", "--sort",
        help="default | review_after | updated_at | title | value_score",
    ),
    output_format: str = typer.Option(
        "compact", "--format",
        help="compact (默认) | table | markdown | json",
    ),
) -> None:
    """规则检索 Knowledge Cards（仅查 frontmatter 白名单字段）。

    M4.1 增量：
    - --keyword 多 token AND（空白分割），ci-contains；
    - --sort 控制排序键；
    - --format 增加 table / markdown，markdown 适合直接粘到 Claude/Copilot；
    - 仍**不**搜 body / source 原文 / human_note；
    - 仍默认仅 human_approved；--include-drafts 显式打开。
    """
    from .cards import filter_cards, iter_cards, sort_cards

    cfg = _load_cfg(config)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cards = filter_cards(
        scan.cards,
        track=track,
        project=project,
        tags=tag,
        source_type=source_type,
        status=status,
        keyword=keyword,
        since=_parse_date(since),
        until=_parse_date(until),
        include_drafts=include_drafts,
    )
    try:
        cards = sort_cards(cards, by=sort)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    cards = cards[:limit]

    kw_provided, kw_hash = _hash_keyword(keyword)
    with RunLogger(cfg.state.runs_path, command="recall") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "recall_executed",
            count=len(cards),
            filters=_filters_dict(
                track=track,
                project=project,
                tags=list(tag),
                source_type=source_type,
                status=status,
                include_drafts=include_drafts,
                since=since,
                until=until,
                limit=limit,
                sort=sort,
            ),
            keyword_provided=kw_provided,
            keyword_hash=kw_hash,
            output_format=output_format,
        )

    if output_format == "json":
        import json as _json

        payload = {
            "version": 1,
            "query": {
                "track": track,
                "project": project,
                "tags": list(tag),
                "keyword_provided": kw_provided,
                "keyword_hash": kw_hash,
                "status_filter": status,
                "since": since,
                "until": until,
                "limit": limit,
                "sort": sort,
            },
            "count": len(cards),
            "items": [_card_to_safe_dict(c) for c in cards],
        }
        console.print(_json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if output_format == "markdown":
        # 直接 print 避免 rich 把 [id] 当 markup 吞掉
        print(f"# Recall · {len(cards)} 项 (sort={sort})\n")
        if not cards:
            print("_(no cards matched)_")
            return
        for c in cards:
            print(
                f"- **[{c.id or c.path.stem}]** {c.title or '(untitled)'}  "
                f"`status={c.status}` `track={c.track or '-'}` "
                f"`value_score={c.value_score if c.value_score is not None else '-'}`  "
                f"`path={c.rel_path}`"
            )
        return

    if output_format == "table":
        if not cards:
            console.print("[yellow]没有匹配的卡片。[/yellow]")
            return
        table = Table(title=f"Recall · {len(cards)} 项 (sort={sort})")
        table.add_column("id")
        table.add_column("title")
        table.add_column("status")
        table.add_column("track")
        table.add_column("score", justify="right")
        table.add_column("review_after")
        for c in cards:
            table.add_row(
                c.id or c.path.stem,
                c.title or "(untitled)",
                c.status,
                c.track or "-",
                str(c.value_score) if c.value_score is not None else "-",
                _safe_date(c.review_after),
            )
        console.print(table)
        return

    # compact (默认)
    if not cards:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        return
    console.print(f"[bold]Recall[/bold] · {len(cards)} 项 (sort={sort})")
    for c in cards:
        console.print(
            f"- {c.id or c.path.stem} · {c.title or '(untitled)'} · "
            f"status={c.status} · track={c.track or '-'} · "
            f"value_score={c.value_score if c.value_score is not None else '-'}"
        )


# ---------------------------------------------------------------------------
# project list / context
# ---------------------------------------------------------------------------


@project_app.command("list")
def project_list(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("markdown", "--format"),
) -> None:
    """列出所有卡片 frontmatter 中出现过的 project（并集去重，按字母序）。"""
    from .cards import iter_cards

    cfg = _load_cfg(config)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    counts: dict[str, int] = {}
    for c in scan.cards:
        for p in c.projects:
            counts[p] = counts.get(p, 0) + 1
    items = sorted(counts.items())

    with RunLogger(cfg.state.runs_path, command="project-list") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "project_list_emitted",
            count=len(items),
            output_format=output_format,
        )

    if output_format == "json":
        import json as _json

        console.print(_json.dumps(
            {"version": 1, "count": len(items), "items": [
                {"name": n, "card_count": k} for n, k in items
            ]},
            ensure_ascii=False, indent=2,
        ))
        return
    if not items:
        console.print("[yellow]当前没有任何卡片声明 project。[/yellow]")
        return
    console.print(f"[bold]Projects[/bold] · {len(items)} 项")
    for name, n in items:
        console.print(f"- {name} ({n} card{'s' if n != 1 else ''})")


@project_app.command("context")
def project_context(
    project_names: list[str] = typer.Argument(
        ...,
        help=(
            "一个或多个项目名（与卡片 frontmatter projects[] 比对，并匹配 "
            "30-Projects/<name>.md）。多于一个 → 启用多 project 联合模式。"
        ),
    ),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    limit: int = typer.Option(20, "--limit"),
    no_prompts: bool = typer.Option(False, "--no-prompts", help="不输出 Reusable Prompts 段"),
    include_drafts: bool = typer.Option(False, "--include-drafts"),
    include_actions: bool = typer.Option(
        True, "--include-actions/--no-actions", help="是否聚合 Action Items 段（默认开）"
    ),
    include_review_due: bool = typer.Option(
        True, "--include-review-due/--no-review-due", help="是否输出 Review Due 段（默认开）"
    ),
    include_next_step_prompt: bool = typer.Option(
        True, "--include-next-step-prompt/--no-next-step-prompt",
        help="是否附固定模板的下一步 prompt（**不调 LLM**，仅模板）",
    ),
    target: str | None = typer.Option(
        None, "--target",
        help="目标助手：claude-code | copilot | codex | generic（默认按 project profile.default_target，再退化为 generic）",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o",
        help="把结果写到该文件而不是 stdout；安全：写入前不读 .env，不调 LLM",
    ),
    output_format: str = typer.Option("markdown", "--format"),
) -> None:
    """渲染一个或多个 project 的只读上下文包（markdown / json）。

    - 单 project：保持 v0.2.2 的固定 9 段结构（向后兼容）；
    - 多 project：使用 ``multi_project_context`` 渲染器；卡片去重、原则
      并列（不自动裁决）、suggested prompt 明确"multi-project context pack"。

    任何模式都**不**调 LLM、**不**读 .env、**不**读 raw source。
    """
    from .cards import filter_cards, iter_cards
    from .multi_project_context import (
        render_multi_project_context_json,
        render_multi_project_context_markdown,
    )
    from .project_context import (
        ProjectContextOptions,
        render_project_context_json,
        render_project_context_markdown,
        resolve_target,
    )
    from .project_profile import (
        ProjectProfile,
        ProjectProfileError,
        load_project_profile,
    )
    from .telemetry import measure

    cfg = _load_cfg(config)

    # 去重并保持用户顺序（"a a b" → ["a", "b"]）
    seen: set[str] = set()
    project_names = [n for n in project_names if not (n in seen or seen.add(n))]
    if not project_names:
        console.print("[red]至少需要一个 project_name[/red]")
        raise typer.Exit(code=2)

    is_multi = len(project_names) > 1

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)

    profiles: dict[str, ProjectProfile] = {}
    cards_by_project: dict[str, list] = {}
    for name in project_names:
        try:
            profiles[name] = load_project_profile(
                cfg.vault.root, cfg.vault.projects_dir, name
            )
        except ProjectProfileError as e:
            console.print(f"[red]project_name 非法：{e}[/red]")
            raise typer.Exit(code=2) from e
        cards_by_project[name] = filter_cards(
            scan.cards,
            project=name,
            status="human_approved",
            include_drafts=include_drafts,
        )

    # 多项目模式下，target 解析仅看第一个 found=true 的 profile.default_target
    primary_profile = next(
        (profiles[n] for n in project_names if profiles[n].found),
        profiles[project_names[0]],
    )
    try:
        resolved_target = resolve_target(target, primary_profile)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e

    opts = ProjectContextOptions(
        include_prompts=not no_prompts,
        include_drafts=include_drafts,
        include_actions=include_actions,
        include_review_due=include_review_due,
        include_next_step_prompt=include_next_step_prompt,
        limit=limit,
        target=resolved_target,
    )

    if output_format not in {"markdown", "json"}:
        console.print(f"[red]--format 必须是 markdown 或 json，收到 {output_format!r}[/red]")
        raise typer.Exit(code=2)

    with measure(
        cfg.state.workdir, cfg.telemetry, "project-context",
        project_count=len(project_names),
    ) as th:
        if is_multi:
            if output_format == "json":
                out = render_multi_project_context_json(
                    project_names, cards_by_project, profiles, options=opts
                )
            else:
                out = render_multi_project_context_markdown(
                    project_names, cards_by_project, profiles, options=opts
                )
            total_cards = sum(min(len(c), limit) for c in cards_by_project.values())
        else:
            single_name = project_names[0]
            if output_format == "json":
                out = render_project_context_json(
                    single_name, cards_by_project[single_name],
                    options=opts, profile=profiles[single_name],
                )
            else:
                out = render_project_context_markdown(
                    single_name, cards_by_project[single_name],
                    options=opts, profile=profiles[single_name],
                )
            total_cards = min(len(cards_by_project[single_name]), limit)

        th.set_counts(card_count=total_cards, result_count=total_cards)

        with RunLogger(cfg.state.runs_path, command="project-context") as logger:  # type: ignore[attr-defined]
            # 多项目模式：runs jsonl 仅记 project_count + 第一个 project_name；
            # 不展开各项目名，避免日志结构每次随用户输入暴增。
            logger.emit(
                "project_context_emitted",
                project_name=project_names[0] if not is_multi else f"<{len(project_names)} projects>",
                count=total_cards,
                output_format=output_format,
                target=resolved_target,
                project_profile_found=primary_profile.found,
            )

        if output is not None:
            if not output.parent.exists():
                console.print(
                    f"[red]--output 父目录不存在：{output.parent}（请先 mkdir）[/red]"
                )
                raise typer.Exit(code=2)
            output.write_text(out, encoding="utf-8")
            console.print(f"[green]✔ project context 已写入[/green] {output}")
            return

        print(out)


# ---------------------------------------------------------------------------
# project update-evidence — 幂等写入 30-Projects/<name>.md 受控区块
# ---------------------------------------------------------------------------


@project_app.command("update-evidence")
def project_update_evidence(
    project_name: str = typer.Argument(..., help="项目名；必须已存在 30-Projects/<name>.md"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    include_drafts: bool = typer.Option(
        False, "--include-drafts", help="同时纳入 ai_draft 卡片（默认仅 human_approved）"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="只打印将要写入的内容，不落盘"
    ),
) -> None:
    """把当前项目已审核卡片的安全摘要，幂等写入项目笔记的受控区块。

    - 区块由 ``<!-- MINDFORGE:EVIDENCE:START -->`` 与 ``END`` 包围；
    - 多次运行同一参数时除时间戳外保持稳定，**不会重复追加**；
    - 不创建项目 profile；profile 文件不存在 → 退出 2 + 友好提示；
    - **永不**写 ai_summary / source_excerpt / 卡片正文 / prompt / completion。
    """
    from .cards import filter_cards, iter_cards
    from .evidence import EvidenceError, update_evidence_block, write_evidence_update
    from .project_profile import ProjectProfileError, _validate_project_name
    from .telemetry import measure

    cfg = _load_cfg(config)

    try:
        _validate_project_name(project_name)
    except ProjectProfileError as e:
        console.print(f"[red]project_name 非法：{e}[/red]")
        raise typer.Exit(code=2) from e

    profile_path = cfg.vault.projects_path / f"{project_name}.md"

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cards = filter_cards(
        scan.cards,
        project=project_name,
        status="human_approved",
        include_drafts=include_drafts,
    )

    with measure(
        cfg.state.workdir, cfg.telemetry, "project-update-evidence",
        project_count=1,
    ) as th:
        try:
            update = update_evidence_block(
                profile_path, project_name, cards,
                cards_dir_rel=cfg.vault.cards_dir,
            )
        except EvidenceError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(code=2) from e

        th.set_counts(card_count=update.card_count, result_count=update.card_count)

        with RunLogger(cfg.state.runs_path, command="project-update-evidence") as logger:  # type: ignore[attr-defined]
            logger.emit(
                "project_context_emitted",  # 复用 M5.3 事件类型，仅 metadata
                project_name=project_name,
                count=update.card_count,
                output_format="evidence-block",
                target="-",
                project_profile_found=True,
            )

        if dry_run:
            console.print(
                f"[bold]dry-run[/bold] · {profile_path} · "
                f"will_change={update.will_change} · existed={update.block_existed_before} · "
                f"cards={update.card_count}"
            )
            print(update.new_text)
            return

        if not update.will_change:
            console.print(
                f"[green]✔ evidence block 已是最新（{update.card_count} cards），未写盘[/green]"
            )
            return

        write_evidence_update(update)
        console.print(
            f"[green]✔ evidence block 已更新[/green] {profile_path} "
            f"· cards={update.card_count} · existed={update.block_existed_before}"
        )


# ---------------------------------------------------------------------------
# telemetry status / summary — 本地使用观察日志
# ---------------------------------------------------------------------------


telemetry_app = typer.Typer(
    add_completion=False,
    help="本地 telemetry（M5.7 / v0.2.3）— 仅元数据，永不上传",
)
app.add_typer(telemetry_app, name="telemetry")


@telemetry_app.command("status")
def telemetry_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """打印 telemetry 配置与本地文件位置（不读取事件内容）。"""
    from .telemetry import telemetry_path

    cfg = _load_cfg(config)
    p = telemetry_path(cfg.state.workdir)
    console.print("[bold]Telemetry status[/bold]")
    console.print(f"- enabled: {cfg.telemetry.enabled}")
    console.print(f"- local_only: {cfg.telemetry.local_only}")
    console.print(f"- file: {p}")
    console.print(f"- exists: {p.exists()}")
    if p.exists():
        try:
            line_count = sum(1 for _ in p.open("r", encoding="utf-8"))
        except OSError:
            line_count = 0
        console.print(f"- event_count: {line_count}")


@telemetry_app.command("summary")
def telemetry_summary_cmd(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("markdown", "--format"),
    recent_errors: int = typer.Option(5, "--recent-errors"),
) -> None:
    """聚合统计：总数 / 成功率 / 最常用命令 / 平均耗时 / 最近错误。

    所有数据仅来自本地 ``.mindforge/telemetry.jsonl``；不读取卡片正文。
    """
    from .telemetry import read_events, summarize

    cfg = _load_cfg(config)
    if output_format not in {"markdown", "json"}:
        console.print(f"[red]--format 必须是 markdown 或 json，收到 {output_format!r}[/red]")
        raise typer.Exit(code=2)

    events = read_events(cfg.state.workdir)
    summary = summarize(events, recent_errors=recent_errors)

    if output_format == "json":
        import json as _json

        print(_json.dumps(
            {
                "total": summary.total,
                "success": summary.success,
                "failure": summary.failure,
                "by_command": summary.by_command,
                "avg_duration_ms_by_command": summary.avg_duration_ms_by_command,
                "recent_errors": summary.recent_errors,
            },
            ensure_ascii=False, indent=2,
        ))
        return

    console.print("[bold]Telemetry summary[/bold]")
    console.print(f"- total: {summary.total}")
    console.print(f"- success: {summary.success}")
    console.print(f"- failure: {summary.failure}")
    if summary.by_command:
        console.print("[bold]Most used commands:[/bold]")
        for cmd, n in sorted(summary.by_command.items(), key=lambda kv: (-kv[1], kv[0])):
            avg = summary.avg_duration_ms_by_command.get(cmd)
            avg_part = f" · avg {avg}ms" if avg is not None else ""
            console.print(f"- {cmd}: {n}{avg_part}")
    if summary.recent_errors:
        console.print("[bold]Recent errors:[/bold]")
        for e in summary.recent_errors:
            console.print(
                f"- {e.get('timestamp')} · {e.get('command')} · "
                f"{e.get('error_code')} · {e.get('duration_ms')}ms"
            )


# ---------------------------------------------------------------------------
# 内部辅助 — 卡片摘要的安全字典 / 日期格式化
# ---------------------------------------------------------------------------


def _card_to_safe_dict(c) -> dict:  # type: ignore[no-untyped-def]
    return {
        "id": c.id,
        "title": c.title,
        "path": c.rel_path,
        "status": c.status,
        "track": c.track,
        "projects": list(c.projects),
        "tags": list(c.tags),
        "source_type": c.source_type,
        "source_url": c.source_url,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "review_after": c.review_after.isoformat() if c.review_after else None,
        "value_score": c.value_score,
    }


def _safe_date(dt) -> str:  # type: ignore[no-untyped-def]
    if dt is None:
        return "-"
    return dt.date().isoformat()


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
