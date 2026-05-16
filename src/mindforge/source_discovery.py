"""Safe source discovery for watch/import ingestion.

中文学习型说明：本模块只做两件事：枚举用户给定的 file/folder，并把候选文件
交给现有 SourceAdapter 构造 ``SourceDocument``。它不复制 source，不移动
source，不重写 Adapter 抽象，也不调用 process pipeline。
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
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
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        "runtime",
        "index",
        "cache",
        "log",
        "logs",
        "runs",
    }
)


@dataclass(frozen=True)
class SourceScanPolicy:
    recursive: bool = True
    skip_hidden_dirs: bool = True
    skip_hidden_files: bool = True
    max_file_size_bytes: int | None = None


@dataclass(frozen=True)
class SourceFileCandidate:
    path: Path


@dataclass(frozen=True)
class SkippedSourceFile:
    path: Path
    reason: str


@dataclass(frozen=True)
class SourceFileEnumeration:
    candidates: tuple[SourceFileCandidate, ...]
    skipped: tuple[SkippedSourceFile, ...]
    recursive: bool

    @property
    def skipped_reason_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for item in self.skipped:
            summary[item.reason] = summary.get(item.reason, 0) + 1
        return summary


def enumerate_supported_source_files(
    cfg: MindForgeConfig,
    targets: Path | Iterable[Path],
    policy: SourceScanPolicy | None = None,
) -> SourceFileEnumeration:
    """按统一 folder watch/import policy 枚举可交给 parser 的 source 文件。

    中文学习型说明：这里故意只返回候选文件和 skipped reason，不返回
    ``SourceDocument``，更不生成 Knowledge Card。folder scanner 的边界是
    “发现文件”；parser/adapter 才负责把文件解析成 ``SourceDocument``；
    process pipeline 才负责生成 ai_draft，避免 watch folder 变成第二套管线。
    """

    scan_policy = policy or SourceScanPolicy()
    adapters = build_active_adapters(cfg.sources)
    entries = tuple(cfg.sources.active_entries())
    candidates: list[SourceFileCandidate] = []
    skipped: list[SkippedSourceFile] = []
    seen_candidates: set[Path] = set()
    seen_skipped: set[tuple[Path, str]] = set()
    target_list = [targets] if isinstance(targets, Path) else list(targets)
    for target in target_list:
        for event in _iter_scanned_files(cfg, target, scan_policy, adapters, entries):
            if isinstance(event, SourceFileCandidate):
                if event.path in seen_candidates:
                    continue
                seen_candidates.add(event.path)
                candidates.append(event)
                continue
            key = (event.path, event.reason)
            if key in seen_skipped:
                continue
            seen_skipped.add(key)
            skipped.append(event)
    return SourceFileEnumeration(
        candidates=tuple(candidates),
        skipped=tuple(skipped),
        recursive=scan_policy.recursive,
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
    scan = enumerate_supported_source_files(cfg, targets)
    for candidate in scan.candidates:
        resolved = candidate.path
        result = _load_with_first_matching_adapter(cfg, adapters, resolved)
        if result is not None:
            yield result


def _iter_scanned_files(
    cfg: MindForgeConfig,
    target: Path,
    policy: SourceScanPolicy,
    adapters: dict[str, SourceAdapter],
    entries,
) -> Iterator[SourceFileCandidate | SkippedSourceFile]:
    path = target.expanduser().resolve()
    if path.is_file():
        yield _candidate_or_skip(cfg, path, policy, adapters, entries)
        return
    if not path.exists() or not path.is_dir():
        return
    if _is_generated_output_dir(cfg, path):
        yield SkippedSourceFile(path=path, reason="generated_output")
        return
    yield from _walk_scanned_dir(cfg, path, policy, adapters, entries)


def _walk_scanned_dir(
    cfg: MindForgeConfig,
    root: Path,
    policy: SourceScanPolicy,
    adapters: dict[str, SourceAdapter],
    entries,
) -> Iterator[SourceFileCandidate | SkippedSourceFile]:
    for child in sorted(root.iterdir()):
        resolved = child.resolve()
        if resolved.is_dir():
            dir_reason = _skip_dir_reason(cfg, resolved, policy)
            if dir_reason is not None:
                yield SkippedSourceFile(path=resolved, reason=dir_reason)
                continue
            if policy.recursive:
                yield from _walk_scanned_dir(cfg, resolved, policy, adapters, entries)
            continue
        if resolved.is_file():
            yield _candidate_or_skip(cfg, resolved, policy, adapters, entries)


def _candidate_or_skip(
    cfg: MindForgeConfig,
    path: Path,
    policy: SourceScanPolicy,
    adapters: dict[str, SourceAdapter],
    entries,
) -> SourceFileCandidate | SkippedSourceFile:
    file_reason = _skip_file_reason(cfg, path, policy, adapters, entries)
    if file_reason is not None:
        return SkippedSourceFile(path=path, reason=file_reason)
    return SourceFileCandidate(path=path)


def _skip_dir_reason(
    cfg: MindForgeConfig,
    path: Path,
    policy: SourceScanPolicy,
) -> str | None:
    name = path.name
    if _is_generated_output_dir(cfg, path) or name == cfg.vault.cards_path.name:
        return "generated_output"
    if name in _SKIP_DIR_NAMES or (policy.skip_hidden_dirs and name.startswith(".")):
        return "ignored_directory"
    return None


def _skip_file_reason(
    cfg: MindForgeConfig,
    path: Path,
    policy: SourceScanPolicy,
    adapters: dict[str, SourceAdapter],
    entries,
) -> str | None:
    name = path.name
    if _is_generated_output_file(cfg, path):
        return "generated_output"
    if name == ".DS_Store" or (policy.skip_hidden_files and name.startswith(".")):
        return "hidden_file"
    if name.startswith("~$") or name.endswith(".tmp") or name.endswith(".swp"):
        return "temp_file"
    if policy.max_file_size_bytes is not None and path.stat().st_size > policy.max_file_size_bytes:
        return "too_large"
    parser_reason = _parser_skip_reason(path, adapters, entries)
    if parser_reason is not None:
        return parser_reason
    if not _has_matching_adapter(path, adapters, entries):
        if path.suffix.lower() == ".doc":
            return (
                "unsupported_legacy_doc: Legacy .doc (binary OLE) is not supported in v0.2. "
                "Please convert to .docx or export as PDF/TXT, then import the converted file."
            )
        return "unsupported_extension"
    return None


def _parser_skip_reason(path: Path, adapters: dict[str, SourceAdapter], entries) -> str | None:
    """询问 parser registry 是否有更精确的 skip reason。

    中文学习型说明：missing optional dependency 属于 parser 层知识，不应硬编码
    在 folder scanner。scanner 只消费 adapter 暴露的窄接口，并继续输出统一
    skipped reason。
    """

    path_str = str(path)
    for entry in entries:
        adapter = adapters[entry.source_type]
        reason_fn = getattr(adapter, "skip_reason", None)
        if not callable(reason_fn):
            continue
        if not path.match(entry.file_glob) and not adapter.can_handle(path_str):
            continue
        reason = reason_fn(path_str)
        if reason:
            return str(reason)
    return None


def _has_matching_adapter(path: Path, adapters: dict[str, SourceAdapter], entries) -> bool:
    path_str = str(path)
    for entry in entries:
        adapter = adapters[entry.source_type]
        if not path.match(entry.file_glob) and not adapter.can_handle(path_str):
            continue
        if adapter.can_handle(path_str):
            return True
    return False


def _is_generated_output_dir(cfg: MindForgeConfig, path: Path) -> bool:
    generated_roots = _generated_output_roots(cfg)
    return any(path == root or path.is_relative_to(root) for root in generated_roots)


def _is_generated_output_file(cfg: MindForgeConfig, path: Path) -> bool:
    return any(path.is_relative_to(root) for root in _generated_output_roots(cfg))


def _generated_output_roots(cfg: MindForgeConfig) -> tuple[Path, ...]:
    return (
        cfg.vault.cards_path.resolve(),
        cfg.state.workdir.resolve(),
        cfg.state.runs_path.resolve(),
    )


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


__all__ = [
    "SkippedSourceFile",
    "SourceFileCandidate",
    "SourceFileEnumeration",
    "SourceScanPolicy",
    "discover_source_results",
    "enumerate_supported_source_files",
]
