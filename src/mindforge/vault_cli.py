"""Vault helper CLI adapter.

只生成/维护 MindForge 标记的 index/link-candidate 文件，不改 Knowledge Card 正文。
"""
from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, load_cfg

# ---------------------------------------------------------------------------
# vault subcommand — Obsidian 友好度（M5.5 / v0.2.5）
# 设计原则：只生成 _index.md / _link_candidates.md 两类**新文件**，
# 绝不改写已有 Knowledge Card 正文。如果同名文件已存在但缺 marker，
# 就写到 sibling 文件（_index.mindforge.md）避免覆盖人手内容。
# ---------------------------------------------------------------------------


vault_app = typer.Typer(
    add_completion=False,
    help="Obsidian 友好度（M5.5 / v0.2.5）：导航索引与双链候选，仅写新文件。",
)

@vault_app.command("index")
def vault_index(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    reviews_dir: str = typer.Option(
        "80-Reviews",
        "--reviews-dir",
        help="复习索引落盘的目录（相对 vault.root）；不存在则跳过。",
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """生成或更新 cards / projects / reviews 三处的 _index.md。

    幂等：``_index.md`` 由 MindForge 维护，每次重写整个文件；首行的
    ``MINDFORGE:VAULT_INDEX`` marker 保证可识别 / 可覆盖。
    """
    from .vault import refresh_indexes

    cfg = load_cfg(config, read_env=False)
    res = refresh_indexes(
        cfg.vault.root,
        cfg.vault.cards_dir,
        cfg.vault.projects_dir,
        reviews_dir,
        dry_run=dry_run,
    )
    if dry_run:
        console.print("[yellow]dry-run（未写文件）[/yellow]")
    for p in res.written:
        console.print(f"  → {p}")
    console.print(f"[green]✓ 完成：写入 {len(res.written)} 个 index 文件[/green]")


@vault_app.command("links")
def vault_links(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    top_k: int = typer.Option(5, "--top-k", min=1, max=20),
    min_score: int = typer.Option(3, "--min-score", min=1),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """基于安全字段（learning_track / projects / tags / source_type / title token）
    生成 ``_link_candidates.md``。**不**调 LLM、**不**做 embedding、**不**改卡片正文。
    """
    from .cards import iter_cards
    from .vault import build_link_candidates, write_link_candidates

    cfg = load_cfg(config, read_env=False)
    res = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cands = build_link_candidates(res.cards, top_k=top_k, min_score=min_score)
    p, _ = write_link_candidates(
        cfg.vault.root / cfg.vault.cards_dir, cands, dry_run=dry_run
    )
    if dry_run:
        console.print(f"[yellow]dry-run；预览路径 {p}[/yellow]")
    else:
        console.print(f"[green]✓ 写入 {p}[/green]")
    console.print(
        f"  cards={len(cands)}  with_candidates={sum(1 for c in cands if c.candidates)}"
    )


@vault_app.command("refresh")
def vault_refresh(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    reviews_dir: str = typer.Option("80-Reviews", "--reviews-dir"),
) -> None:
    """vault index + vault links 的组合糖；幂等。"""
    vault_index(config=config, reviews_dir=reviews_dir, dry_run=False)
    vault_links(config=config, top_k=5, min_score=3, dry_run=False)


def _obsidian_workflow_command_snippets(
    vault: Path,
    source_hint: str,
    output_dir: Path,
) -> list[tuple[str, str]]:
    """兼容旧测试入口；Obsidian CLI adapter 实现已迁到 obsidian_cli.py。"""
    from .obsidian_cli import _obsidian_workflow_command_snippets as _snippets

    return _snippets(vault, source_hint, output_dir)
