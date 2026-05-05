"""Web source/workspace status service.

中文学习型说明：Sources 页第一版只做真实本地只读状态，不偷偷 scan/write
state。真正 scan/import 仍需要现有 CLI 或未来显式 Web write service。
"""

from __future__ import annotations

from mindforge.config import MindForgeConfig
from mindforge.scanner import Scanner

from mindforge_web.schemas import NextAction, SourceStatus, StatusItem


class WebSourceService:
    def __init__(self, cfg: MindForgeConfig) -> None:
        self.cfg = cfg

    def list_sources(self) -> list[SourceStatus]:
        results: list[SourceStatus] = []
        scan_errors = self._scan_error_counts()
        for entry in self.cfg.sources.active_entries():
            path = self.cfg.vault.inbox_path / entry.inbox_subdir
            files = list(path.rglob(entry.file_glob)) if path.exists() else []
            results.append(
                SourceStatus(
                    source_type=entry.source_type,
                    adapter=entry.adapter,
                    inbox_subdir=entry.inbox_subdir,
                    file_glob=entry.file_glob,
                    enabled=entry.enabled,
                    path=str(path),
                    exists=path.exists(),
                    file_count=sum(1 for item in files if item.is_file()),
                    error_count=scan_errors.get(entry.source_type, 0),
                    next_action=None
                    if path.exists()
                    else NextAction(
                        label="Create source folder",
                        description="创建该 inbox 子目录后再放入本地 source 文件。",
                        command=f"mkdir -p {path}",
                    ),
                )
            )
        return results

    def available_imports(self) -> list[StatusItem]:
        return [
            StatusItem(
                key="import_local",
                label="Local file import",
                status="warn",
                value="unavailable in Web v1",
                detail="当前后端没有独立安全的 Web import service；请先把文件放入配置的 inbox 并运行 scan/process。",
                next_action=NextAction(
                    label="Use CLI scan",
                    description="Web v1 先提供只读状态；写入导入留给下一 slice。",
                    command=f"mindforge scan --vault {self.cfg.vault.root}",
                ),
            ),
            StatusItem(
                key="import_cubox_json",
                label="Cubox JSON export",
                status="warn",
                value="unavailable in Web v1",
                detail="Cubox JSON export 解析已有 CLI dry-run；Web 写入入口需要独立安全边界后再开放。",
                next_action=NextAction(
                    label="Use Cubox dry-run",
                    description="先用 CLI 验证 export，不触发网络或自动 approve。",
                    command="mindforge cubox dry-run --export <file.json>",
                ),
            ),
        ]

    def _scan_error_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        scanner = Scanner(self.cfg)
        for result in scanner.iter_results():
            if not result.ok:
                counts[result.source_type] = counts.get(result.source_type, 0) + 1
        return counts
