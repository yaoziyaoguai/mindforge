"""Daily loop / command discovery CLI adapter.

个人每日入口只组合可观察本地事实：state、frontmatter、索引文件和静态命令地图。
不读取 source 原文、不调 LLM、不自动 approve、不写正式 Obsidian notes。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import typer

from .app_context import AppContextError, load_app_config
from .checkpoint import Checkpoint
from .cli_runtime import console, global_vault_override, load_cfg
from .config import MindForgeConfig
from .models import ItemState
from .model_setup_readiness import model_setup_readiness
from .next_suggestions import NextSuggestion, compact_next_suggestions, next_suggestions

daily_app = typer.Typer(add_completion=False)

# ---------------------------------------------------------------------------
# version — 打印版本与运行配置摘要（不含 secret）
# 设计意图：终端用户最常问的是"我装的哪个版本？现在用的哪个 workspace / model？"
# 输出严格仅元数据：不读取 provider key，不打印 api_key / model 名以外的敏感字段。
# ---------------------------------------------------------------------------


@daily_app.command()
def version(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径（找不到也不报错，仅展示 MindForge 版本）",
    ),
) -> None:
    """打印 MindForge 版本与当前运行配置摘要。"""
    from . import __version__
    from .telemetry import telemetry_path

    console.print(f"[bold]MindForge[/bold] v{__version__}")
    console.print(f"- config: {config}")
    if not config.exists():
        console.print("  [yellow](config 文件不存在；以下字段省略)[/yellow]")
        console.print("[dim]提示：复制 configs/mindforge.yaml 到目标位置后重试。[/dim]")
        return
    config_explicit = (config != Path("configs/mindforge.yaml"))
    try:
        cfg = load_app_config(
            config,
            vault_override=global_vault_override(),
            config_explicit=config_explicit,
        )
    except AppContextError as e:
        console.print(f"  [red]config 解析失败：{e}[/red]")
        raise typer.Exit(code=2) from e

    console.print(f"- vault.root        : {cfg.vault.root}")
    console.print(f"- vault.inbox_root  : {cfg.vault.inbox_root}")
    console.print(f"- vault.cards_dir   : {cfg.vault.cards_dir}")
    console.print(f"- vault.projects_dir: {cfg.vault.projects_dir}")
    console.print(f"- state.workdir     : {cfg.state.workdir}")
    console.print(f"- llm.default_model  : {cfg.llm.default_model or '(not set)'}")

    enabled_sources = sorted(cfg.sources.enabled)
    console.print(f"- sources.enabled   : {', '.join(enabled_sources) or '(none)'}")
    console.print(f"- telemetry.enabled : {cfg.telemetry.enabled}")
    console.print(f"- telemetry.local_only: {cfg.telemetry.local_only}")
    if cfg.telemetry.enabled:
        console.print(f"- telemetry.file    : {telemetry_path(cfg.state.workdir)}")
    console.print("[dim]说明：本命令不读 provider key、不发 HTTP、不打印任何 api_key 或 token。[/dim]")


# ---------------------------------------------------------------------------
# v0.4.2: 产品体验闭环 — `mindforge commands` 与 `mindforge next`
# ---------------------------------------------------------------------------
# 设计意图（学习要点）
# --------------------
# 1. CLI 变多以后，`mindforge --help` 会按字母序铺平展示，新用户根本不知道
#    "下一步该敲哪一条"。这两条命令解决"命令发现"和"工作流引导"两个问题：
#    - `commands` 按"任务场景"分组，给每条命令一句中文"什么时候用"。
#    - `next` 读取当前 vault / state 的健康指标，给出"现在最该做的下一步"。
# 2. 这两条命令必须遵守 v0.x 安全核心：
#    - **不读 secret 内容**；
#    - **不调 LLM**（纯字符串模板 + 文件系统统计）；
#    - **不联网**；
#    - **不输出 raw_text / 卡片正文 / prompt / completion / api_key**。
# 3. `next` 的判定基于"显式可观察事实"：vault 是否存在、inbox 是否有文件、
#    state.json 是否有 raw / triaged 残留、卡片目录是否有 ai_draft、
#    .mindforge/index/ 是否存在、review backlog 是否非空 …… 都是文件系统能
#    答的问题，不需要任何 AI 推断。
# ---------------------------------------------------------------------------

# `commands` 的固定脚本：(group, command, "什么时候用")
_COMMAND_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "第一次开始",
        [
            ("mindforge web", "打开本地 Web 控制台，配置真实模型和 API key"),
            ("mindforge status", "查看本地 workspace / draft / library 状态"),
            ("mindforge doctor", "健康检查 + 本地读写边界"),
            ("mindforge runs list", "查看后台 processing runs"),
        ],
    ),
    (
        "导入 / 处理资料",
        [
            ("mindforge watch list", "查看本地文件/文件夹 sources"),
            ("mindforge watch add <file-or-folder>", "注册 watched source，并启动后台 processing"),
            ("mindforge import <file-or-folder>", "一次性导入并启动后台 processing"),
            ("mindforge runs show <run_id>", "查看单个后台 processing run 结果"),
        ],
    ),
    (
        "审批 ai_draft",
        [
            ("mindforge approve list", "查看待人工批准的草稿"),
            ("mindforge approve show --card PATH", "预览单张草稿安全摘要"),
            ("mindforge approve 1 --confirm", "用短编号把单张卡片晋升为 human_approved"),
            ("mindforge approve --all --dry-run", "批量预览；不会自动 approve"),
        ],
    ),
    (
        "Library / Trash / Prompt",
        [
            ("mindforge library list", "查看 Knowledge Library 卡片清单"),
            ("mindforge library show <ref>", "查看单张卡片 metadata"),
            ("mindforge trash list", "查看 Trash 中已移除的卡片"),
            ("mindforge trash move <path> --confirm", "安全移入 Trash（不删 source）"),
            ("mindforge trash restore <path> --confirm", "从 Trash 恢复卡片"),
            ("mindforge wiki rebuild", "从 approved cards 重建 Wiki（LLM synthesis，使用当前配置）"),
            ("mindforge prompts list", "只读查看内置 prompt assets"),
            ("mindforge prompts show triage", "只读查看单个 prompt 全文"),
        ],
    ),
    (
        "Recall",
        [
            ("mindforge index rebuild", "本地 BM25 索引重建（不联网）"),
            ("mindforge recall --query \"...\"", "本地词法检索"),
            ("mindforge recall --ranking hybrid --explain", "三路融合 + 评分解释"),
        ],
    ),
    (
        "Review",
        [
            ("mindforge review backlog", "overdue / today / upcoming / missing 四桶"),
            ("mindforge review schedule --days 7", "未来 N 天复习计划"),
            ("mindforge review weekly", "周报（不调 LLM）"),
            ("mindforge review mark --card PATH --result remembered", "标记复习结果"),
        ],
    ),
    (
        "Backup / Doctor",
        [
            ("mindforge doctor --paths", "检查恢复状态和本地读写边界"),
        ],
    ),
    (
        "Debug / Safety",
        [
            ("mindforge commands", "按目标查看命令导航"),
            ("mindforge next", "根据当前状态推荐下一步"),
            ("mindforge today", "每日待办 / review / index 状态"),
            ("mindforge version", "版本与运行配置摘要（不含 secret）"),
        ],
    ),
]


@daily_app.command("commands")
def commands_cmd() -> None:
    """按"任务场景"列出 MindForge 所有命令 + 一句话用途说明。

    设计原则：
    - 仅从静态脚本生成，不读 vault、不读 secret、不发 HTTP；
    - 不调 LLM；
    - 不输出任何卡片正文 / raw_text / prompt / completion / api_key。
    """
    from . import __version__
    from rich.markup import escape

    console.print(f"[bold]MindForge[/bold] v{__version__} — 命令地图（按场景）\n")
    for group, items in _COMMAND_GROUPS:
        console.print(f"[bold cyan]{group}[/bold cyan]")
        for cmd, desc in items:
            console.print(f"  [green]{escape(cmd)}[/green]")
            console.print(f"    {escape(desc)}")
        console.print("")
    console.print(
        "[dim]说明：完整使用入口见 README.md。"
        "本命令不发 HTTP、不调用 LLM。[/dim]"
    )


@dataclass(frozen=True)
class DailySnapshot:
    """个人每日入口的只读状态快照。

    中文学习型说明：v0.5.4 的 daily loop 只汇总可观察状态，不读取 source
    正文、不调用 LLM、不自动 approve，也不修改 Obsidian notes。它是产品引导层，
    不是 SourceAdapter / processor / recall 架构的一部分。
    """

    vault_root: str
    vault_exists: bool
    inbox_files: int
    state_exists: bool
    state_counts: dict[str, int]
    recent_sources: tuple[str, ...]
    card_counts: dict[str, int]
    review_overdue: int
    review_due_week: int
    index_exists: bool
    latest_run: str | None
    model_setup: str


def _daily_snapshot(cfg: MindForgeConfig) -> DailySnapshot:
    """读取本地 daily loop 所需的安全摘要。

    所有信息来自文件名、state.json 状态字段和 Knowledge Card frontmatter
    白名单字段；不会读取 provider key、prompt、completion、source raw_text 或
    Obsidian 正式 note 正文。
    """
    from .cards import iter_cards

    vault_root = cfg.vault.root
    inbox_files = 0
    if cfg.vault.inbox_path.exists():
        inbox_files = sum(
            1 for p in cfg.vault.inbox_path.rglob("*") if p.is_file() and not p.name.startswith(".")
        )

    state_counts: dict[str, int] = {}
    recent_items: list[ItemState] = []
    if cfg.state.state_path.exists():
        try:
            cp = Checkpoint.load(cfg.state.state_path, backup=False)
            state_counts = cp.count_by_status()
            recent_items = sorted(
                (item for item in cp.all_items() if _state_source_belongs_to_vault(item, cfg.vault.root)),
                key=lambda it: it.processed_at or it.first_seen_at or datetime.min,
                reverse=True,
            )[:3]
        except Exception:
            state_counts = {"unreadable": 1}

    scan = iter_cards(vault_root, cfg.vault.cards_dir)
    card_counts: dict[str, int] = {}
    review_overdue = 0
    review_due_week = 0
    now = datetime.now().astimezone()
    for card in scan.cards:
        card_counts[card.status] = card_counts.get(card.status, 0) + 1
        if card.status != "human_approved" or card.review_after is None:
            continue
        due_at = card.review_after if card.review_after.tzinfo else card.review_after.replace(tzinfo=now.tzinfo)
        if due_at <= now:
            review_overdue += 1
        elif due_at <= now + timedelta(days=7):
            review_due_week += 1

    runs_dir = cfg.state.runs_path
    latest_run = None
    if runs_dir.exists():
        files = sorted((p for p in runs_dir.glob("*.jsonl") if p.is_file()), key=lambda p: p.stat().st_mtime)
        if files:
            latest_run = files[-1].name

    return DailySnapshot(
        vault_root=str(vault_root),
        vault_exists=vault_root.exists(),
        inbox_files=inbox_files,
        state_exists=cfg.state.state_path.exists(),
        state_counts=state_counts,
        recent_sources=tuple(item.source_path for item in recent_items),
        card_counts=card_counts,
        review_overdue=review_overdue,
        review_due_week=review_due_week,
        index_exists=(cfg.state.workdir / "index" / "bm25.json").exists(),
        latest_run=latest_run,
        model_setup=model_setup_readiness(cfg).label,
    )


def _state_source_belongs_to_vault(item: ItemState, vault_root: Path) -> bool:
    """判断 state 记录是否属于当前 vault。

    中文学习型说明：开发/packaged smoke 可能共用同一个 `.mindforge/state.json`，
    里面混有不同临时 vault 的历史 source。daily loop 不能把别的 vault 的路径
    显示成当前用户今天的进度，所以只展示当前 vault 内的绝对路径或普通相对路径。
    """
    p = Path(item.source_path)
    if not p.is_absolute():
        return True
    try:
        p.resolve().relative_to(vault_root.resolve())
        return True
    except ValueError:
        return False


def _snapshot_to_dict(snapshot: DailySnapshot) -> dict[str, object]:
    return {
        "vault_root": snapshot.vault_root,
        "vault_exists": snapshot.vault_exists,
        "inbox_files": snapshot.inbox_files,
        "state_exists": snapshot.state_exists,
        "state_counts": snapshot.state_counts,
        "recent_sources": list(snapshot.recent_sources),
        "card_counts": snapshot.card_counts,
        "review": {
            "overdue": snapshot.review_overdue,
            "due_this_week": snapshot.review_due_week,
        },
        "index_exists": snapshot.index_exists,
        "latest_run": snapshot.latest_run,
    }


def _print_daily_snapshot(snapshot: DailySnapshot) -> None:
    console.print("[bold]Daily status[/bold]")
    console.print(f"  vault        : {snapshot.vault_root}")
    console.print(f"  inbox files  : {snapshot.inbox_files}")
    console.print(
        "  cards        : "
        f"ai_draft={snapshot.card_counts.get('ai_draft', 0)} · "
        f"human_approved={snapshot.card_counts.get('human_approved', 0)}"
    )
    console.print(
        f"  review       : overdue={snapshot.review_overdue} · "
        f"due_this_week={snapshot.review_due_week}"
    )
    console.print(f"  index        : {'ready' if snapshot.index_exists else 'missing'}")
    console.print(f"  latest run   : {snapshot.latest_run or '-'}")
    if snapshot.recent_sources:
        console.print("  recent source:")
        for src in snapshot.recent_sources:
            console.print(f"    - {src}")
    else:
        console.print("  recent source: -")


def _print_next_actions(suggestions: list[NextSuggestion]) -> None:
    console.print("\n[bold]Next actions[/bold]")
    for item in suggestions:
        # 中文学习型说明：命令行必须是可复制产品面，不交给 Rich 自动换行。
        # 真实 dogfood 里用户常带很长的 /tmp vault 路径；一旦被 Rich 包装成
        # 多行，新用户很难判断该复制哪一段。原因说明仍可由 Rich 渲染。
        print(f"  [{item.priority}] → {item.command}")
        console.print(f"    {item.reason}")


def _print_start_guidance(snapshot: DailySnapshot, suggestions: list[NextSuggestion]) -> None:
    """打印第一天 onboarding 状态，不触发任何写操作。

    中文学习型说明：`start` 是 CLI 产品入口，不是新的业务管线。它只把
    doctor/today/next 的只读信号组合成用户能理解的步骤，避免把 onboarding
    做成 Web UI/TUI 或隐藏式自动流程。
    """
    console.print("[bold]First-run checklist[/bold]")
    workspace_state = "ready" if snapshot.vault_exists else "missing"
    source_state = "empty" if snapshot.inbox_files == 0 else f"{snapshot.inbox_files} file(s)"
    processing_state = "no runs" if snapshot.latest_run is None else snapshot.latest_run
    draft_count = snapshot.card_counts.get("ai_draft", 0)
    console.print(f"  Workspace: {workspace_state}")
    console.print(f"  Model setup: {snapshot.model_setup}")
    console.print(f"  Sources: {source_state}")
    console.print(f"  Processing: {processing_state}")
    console.print(f"  Drafts: {draft_count}")
    if suggestions:
        console.print(f"  Next action: {suggestions[0].command}", markup=False, soft_wrap=True)
        console.print(f"    {suggestions[0].reason}", markup=False, soft_wrap=True)
    else:
        console.print("  Next action: mindforge status", markup=False)
    console.print(
        "\n[dim]安全默认：start 只做本地状态检查；不会调用模型、不会发起网络请求、"
        "不会写入 approved knowledge。AI draft 生成需要完成 model setup，并通过 "
        "background processing 产生。[/dim]"
    )


# Historical _next_suggestions / _compact_next_suggestions extracted to
# the next_suggestions module. cli.py keeps thin private aliases so
# existing call sites stay unchanged. See next_suggestions.py module
# docstring for the architecture boundary (no console / no Typer).
def _next_suggestions(cfg):
    return next_suggestions(cfg)


def _compact_next_suggestions(suggestions):
    return compact_next_suggestions(suggestions)


@daily_app.command("start")
def start_cmd(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("text", "--format", "-f", help="text | json"),
) -> None:
    """第一天入口：展示当前状态、安全边界和下一条推荐命令。

    该命令只读本地文件系统和卡片 frontmatter，不会 init、scan、process、
    approve 或写 Obsidian notes。真正动作仍由用户显式执行。
    """
    try:
        cfg = load_cfg(config, read_env=False)
    except typer.Exit:
        # load_cfg 失败 → config 找不到或无 workspace
        if output_format == "json":
            import json as _json

            print(
                _json.dumps(
                    {
                        "version": 1,
                        "error": "config_missing",
                        "next_command": "mindforge init --interactive",
                        "safety": _start_safety_dict(),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            console.print("[bold]MindForge start[/bold]\n")
            console.print("[yellow]尚未找到配置。[/yellow]")
            console.print("  1. 创建新 workspace：[bold]mindforge init[/bold]", markup=False)
            console.print("  2. 切换已有 workspace：[bold]mindforge workspace use /path/to/workspace[/bold]", markup=False)
            console.print("  3. 临时指定：[bold]mindforge start --workspace /path/to/workspace[/bold]", markup=False)
            console.print("[dim]安全默认：初始化不会调用模型；完成 Web Setup 后再处理 source。[/dim]")
        return
    snapshot = _daily_snapshot(cfg)
    suggestions = _next_suggestions(cfg)
    if output_format == "json":
        import json as _json

        print(
            _json.dumps(
                {
                    "version": 1,
                    "status": _snapshot_to_dict(snapshot),
                    "suggestions": [
                        {"command": s.command, "reason": s.reason, "priority": s.priority}
                        for s in suggestions
                    ],
                    "safety": _start_safety_dict(),
                },
                ensure_ascii=False,
            )
        )
        return

    console.print(f"[bold]MindForge start[/bold]  — vault: {cfg.vault.root}\n")
    _print_start_guidance(snapshot, suggestions)


def _start_safety_dict() -> dict[str, bool]:
    return {
        "model_calls": False,
        "reads_env": False,
        "calls_real_llm": False,
        "writes_formal_obsidian_notes": False,
        "uploads_telemetry": False,
    }


@daily_app.command("today")
def today_cmd(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    output_format: str = typer.Option("text", "--format", "-f", help="text | json"),
) -> None:
    """每日入口：只读汇总待办、复习、索引和下一条命令。

    中文学习型说明：`today` 是 v0.5.4 的个人日常使用入口。它只读取本地状态
    与卡片 frontmatter 安全字段，不触发 process、不自动 approve、不读取
    provider key、不调用真实 LLM，也不修改 Obsidian notes。
    """
    try:
        cfg = load_cfg(config, read_env=False)
    except typer.Exit:
        if output_format == "json":
            import json as _json

            print(_json.dumps({"version": 1, "error": "config_missing"}, ensure_ascii=False))
        else:
            console.print("[yellow]配置不存在。[/yellow]")
            console.print("  1. 创建新 workspace：[bold]mindforge init[/bold]", markup=False)
            console.print("  2. 切换已有 workspace：[bold]mindforge workspace use /path/to/workspace[/bold]", markup=False)
        return
    snapshot = _daily_snapshot(cfg)
    suggestions = _next_suggestions(cfg)

    if output_format == "json":
        import json as _json

        print(
            _json.dumps(
                {
                    "version": 1,
                    "status": _snapshot_to_dict(snapshot),
                    "suggestions": [
                        {"command": s.command, "reason": s.reason, "priority": s.priority}
                        for s in suggestions
                    ],
                },
                ensure_ascii=False,
            )
        )
        return

    console.print(f"[bold]MindForge today[/bold]  — vault: {cfg.vault.root}\n")
    _print_daily_snapshot(snapshot)
    _print_next_actions(suggestions)
    console.print(
        "\n[dim]说明：today 只读本地状态和卡片 frontmatter；不读 provider key、不调 LLM、"
        "不发 HTTP、不自动 approve。[/dim]"
    )


@daily_app.command("next")
def next_cmd(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="text | json",
    ),
) -> None:
    """根据 vault 当前状态，推荐"下一步该做什么"。

    安全契约（与 doctor 一致）：
    - 不读 secret 内容；
    - 不调 LLM；
    - 不发 HTTP；
    - 不输出卡片正文 / raw_text / prompt / completion；
    - 输出仅含命令字符串与中文原因，不含 secret。
    """
    try:
        cfg = load_cfg(config, read_env=False)
    except typer.Exit:
        # load_cfg 已输出 workspace-aware 错误信息
        if output_format == "json":
            import json as _json

            print(_json.dumps({
                "version": 2,
                "error": "config_missing",
                "suggestions": [
                    {
                        "command": "mindforge init",
                        "reason": "config not found — create a workspace first",
                        "priority": "critical",
                    }
                ],
            }, ensure_ascii=False))
        return

    suggestions = _next_suggestions(cfg)

    if output_format == "json":
        import json as _json

        print(
            _json.dumps(
                {
                    "version": 2,
                    "vault_root": str(cfg.vault.root),
                    "status": _snapshot_to_dict(_daily_snapshot(cfg)),
                    "suggestions": [
                        {
                            "command": item.command,
                            "reason": item.reason,
                            "priority": item.priority,
                        }
                        for item in suggestions
                    ],
                },
                ensure_ascii=False,
            )
        )
        return

    console.print(f"[bold]MindForge next[/bold]  — vault: {cfg.vault.root}\n")
    _print_daily_snapshot(_daily_snapshot(cfg))
    _print_next_actions(suggestions)
    console.print(
        "\n[dim]说明：本命令不读 provider key、不调 LLM、不发 HTTP；"
        "建议来自文件系统可观察事实（state.json / 卡片 frontmatter / 索引文件）。[/dim]"
    )
