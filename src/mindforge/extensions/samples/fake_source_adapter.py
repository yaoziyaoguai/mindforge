"""示例 Fake Source Adapter — 演示 ExtensionManifest + SourceAdapter 自注册模式。

本适配器完全基于内存中的 fake 数据，不读取文件系统、不访问网络、
不调用 LLM、不需要 API key。用于:
- 演示 SourceAdapter 端口的标准实现方式
- 展示 ExtensionManifest 如何与适配器关联
- 作为 dogfood scenario 的可控数据源
"""

from __future__ import annotations

from pathlib import Path

from mindforge.extensions.manifest import (
    Capability,
    ExtensionManifest,
    ExtensionType,
    RiskLevel,
)
from mindforge.sources.adapter_result import AdapterResult
from mindforge.sources.base import SourceDocument
from mindforge.sources.source_adapter import SourceAdapter

# ── Manifest ──────────────────────────────────────────────

FAKE_SOURCE_MANIFEST = ExtensionManifest(
    name="fake_source_sample",
    version="1.0.0",
    description="内存 fake 数据源适配器，用于演示扩展边界和 dogfood 场景",
    extension_type=ExtensionType.SOURCE_ADAPTER,
    capabilities=frozenset({
        Capability.LOCAL_FILE,
        Capability.FAKE_SAFE,
        Capability.DRY_RUN,
        Capability.READ_ONLY,
    }),
    risk_level=RiskLevel.LOW,
    requires_approval=False,
    entry_point="mindforge.extensions.samples.fake_source_adapter.FakeSourceAdapter",
    author="MindForge",
)


# ── Adapter ───────────────────────────────────────────────

class FakeSourceAdapter(SourceAdapter):
    """Fake 数据源适配器 — 仅用于演示和测试。

    不读取任何真实文件，所有 load() 调用从内存中的 fake 数据构造
    AdapterResult，确保:
    - 确定性输出（相同输入始终返回相同结果）
    - 零副作用（不写文件、不发网络请求）
    - 无密钥依赖
    """

    name = "fake_source_sample"
    source_type = "fake"

    def can_handle(self, path: Path) -> bool:
        """仅处理以 .fake.md 结尾或以 fake_ 开头的虚拟路径。"""
        return path.name.endswith(".fake.md") or path.name.startswith("fake_")

    def load(self, path: Path) -> AdapterResult:
        """从内存 fake 数据构造 AdapterResult。

        真实实现应解析文件内容；此处返回固定的示例数据以演示接口契约。
        """
        content_hash = f"fake_{hash(path.name) & 0xFFFFFFFF:08x}"
        source_id = f"fake_{path.name}"

        fake_body = (
            f"# Fake Source: {path.name}\n\n"
            "这是 fake 数据源适配器生成的示例内容。\n"
            "用于演示 SourceAdapter 端口边界的标准实现模式。\n"
        )

        document = SourceDocument(
            source_id=source_id,
            source_path=str(path),
            source_type=self.source_type,
            title=f"Fake: {path.stem}",
            raw_text=fake_body,
            content_hash=content_hash,
            adapter_name=self.name,
            tags=[],
        )

        return AdapterResult(
            status="loaded",
            document=document,
            warnings=[],
        )

    def capabilities(self) -> frozenset[str]:
        """声明能力标签 — 与 FAKE_SOURCE_MANIFEST.capabilities 保持同步。"""
        return frozenset({"local_file", "fake_safe", "dry_run", "read_only"})
