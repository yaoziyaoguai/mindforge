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

from .assets_runtime import asset_root
from .config import load_mindforge_config
from .cubox_dryrun_presenter import (
    DryRunSampleItem,
    DryRunSummary,
    render_json,
    render_text,
)
from .cubox_preview_presenter import (
    AiDraftPreviewItem,
    AiDraftPreviewSummary,
)
from .cubox_preview_presenter import render_json as preview_render_json
from .cubox_preview_presenter import render_text as preview_render_text
from .llm import LLMClient, build_providers
from .scanner import ScanResult
from .source_mux import SourceMux
from .sources.cubox_api import CuboxApiAdapter
from .sources.base import SourceDocument
from .strategies import DEFAULT_STRATEGY_NAME, StrategyContext, build_strategy

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


# ---------------------------------------------------------------------------
# preview-ai-draft：本地 export → fake KnowledgeStrategy → in-memory preview
# ---------------------------------------------------------------------------


class _NoOpRunLogger:
    """与 ``RunLogger`` 鸭子类型兼容的占位 logger。

    ``Pipeline``/``run_stage`` 只通过 ``logger.emit(event, **fields)``
    与 logger 交互；preview 命令必须**永不**写 ``.mindforge/runs/*.jsonl``，
    因此这里提供一个零副作用实现。``run_id`` 仅用于满足可能的字段访问；
    不返回真实路径，避免任何下游误用拼接出磁盘路径。
    """

    run_id = "cubox-preview-noop"

    def emit(self, event: str, **fields: object) -> None:  # noqa: D401 - 简单接口
        """丢弃所有事件；preview 不持久化。"""
        return None

    def open(self) -> "_NoOpRunLogger":
        return self

    def close(self) -> None:
        return None


def _load_default_config_path() -> Path:
    """优先 cwd 的 ``configs/mindforge.yaml``；否则用 package 内置 asset。

    preview 命令的设计目标是 ``cd 任何目录 → 跑就能看 fake ai_draft``，
    不需要项目用户先建配置文件。包内 ``configs/mindforge.yaml`` 已经把
    ``active_profile`` 设为 ``fake``，与本命令的安全语义天然吻合。
    """
    local = Path.cwd() / "configs" / "mindforge.yaml"
    if local.exists():
        return local
    bundled = asset_root().joinpath("configs", "mindforge.yaml")
    # importlib.resources Traversable → 实际是仓库内文件；直接 read 即可。
    # load_mindforge_config 接受 Path，因此这里若不是 Path 就落到临时文件。
    if isinstance(bundled, Path):
        return bundled
    # Fallback：写到临时缓存（不污染 cwd）。
    import tempfile

    cache = Path(tempfile.gettempdir()) / "mindforge-bundled-config.yaml"
    cache.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
    return cache


def _parse_cubox_export_or_exit(export: Path) -> list[SourceDocument]:
    """解析本地 Cubox export；只读本地文件，不触达真实 Cubox API。"""
    if not export.exists():
        console.print(f"[red]Cubox export 文件不存在：{export}[/red]")
        raise typer.Exit(code=2)

    adapter = CuboxApiAdapter()
    try:
        return adapter.parse_export(export)
    except json.JSONDecodeError as exc:
        console.print(
            f"[red]Cubox export JSON 解析失败：{export}"
            f"（{exc.msg} @ line {exc.lineno}）[/red]"
        )
        raise typer.Exit(code=2) from exc
    except ValueError as exc:
        console.print(f"[red]Cubox export 内容非法：{exc}[/red]")
        raise typer.Exit(code=2) from exc


def _dedup_cubox_docs(
    docs: list[SourceDocument],
    *,
    export: Path,
) -> tuple[list[SourceDocument], SourceMux]:
    """沿用 SourceMux 去重 seam，保证 preview 与 dry-run 对同一 export 行为一致。"""
    adapter = CuboxApiAdapter()
    mux = SourceMux()
    yielded_docs: list[SourceDocument] = []
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
    return yielded_docs, mux


def _fake_preview_strategy():
    """构造 fake-only KnowledgeStrategy，维持 no API key / no network 安全路径。"""
    cfg = load_mindforge_config(_load_default_config_path())
    # LLMConfig 是 frozen dataclass：用 ``replace`` 而非赋值，强制 fake profile。
    from dataclasses import replace as _replace

    safe_llm = _replace(cfg.llm, active_profile="fake")
    providers = build_providers(safe_llm)
    client = LLMClient(llm_config=safe_llm, providers=providers)

    prompts_dir = asset_root().joinpath("prompts")
    tracks_text = asset_root().joinpath("configs", "learning_tracks.yaml").read_text(
        encoding="utf-8"
    )
    ctx = StrategyContext(
        client=client,
        prompts_dir=prompts_dir,
        prompt_versions=cfg.prompts,
        triage_threshold=cfg.triage.value_score_threshold,
        learning_tracks_text=tracks_text,
        logger=None,
    )
    pipeline = build_strategy(DEFAULT_STRATEGY_NAME, ctx)
    pipeline.logger = _NoOpRunLogger()  # type: ignore[assignment]
    return pipeline


def _preview_ai_draft_summary(
    *,
    docs: list[SourceDocument],
    yielded_docs: list[SourceDocument],
    mux: SourceMux,
) -> AiDraftPreviewSummary:
    """运行 fake strategy 并只返回观测摘要，不暴露 ai_draft 正文。"""
    pipeline = _fake_preview_strategy()
    outcomes: list[AiDraftPreviewItem] = []
    by_status: dict[str, int] = {}
    for d in yielded_docs:
        outcome = pipeline.run(d)
        status = outcome.status
        by_status[status] = by_status.get(status, 0) + 1
        track, value_score = _preview_triage_fields(outcome.triage)
        outcomes.append(
            AiDraftPreviewItem(
                title=d.title,
                source_id_short=d.source_id.split(":", 1)[-1][:12],
                status=status,
                track=track,
                value_score=value_score,
                has_card_payload=outcome.card_payload is not None,
                skip_reason=outcome.skip_reason,
                error_message=outcome.error_message,
            )
        )

    return AiDraftPreviewSummary(
        items_seen=len(docs),
        yielded=len(yielded_docs),
        deduped=mux.stats.deduped,
        by_status=by_status,
        outcomes=outcomes,
    )


def _preview_triage_fields(triage: object) -> tuple[str | None, int | None]:
    """从 strategy triage 结果中提取 presenter 需要的两个安全字段。"""
    track: str | None = None
    value_score: int | None = None
    parsed = getattr(triage, "parsed", None) if triage is not None else None
    if isinstance(parsed, dict):
        t = parsed.get("track")
        if isinstance(t, str):
            track = t
        v = parsed.get("value_score")
        if isinstance(v, int):
            value_score = v
    return track, value_score


@cubox_app.command("preview-ai-draft")
def cubox_preview_ai_draft(
    export: Path = typer.Option(
        ..., "--export", help="本地 Cubox JSON export 文件路径"
    ),
    limit: int | None = typer.Option(
        None, "--limit", help="最多处理多少条 yielded 文档（None=全跑）", min=1
    ),
    json_out: bool = typer.Option(
        False, "--json", help="输出机器可读 JSON 一行"
    ),
) -> None:
    """对 Cubox export 走 fake KnowledgeStrategy，**仅在内存中**生成
    ai_draft 预览，并打印观测 summary。

    安全边界：永不读 ``.env``、不联网、不调真实 LLM、不调真实 Cubox API、
    不写 ``.mindforge/runs/*.jsonl``、不写 Obsidian vault、不生成
    ``human_approved``、不自动 approve、不展示 ai_draft 正文。
    """

    docs = _parse_cubox_export_or_exit(export)
    yielded_docs, mux = _dedup_cubox_docs(docs, export=export)

    if limit is not None:
        yielded_docs = yielded_docs[:limit]

    summary = _preview_ai_draft_summary(
        docs=docs,
        yielded_docs=yielded_docs,
        mux=mux,
    )

    if json_out:
        typer.echo(preview_render_json(summary))
    else:
        typer.echo(preview_render_text(summary))
