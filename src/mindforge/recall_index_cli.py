"""Recall and BM25 index CLI adapters.

BM25 是本地词法检索，不是 RAG；本模块只读 Knowledge Card 安全字段，
不调用 LLM、不读 .env、不联网。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer
from rich.table import Table

from .cli_cards import card_to_safe_dict as _card_to_safe_dict
from .cli_cards import filters_dict as _filters_dict
from .cli_cards import hash_keyword as _hash_keyword
from .cli_cards import parse_date as _parse_date
from .cli_cards import safe_date as _safe_date
from .cli_runtime import console, load_cfg, render_active_vault_resolution_notice
from .recall_presenter import RecallRenderContext, render_recall_result
from .recall_service import (
    RecallQuery,
    RecallServiceError,
    recall_hit_next_action,
    recall_no_result_next_action,
    run_bm25_recall,
)
from .run_logger import RunLogger

recall_app = typer.Typer(add_completion=False)

# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _RuleRecallResult:
    cfg: object
    cards: list
    keyword_provided: bool
    keyword_hash: str


def _rule_recall_result(
    *,
    config: Path,
    track: str | None,
    project: str | None,
    tag: list[str],
    keyword: str | None,
    source_type: str | None,
    status: str,
    include_drafts: bool,
    since: str | None,
    until: str | None,
    limit: int,
    sort: str,
) -> _RuleRecallResult:
    from .cards import filter_cards, iter_cards, sort_cards

    cfg = load_cfg(config, read_env=False)
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
    keyword_provided, keyword_hash = _hash_keyword(keyword)
    return _RuleRecallResult(
        cfg=cfg,
        cards=cards[:limit],
        keyword_provided=keyword_provided,
        keyword_hash=keyword_hash,
    )


def _log_rule_recall(
    *,
    result: _RuleRecallResult,
    track: str | None,
    project: str | None,
    tag: list[str],
    source_type: str | None,
    status: str,
    include_drafts: bool,
    since: str | None,
    until: str | None,
    limit: int,
    sort: str,
    output_format: str,
) -> None:
    with RunLogger(result.cfg.state.runs_path, command="recall") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "recall_executed",
            count=len(result.cards),
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
            keyword_provided=result.keyword_provided,
            keyword_hash=result.keyword_hash,
            output_format=output_format,
        )


def _print_rule_recall_json(
    *,
    result: _RuleRecallResult,
    track: str | None,
    project: str | None,
    tag: list[str],
    status: str,
    since: str | None,
    until: str | None,
    limit: int,
    sort: str,
) -> None:
    import json as _json

    payload = {
        "version": 1,
        "query": {
            "track": track,
            "project": project,
            "tags": list(tag),
            "keyword_provided": result.keyword_provided,
            "keyword_hash": result.keyword_hash,
            "status_filter": status,
            "since": since,
            "until": until,
            "limit": limit,
            "sort": sort,
        },
        "count": len(result.cards),
        "items": [_card_to_safe_dict(card) for card in result.cards],
    }
    print(_json.dumps(payload, ensure_ascii=False, indent=2))


def _print_rule_recall_markdown(cards: list, *, sort: str) -> None:
    # 直接 print 避免 rich 把 [id] 当 markup 吞掉。
    print(f"# Recall · {len(cards)} 项 (sort={sort})\n")
    if not cards:
        print("_(no cards matched)_")
        print("\n" + recall_no_result_next_action())
        return
    for card in cards:
        print(
            f"- **[{card.id or card.path.stem}]** {card.title or '(untitled)'}  "
            f"`status={card.status}` `track={card.track or '-'}` "
            f"`value_score={card.value_score if card.value_score is not None else '-'}`  "
            f"`path={card.rel_path}`"
        )
    print("\n" + recall_hit_next_action())


def _print_rule_recall_table(cards: list, *, sort: str) -> None:
    if not cards:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        console.print(f"[dim]{recall_no_result_next_action()}[/dim]")
        return
    table = Table(title=f"Recall · {len(cards)} 项 (sort={sort})")
    table.add_column("id")
    table.add_column("title")
    table.add_column("status")
    table.add_column("track")
    table.add_column("score", justify="right")
    table.add_column("review_after")
    for card in cards:
        table.add_row(
            card.id or card.path.stem,
            card.title or "(untitled)",
            card.status,
            card.track or "-",
            str(card.value_score) if card.value_score is not None else "-",
            _safe_date(card.review_after),
        )
    console.print(table)
    console.print(f"[dim]{recall_hit_next_action()}[/dim]")


def _print_rule_recall_compact(cards: list, *, sort: str) -> None:
    if not cards:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        console.print(f"[dim]{recall_no_result_next_action()}[/dim]")
        return
    console.print(f"[bold]Recall[/bold] · {len(cards)} 项 (sort={sort})")
    for card in cards:
        console.print(
            f"- {card.id or card.path.stem} · {card.title or '(untitled)'} · "
            f"status={card.status} · track={card.track or '-'} · "
            f"value_score={card.value_score if card.value_score is not None else '-'}"
        )
    console.print(f"[dim]{recall_hit_next_action()}[/dim]")


def _print_rule_recall(
    *,
    result: _RuleRecallResult,
    track: str | None,
    project: str | None,
    tag: list[str],
    status: str,
    since: str | None,
    until: str | None,
    limit: int,
    sort: str,
    output_format: str,
) -> None:
    if output_format == "json":
        _print_rule_recall_json(
            result=result,
            track=track,
            project=project,
            tag=tag,
            status=status,
            since=since,
            until=until,
            limit=limit,
            sort=sort,
        )
    elif output_format == "markdown":
        render_active_vault_resolution_notice(result.cfg)  # type: ignore[arg-type]
        _print_rule_recall_markdown(result.cards, sort=sort)
    elif output_format == "table":
        render_active_vault_resolution_notice(result.cfg)  # type: ignore[arg-type]
        _print_rule_recall_table(result.cards, sort=sort)
    else:
        render_active_vault_resolution_notice(result.cfg)  # type: ignore[arg-type]
        _print_rule_recall_compact(result.cards, sort=sort)


@recall_app.command()
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
    query: str | None = typer.Option(
        None, "--query", "-q",
        help="BM25 词法检索（v0.3）。给定时走 BM25 路径，忽略 --keyword 与 --sort。",
    ),
    explain: bool = typer.Option(
        False, "--explain",
        help="仅 --query 路径生效：打印每条命中的字段贡献分。",
    ),
    ranking: str = typer.Option(
        "bm25", "--ranking",
        help="仅 --query 路径生效：bm25 (默认) | hybrid（bm25+value_score+review_due）",
    ),
    weight_bm25: float | None = typer.Option(
        None, "--weight-bm25",
        help="仅 --ranking hybrid：临时覆盖 bm25 权重（不改 yaml）",
    ),
    weight_value_score: float | None = typer.Option(
        None, "--weight-value-score",
        help="仅 --ranking hybrid：临时覆盖 value_score 权重（不改 yaml）",
    ),
    weight_review_due: float | None = typer.Option(
        None, "--weight-review-due",
        help="仅 --ranking hybrid：临时覆盖 review_due 权重（不改 yaml）",
    ),
) -> None:
    """检索 Knowledge Cards。

    两条互斥路径：
    - **不带 --query**：M4.1 规则检索（含 --keyword AND 过滤）；
    - **带 --query**：v0.3 BM25 词法检索，按相关度排序，可 --explain。

    无论哪条路径，都**只**读 frontmatter 白名单字段 + 卡片内 AI 已生成的安全
    section（``## AI Summary`` / ``## Action Items`` / ``## Principles`` /
    ``## Known Risks``）；**绝不**碰 source 原文、Source Excerpt、Human Note。
    """
    if query is not None:
        return _do_bm25_recall(
            config=config,
            query=query,
            track=track,
            project=project,
            tags=list(tag),
            source_type=source_type,
            status=status,
            include_drafts=include_drafts,
            since=since,
            until=until,
            limit=limit,
            output_format=output_format,
            explain=explain,
            ranking=ranking,
            weight_bm25=weight_bm25,
            weight_value_score=weight_value_score,
            weight_review_due=weight_review_due,
        )

    return _do_rule_recall(
        config=config,
        track=track,
        project=project,
        tag=tag,
        keyword=keyword,
        source_type=source_type,
        status=status,
        include_drafts=include_drafts,
        since=since,
        until=until,
        limit=limit,
        sort=sort,
        output_format=output_format,
    )


def _do_rule_recall(
    *,
    config: Path,
    track: str | None,
    project: str | None,
    tag: list[str],
    keyword: str | None,
    source_type: str | None,
    status: str,
    include_drafts: bool,
    since: str | None,
    until: str | None,
    limit: int,
    sort: str,
    output_format: str,
) -> None:
    """规则路径 recall：从卡片白名单字段做过滤 / 排序 / 输出。

    架构边界：
    - 与 _do_bm25_recall 平行的 cli.py 内部 helper；不是新模块。原因：
      它紧耦合 cli.py 的 console / RunLogger / _filters_dict / _hash_keyword
      / _card_to_safe_dict / _safe_date / _parse_date / _pp 等本地 utility，
      抽成新模块会显著扩大边界但收益不大。
    - 仍然不读 source 原文 / Source Excerpt / Human Note；只走 cards 模块的
      白名单读取。
    - 输出层 4 个 format 与原实现等价（json / markdown / table / compact），
      不引入新 markup 行为。
    """
    result = _rule_recall_result(
        config=config,
        track=track,
        project=project,
        tag=tag,
        keyword=keyword,
        source_type=source_type,
        status=status,
        include_drafts=include_drafts,
        since=since,
        until=until,
        limit=limit,
        sort=sort,
    )
    _log_rule_recall(
        result=result,
        track=track,
        project=project,
        tag=tag,
        source_type=source_type,
        status=status,
        include_drafts=include_drafts,
        since=since,
        until=until,
        limit=limit,
        sort=sort,
        output_format=output_format,
    )
    _print_rule_recall(
        result=result,
        track=track,
        project=project,
        tag=tag,
        status=status,
        since=since,
        until=until,
        limit=limit,
        sort=sort,
        output_format=output_format,
    )




# ---------------------------------------------------------------------------
# v0.3 — BM25 lexical recall + index 子命令
# ---------------------------------------------------------------------------
# 设计契约（详见 README.md 的 lexical recall 说明）：
# 1. BM25 是**纯本地词法检索**，不调用 LLM、不读 .env、不联网。
# 2. 索引只构建在 Knowledge Card 的安全字段上（frontmatter + 白名单 body
#    section），永远不索引 source 原文 / Source Excerpt / Human Note。
# 3. 索引产物落在 `.mindforge/index/bm25.json`，由 .gitignore 挡住。
# 4. recall 默认仍只查 human_approved；--include-drafts 显式打开。


index_app = typer.Typer(
    add_completion=False,
    help="BM25 本地索引子命令（v0.3，纯词法、不联网、不调 LLM）",
    no_args_is_help=True,
)


def _do_bm25_recall(
    *,
    config: Path,
    query: str,
    track: str | None,
    project: str | None,
    tags: list[str],
    source_type: str | None,
    status: str,
    include_drafts: bool,
    since: str | None,
    until: str | None,
    limit: int,
    output_format: str,
    explain: bool,
    ranking: str = "bm25",
    weight_bm25: float | None = None,
    weight_value_score: float | None = None,
    weight_review_due: float | None = None,
) -> None:
    """BM25 / hybrid CLI wrapper；核心检索逻辑在 recall_service。"""
    if not query.strip():
        console.print("[red]query is empty; local lexical recall needs a keyword.[/red]")
        console.print(
            "This is local lexical recall only: not RAG, not embedding, no LLM call.\n"
            "Safe next command: mindforge recall --query <keyword>",
            markup=False,
        )
        raise typer.Exit(code=2)
    cfg = load_cfg(config, read_env=False)
    recall_query = RecallQuery(
        query=query,
        track=track,
        project=project,
        tags=tuple(tags),
        source_type=source_type,
        status=status,
        include_drafts=include_drafts,
        since=_parse_date(since),
        until=_parse_date(until),
        limit=limit,
        output_format=output_format,
        explain=explain,
        ranking=ranking,
        weight_bm25=weight_bm25,
        weight_value_score=weight_value_score,
        weight_review_due=weight_review_due,
    )
    try:
        result = run_bm25_recall(cfg, recall_query)
    except RecallServiceError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e

    if output_format != "json":
        render_active_vault_resolution_notice(cfg)
        for warning in result.warnings:
            console.print(f"[yellow]{warning}[/yellow]")
        console.print(
            "[dim]Boundary: local lexical recall only; not RAG, not embedding, no LLM call.[/dim]"
        )
    else:
        for warning in result.warnings:
            console.print(f"[yellow]{warning}[/yellow]")

    # 不把 query 原文写入 telemetry/runs；只记录是否提供 + hash 化指纹。
    kw_provided, kw_hash = _hash_keyword(query)
    with RunLogger(cfg.state.runs_path, command="recall_bm25") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "recall_bm25_executed",
            count=result.count,
            filters=_filters_dict(
                track=track,
                project=project,
                tags=list(tags),
                source_type=source_type,
                status=status,
                include_drafts=include_drafts,
                since=since,
                until=until,
                limit=limit,
                explain=explain,
                used_disk_index=result.index.used_disk,
                ranking_mode=ranking,
                index_stale=result.index.stale,
                weight_source=result.weight_source,
            ),
            keyword_provided=kw_provided,
            keyword_hash=kw_hash,
            output_format=output_format,
        )

    render_recall_result(
        console=console,
        result=result,
        output_format=output_format,
        context=RecallRenderContext(
            keyword_provided=kw_provided,
            keyword_hash=kw_hash,
            since=since,
            until=until,
        ),
    )


@index_app.command("rebuild")
def index_rebuild(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """全量重建 BM25 本地索引到 ``<workdir>/index/bm25.json``。

    幂等：永远写整文件（先写 .tmp 再原子 rename）。索引内容只来自当前
    Knowledge Card 的安全字段；无网络、无 LLM。
    """
    from . import lexical_index as lx

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    result = lx.rebuild_index_for_config(cfg)
    if result.scan_error_count:
        console.print(f"[yellow]跳过 {result.scan_error_count} 张损坏卡片[/yellow]")
    console.print(
        f"[green]✓ 索引已写入[/green] {result.path} · "
        f"卡片={result.card_count} · avgdl={result.avgdl:.1f} · "
        f"config_hash={result.config_hash} · 时间={result.built_at}"
    )


@index_app.command("status")
def index_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("compact", "--format", help="compact (默认) | json"),
    as_json: bool = typer.Option(False, "--json", help="等价于 --format json（v0.3.2 加）"),
) -> None:
    """打印索引存在性、字段权重、staleness 摘要。不读 query、不打印卡片正文。"""
    return _do_index_status(config=config, output_format="json" if as_json else output_format)


@index_app.command("info")
def index_info(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("compact", "--format", help="compact (默认) | json"),
    as_json: bool = typer.Option(False, "--json", help="等价于 --format json"),
) -> None:
    """v0.3.2：``index status`` 的别名，配合 ``--json`` 给机器可读的索引快照。

    JSON schema 稳定（version=1），字段：
      index_path / exists / stale / card_count / last_built_at /
      included_statuses / config_hash / current_config_hash /
      field_weights / k1 / b / ranking_defaults / hybrid_weights / tokenizer
    """
    return _do_index_status(config=config, output_format="json" if as_json else output_format)


def _do_index_status(*, config: Path, output_format: str) -> None:
    from . import lexical_index as lx
    from .cards import iter_cards

    cfg = load_cfg(config, read_env=False)
    idx_path = lx.default_index_path(cfg.state.workdir)  # type: ignore[attr-defined]
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    fw_cur = lx.resolve_field_weights(cfg.search.bm25.fields)
    cur_hash = lx.compute_config_hash(field_weights=fw_cur, k1=cfg.search.bm25.k1, b=cfg.search.bm25.b)

    # ── 索引不存在分支 ──
    if not idx_path.exists():
        if output_format == "json":
            import json as _json
            print(_json.dumps({
                "version": 1,
                "index_path": str(idx_path),
                "exists": False,
                "stale": True,
                "card_count": len(scan.cards),
                "last_built_at": None,
                "included_statuses": ["human_approved", "ai_draft"],
                "config_hash": None,
                "current_config_hash": cur_hash,
                "field_weights": fw_cur,
                "k1": cfg.search.bm25.k1,
                "b": cfg.search.bm25.b,
                "ranking_defaults": "bm25",
                "hybrid_weights": dict(cfg.search.hybrid.weights),
                "tokenizer": "ascii_word_plus_cjk_char_v1",
            }, ensure_ascii=False, indent=2))
            return
        render_active_vault_resolution_notice(cfg)
        console.print("[yellow]索引文件不存在[/yellow]")
        console.print(f"  路径：{idx_path}")
        console.print(f"  当前 vault 卡片数：{len(scan.cards)}")
        console.print("  建议：[bold]mindforge index rebuild[/bold]")
        return

    try:
        index = lx.BM25Index.load(idx_path)
    except (lx.IndexFormatError, ValueError, OSError) as e:
        console.print(f"[red]索引读取失败：{e}[/red]")
        console.print("  建议：[bold]mindforge index rebuild[/bold]")
        raise typer.Exit(code=1) from e

    diff = lx.diff_index(index, scan.cards)
    config_drift = bool(index.config_hash) and index.config_hash != cur_hash
    fresh = diff.fresh and not config_drift

    if output_format == "json":
        import json as _json
        print(_json.dumps({
            "version": 1,
            "index_path": str(idx_path),
            "exists": True,
            "stale": not fresh,
            "config_drift": config_drift,
            "card_count": diff.indexed_count,
            "current_card_count": diff.current_count,
            "last_built_at": index.built_at,
            "included_statuses": ["human_approved", "ai_draft"],
            "config_hash": index.config_hash or None,
            "current_config_hash": cur_hash,
            "field_weights": index.field_weights,
            "k1": index.k1,
            "b": index.b,
            "avgdl": index.avgdl,
            "ranking_defaults": "bm25",
            "hybrid_weights": dict(cfg.search.hybrid.weights),
            "tokenizer": index.tokenizer_name,
            "added_count": len(diff.added),
            "removed_count": len(diff.removed),
            "changed_count": len(diff.changed),
        }, ensure_ascii=False, indent=2))
        return

    state_label = "[green]fresh[/green]" if fresh else "[yellow]stale[/yellow]"
    render_active_vault_resolution_notice(cfg)
    console.print(f"[bold]Index status[/bold] · {state_label}")
    console.print(f"  路径：{idx_path}")
    console.print(f"  built_at：{index.built_at}")
    console.print(f"  schema_version：{index.schema_version}")
    console.print(f"  tokenizer：{index.tokenizer_name}")
    console.print(f"  k1={index.k1} b={index.b} avgdl={index.avgdl:.1f}")
    console.print(f"  字段权重：{index.field_weights}")
    console.print(f"  config_hash（索引）：{index.config_hash or '(未记录)'}")
    console.print(f"  config_hash（当前）：{cur_hash}")
    if config_drift:
        console.print("  [yellow]⚠ 配置漂移[/yellow]：索引按旧 search 配置打分，结果不可信")
    console.print(f"  索引卡片数：{diff.indexed_count}  当前卡片数：{diff.current_count}")
    if diff.added:
        console.print(f"  [yellow]新增未索引[/yellow]：{len(diff.added)}（前 {min(5,len(diff.added))} 项）")
        for rp in diff.added[:5]:
            console.print(f"    + {rp}")
    if diff.removed:
        console.print(f"  [yellow]索引内已删除[/yellow]：{len(diff.removed)}")
        for rp in diff.removed[:5]:
            console.print(f"    - {rp}")
    if diff.changed:
        console.print(f"  [yellow]mtime 漂移[/yellow]：{len(diff.changed)}")
        for rp in diff.changed[:5]:
            console.print(f"    ~ {rp}")
    if not fresh:
        console.print("  建议：[bold]mindforge index rebuild[/bold]")
