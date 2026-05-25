"""导出适配器(ExportAdapter)抽象基类。

MindForge 导出层目前缺少统一的端口抽象 — 导出逻辑分散在 wiki_service、
library_service、obsidian_stage 和 web router 中。

ExportAdapter 提供与 SourceAdapter 对等的导出侧端口，使得:
- Markdown 导出、JSON 导出、HTML 导出等格式可作为可替换适配器
- 每个适配器自声明 capabilities 和 manifest
- 不替代现有 StagedExportPlan，仅补充导出端口抽象层

设计参考:
- SourceAdapter (sources/base.py, sources/source_adapter.py) 的 ABC + capabilities 模式
- StagedExportPlan (obsidian_stage.py) 的安全导出路径规划
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExportResult:
    """一次导出操作的结构化结果。

    与 AdapterResult (sources/adapter_result.py) 保持对等语义:
    - success=True 表示导出成功，output_path 指向产出文件
    - success=False 表示导出失败，errors 包含错误信息
    - warnings 记录非致命警告
    """

    success: bool
    output_path: Path
    format: str
    card_count: int
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    """额外的键值对元数据，如导出时间、版本号等。使用 frozenset[tuple] 保持不可变性。"""


class ExportAdapter(ABC):
    """导出适配器抽象基类。

    每个导出适配器负责将 KnowledgeCard 集合转换为特定格式的输出文件。

    Usage:
        class MarkdownExportAdapter(ExportAdapter):
            name = "markdown_export"
            export_format = "markdown"

            def can_handle(self, card_ids, target_format):
                return target_format == "markdown"

            def export(self, card_ids, output_path, **options):
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器唯一标识名称。如 'markdown_export', 'json_export'。"""
        ...

    @property
    @abstractmethod
    def export_format(self) -> str:
        """输出格式标识。如 'markdown', 'json', 'html', 'obsidian'。"""
        ...

    @abstractmethod
    def can_handle(self, card_ids: frozenset[str], target_format: str) -> bool:
        """判断该适配器是否能处理指定卡片集合和目标格式。

        Args:
            card_ids: 待导出卡片 ID 集合
            target_format: 目标导出格式

        Returns:
            True 表示可以处理该导出请求
        """
        ...

    @abstractmethod
    def export(self, card_ids: frozenset[str], output_path: Path, **options: Any) -> ExportResult:
        """执行导出操作。

        Args:
            card_ids: 待导出卡片 ID 集合
            output_path: 输出目标路径（文件或目录，取决于适配器实现）
            **options: 格式特定选项

        Returns:
            ExportResult 包含成功/失败状态和输出信息
        """
        ...

    def capabilities(self) -> frozenset[str]:
        """返回适配器能力标签集合。

        默认: local_file + fake_safe（纯本地文件操作，不涉及外部服务）。
        子类可覆盖以声明 read_only、dry_run 或 network 等能力。

        标签与 mindforge.extensions.manifest.Capability 对齐。
        """
        return frozenset({"local_file", "fake_safe", "read_only"})
