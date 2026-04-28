"""Scanner — 扫描 ``00-Inbox/<sub>/`` 派发到对应 adapter，输出 SourceDocument 流。

职责边界
--------
- **只读**：从不写入 inbox 任何文件。
- **不调 LLM**：纯 IO + 派发，可独立运行（这是 ``mindforge scan`` 命令的本体）。
- **不写 state**：写入 checkpoint 是上层调用方（CLI）的事，便于测试。

派发规则
--------
按 ``configs/mindforge.yaml.sources.registry.<source_type>``：
- 在 ``vault.inbox_root / inbox_subdir`` 目录下；
- 按 ``file_glob`` 匹配文件；
- 用对应 adapter 的 ``load`` 转成 ``SourceDocument``。

子目录之间互不重叠（v0.1 约定一种 source_type 占一个子目录），
所以不需要"歧义裁定"逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .config import MindForgeConfig
from .sources.base import SourceAdapter, SourceDocument
from .sources.registry import build_active_adapters


@dataclass(frozen=True)
class ScanResult:
    """Scanner 单条产出：原始文件路径 + 解析后的 SourceDocument 或错误。"""

    source_type: str
    adapter_name: str
    path: Path
    document: SourceDocument | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.document is not None and self.error is None


class Scanner:
    """按 SourcesConfig 遍历 inbox 子目录并派发到对应 adapter。"""

    def __init__(self, config: MindForgeConfig) -> None:
        self.config = config
        self.adapters: dict[str, SourceAdapter] = build_active_adapters(config.sources)

    # ------------------------------------------------------------------ scan
    def iter_results(self) -> Iterator[ScanResult]:
        """惰性生成扫描结果，便于 CLI 边扫边显示进度。"""
        inbox_root = self.config.vault.inbox_path
        for entry in self.config.sources.active_entries():
            adapter = self.adapters[entry.source_type]
            subdir = inbox_root / entry.inbox_subdir
            if not subdir.exists():
                # 子目录不存在不算错误；可能 vault 还没建好对应目录
                continue
            for path in sorted(subdir.rglob(entry.file_glob)):
                if not path.is_file():
                    continue
                yield self._safe_load(adapter, entry.source_type, path)

    def scan_all(self) -> list[ScanResult]:
        return list(self.iter_results())

    # ----------------------------------------------------------------- 内部
    def _safe_load(
        self,
        adapter: SourceAdapter,
        source_type: str,
        path: Path,
    ) -> ScanResult:
        try:
            doc = adapter.load(str(path))
            return ScanResult(
                source_type=source_type,
                adapter_name=adapter.name,
                path=path,
                document=doc,
            )
        except Exception as e:  # noqa: BLE001 — 任何 adapter 异常都收敛为 ScanResult
            return ScanResult(
                source_type=source_type,
                adapter_name=adapter.name,
                path=path,
                document=None,
                error=f"{type(e).__name__}: {e}",
            )


__all__ = ["Scanner", "ScanResult"]
