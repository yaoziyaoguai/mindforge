"""示例 Fake Export Adapter — 演示 ExtensionManifest + ExportAdapter 模式。

本适配器将卡片导出为 Markdown 文件，只写本地临时目录，
不访问网络、不调用外部服务、不处理真实 Obsidian vault。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mindforge.extensions.export_adapter import ExportAdapter, ExportResult
from mindforge.extensions.manifest import (
    Capability,
    ExtensionManifest,
    ExtensionType,
    RiskLevel,
)

# ── Manifest ──────────────────────────────────────────────

FAKE_EXPORT_MANIFEST = ExtensionManifest(
    name="fake_export_markdown",
    version="1.0.0",
    description="Fake Markdown 导出适配器，将卡片集合导出为本地 Markdown 文件",
    extension_type=ExtensionType.EXPORT_ADAPTER,
    capabilities=frozenset({
        Capability.LOCAL_FILE,
        Capability.FAKE_SAFE,
        Capability.DRY_RUN,
        Capability.READ_ONLY,
    }),
    risk_level=RiskLevel.LOW,
    requires_approval=False,
    entry_point="mindforge.extensions.samples.fake_export_adapter.FakeMarkdownExportAdapter",
    author="MindForge",
)


# ── Adapter ───────────────────────────────────────────────

class FakeMarkdownExportAdapter(ExportAdapter):
    """Fake Markdown 导出适配器 — 仅用于演示和测试。

    将卡片元数据渲染为 Markdown 格式，输出到指定本地路径。
    不读取真实卡片存储，不访问 Obsidian vault。
    """

    name = "fake_export_markdown"
    export_format = "markdown"

    def can_handle(self, card_ids: frozenset[str], target_format: str) -> bool:
        """接受任意非空卡片集合和 markdown 目标格式。"""
        return len(card_ids) > 0 and target_format == "markdown"

    def export(self, card_ids: frozenset[str], output_path: Path, **options: Any) -> ExportResult:
        """将卡片 ID 集合渲染为 Markdown 并写入 output_path。

        真实实现应从 library_service 读取卡片；此处使用 fake 元数据。
        """
        if not card_ids:
            return ExportResult(
                success=False,
                output_path=output_path,
                format=self.export_format,
                card_count=0,
                errors=("card_ids 为空",),
            )

        lines = [
            "# MindForge Export",
            "",
            f"导出时间: {datetime.now(timezone.utc).isoformat()}",
            f"格式: {self.export_format}",
            f"适配器: {self.name}",
            f"卡片数量: {len(card_ids)}",
            "",
            "## 卡片列表",
            "",
        ]
        for cid in sorted(card_ids):
            lines.append(f"- {cid}")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            return ExportResult(
                success=False,
                output_path=output_path,
                format=self.export_format,
                card_count=len(card_ids),
                errors=(f"写入失败: {exc}",),
            )

        return ExportResult(
            success=True,
            output_path=output_path,
            format=self.export_format,
            card_count=len(card_ids),
        )

    def capabilities(self) -> frozenset[str]:
        return frozenset({"local_file", "fake_safe", "dry_run", "read_only"})
