"""Obsidian command adapter：承接 `mindforge obsidian ...` 子命令。

中文学习型说明：
本模块是 CLI adapter，不是 Obsidian service。它可以依赖 Typer/Rich，因为职责
就是定义子命令、解析参数、渲染人类可见输出，并调用 `obsidian.py` /
`obsidian_stage.py` / `obsidian_workflow.py` 中已有的结构化业务能力。

它不新增功能，不做 apply/write-back，不读取 `.env`，不调用 LLM，不写正式
Obsidian notes。`cli.py` 只负责挂载这里导出的 `obsidian_app`。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .app_context import AppContextError, load_app_config
from .config import MindForgeConfig
from .obsidian_stage import (
    build_preflight_display_plan,
    build_staged_diff_preview_plan,
    build_staged_manifest_payload,
    first_markdown_hint,
    obsidian_export_filename,
    plan_staged_export,
    resolve_obsidian_source_for_preview,
    safe_relative_to,
    staged_export_dir,
)
from .obsidian_workflow import build_obsidian_next_plan, obsidian_workflow_command_snippets
from .obsidian_cli_presenter import (
    build_skipped_notes_table,
    build_stage_preview_table,
    diff_preview_header,
    diff_preview_inspection_hint,
    diff_preview_missing_lines,
    diff_preview_no_changes,
    diff_preview_truncated,
    extract_stage_preview_fields as _stage_preview_fields,
    format_copy_warning,
    format_doctor_icon as _doctor_icon,
    format_dry_run_safety_footer,
    stage_preview_next_command,
)


obsidian_app = typer.Typer(
    add_completion=False,
    help="v0.5 Obsidian Binding：只读扫描真实 Obsidian vault，候选输出只进 staging/review。",
)
console = Console()


def _load_cfg(config_path: Path) -> MindForgeConfig:
    """加载 config，但不读 `.env`。

    中文学习型说明：Obsidian CLI adapter 当前只做 dry-run/staged-export/preflight。
    因此这里故意不提供 read_env=True 路径，避免把真实 provider/env 读取混入
    Obsidian 本地检查流程。
    """

    config_explicit = (config_path != Path("configs/mindforge.yaml"))
    try:
        return load_app_config(
            config_path,
            vault_override=_global_vault_override(),
            config_explicit=config_explicit,
        )
    except AppContextError as e:
        if e.kind == "missing_config":
            console.print(f"[red]✗ 配置文件不存在：{config_path}[/red]")
            console.print(
                "[dim]提示：可以从仓库中的 configs/mindforge.yaml 复制一份到目标位置，"
                "再用 --config 指定，或直接在仓库根运行命令。[/dim]"
            )
            raise typer.Exit(code=2) from e
        console.print(f"[red]✗ 配置错误：{e}[/red]")
        console.print(
            "[dim]提示：请检查 vault.root、sources.enabled、llm.active_profile "
            "三个字段是否合法。[/dim]"
        )
        raise typer.Exit(code=2) from e


def _global_vault_override() -> Path | None:
    """读取 CLI 入口设置的 vault override；不读取 `.env` 文件。"""

    import os as _os

    override = _os.environ.get("MINDFORGE_VAULT_OVERRIDE")
    if not override:
        return None
    return Path(override)


def _obsidian_vault_override(arg: Path | None) -> Path | None:
    """解析 Obsidian vault override；只读环境变量，不读取 `.env` 文件。"""

    import os

    if arg is not None:
        return arg.expanduser().resolve()
    env = os.environ.get("MINDFORGE_OBSIDIAN_VAULT_OVERRIDE")
    return Path(env).expanduser().resolve() if env else None


def _obsidian_options(
    cfg: MindForgeConfig,
    vault_override: Path | None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> tuple[Path, object]:
    """把 CLI 参数解析成 Obsidian scan options；不做扫描业务本身。"""

    from .obsidian import ObsidianScanOptions, resolve_obsidian_vault

    vault_root = resolve_obsidian_vault(
        cfg.obsidian,
        cfg.vault.root,
        override=_obsidian_vault_override(vault_override),
    )
    return vault_root, ObsidianScanOptions(
        vault_root=vault_root,
        include_dirs=tuple(include) if include else cfg.obsidian.include_dirs,
        exclude_dirs=(*cfg.obsidian.exclude_dirs, *(exclude or [])),
    )


def _obsidian_copy_warning() -> None:
    console.print(format_copy_warning())


def _print_obsidian_issues(vault_root: Path, issues: list[object]) -> None:
    """打印单文件跳过原因，不输出 note 正文。"""

    table = build_skipped_notes_table(vault_root, list(issues))
    if table is None:
        return
    console.print(table)


def _print_stage_preview(
    *,
    vault_root: Path,
    source: Path,
    target: Path | None,
    action: str,
    skipped_reason: str,
    content_hash: str = "-",
    title: str = "-",
    wikilinks: list[str] | None = None,
    frontmatter_keys: list[str] | None = None,
    source_type: str = "-",
    source_exists: bool | None = None,
    source_in_vault: bool | None = None,
) -> None:
    """输出 Obsidian stage dry-run preview，且不写文件。"""

    table = build_stage_preview_table(
        vault_root=vault_root,
        source=source,
        target=target,
        action=action,
        skipped_reason=skipped_reason,
        content_hash=content_hash,
        title=title,
        wikilinks=wikilinks,
        frontmatter_keys=frontmatter_keys,
        source_type=source_type,
        source_exists=source_exists,
        source_in_vault=source_in_vault,
    )
    console.print(table)
    source_hint = safe_relative_to(source, vault_root) or str(source)
    print(
        "next command: "
        + stage_preview_next_command(vault_root=vault_root, source_hint=source_hint)
    )
    if skipped_reason:
        print(f"skipped reason: {skipped_reason}")
    console.print(format_dry_run_safety_footer())


def _print_staged_diff_preview(existing: Path, proposed_content: str) -> None:
    """打印 staged export 的轻量 diff；只比较 staged 目录，不写正式 notes。"""

    plan = build_staged_diff_preview_plan(existing, proposed_content)
    if not plan.exists:
        for line in diff_preview_missing_lines(plan.manual_inspection_hint):
            console.print(line)
        return
    console.print(diff_preview_header())
    if not plan.has_changes:
        console.print(diff_preview_no_changes())
        return
    for line in plan.diff_lines:
        console.print(line, markup=False)
    if plan.truncated_count:
        console.print(diff_preview_truncated(plan.truncated_count))
    console.print(diff_preview_inspection_hint(plan.manual_inspection_hint))


def _write_obsidian_staged_export(
    *,
    cfg: MindForgeConfig,
    vault_root: Path,
    source_path: Path,
    doc: Any,
    content: str,
    output_dir: Path | None,
    diff_preview: bool,
) -> Path:
    """写 staged export markdown + manifest，明确不写正式 Obsidian notes。"""

    import json as _json

    plan = plan_staged_export(cfg=cfg, vault_root=vault_root, doc=doc, output_dir=output_dir)
    if diff_preview:
        _print_staged_diff_preview(plan.proposed_path, content)
    plan.export_dir.mkdir(parents=True, exist_ok=True)
    plan.target_path.write_text(content, encoding="utf-8")
    payload = build_staged_manifest_payload(plan=plan, source_path=source_path, doc=doc)
    plan.manifest_path.write_text(_json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    console.print(f"[green]✓ staged export written[/green] {plan.target_path}")
    console.print(f"[green]✓ manifest written[/green] {plan.manifest_path}")
    if plan.formal_conflicts:
        console.print("[yellow]可能存在正式 vault 同名 note；仅提示人工检查，未覆盖：[/yellow]")
        for item in plan.formal_conflicts[:10]:
            console.print(f"  - {safe_relative_to(item, vault_root) or item}")
    console.print("[dim]说明：未写正式 Obsidian notes；未移动 source；未读取 .env；未调用 LLM。[/dim]")
    console.print(
        f"Next: mindforge obsidian preflight --vault {vault_root} --manifest {plan.manifest_path}",
        markup=False,
    )
    return plan.target_path


def _preview_stage_skip(
    *,
    vault_root: Path,
    source_path: Path,
    skipped_reason: str,
    source_exists: bool,
    source_in_vault: bool,
) -> None:
    _print_stage_preview(
        vault_root=vault_root,
        source=source_path,
        target=None,
        action="skipped",
        skipped_reason=skipped_reason,
        source_exists=source_exists,
        source_in_vault=source_in_vault,
    )


def _reject_or_preview_stage_skip(
    *,
    vault_root: Path,
    source_path: Path,
    dry_run: bool,
    skipped_reason: str,
    source_exists: bool,
    source_in_vault: bool,
    error_text: str,
) -> bool:
    """处理 stage source validation 失败。

    中文学习型说明：dry-run 路径必须展示安全摘要并返回；write 路径必须显式
    非零退出。这个 helper 把“预览 vs 拒绝”的边界固定在一个地方，避免
    ``obsidian_stage`` 命令体重新长出重复分支。
    """

    if dry_run:
        _preview_stage_skip(
            vault_root=vault_root,
            source_path=source_path,
            skipped_reason=skipped_reason,
            source_exists=source_exists,
            source_in_vault=source_in_vault,
        )
        return False
    console.print(f"[red]✗ {error_text}[/red]")
    raise typer.Exit(code=2)


def _stage_source_is_valid(*, vault_root: Path, options: object, source_path: Path, dry_run: bool) -> bool:
    from .obsidian import obsidian_path_in_scope

    if not vault_root.exists() or not vault_root.is_dir():
        _preview_stage_skip(
            vault_root=vault_root,
            source_path=source_path,
            skipped_reason="Obsidian vault 不存在或不是目录；请检查 --vault。",
            source_exists=source_path.exists(),
            source_in_vault=safe_relative_to(source_path, vault_root) is not None,
        )
        return False
    if safe_relative_to(source_path, vault_root) is None:
        return _reject_or_preview_stage_skip(
            vault_root=vault_root,
            source_path=source_path,
            dry_run=dry_run,
            skipped_reason="--source 必须位于 Obsidian vault 内，避免误处理外部资料。",
            source_exists=source_path.exists(),
            source_in_vault=False,
            error_text="--source 必须位于 Obsidian vault 内，避免误处理真实外部资料。",
        )
    if not source_path.exists():
        return _reject_or_preview_stage_skip(
            vault_root=vault_root,
            source_path=source_path,
            dry_run=dry_run,
            skipped_reason="source note 不存在。",
            source_exists=False,
            source_in_vault=True,
            error_text=f"source note 不存在：{source_path}",
        )
    if source_path.is_dir():
        return _reject_or_preview_stage_skip(
            vault_root=vault_root,
            source_path=source_path,
            dry_run=dry_run,
            skipped_reason="--source 是目录；stage 需要单个 Markdown note。",
            source_exists=True,
            source_in_vault=True,
            error_text=f"--source 是目录；请传单个 Markdown note：{source_path}",
        )
    if source_path.suffix.lower() != ".md":
        return _reject_or_preview_stage_skip(
            vault_root=vault_root,
            source_path=source_path,
            dry_run=dry_run,
            skipped_reason="--source 不是 Markdown 文件。",
            source_exists=True,
            source_in_vault=True,
            error_text=f"--source 不是 Markdown 文件：{source_path}",
        )

    in_scope, scope_reason = obsidian_path_in_scope(source_path, options)  # type: ignore[arg-type]
    if not in_scope:
        return _reject_or_preview_stage_skip(
            vault_root=vault_root,
            source_path=source_path,
            dry_run=dry_run,
            skipped_reason=f"source 不在当前 include/exclude scope：{scope_reason}。",
            source_exists=True,
            source_in_vault=True,
            error_text=f"source 不在当前 include/exclude scope：{scope_reason}。",
        )
    return True


def _load_stage_document_or_exit(*, vault_root: Path, source_path: Path, dry_run: bool) -> Any | None:
    from .sources.obsidian_vault import ObsidianVaultSourceAdapter

    adapter = ObsidianVaultSourceAdapter(vault_root)
    try:
        return adapter.load(str(source_path))
    except Exception as e:  # noqa: BLE001 - 只打印安全错误摘要，不输出 note 正文
        if dry_run:
            _preview_stage_skip(
                vault_root=vault_root,
                source_path=source_path,
                skipped_reason=f"source 解析失败：{type(e).__name__}: {e}",
                source_exists=True,
                source_in_vault=True,
            )
            return None
        console.print(f"[red]✗ source 解析失败：{type(e).__name__}: {e}[/red]")
        raise typer.Exit(code=2) from e


def _stage_target_or_exit(
    *,
    cfg: MindForgeConfig,
    vault_root: Path,
    doc: Any,
    output_dir: Path | None,
    staged_export: bool,
) -> Path:
    if staged_export:
        return staged_export_dir(cfg, output_dir) / obsidian_export_filename(doc)

    from .obsidian import stage_output_path

    try:
        return stage_output_path(vault_root, cfg.obsidian, doc, output_dir)
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=2) from e


def _stage_preview_action(*, staged_export: bool, target: Path) -> str:
    if staged_export:
        return "would-create-staged-export" if not target.exists() else "would-update-staged-export"
    return "would-create-staging-candidate" if not target.exists() else "would-update-staging-candidate"


def _print_stage_success_preview(
    *,
    vault_root: Path,
    source_path: Path,
    target: Path,
    doc: Any,
    staged_export: bool,
) -> None:
    preview_fields = _stage_preview_fields(doc)
    _print_stage_preview(
        vault_root=vault_root,
        source=source_path,
        target=target,
        action=_stage_preview_action(staged_export=staged_export, target=target),
        skipped_reason="",
        content_hash=doc.content_hash,
        title=str(preview_fields["title"]),
        wikilinks=list(preview_fields["wikilinks"]),  # type: ignore[arg-type]
        frontmatter_keys=list(preview_fields["frontmatter_keys"]),  # type: ignore[arg-type]
        source_type=str(preview_fields["source_type"]),
        source_exists=True,
        source_in_vault=True,
    )


def _write_regular_stage_candidate(*, target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    console.print(f"[green]✓ staged[/green] {target}")
    console.print("[dim]说明：未修改 source note、未移动文件、未重写 wikilinks、未 auto approve。[/dim]")


@obsidian_app.command("scan")
def obsidian_scan(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        "--obsidian-vault",
        help="Obsidian vault 路径；覆盖 obsidian.vault_path。",
    ),
    include: list[str] | None = typer.Option(None, "--include", help="本次 scan 的 include pattern，可重复"),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="本次 scan 的 exclude pattern，可重复"),
    limit: int = typer.Option(0, "--limit", min=0, help="最多展示多少条（0=全部）"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON 安全摘要"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """只读扫描 Obsidian Markdown note，输出安全摘要，不输出正文。"""

    from .obsidian import load_obsidian_documents_with_issues, summarize_doc

    cfg = _load_cfg(config)
    vault_root, options = _obsidian_options(cfg, vault, include=include, exclude=exclude)
    try:
        docs, issues = load_obsidian_documents_with_issues(options, limit=limit)
    except (FileNotFoundError, NotADirectoryError) as e:
        console.print(f"[red]✗ {e}[/red]")
        console.print("[dim]提示：传 --vault <ObsidianVault>，或配置 obsidian.vault_path。[/dim]")
        raise typer.Exit(code=2) from e

    rows = [summarize_doc(doc) for doc in docs]
    if json_output:
        import json as _json

        print(_json.dumps({"version": 1, "vault": str(vault_root), "notes": rows}, ensure_ascii=False))
        return

    _obsidian_copy_warning()
    console.print(
        f"[dim]scope: include={', '.join(options.include_dirs) or '<all markdown>'}; "
        f"exclude={', '.join(options.exclude_dirs) or '<default runtime dirs>'}[/dim]"
    )
    table = Table(title=f"Obsidian scan · {vault_root}", show_lines=False)
    for col in ("title", "relative_path", "tags", "wikilinks", "headings", "hash"):
        table.add_column(col, overflow="fold")
    for row in rows:
        table.add_row(
            str(row["title"] or ""),
            str(row["relative_path"]),
            ", ".join(row["tags"]) or "-",
            str(row["wikilink_count"]),
            str(row["heading_count"]),
            str(row["content_hash"])[:18] + "...",
        )
    console.print(table)
    console.print(
        f"[green]✓ scanned {len(rows)} Obsidian notes[/green] "
        "[dim](只读；未输出 note 全文；未写正式 notes)[/dim]"
    )
    if not rows:
        console.print(
            "[yellow]未发现 Markdown notes。请检查 --vault、include_dirs，或先复制一个"
            "非敏感 Obsidian vault 副本再 dry-run。[/yellow]"
        )
    _print_obsidian_issues(vault_root, issues)
    if (vault_root / ".obsidian").is_dir():
        console.print("[dim]检测到 .obsidian/；仅确认存在，未读取其配置内容。[/dim]")
    console.print(f"Next: mindforge obsidian links --vault {vault_root}", markup=False)
    console.print(
        f"Then: mindforge obsidian stage --vault {vault_root} --source {first_markdown_hint(vault_root)} --dry-run",
        markup=False,
    )


@obsidian_app.command("links")
def obsidian_links(
    vault: Path | None = typer.Option(None, "--vault", "--obsidian-vault"),
    include: list[str] | None = typer.Option(None, "--include", help="本次 links 的 include pattern，可重复"),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="本次 links 的 exclude pattern，可重复"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """只读解析 Obsidian [[wikilinks]]，不建 graph DB、不改 note。"""

    from .obsidian import build_link_entries, load_obsidian_documents_with_issues

    cfg = _load_cfg(config)
    vault_root, options = _obsidian_options(cfg, vault, include=include, exclude=exclude)
    try:
        docs, issues = load_obsidian_documents_with_issues(options)
    except (FileNotFoundError, NotADirectoryError) as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=2) from e
    entries = build_link_entries(docs)
    if json_output:
        import json as _json

        print(_json.dumps({"version": 1, "vault": str(vault_root), "links": entries}, ensure_ascii=False))
        return

    _obsidian_copy_warning()
    console.print(
        f"[dim]scope: include={', '.join(options.include_dirs) or '<all markdown>'}; "
        f"exclude={', '.join(options.exclude_dirs) or '<default runtime dirs>'}[/dim]"
    )
    table = Table(title=f"Obsidian links · {vault_root}", show_lines=False)
    table.add_column("note", overflow="fold")
    table.add_column("outgoing_links", overflow="fold")
    table.add_column("incoming", justify="right")
    for item in entries:
        table.add_row(
            item["note"],
            ", ".join(item["outgoing_links"]) or "-",
            str(item["incoming_count"]),
        )
    console.print(table)
    if not entries:
        console.print("[yellow]未发现可解析的 Markdown notes；未建立链接报告。[/yellow]")
    _print_obsidian_issues(vault_root, issues)
    console.print("说明：只读解析 [[wikilinks]]；不做 graph DB / RAG / embedding。", markup=False)
    console.print(
        f"Next: mindforge obsidian stage --vault {vault_root} --source {first_markdown_hint(vault_root)} --dry-run",
        markup=False,
    )


@obsidian_app.command("stage")
def obsidian_stage(
    source: Path = typer.Option(..., "--source", help="要生成 staging 候选的 Obsidian note"),
    vault: Path | None = typer.Option(None, "--vault", "--obsidian-vault"),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="输出目录；普通 staging 限定在 vault staging/review，--staged-export 时可为任意 staged export 目录。",
    ),
    staged_export: bool = typer.Option(False, "--staged-export", help="写入 staged export directory，不写正式 Obsidian notes"),
    diff_preview: bool = typer.Option(False, "--diff", help="显示 proposed markdown 与已有 staged file 的轻量 diff"),
    include: list[str] | None = typer.Option(None, "--include", help="本次 stage 的 include pattern，可重复"),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="本次 stage 的 exclude pattern，可重复"),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--write",
        help="默认 dry-run；真正写入需 --write --confirm。",
    ),
    confirm: bool = typer.Option(False, "--confirm", help="搭配 --write 才允许落盘"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """把 Obsidian note 的候选加工结果写入 staging/review，而不是修改原 note。"""

    from .obsidian import build_stage_markdown

    cfg = _load_cfg(config)
    vault_root, options = _obsidian_options(cfg, vault, include=include, exclude=exclude)
    _obsidian_copy_warning()
    source_path = resolve_obsidian_source_for_preview(source, vault_root)
    if not _stage_source_is_valid(
        vault_root=vault_root,
        options=options,
        source_path=source_path,
        dry_run=dry_run,
    ):
        return

    doc = _load_stage_document_or_exit(vault_root=vault_root, source_path=source_path, dry_run=dry_run)
    if doc is None:
        return
    target = _stage_target_or_exit(
        cfg=cfg,
        vault_root=vault_root,
        doc=doc,
        output_dir=output_dir,
        staged_export=staged_export,
    )
    content = build_stage_markdown(doc)

    if dry_run:
        _print_stage_success_preview(
            vault_root=vault_root,
            source_path=source_path,
            target=target,
            doc=doc,
            staged_export=staged_export,
        )
        return
    if not confirm:
        console.print("[red]✗ 写入 staging 需要显式 --write --confirm。[/red]")
        raise typer.Exit(code=2)

    if staged_export:
        _write_obsidian_staged_export(
            cfg=cfg,
            vault_root=vault_root,
            source_path=source_path,
            doc=doc,
            content=content,
            output_dir=output_dir,
            diff_preview=diff_preview,
        )
        return

    _write_regular_stage_candidate(target=target, content=content)


@obsidian_app.command("preflight")
def obsidian_preflight_cmd(
    manifest: Path = typer.Option(..., "--manifest", help="staged export manifest JSON 路径"),
    vault: Path | None = typer.Option(None, "--vault", "--obsidian-vault"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """只读检查 staged export 是否具备未来 write-gate 条件；本版本不写正式 notes。"""

    from .obsidian import obsidian_preflight, resolve_obsidian_vault

    cfg = _load_cfg(config)
    vault_root = resolve_obsidian_vault(
        cfg.obsidian,
        cfg.vault.root,
        override=_obsidian_vault_override(vault),
    )
    result = obsidian_preflight(
        vault_root=vault_root,
        manifest_path=manifest,
        default_staged_root=cfg.state.workdir / "staged" / "obsidian",
    )
    display = build_preflight_display_plan(result)

    _obsidian_copy_warning()
    console.print(f"[bold]MindForge Obsidian preflight[/bold] · {result.status}")
    table = Table(title="Write-gate prep", show_lines=False)
    table.add_column("field", style="bold")
    table.add_column("value", overflow="fold")
    table.add_row("status", result.status)
    table.add_row("manifest", str(result.manifest_path))
    table.add_row("staged markdown", str(result.staged_markdown or "-"))
    table.add_row("proposed target", str(result.proposed_target or "-"))
    table.add_row("backup path", str(result.backup_path or "-"))
    table.add_row("recovery plan", result.recovery_plan or "-")
    table.add_row("formal note writes", "NO - this version only validates write-gate readiness")
    table.add_row("future gate", display.future_gate)
    console.print(table)

    if result.blocked:
        console.print("[red]BLOCKED reasons[/red]")
        for reason in result.blocked:
            console.print(f"  - {reason}", markup=False)
            print(f"BLOCKED reason: {reason}")
    if result.warnings:
        console.print("[yellow]WARNING reasons[/yellow]")
        for reason in result.warnings:
            console.print(f"  - {reason}", markup=False)
            print(f"WARNING reason: {reason}")
    if result.status == "PASS":
        console.print(f"[green]{display.outcome_message}[/green]")
    elif result.status == "WARNING":
        console.print(f"[yellow]{display.outcome_message}[/yellow]")
    else:
        console.print(f"[red]{display.outcome_message}[/red]")
    console.print(display.next_action, markup=False)
    print(f"future gate: {display.future_gate}")
    console.print(display.no_write_boundary, markup=False)
    if display.exit_code:
        raise typer.Exit(code=display.exit_code)


@obsidian_app.command("next")
def obsidian_next(
    vault: Path | None = typer.Option(None, "--vault", "--obsidian-vault"),
    output_dir: Path = typer.Option(
        Path("/tmp/mindforge-obsidian-staged"),
        "--output-dir",
        help="推荐 staged export 目录；仅用于生成命令建议，不会创建目录。",
    ),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """输出 Obsidian staged workflow 路径；只做导航，不执行命令、不写 vault。"""

    from .obsidian import resolve_obsidian_vault

    cfg = _load_cfg(config)
    vault_root = resolve_obsidian_vault(
        cfg.obsidian,
        cfg.vault.root,
        override=_obsidian_vault_override(vault),
    )
    plan = build_obsidian_next_plan(vault_root=vault_root, output_dir=output_dir)
    console.print("[bold]MindForge Obsidian staged workflow[/bold]")
    console.print(f"vault copy: {plan.vault_root}")
    console.print(f"staged export dir: {plan.output_dir}")
    print(plan.safety_line)
    print(plan.boundary_line)
    console.print("[bold]Current status[/bold]")
    print(f"- vault exists: {'yes' if plan.vault_exists else 'no'}")
    print(f"- safe mode: {plan.safe_mode_line}")
    print(f"- staged exports: {plan.staged_export_count}")
    print(f"- manifests: {plan.manifest_count}")
    if plan.latest_manifest is not None:
        print(f"- latest manifest: {plan.latest_manifest}")
        print(f"- recommended next: {plan.recommended_next}")
    else:
        print(f"- recommended next: {plan.recommended_next}")
    console.print("[bold]Commands[/bold]")
    for item in plan.commands:
        print(f"- {item.command}")
        print(f"  {item.note}")
    console.print("[bold]Manual inspection[/bold]")
    for step in plan.manual_inspection_steps:
        print(f"- {step}")


def _obsidian_workflow_command_snippets(
    vault: Path,
    source_hint: str,
    output_dir: Path,
) -> list[tuple[str, str]]:
    """兼容旧测试入口；实际 snippets 已迁到 service 层。"""

    return [(item.command, item.note) for item in obsidian_workflow_command_snippets(vault, source_hint, output_dir)]


@obsidian_app.command("doctor")
def obsidian_doctor(
    vault: Path | None = typer.Option(None, "--vault", "--obsidian-vault"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """检查 Obsidian binding 安全边界。"""

    from .obsidian import obsidian_doctor_rows, resolve_obsidian_vault

    cfg = _load_cfg(config)
    vault_root = resolve_obsidian_vault(
        cfg.obsidian,
        cfg.vault.root,
        override=_obsidian_vault_override(vault),
    )
    rows = obsidian_doctor_rows(vault_root, cfg.obsidian)
    console.print(f"[bold]MindForge Obsidian doctor[/bold] · {vault_root}")
    _obsidian_copy_warning()
    for state, label, detail in rows:
        console.print(f"  {_doctor_icon(state)} {label:<20}: {detail}")
    staged_dir = (cfg.state.workdir / "staged" / "obsidian").expanduser().resolve()
    staged_count = len(list(staged_dir.glob("*"))) if staged_dir.exists() else 0
    console.print(
        f"  {_doctor_icon('warn' if staged_count else 'ok')} {'staged export dir':<20}: "
        f"{staged_dir} · files={staged_count}"
    )
    if not vault_root.exists():
        console.print("[critical] 设置 Obsidian vault：mindforge obsidian doctor --vault <path>", markup=False)
        raise typer.Exit(code=2)
    console.print("[bold]Next steps[/bold]")
    console.print("  [recommended] mindforge obsidian scan --vault <path> --limit 20", markup=False)
    console.print("  [recommended] mindforge obsidian links --vault <path>", markup=False)
    console.print(
        "  [info] mindforge obsidian stage --vault <path> --source <note.md> --dry-run",
        markup=False,
    )
    console.print(
        "  [info] mindforge obsidian stage --vault <path> --source <note.md> --staged-export --write --confirm",
        markup=False,
    )
    console.print("  [info] mindforge obsidian preflight --vault <path> --manifest <export.manifest.json>", markup=False)
    console.print("  [info] mindforge obsidian next --vault <path>", markup=False)
    console.print("[dim]不建议、也不会直接修改正式 Obsidian notes。[/dim]")


__all__ = ["obsidian_app"]
