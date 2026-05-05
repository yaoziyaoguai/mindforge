"""Safe source discovery for watch/import ingestion.

中文学习型说明：本模块只做两件事：枚举用户给定的 file/folder，并把候选文件
交给现有 SourceAdapter 构造 ``SourceDocument``。它不复制 source，不移动
source，不重写 Adapter 抽象，也不调用 process pipeline。
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from .config import MindForgeConfig
from .scanner import ScanResult
from .sources.base import SourceAdapter
from .sources.registry import build_active_adapters

_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".mindforge",
        "_processed",
        "_ignored",
        "_rejected",
        "20-Knowledge-Cards",
        "runtime",
        "index",
        "cache",
        "log",
        "logs",
        "runs",
    }
)


def discover_source_results(
    cfg: MindForgeConfig,
    targets: Path | Iterable[Path],
) -> Iterator[ScanResult]:
    """发现 file/folder 中可由现有 adapter 处理的 source 文件。

    文件夹递归时跳过 runtime / index / cache / card 输出等派生目录，避免把
    MindForge 自己的输出重新喂回输入。多个 target 重叠时按 resolved path
    去重，保证 watch folder + file 不会重复生成 ai_draft。
    """

    adapters = build_active_adapters(cfg.sources)
    seen: set[Path] = set()
    target_list = [targets] if isinstance(targets, Path) else list(targets)
    for target in target_list:
        for path in _iter_candidate_files(target):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            result = _load_with_first_matching_adapter(cfg, adapters, resolved)
            if result is not None:
                yield result


def _iter_candidate_files(target: Path) -> Iterator[Path]:
    path = target.expanduser()
    if path.is_file():
        yield path
        return
    if not path.exists():
        return
    if not path.is_dir():
        return
    yield from _walk_dir(path)


def _walk_dir(root: Path) -> Iterator[Path]:
    for child in sorted(root.iterdir()):
        if child.is_dir():
            if _should_skip_dir(child):
                continue
            yield from _walk_dir(child)
            continue
        if child.is_file():
            yield child


def _should_skip_dir(path: Path) -> bool:
    name = path.name
    return name.startswith(".") or name in _SKIP_DIR_NAMES


def _load_with_first_matching_adapter(
    cfg: MindForgeConfig,
    adapters: dict[str, SourceAdapter],
    path: Path,
) -> ScanResult | None:
    for entry in cfg.sources.active_entries():
        adapter = adapters[entry.source_type]
        if not path.match(entry.file_glob) and not adapter.can_handle(str(path)):
            continue
        if not adapter.can_handle(str(path)):
            continue
        return _safe_load(adapter, entry.source_type, path)
    return None


def _safe_load(adapter: SourceAdapter, source_type: str, path: Path) -> ScanResult:
    try:
        doc = adapter.load(str(path))
        if not doc.adapter_name:
            from dataclasses import replace

            doc = replace(doc, adapter_name=adapter.name or adapter.__class__.__name__)
        return ScanResult(
            source_type=source_type,
            adapter_name=adapter.name,
            path=path,
            document=doc,
        )
    except Exception as exc:  # noqa: BLE001
        return ScanResult(
            source_type=source_type,
            adapter_name=adapter.name,
            path=path,
            document=None,
            error=f"{type(exc).__name__}: {exc}",
        )


__all__ = ["discover_source_results"]
