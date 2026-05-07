"""Project memory CLI adapter.

只读/受控写项目上下文：context 不调 LLM、不读 .env、不读 raw source；
update-evidence 只写受控 evidence block。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer

from .cli_runtime import console, load_cfg
from .run_logger import RunLogger

project_app = typer.Typer(add_completion=False, help="项目记忆与上下文（M4）")

# ---------------------------------------------------------------------------
# project list / context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ProjectContextBundle:
    project_names: list[str]
    profiles: dict[str, object]
    cards_by_project: dict[str, list]
    primary_profile: object
    resolved_target: str
    options: object


def _unique_project_names(project_names: list[str]) -> list[str]:
    seen: set[str] = set()
    return [name for name in project_names if not (name in seen or seen.add(name))]


def _context_options_or_exit(
    *,
    target: str | None,
    primary_profile,
    no_prompts: bool,
    include_drafts: bool,
    include_actions: bool,
    include_review_due: bool,
    include_next_step_prompt: bool,
    limit: int,
):
    from .project_context import ProjectContextOptions, resolve_target

    try:
        resolved_target = resolve_target(target, primary_profile)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    return resolved_target, ProjectContextOptions(
        include_prompts=not no_prompts,
        include_drafts=include_drafts,
        include_actions=include_actions,
        include_review_due=include_review_due,
        include_next_step_prompt=include_next_step_prompt,
        limit=limit,
        target=resolved_target,
    )


def _load_project_context_bundle(
    *,
    cfg,
    project_names: list[str],
    target: str | None,
    no_prompts: bool,
    include_drafts: bool,
    include_actions: bool,
    include_review_due: bool,
    include_next_step_prompt: bool,
    limit: int,
) -> _ProjectContextBundle:
    from .cards import filter_cards, iter_cards
    from .project_profile import ProjectProfileError, load_project_profile

    project_names = _unique_project_names(project_names)
    if not project_names:
        console.print("[red]至少需要一个 project_name[/red]")
        raise typer.Exit(code=2)

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    profiles: dict[str, object] = {}
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

    # 多项目模式下，target 解析仅看第一个 found=true 的 profile.default_target。
    primary_profile = next(
        (profiles[name] for name in project_names if profiles[name].found),
        profiles[project_names[0]],
    )
    resolved_target, options = _context_options_or_exit(
        target=target,
        primary_profile=primary_profile,
        no_prompts=no_prompts,
        include_drafts=include_drafts,
        include_actions=include_actions,
        include_review_due=include_review_due,
        include_next_step_prompt=include_next_step_prompt,
        limit=limit,
    )
    return _ProjectContextBundle(
        project_names=project_names,
        profiles=profiles,
        cards_by_project=cards_by_project,
        primary_profile=primary_profile,
        resolved_target=resolved_target,
        options=options,
    )


def _render_project_context_bundle(bundle: _ProjectContextBundle, *, output_format: str) -> tuple[str, int]:
    from .multi_project_context import (
        render_multi_project_context_json,
        render_multi_project_context_markdown,
    )
    from .project_context import (
        render_project_context_json,
        render_project_context_markdown,
    )

    if output_format not in {"markdown", "json"}:
        console.print(f"[red]--format 必须是 markdown 或 json，收到 {output_format!r}[/red]")
        raise typer.Exit(code=2)

    is_multi = len(bundle.project_names) > 1
    if is_multi:
        if output_format == "json":
            out = render_multi_project_context_json(
                bundle.project_names,
                bundle.cards_by_project,
                bundle.profiles,
                options=bundle.options,
            )
        else:
            out = render_multi_project_context_markdown(
                bundle.project_names,
                bundle.cards_by_project,
                bundle.profiles,
                options=bundle.options,
            )
        total_cards = sum(min(len(cards), bundle.options.limit) for cards in bundle.cards_by_project.values())
        return out, total_cards

    single_name = bundle.project_names[0]
    if output_format == "json":
        out = render_project_context_json(
            single_name,
            bundle.cards_by_project[single_name],
            options=bundle.options,
            profile=bundle.profiles[single_name],
        )
    else:
        out = render_project_context_markdown(
            single_name,
            bundle.cards_by_project[single_name],
            options=bundle.options,
            profile=bundle.profiles[single_name],
        )
    return out, min(len(bundle.cards_by_project[single_name]), bundle.options.limit)


def _log_project_context_emitted(
    *,
    cfg,
    bundle: _ProjectContextBundle,
    total_cards: int,
    output_format: str,
) -> None:
    with RunLogger(cfg.state.runs_path, command="project-context") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "project_context_emitted",
            project_name=(
                bundle.project_names[0]
                if len(bundle.project_names) == 1
                else f"<{len(bundle.project_names)} projects>"
            ),
            count=total_cards,
            output_format=output_format,
            target=bundle.resolved_target,
            project_profile_found=bundle.primary_profile.found,
        )


def _write_or_print_project_context(out: str, output: Path | None) -> None:
    if output is None:
        print(out)
        return
    if not output.parent.exists():
        console.print(f"[red]--output 父目录不存在：{output.parent}（请先 mkdir）[/red]")
        raise typer.Exit(code=2)
    output.write_text(out, encoding="utf-8")
    console.print(f"[green]✔ project context 已写入[/green] {output}")


@project_app.command("list")
def project_list(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("markdown", "--format"),
) -> None:
    """列出所有卡片 frontmatter 中出现过的 project（并集去重，按字母序）。"""
    from .cards import iter_cards

    cfg = load_cfg(config, read_env=False)
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

        print(_json.dumps(
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
    from .telemetry import measure

    cfg = load_cfg(config, read_env=False)
    bundle = _load_project_context_bundle(
        cfg=cfg,
        project_names=project_names,
        target=target,
        no_prompts=no_prompts,
        include_drafts=include_drafts,
        include_actions=include_actions,
        include_review_due=include_review_due,
        include_next_step_prompt=include_next_step_prompt,
        limit=limit,
    )

    with measure(
        cfg.state.workdir, cfg.telemetry, "project-context",
        project_count=len(bundle.project_names),
    ) as th:
        out, total_cards = _render_project_context_bundle(bundle, output_format=output_format)
        th.set_counts(card_count=total_cards, result_count=total_cards)
        _log_project_context_emitted(
            cfg=cfg,
            bundle=bundle,
            total_cards=total_cards,
            output_format=output_format,
        )
        _write_or_print_project_context(out, output)


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

    cfg = load_cfg(config, read_env=False)

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
